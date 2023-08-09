import base64
import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import Tuple

import numpy as np
import pandas as pd
from PIL import Image
from dateutil import parser


def converte_datetime(str_datetime: str):
    return parser.isoparse(str_datetime).replace(tzinfo=None).replace(microsecond=0)
    # return datetime.datetime.fromisoformat(str_datetime)
    # return datetime.datetime.strptime(str_datetime, '%Y-%m-%dT%H:%M:%S.000-%Z')


def converte_cpf(campo_cpf):
    if not isinstance(campo_cpf, str):
        campo_cpf = str(int(campo_cpf))
    if campo_cpf.strip() == '':
        return ''
    campo_cpf = campo_cpf.zfill(11)
    return campo_cpf


def get_campos_comum(evento) -> Tuple[dict, dict]:
    campos = {}
    campos['dataHoraTransmissao'] = converte_datetime(evento['dadosTransmissao']['dataHoraTransmissao'])
    sub_evento = evento['jsonOriginal']
    campos['dataHoraOcorrencia'] = converte_datetime(sub_evento['dataHoraOcorrencia'])
    return campos, sub_evento


def get_campos_gate(evento) -> dict:
    campos, sub_evento = get_campos_comum(evento)
    campos['operacao'] = sub_evento['operacao']  # G - A*g*endamento C - A*c*esso  -> Filtrar acesso
    campos['direcao'] = sub_evento['direcao']
    campos['placa'] = letras_e_numeros(sub_evento['placa'])
    campos['ocrPlaca'] = sub_evento['ocrPlaca']
    try:
        campos['numeroConteiner'] = letras_e_numeros(sub_evento['listaConteineresUld'][0]['numeroConteiner'])
    except:
        campos['numeroConteiner'] = None
    try:
        campos['motorista.cpf'] = converte_cpf(sub_evento['motorista']['cpf'])
    except:
        campos['motorista.cpf'] = None
    return campos


def get_campos_pesagem(evento) -> dict:
    campos, sub_evento = get_campos_comum(evento)
    campos['placa'] = letras_e_numeros(sub_evento['placa'])
    # campos['ocrPlaca'] = sub_evento['ocrPlaca'] ERRO??? (não tem ocrPlaca no Evento??)
    # print(evento)
    # print(sub_evento)
    campos['tara'] = sub_evento.get('taraConjunto', 'Campo não existente!')
    campos['capturaAutoPeso'] = sub_evento['capturaAutoPeso']
    campos['pesoBrutoManifesto'] = sub_evento.get('pesoBrutoManifesto', 'Campo não existente!')
    campos['pesoBrutoBalanca'] = sub_evento.get('pesoBrutoBalanca', 'Campo não existente!')
    try:
        campos['numeroConteiner'] = letras_e_numeros(sub_evento['listaConteineresUld'][0]['numeroConteiner'])
    except:
        campos['numeroConteiner'] = None
    try:
        campos['placaReboque'] = letras_e_numeros(sub_evento['listaSemirreboque'][0]['placa'])
    except:
        campos['placaReboque'] = None
    return campos


def letras_e_numeros(texto: str):
    return ''.join([c for c in texto if c.isalpha() or c.isnumeric()])


def get_campos_inspecaonaoinvasiva(evento) -> dict:
    campos, sub_evento = get_campos_comum(evento)
    try:
        campos['placa'] = letras_e_numeros(sub_evento['placa'])
    except:
        campos['placa'] = None
    try:
        campos['numeroConteiner'] = letras_e_numeros(sub_evento['listaConteineresUld'][0]['numeroConteiner'])
    except:
        campos['numeroConteiner'] = None
    try:
        campos['dataHoraScaneamento'] = converte_datetime(sub_evento['imagemScanner']['dataHoraScaneamento'])
    except:
        campos['dataHoraScaneamento'] = None
    try:
        campos['arquivoImagem'] = sub_evento['imagemScanner']['arquivoImagem']
    except:
        campos['arquivoImagem'] = None
    return campos


