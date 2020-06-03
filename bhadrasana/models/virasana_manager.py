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


def get_imagens(mongodb, conhecimento: str) -> dict:
    if conhecimento is None or conhecimento == '':
        raise ValueError('get_imagens: Informe o conhecimento!')
    query = {'metadata.carga.conhecimento.conhecimento': conhecimento,
             'metadata.contentType': 'image/jpeg'
             }
    projection = {'metadata.numeroinformado': 1,
                  'metadata.dataescaneamento': 1}

    try:
        cursor = mongodb['fs.files'].find(query, projection)
    except Exception as err:
        logger.error(err, exc_info=True)
        return {}
    return cursor


def get_imagens_dict_container_id(mongodb, conhecimento: str) -> dict:
    """Retorna lista de imagens no formato numeroContainer: _id imagem"""
    imagens = get_imagens(mongodb, conhecimento)
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
