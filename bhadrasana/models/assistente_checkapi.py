import json
from datetime import datetime

import numpy as np
import pandas as pd
from dateutil import parser


def converte_datetime(str_datetime: str):
    return parser.isoparse(str_datetime).replace(tzinfo=None).replace(microsecond=0)
    # return datetime.datetime.fromisoformat(str_datetime)
    # return datetime.datetime.strptime(str_datetime, '%Y-%m-%dT%H:%M:%S.000-%Z')


def get_campos_gate(evento):
    campos = {}
    campos['dataHoraTransmissao'] = converte_datetime(evento['dadosTransmissao']['dataHoraTransmissao'])
    sub_evento = evento['jsonOriginal']
    campos['dataHoraOcorrencia'] = converte_datetime(sub_evento['dataHoraOcorrencia'])
    campos['direcao'] = sub_evento['direcao']
    campos['placa'] = sub_evento['placa']
    try:
        campos['container'] = sub_evento['listaConteineresUld'][0]['numeroConteiner']
    except:
        campos['container'] = None
    return campos


depara_campos = {'dataHoraOcorrencia': 'dataHoraOcorrencia', 'NúmeroContêiner': 'container'}


def compara_linha(linha_api, linha_fisico) -> list:  # Retorna texto com as diferenças
    diferencas = []
    for campo_fisico, campo_api in depara_campos.items():
        val_fisico = linha_fisico[1][campo_fisico]
        val_api = linha_api[campo_api].iloc[0]
        if val_fisico != val_api:
            diferencas.append(f'{campo_fisico} diferente. Checagem física: {val_fisico} Conteúdo API: {val_api}')
    return diferencas


def get_eventos_fisico(planilha):
    lfilename = planilha.filename
    df = pd.read_excel(planilha, engine='openpyxl', header=1)
    return df.replace({np.nan: None})


def get_eventos_api(stream):
    return json.loads(stream.read())


def processa_auditoria(planilha, stream_json):
    eventos_fisico = get_eventos_fisico(planilha)
    eventos_fisico['dataHoraOcorrencia'] = eventos_fisico.apply(
        lambda x: datetime.combine(x['Data'], x['Hora']), axis=1)
    json_raw = get_eventos_api(stream_json)
    eventos = [get_campos_gate(evento) for evento in json_raw]
    eventos_api = pd.DataFrame(eventos)
    placas_nao_encontradas = eventos_fisico[~ eventos_fisico['PlacaVeiculo'].isin(eventos_api['placa'])]
    placas_encontradas = eventos_fisico[eventos_fisico['PlacaVeiculo'].isin(eventos_api['placa'])]
    linhas_divergentes = []
    for linha_fisico in placas_encontradas.iterrows():
        linha_api = eventos_api[eventos_api['placa'] == linha_fisico[1]['PlacaVeiculo']]
        diferencas = compara_linha(linha_api, linha_fisico)
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
