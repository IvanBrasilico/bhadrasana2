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
    query = {'metadata.carga.container.container': numero.lower().strip(),
             'metadata.contentType': 'image/jpeg'
             }
    projection = {'metadata.numeroinformado': 1,
                  'metadata.dataescaneamento': 1}

    cursor = mongodb['fs.files'].find(query, projection)
    return list(cursor)


def get_imagens(mongodb, conhecimento: str) -> dict:
    if conhecimento is None or conhecimento == '':
        raise ValueError('get_imagens: Informe o conhecimento!')
    query = {'metadata.carga.conhecimento.conhecimento': conhecimento,
             'metadata.contentType': 'image/jpeg'
             }
    projection = {'metadata.numeroinformado': 1,
                  'metadata.dataescaneamento': 1}

    cursor = mongodb['fs.files'].find(query, projection)
    return cursor


def get_imagens_dict_container_id(mongodb, conhecimento: str) -> dict:
    """Retorna lista de imagens no formato numeroContainer: _id imagem"""
    imagens = get_imagens(mongodb, conhecimento)
    return {item['metadata']['numeroinformado']: str(item['_id'])
            for item in imagens}


def get_conhecimento(session, numero: str) -> List[Conhecimento]:
    return session.query(Conhecimento).filter(
        Conhecimento.numeroCEmercante == numero).one_or_none()


def get_containers_conhecimento(session, numero: str) -> List[Item]:
    return list(session.query(Item).filter(
        Item.numeroCEmercante == numero).all())


def get_ncms_conhecimento(session, numero: str) -> List[NCMItem]:
    return session.query(NCMItem).filter(
        NCMItem.numeroCEMercante == numero).all()
