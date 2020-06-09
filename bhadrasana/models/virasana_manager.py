from typing import List

import requests

from ajna_commons.flask.log import logger
from virasana.integracao.mercante.mercantealchemy import Item, Conhecimento, NCMItem

VIRASANA_URL = 'https://localhost/virasana/'


def get_imagens_json(conhecimento: str) -> dict:
    try:
        if conhecimento is None or conhecimento == '':
            raise ValueError('get_imagens_json: Informe o conhecimento!')
        params = {'query':
                      {'metadata.carga.conhecimento.conhecimento': conhecimento,
                       'metadata.contentType': 'image/jpeg'
                       },
                  'projection':
                      {'metadata.numeroinformado': 1,
                       'metadata.dataescaneamento': 1}
                  }
        r = requests.post(VIRASANA_URL + 'grid_data',
                          json=params,
                          verify=False)
        return r.json()
    except Exception as err:
        logger.error(str(r.status_code) + ' ' + r.text)
        raise err


def get_imagens_container(mongodb, numero: str) -> list:
    if numero is None or numero == '':
        raise ValueError('get_imagens: Informe o número do contêiner!')
    query = {'metadata.numeroinformado': numero.strip(),
             'metadata.contentType': 'image/jpeg'
             }
    projection = {'metadata.numeroinformado': 1,
                  'metadata.dataescaneamento': 1}
    cursor = mongodb['fs.files'].find(query, projection)
    return list(cursor)


def get_due(mongodb, numerodeclaracao: str) -> dict:
    due = {}
    if numerodeclaracao:
        cursor = mongodb.fs.files.find(
            {'metadata.due.numero': numerodeclaracao},
            {'metadata.due': 1})
        due = list(cursor)
        if due and len(due) > 0:
            due = due[len(due) - 1]
            due = due.get('metadata')
            if due:
                due = due.get('due')[0]
    return due


def get_dues_container(mongodb, numero: str) -> list:
    if numero is None or numero == '':
        raise ValueError('get_dues: Informe o número do contêiner!')
    query = {'metadata.numeroinformado': numero.strip(),
             'metadata.contentType': 'image/jpeg'
             }
    projection = {'metadata.due': 1}
    cursor = mongodb['fs.files'].find(query, projection)
    result = []
    for row in cursor:
        metadata = row.get('metadata')
        if metadata:
            due = metadata.get('due')
            if due:
                result.append(due[0])
    return result


def get_dues_empresa(mongodb, cnpj: str) -> list:
    if cnpj is None or cnpj == '':
        raise ValueError('get_dues: Informe o CNPJ da empresa!')
    query = {'metadata.due.itens.Exportador': cnpj.strip(),
             'metadata.contentType': 'image/jpeg'
             }
    projection = {'metadata.due': 1}
    cursor = mongodb['fs.files'].find(query, projection)
    result = []
    for row in cursor:
        metadata = row.get('metadata')
        if metadata:
            due = metadata.get('due')
            if due:
                result.append(due[0])
    return result


def get_imagens_query(mongodb, query: dict) -> list:
    """Retorna cursor da query, campos: _id, numeroinformado, dataescaneamento."""
    projection = {'metadata.numeroinformado': 1,
                  'metadata.dataescaneamento': 1}
    try:
        cursor = mongodb['fs.files'].find(query, projection)
        return list(cursor)
    except Exception as err:
        logger.error(err, exc_info=True)
        return []


def get_imagens_conhecimento(mongodb, conhecimento: str) -> list:
    if conhecimento is None or conhecimento == '' or len(conhecimento) < 15:
        raise ValueError('get_imagens: Informe o conhecimento com 15 números!')
    query = {'metadata.carga.conhecimento.conhecimento': conhecimento,
             'metadata.contentType': 'image/jpeg'
             }
    return get_imagens_query(mongodb, query)


def get_imagens_due(mongodb, due: str) -> list:
    if due is None or due == '' or len(due) < 14:
        raise ValueError('get_imagens: Informe o número da DUE'
                         ' com 14 dígitos (AABR9999999999)!')
    query = {'metadata.due.numero': due,
             'metadata.contentType': 'image/jpeg'
             }
    return get_imagens_query(mongodb, query)


def get_imagens_dict_container_id(mongodb, conhecimento: str, due: str) -> dict:
    """Retorna lista de imagens no formato numeroContainer: _id imagem"""
    try:
        imagens_conhecimento = get_imagens_conhecimento(mongodb, conhecimento)
    except ValueError:
        imagens_conhecimento = []
    try:
        imagens_due = get_imagens_due(mongodb, due)
    except ValueError:
        imagens_due = []
    logger.info('imagens_conhecimento')
    logger.info(imagens_conhecimento)
    logger.info('imagens_due')
    logger.info(imagens_due)
    imagens = [*imagens_conhecimento, *imagens_due]
    return {item['metadata']['numeroinformado']: str(item['_id'])
            for item in imagens}


def get_conhecimento(session, numero: str) -> Conhecimento:
    return session.query(Conhecimento).filter(
        Conhecimento.numeroCEmercante == numero).one_or_none()


def get_ces_empresa(session, cnpj: str) -> List[Conhecimento]:
    return session.query(Conhecimento).filter(
        Conhecimento.consignatario.like(cnpj[:8] + '%')).all()


def get_containers_conhecimento(session, numero: str) -> List[Item]:
    return list(session.query(Item).filter(
        Item.numeroCEmercante == numero).all())


def get_ncms_conhecimento(session, numero: str) -> List[NCMItem]:
    return session.query(NCMItem).filter(
        NCMItem.numeroCEMercante == numero).all()
