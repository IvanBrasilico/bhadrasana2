import csv
import os
from collections import defaultdict
from datetime import datetime

import requests

from ajna_commons.flask.log import logger
from bhadrasana.models.ovr import OVR

DTE_USERNAME = os.environ.get('DTE_USERNAME')
DTE_PASSWORD = os.environ.get('DTE_PASSWORD')

if DTE_PASSWORD is None:
    dte_file = os.path.join(os.path.dirname(__file__), 'dte.info')
    with open(dte_file) as dte_info:
        linha = dte_info.readline()
    DTE_USERNAME = linha.split(',')[0]
    DTE_PASSWORD = linha.split(',')[1]

try:
    recintos_file = os.path.join(os.path.dirname(__file__), 'recintos.csv')
    with open(recintos_file, encoding='utf-8') as csv_in:
        reader = csv.reader(csv_in)
        recintos_list = [row for row in reader]
except FileNotFoundError:
    recintos_list = []

DTE_TOKEN = 'https://jupapi.org.br/api/sepes/Pesagem/token'
DTE_URL_FMA = 'https://jupapi.org.br/api/sepes/PesagemMovimentacao'


def get_token_dte(username=DTE_USERNAME, password=DTE_PASSWORD):
    data = {'username': username, 'password': password, 'grant_type': 'password'}
    r = requests.post(DTE_TOKEN, data=data, verify=False)
    print(r.url)
    print(r.text)
    print(r.status_code)
    token = r.json().get('access_token')
    return token


def get_lista_fma(start, end, cod_recinto, token):
    payload = {'data_inicio': datetime.strftime(start, '%Y-%m-%d'),
               'data_fim': datetime.strftime(end, '%Y-%m-%d'),
               'cod_recinto': cod_recinto}
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.get(DTE_URL_FMA, headers=headers, params=payload)
    logger.debug('get_pesagens_dte ' + r.url)
    try:
        lista_fma = r.json()['JUP_WS']['FMA_Eletronica']['Lista_FMA']
    except:
        logger.error(r, r.text)
    return lista_fma


def get_lista_fma_recintos(recintos_list, datainicial, datafinal):
    token = get_token_dte()
    fmas_recintos = defaultdict(list)
    for linha in recintos_list[1:]:
        recinto = linha[0]
        lista_fma = get_lista_fma(datainicial, datafinal,
                                  recinto, token)
        if lista_fma and len(lista_fma) > 0:
            logger.info('%s: %s FMAs baixadas do recinto %s' %
                        (datainicial, len(lista_fma), recinto))
            fmas_recintos[recinto].extend(lista_fma)
    return fmas_recintos


def processa_fma(fma: dict):
    ovr = session.query(OVR).filter(
        OVR.numero == fma['Numero_FMA'] & OVR.recinto_id == int(fma['Cod_Recinto'])
    ).one_or_none()
    if ovr is not None:
        logger.info('FMA %s - %s já existente, pulando... ' %
                    (fma['Cod_Recinto'], fma['Numero_FMA']))
        return
    ovr = OVR()
    ovr.numero = fma['Numero_FMA']
    ovr.ano = fma['Ano_FMA']
    ovr.datahora = datetime.strptime(fma['Data_Emissao'], '%Y-%m-%d')
    ovr.recinto_id = int(fma['Cod_Recinto'])
    ovr.numeroCEmercante = fma['CE_Mercante']
    ovr.tipooperacao = 0
    ovr.fase = 0
    ovr.tipoevento_id = 1
    try:
        session.add(ovr)
        session.commit()
    except Exception as err:
        print(err)
        session.rollback()


def processa_lista_fma(lista_recintos_fmas):
    for recinto, lista_fma in lista_recintos_fmas:
        for fma in lista_fma:
            processa_fma(fma)


if __name__ == '__main__':  # pragma: no cover
    import sys
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker

    if len(sys.argv) == 1:
        sys.exit('Informar endereço do MySQL')
    engine = create_engine(sys.argv[1])
    Session = sessionmaker(bind=engine)
    session = Session()

    print('Adquirindo FMAs')
    qry = session.query(func.max(OVR.datahora).label("last_date"))
    res = qry.one()
    start = res.last_date
    end = datetime.today()
    print(start, end)
    lista_recintos_fmas = get_lista_fma_recintos(recintos_list, start, end)
    processa_lista_fma(lista_recintos_fmas)
