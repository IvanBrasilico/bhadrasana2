import csv
import sys

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from datetime import datetime

import click
import requests

from ajna_commons.flask.log import logger

URL_AUTH = \
    'http://localhost:5004/ajnaapi/api/login'
URL_OVR = \
    'http://localhost:5004/ajnaapi/api/fichas'


def get_token_ajnaapi(username, password):
    data = {'username': username, 'password': password}
    token = None
    try:
        r = requests.post(URL_AUTH, json=data)
        print(r.url, data)
        if r.status_code == 200:
            token = r.json().get('access_token')
        else:
            raise Exception('Erro: %s' % r.status_code)
    except Exception as err:
        logger.error(str(type(err)) + str(err))
        logger.error(r.status_code)
        logger.error(r.text)
    return token


def get_lista_ovr(start, end, user_name, token):
    payload = {'datahora': datetime.strftime(start, '%Y-%m-%d'),
               'data_fim': datetime.strftime(end, '%Y-%m-%d'),}
    payload = {'user_name': user_name}
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.post(URL_OVR, headers=headers, json=payload)
    logger.info('get_lista_ovr ' + r.url)
    try:
        if r.status_code == 200:
            lista_ovrs = r.json()
        else:
            raise Exception('Erro: %s' % r.status_code)
    except Exception as err:
        logger.error(str(type(err)) + str(err))
        logger.error(r.status_code)
        logger.error(r.text)
        return None
    return lista_ovrs


def get_ovrs(datainicial, datafinal, username, password):
    lista_ovr = []
    token = get_token_ajnaapi(username, password)
    if token:
        lista_ovr = get_lista_ovr(datainicial, datafinal,
                                  username, token)
    return lista_ovr


@click.command()
@click.option('--inicio', default=None,
              help='Dia de início (dia/mês/ano) - padrão data da última FMA')
@click.option('--fim', default=None,
              help='Dia de fim')
@click.option('--usuario', default='ivan',
              help='Nome de usuário')
@click.option('--senha', default='ivan',
              help='Senha do usuário')
def run(inicio, fim, usuario, senha):
    if inicio is None:
        start = datetime.today()
    else:
        start = datetime.strptime(inicio, '%d/%m/%Y')
    if fim is None:
        end = datetime.today()
    else:
        end = datetime.strptime(fim, '%d/%m/%Y')
    print(start, end)
    ovrs = get_ovrs(start, end, usuario, senha)
    with open('maladireta.csv', 'w', newline='') as csv_out:
        writer = csv.writer(csv_out)
        writer.writerow(ovrs[0].keys())
        for ovr in ovrs[:2]:
            writer.writerow(ovr.values())


if __name__ == '__main__':  # pragma: no cover
    run()