_depara_campos = {
    'AgendamentoAcessoVeiculo':
        {'dataHoraOcorrencia': 'dataHoraOcorrencia', 'NúmeroContêiner': 'numeroConteiner',
         'CPF': 'motorista.cpf', 'OCR': 'ocrPlaca'},
    'PesagemVeiculo':
        {'dataHoraOcorrencia': 'dataHoraOcorrencia', 'NúmeroContêiner': 'numeroConteiner',
         'Peso': 'pesoBrutoBalanca'},
    'InspecaoNaoInvasiva':
        {'dataHoraOcorrencia': 'dataHoraOcorrencia', 'NúmeroContêiner': 'numeroConteiner',
         'dataHoraScaneamento': 'dataHoraScaneamento'},
}


def campos_sao_diferentes(val_fisico, val_api):
    if isinstance(val_fisico, datetime):
        dif = val_api - val_fisico
        return dif.total_seconds() > 300  # Datas com diferenca de 5 minutos
    else:
        if isinstance(val_fisico, str):
            if str(val_fisico).strip() == '':  # Ignora campo vazio
                return False
        return val_fisico != val_api


def compara_linha(linhas_api, linha_fisico, depara_campos: dict) -> list:  # Retorna texto com as diferenças
    diferencas = []
    # Código precisa comparar várias linhas,
    # pois placa pode ter passado várias vezes no período
    # Filtrar por data ocorrência mais próxima
    linha_api = linhas_api[linhas_api['dataHoraOcorrencia'].between(
        linha_fisico[1]['dataHoraOcorrencia'] - timedelta(hours=0, minutes=50),
        linha_fisico[1]['dataHoraOcorrencia'] + timedelta(hours=0, minutes=50),
    )]
    if len(linha_api) == 0:
        return ['Não encontrado registro no intervalo de 50 minutos antes e depois!']
    for campo_fisico, campo_api in depara_campos.items():
        val_fisico = linha_fisico[1][campo_fisico]
        val_api = linha_api[campo_api].iloc[0]
        diferente = campos_sao_diferentes(val_fisico, val_api)
        if diferente:
            diferencas.append(f'{campo_fisico} diferente. Checagem física: {val_fisico} Conteúdo API: {val_api}')
    return diferencas


def get_eventos_fisico(planilha):
    # lfilename = planilha.filename
    df = pd.read_excel(planilha, engine='openpyxl', header=0)
    # print(len(df))
    df = df[~df['Data'].isna()]
    # print(len(df))
    df = df.replace({np.nan: ''})
    if 'CPF' in df.columns:
        df['CPF'] = df['CPF'].apply(converte_cpf)
    for column_name in df.columns:
        if 'placa' in column_name.lower() or 'contêiner' in column_name.lower():
            df[column_name] = df[column_name].apply(letras_e_numeros)
    return df


def get_eventos_api(stream):
    return json.loads(stream.read())


def checa_imagens(eventos_api):
    contador = 0
    largura_total = 0
    altura_total = 0
    for row in eventos_api.iterrows():
        imagem_base64 = row[1]['arquivoImagem']
        im = Image.open(BytesIO(base64.b64decode(imagem_base64)))
        print(row[1]['numeroConteiner'], im.size)
        if im.size[1] < 800:
            contador += 1
        largura_total += im.size[0]
        altura_total += im.size[1]
    total_imagens = len(eventos_api)
    largura_media = largura_total // total_imagens
    altura_media = altura_total // total_imagens
    return f'Observação: arquivo possui {contador} imagens com menos de 800 linhas,' \
           f' de um total de {total_imagens} imagens. ' \
           f'Média de resoluçao: ({largura_media} x {altura_media}).'


