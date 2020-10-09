import unicodedata
import warnings
from datetime import datetime
from threading import Thread
from typing import Tuple

warnings.simplefilter('ignore')
import pandas as pd
import requests

from ajna_commons.flask.log import logger

# AJNA_API_URL = 'https://ajna.labin.rf08.srf/ajnaapi/api'
AJNA_API_URL = 'http://localhost:5004/api'
try:
    with open('bhadrasana2_password.txt') as pwd_in:
        bhadrasana2_password = pwd_in.read()
except FileNotFoundError:
    bhadrasana2_password = ''  # nosec

mapa_SBT = {'dataevento': ['dtHrOcorrencia', 'dtHrRegistro'],
            'Conteiner': {'listaContainersUld': 'num'},
            'Tipo conteiner': {'listaContainersUld': 'tipo'},
            'Motorista': 'motorista_nome',
            'CPF': 'motorista_cpf',
            'Transportadora': 'nmTransportador',
            'Cnpj': 'cnpjTransportador',
            'Navio': {'listaContainersUld': 'imoNavio'},
            'Porto descarga': {'listaContainersUld': 'portoDescarga'},
            'Porto final': {'listaContainersUld': 'destinoCarga'},
            # Provisório
            'Login': 'login',
            'Mercadoria': 'mercadoria'
            }

mapa_BTP = {'dataevento': ['dtHrOcorrencia', 'dtHrRegistro'],
            'Conteiner': {'listaContainersUld': 'num'},
            'Iso Code': {'listaContainersUld': 'tipo'},
            'CNPJ Transportadora': 'cnpjTransportador',
            'Transportadora': 'nmtransportador',
            'Nome Motorista': 'motorista_nome',
            'Cpf Motorista': 'motorista_cpf',
            'Navio Embarque': {'listaContainersUld': 'imoNavio'},
            'Porto Descarga': {'listaContainersUld': 'portoDescarga'},
            'Porto Destino Final': {'listaContainersUld': 'destinoCarga'},
            # Provisório
            'Nome Operador Scanner': 'login',
            'Descricao Ncm': 'mercadoria'
            }


def ascii_sanitizar(text):
    """Remove marcas de diacríticos (acentos e caracteres especiais).

    Retorna NFC normalizado ASCII
    """
    if not text:
        return None
    return unicodedata.normalize('NFKD', text) \
        .encode('ASCII', 'ignore') \
        .decode('ASCII')


def convert_data_toiso(data):
    try:
        data = datetime.strptime(data, '%d/%m/%Y %H:%M:%S')
    except ValueError:
        data = datetime.strptime(data, '%d/%m/%Y')
    return data.isoformat()


def processa_planilha_SBT(filename):
    df = pd.read_excel(filename, engine='odf')
    df['dataevento'] = df['Data hora entrada'].apply(convert_data_toiso)
    return df


def processa_planilha_BTP(filename):
    df_BTP = pd.read_excel(filename)
    df_BTP.columns = [ascii_sanitizar(col) for col in df_BTP.columns]
    df_BTP['Entrada Carreta'] = df_BTP['Entrada Carreta'].fillna(method='ffill'). \
        fillna(method='bfill')
    df_BTP['CNPJ Transportadora'] = df_BTP['CNPJ Transportadora'].fillna(method='ffill')
    df_BTP['Entrada Carreta'] = df_BTP['Entrada Carreta'].astype(str)
    df_BTP['dataevento'] = df_BTP['Entrada Carreta'].apply(convert_data_toiso)
    df_BTP['CNPJ Transportadora'] = \
        df_BTP['CNPJ Transportadora'].apply(lambda x: '{:014.0f}'.format(x))
    df_BTP['Cpf Motorista'] = \
        df_BTP['Cpf Motorista'].apply(lambda x: '{:011.0f}'.format(x))
    df_BTP = df_BTP.fillna('')
    return df_BTP


def get_login_headers():
    rv = requests.post(AJNA_API_URL + '/login',
                       json={'username': 'bhadrasana2', 'password': bhadrasana2_password},
                       verify=False)
    if rv.status_code != 200:
        raise Exception(str(rv.status_code) + rv.text)
    token = rv.json().get('access_token')
    headers = {'Authorization': 'Bearer ' + token}
    return headers


def update_destino(destino, key, valor):
    if isinstance(key, str):
        destino[key] = valor
    elif isinstance(key, list):
        for k in key:
            destino[k] = valor
    elif isinstance(key, dict):
        for subk, subv in key.items():
            subdestino = destino.get(subk)
            if subdestino is None:
                subdestino = {}
                destino[subk] = subdestino
            update_destino(subdestino, subv, valor)


def upload_eventos(recinto: str, mapa: dict, df: pd.DataFrame, headers: dict) -> int:
    count = 0
    for index, row in list(df.iterrows()):
        destino = {'idEvento': hash(recinto + row['dataevento']),
                   'cpfOperOcor': '00000000000',
                   'cpfOperReg': '00000000000',
                   'recinto': recinto,
                   'protocoloEventoRetifCanc': None,
                   'contingencia': False,
                   'codRecintoDestino': 0}
        for key_origem, key_destino in mapa.items():
            update_destino(destino, key_destino, row[key_origem])
        destino['cnpjTransportador'] = destino['cnpjTransportador'] \
            .replace('/', '').replace('.', '').replace('-', '')
        destino['listaContainersUld'] = [destino['listaContainersUld']]
        rv = requests.post(AJNA_API_URL + '/acessoveiculo', json=destino,
                           headers=headers, verify=False)
        if rv.status_code == 201:
            count += 1
        else:
            logger.error(destino)
            logger.error(rv.status_code, rv.text)
    return count


def processa_planilha(filename) -> Tuple[bool, str]:
    """Recebe nome de arquivo, processa, retorna False se ocorreram erros.
    """

    def threaded_upload(recinto, mapa, df):
        headers = get_login_headers()
        count = upload_eventos(recinto, mapa, df, headers)
        logger.info('{} processados de {:d} linhas na planilha {}'.format(
            count, len(df), filename))

    if 'BTP' in filename:
        recinto = 'BTP'
        mapa = mapa_BTP
        funcao_processamento = processa_planilha_BTP
    else:
        recinto = 'SBT'
        mapa = mapa_SBT
        funcao_processamento = processa_planilha_SBT
    df = []
    try:
        df = funcao_processamento(filename)
        thread = Thread(target=threaded_upload, args=(recinto, mapa, df))
        thread.daemon = True
        thread.start()
        return True, str(len(df))
    except Exception as err:
        logger.error(err, exc_info=True)
        return False, str(err)
