import sys

from bhadrasana.docx.docx_functions import gera_OVR

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from datetime import datetime

import click
import requests

from ajna_commons.flask.log import logger

BASE_URL = 'http://localhost:5004/'
URL_AUTH = BASE_URL + 'ajnaapi/api/login'
URL_OVR = BASE_URL + 'ajnaapi/api/ficha/'
URL_OVRS = BASE_URL + 'ajnaapi/api/fichas'
URL_RVF = BASE_URL + 'ajnaapi/api/rvf/'


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
               'data_fim': datetime.strftime(end, '%Y-%m-%d'), }
    payload = {'user_name': user_name}
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.post(URL_OVRS, headers=headers, json=payload)
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


def get_rvf_id(rvf_id, token):
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.get(URL_RVF + str(rvf_id), headers=headers)
    logger.info('get_rvf_id ' + r.url)
    try:
        if r.status_code == 200:
            return r.json()
        raise Exception('Erro: %s' % r.status_code)
    except Exception as err:
        logger.error(str(type(err)) + str(err))
        logger.error(r.status_code)
        logger.error(r.text[:200])


def get_ficha_id(ovr_id, token):
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.get(URL_OVR + str(ovr_id), headers=headers)
    logger.info('get_ovr_id ' + r.url)
    try:
        if r.status_code == 200:
            return r.json()
        raise Exception('Erro: %s' % r.status_code)
    except Exception as err:
        logger.error(str(type(err)) + str(err))
        logger.error(r.status_code)
        logger.error(r.text[:200])


def get_ovrs(datainicial, datafinal, username, password):
    lista_ovr = []
    token = get_token_ajnaapi(username, password)
    if token:
        lista_ovr = get_lista_ovr(datainicial, datafinal,
                                  username, token)
    return lista_ovr


def get_ficha(ovr_id, username, password):
    token = get_token_ajnaapi(username, password)
    if token:
        return get_ficha_id(ovr_id, token)


def get_rvf(rvf_id, username, password):
    token = get_token_ajnaapi(username, password)
    if token:
        return get_rvf_id(rvf_id, token)


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
    # ovrs = get_ovrs(start, end, usuario, senha)
    # df = pd.DataFrame.from_dict(ovrs)
    # print(df.head())
    # df.to_excel('maladireta.xlsx')

    rvf = get_rvf(41, 'ivan', 'ivan')
    conteudo = {'unidade': 'ALFSTS', **rvf}
    conteudo_sem_imagens = conteudo.copy()
    conteudo_sem_imagens.pop('imagens')
    print(conteudo_sem_imagens)
    print(conteudo.keys())
    document = gera_OVR(rvf)
    document.save('testes_docx/OVR_RVF{}.docx'.format(conteudo['id']))


if __name__ == '__main__':  # pragma: no cover
    run()
