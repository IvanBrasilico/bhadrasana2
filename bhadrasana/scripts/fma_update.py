import os
import sys

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from collections import defaultdict
from datetime import datetime, timedelta

import click
import requests
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from ajna_commons.flask.log import logger
from bhadrasana.models.ovr import OVR, Recinto
from bhadrasana.models.virasana_manager import get_conhecimento

DTE_USERNAME = os.environ.get('DTE_USERNAME')
DTE_PASSWORD = os.environ.get('DTE_PASSWORD')

if DTE_PASSWORD is None:
    dte_file = os.path.join(os.path.dirname(__file__), 'dte.info')
    with open(dte_file) as dte_info:
        linha = dte_info.readline()
    DTE_USERNAME = linha.split(',')[0]
    DTE_PASSWORD = linha.split(',')[1]

# DTE_URL_AUTH = 'https://jupapi.org.br/api/sepes/Pesagem/token'
# DTE_URL_FMA = 'https://jupapi.org.br/api/sepes/ConsultaFMA'

DTE_URL_AUTH = \
    'https://www.janelaunicaportuaria.org.br/ws_homologacao/sepes/api/Pesagem/token'
DTE_URL_FMA = \
    'https://www.janelaunicaportuaria.org.br/ws_homologacao/sepes/api/ConsultaFMA'


def get_token_dte(username=DTE_USERNAME, password=DTE_PASSWORD):
    data = {'username': username, 'password': password, 'grant_type': 'password'}
    try:
        r = requests.post(DTE_URL_AUTH, data=data)
        print(r.url)
        token = r.json().get('access_token')
    except Exception as err:
        logger.error(str(type(err)) + str(err))
        logger.error(r.status_code)
        logger.error(r.text)
        raise err
    return token


def get_lista_fma(start, end, cod_recinto, token):
    payload = {'data_inicio': datetime.strftime(start, '%Y-%m-%d'),
               'data_fim': datetime.strftime(end, '%Y-%m-%d'),
               'cod_recinto': cod_recinto}
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.get(DTE_URL_FMA, headers=headers, params=payload)
    logger.info('get_fma_dte ' + r.url)
    try:
        lista_fma = r.json()['JUP_WS']['FMA_Eletronica']['Lista_FMA']
    except Exception as err:
        logger.error(str(type(err)) + str(err))
        logger.error(r.status_code)
        logger.error(r.text)
        return None
    return lista_fma


def get_lista_fma_recintos(recintos_list, datainicial, datafinal):
    token = get_token_dte()
    fmas_recintos = defaultdict(list)
    for recinto in recintos_list:
        recinto = recinto.cod_dte
        lista_fma = get_lista_fma(datainicial, datafinal,
                                  recinto, token)
        if lista_fma and len(lista_fma) > 0:
            logger.info('%s: %s FMAs baixadas do recinto %s' %
                        (datainicial, len(lista_fma), recinto))
            fmas_recintos[recinto].extend(lista_fma)
    return fmas_recintos


def processa_fma(session, fma: dict):
    ovr = session.query(OVR).filter(
        OVR.numero == fma['Numero_FMA']
    ).filter(
        OVR.recinto_id == int(fma['Cod_Recinto'])
    ).filter(
        OVR.ano == fma['Ano_FMA']
    ).first()
    if ovr is not None:
        logger.info('FMA %s - %s já existente, pulando... ' %
                    (fma['Cod_Recinto'], fma['Numero_FMA']))
        return
    ovr = OVR()
    ovr.numero = fma['Numero_FMA']
    ovr.ano = fma['Ano_FMA']
    try:
        ovr.datahora = datetime.strptime(fma['Data_Emissao'], '%Y-%m-%d')
    except Exception as err:
        print(err)
        ovr.datahora = datetime.now()
    try:
        ovr.dataentrada = datetime.strptime(fma['Data_Entrada_Recinto'], '%Y-%m-%d')
    except Exception as err:
        print(err)
        ovr.dataentrada = ovr.datahora - timedelta(days=90)
    ovr.recinto_id = int(fma['Cod_Recinto'])
    ovr.setor_id = 4  # EQMAB
    ovr.numeroCEmercante = fma['CE_Mercante']
    try:
        conhecimento = get_conhecimento(session,
                                        ovr.numeroCEmercante)
        if conhecimento:
            ovr.cnpj_fiscalizado = conhecimento.consignatario
    except Exception as err:
        logger.error(str(err), exc_info=True)
    ovr.tipooperacao = 0
    ovr.fase = 0
    ovr.tipoevento_id = 30
    try:
        session.add(ovr)
        logger.info('Inserindo OVR Recinto %s Numero %s ' %
                    (fma['Cod_Recinto'], fma['Numero_FMA']))
        session.commit()
    except Exception as err:
        print(err)
        session.rollback()


def processa_lista_fma(session, lista_recintos_fmas):
    # print(lista_recintos_fmas)
    for recinto, lista_fma in lista_recintos_fmas.items():
        # print(recinto, lista_fma)
        for fma in lista_fma:
            processa_fma(session, fma)


@click.command()
@click.option('--sql_uri', default='mysql+pymysql://ivan@localhost:3306/mercante',
              help='Hoje')
@click.option('--inicio', default=None,
              help='Dia de início (dia/mês/ano) - padrão data da última FMA')
@click.option('--fim', default=None,
              help='Hoje')
def update(sql_uri, inicio, fim):
    engine = create_engine(sql_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    if inicio is None:
        qry = session.query(func.max(OVR.datahora).label('last_date')
                            ).filter(OVR.tipooperacao == 0)
        res = qry.one()
        last_date = res.last_date
        if last_date > datetime.today():
            logger.warning(f'Data de inicio no banco está no futuro : {last_date} !!!')
            last_date = datetime.today()
        start = last_date - timedelta(days=14)
    else:
        start = datetime.strptime(inicio, '%d/%m/%Y')
    if fim is None:
        end = datetime.today()
    else:
        end = datetime.strptime(fim, '%d/%m/%Y')
    print(start, end)
    # recinto = Recinto()
    # recinto.cod_dte = 22
    # recintos_list = [recinto]
    recintos_list = session.query(Recinto).filter(Recinto.cod_dte.isnot(None)).all()
    lista_recintos_fmas = get_lista_fma_recintos(recintos_list, start, end)
    processa_lista_fma(session, lista_recintos_fmas)
    update_cnpj_fiscalizado_historico(session)


def update_cnpj_fiscalizado_historico(session):
    ovrs_list = session.query(OVR).filter(
        OVR.numeroCEmercante.isnot(None)
    ).filter(
        OVR.cnpj_fiscalizado.is_(None)
    ).all()
    for ovr in ovrs_list:
        try:
            conhecimento = get_conhecimento(session,
                                            ovr.numeroCEmercante)
            if conhecimento:
                ovr.cnpj_fiscalizado = conhecimento.consignatario
            session.add(ovr)
        except Exception as err:
            logger.error(str(err), exc_info=True)
    session.commit()


if __name__ == '__main__':  # pragma: no cover
    print('P/ rodar automático, crie arquivo como abaixo em /etc/cron.daily/fma_update.sh')
    print('/home/ivan/ajna/bhadrasana2/bhadrasana-venv/bin/'
          'python bhadrasana/scripts/fma_update.py '
          ' --sql_uri mysql+pymysql://<uri do banco SQL do Fichas> '
          ' >> /var/log/bhadrasana2/fma_error.log 2>&1')
    update()