def processa_auditoria(planilha, stream_json, evento_nome: str):
    _get_campos = {'AgendamentoAcessoVeiculo': get_campos_gate,
                   'PesagemVeiculo': get_campos_pesagem,
                   'InspecaoNaoInvasiva': get_campos_inspecaonaoinvasiva}
    eventos_fisico = get_eventos_fisico(planilha)
    print('#####################--- eventos_fisico')
    print(eventos_fisico.head())
    eventos_fisico['dataHoraOcorrencia'] = eventos_fisico.apply(lambda x: datetime.combine(x['Data'], x['Hora']),
                                                                axis=1)
    json_raw = get_eventos_api(stream_json)
    eventos = [_get_campos[evento_nome](evento) for evento in json_raw]
    eventos_api = pd.DataFrame(eventos)
    chave_api = 'placa'
    chave_fisico = 'PlacaVeiculo'
    if evento_nome == 'AgendamentoAcessoVeiculo':  # Filtrar somente Eventos tipo 'C' de A*c*esso
        eventos_api = eventos_api[eventos_api['operacao'] == 'C']
    if evento_nome == 'InspecaoNaoInvasiva':  # Copiar data da ocorrência para data do escaneamento
        eventos_fisico['dataHoraScaneamento'] = eventos_fisico['dataHoraOcorrencia']
        chave_api = 'numeroConteiner'
        chave_fisico = 'NúmeroContêiner'
    print('#####################--- eventos_api')
    print(eventos_api.head())
    placas_nao_encontradas = eventos_fisico[~ eventos_fisico[chave_fisico].isin(eventos_api[chave_api])]
    placas_encontradas = eventos_fisico[eventos_fisico[chave_fisico].isin(eventos_api[chave_api])]
    api_filtrado = eventos_api[eventos_api[chave_api].isin(eventos_fisico[chave_fisico])]
    print('#####################--- placas_encontradas')
    print(placas_encontradas.head())
    print('#####################--- placas_nao_encontradas')
    print(placas_nao_encontradas.head())
    print(placas_nao_encontradas[chave_fisico].values)
    linhas_divergentes = []
    for linha_fisico in placas_encontradas.iterrows():
        linha_api = eventos_api[eventos_api[chave_api] == linha_fisico[1][chave_fisico]]
        if evento_nome == 'AgendamentoAcessoVeiculo':  # Filtrar também por sentido
            linha_api = linha_api[eventos_api['direcao'] == linha_fisico[1]['FluxoOperacional']]
        diferencas = compara_linha(linha_api, linha_fisico, _depara_campos[evento_nome])
        if len(diferencas) > 0:
            descricao = f'Linha: {linha_fisico[0]} {chave_fisico}: ' + linha_fisico[1][chave_fisico] + ' | '
            descricao = descricao + '; '.join(diferencas)
            linhas_divergentes.append(descricao)
    chaves_nao_encontradas = [chave for chave in placas_nao_encontradas[chave_fisico].values if isinstance(chave, str)]
    mensagens = [
        f'Eventos físicos foram coletados de {eventos_fisico.dataHoraOcorrencia.min()} ' + \
        f'a {eventos_fisico.dataHoraOcorrencia.max()}',
        f'Eventos extraídos baixados desde   {eventos_api.dataHoraOcorrencia.min()} a ' + \
        f'{eventos_api.dataHoraOcorrencia.max()}',
        f'NÃO foram encontradas {len(placas_nao_encontradas)} de {len(eventos_fisico)} chaves {chave_fisico}: ' + \
        ', '.join(chaves_nao_encontradas),
        f'Campos conferidos no arquivo JSON: {list(_depara_campos[evento_nome].values())}',
        'Obs: deixe o campo em branco na planilha para ignorar a checagem deste'
    ]
    if evento_nome == 'InspecaoNaoInvasiva':  # Verificar imagens
        erros_imagens = checa_imagens(eventos_api)
        mensagens.append(erros_imagens)
    return eventos_fisico, api_filtrado, mensagens, linhas_divergentes
