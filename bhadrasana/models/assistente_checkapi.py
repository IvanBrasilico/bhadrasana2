import json
from datetime import datetime

import numpy as np
import pandas as pd
from dateutil import parser


def converte_datetime(str_datetime: str):
    return parser.isoparse(str_datetime).replace(tzinfo=None).replace(microsecond=0)
    # return datetime.datetime.fromisoformat(str_datetime)
    # return datetime.datetime.strptime(str_datetime, '%Y-%m-%dT%H:%M:%S.000-%Z')



def get_campos_comum(evento):
    campos = {}
    campos['dataHoraTransmissao'] = converte_datetime(evento['dadosTransmissao']['dataHoraTransmissao'])
    sub_evento = evento['jsonOriginal']
    campos['dataHoraOcorrencia'] = converte_datetime(sub_evento['dataHoraOcorrencia'])
    return campos, sub_evento

def get_campos_gate(evento):
    campos, sub_evento = get_campos_comum(evento)
    campos['operacao'] = sub_evento['operacao'] # G - A*g*endamento C - A*c*esso  -> Filtrar acesso
    campos['direcao'] = sub_evento['direcao']
    campos['placa'] = sub_evento['placa']
    campos['ocrPlaca'] = sub_evento['ocrPlaca']
    try:
        campos['container'] = sub_evento['listaConteineresUld'][0]['numeroConteiner']
    except:
        campos['container'] = None
    try:
        campos['motorista.cpf'] = sub_evento['motorista']['cpf']
    except:
        campos['motorista.cpf'] = None
    return campos


def get_campos_pesagem(evento):
    campos, sub_evento = get_campos_comum(evento)
    campos['placa'] = sub_evento['placa']
    # campos['ocrPlaca'] = sub_evento['ocrPlaca'] ERRO??? (não tem ocrPlaca no Evento??)
    campos['tara'] = sub_evento['tara']
    campos['capturaAutoPeso'] = sub_evento['capturaAutoPeso']
    campos['pesoBrutoManifesto'] = sub_evento['pesoBrutoManifesto']
    campos['pesoBrutoBalanca'] = sub_evento['pesoBrutoBalanca']
    try:
        campos['container'] = sub_evento['listaConteineresUld'][0]['numeroConteiner']
    except:
        campos['container'] = None

_depara_campos = {
    'PesagemVeiculo':
        {'dataHoraOcorrencia': 'dataHoraOcorrencia', 'NúmeroContêiner': 'container',
         'Peso': 'pesoBrutoBalanca'},
    'AgendamentoAcessoVeiculo':
        {'dataHoraOcorrencia': 'dataHoraOcorrencia', 'NúmeroContêiner': 'container',
         'CPF': 'motorista.cpf', 'OCR': 'ocrPlaca'}
}

def campos_sao_diferentes(val_fisico, val_api):
    if isinstance(val_fisico, datetime):
        dif = val_api - val_fisico
        return dif.total_seconds() > 60
    else:
        return val_fisico != val_api

def compara_linha(linha_api, linha_fisico, depara_campos: dict) -> list:  # Retorna texto com as diferenças
    diferencas = []
    for campo_fisico, campo_api in depara_campos.items():
        val_fisico = linha_fisico[1][campo_fisico]
        val_api = linha_api[campo_api].iloc[0]

        if campos_sao_diferentes(val_fisico, val_api):
            diferencas.append(f'{campo_fisico} diferente. Checagem física: {val_fisico} Conteúdo API: {val_api}')
    return diferencas


def get_eventos_fisico(planilha):
    # lfilename = planilha.filename
    df = pd.read_excel(planilha, engine='openpyxl', header=0)
    print(len(df))
    df = df[~df['Data'].isna()]
    print(len(df))
    return df.replace({np.nan: None})


def get_eventos_api(stream):
    return json.loads(stream.read())


def monta_data(row):
    pass



def processa_auditoria(planilha, stream_json, evento_nome:str):
    _get_campos = {'AgendamentoAcessoVeiculo': get_campos_gate, 'PesagemVeiculo': get_campos_pesagem}
    eventos_fisico = get_eventos_fisico(planilha)
    print(eventos_fisico.head())
    eventos_fisico['dataHoraOcorrencia'] = eventos_fisico.apply(lambda x: datetime.combine(x['Data'], x['Hora']),
                                                                axis=1)
    json_raw = get_eventos_api(stream_json)
    eventos = [_get_campos[evento_nome](evento) for evento in json_raw]
    eventos_api = pd.DataFrame(eventos)
    if evento_nome == 'AgendamentoAcessoVeiculo':  # Filtrar somente Eventos tipo 'C' de A*c*esso
        eventos_api = eventos_api[eventos_api['operacao'] == 'C']
    placas_nao_encontradas = eventos_fisico[~ eventos_fisico['PlacaVeiculo'].isin(eventos_api['placa'])]
    placas_encontradas = eventos_fisico[eventos_fisico['PlacaVeiculo'].isin(eventos_api['placa'])]
    linhas_divergentes = []
    for linha_fisico in placas_encontradas.iterrows():
        linha_api = eventos_api[eventos_api['placa'] == linha_fisico[1]['PlacaVeiculo']]
        if evento_nome == 'AgendamentoAcessoVeiculo':  # Filtrar também por sentido
            linha_api = linha_api[eventos_api['direcao'] == linha_fisico[1]['FluxoOperacional']]
        diferencas = compara_linha(linha_api, linha_fisico, _depara_campos[evento_nome])
        if len(diferencas) > 0:
            descricao = f'Linha: {linha_fisico[0]} Placa: {linha_fisico[1]["PlacaVeiculo"]} | '
            descricao = descricao + '; '.join(diferencas)
            linhas_divergentes.append(descricao)
    mensagens = [
        f'Eventos físicos foram coletados de {eventos_fisico.dataHoraOcorrencia.min()} ' + \
        f'a {eventos_fisico.dataHoraOcorrencia.max()}',
        f'Eventos extraídos baixados desde   {eventos_api.dataHoraOcorrencia.min()} a ' + \
        f'{eventos_api.dataHoraOcorrencia.max()}',
        f'NÃO foram encontradas {len(placas_nao_encontradas)} de {len(eventos_fisico)} placas: ' + \
        ', '.join(list(placas_nao_encontradas['PlacaVeiculo'].values))
    ]
    return eventos_fisico, mensagens, linhas_divergentes
