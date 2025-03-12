from datetime import datetime
from typing import List

import requests

from ajna_commons.flask.log import logger
from ajna_commons.utils.sanitiza import mongo_sanitizar
from bhadrasana.models.laudo import get_empresa, get_sats_cnpj, get_pessoa
from virasana.integracao.due.due_alchemy import Due, DueItem, DueConteiner
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
    query = {'metadata.numeroinformado': mongo_sanitizar(numero.strip()).upper(),
             'metadata.contentType': 'image/jpeg'
             }
    projection = {'metadata.numeroinformado': 1,
                  'metadata.dataescaneamento': 1}
    cursor = mongodb['fs.files'].find(query, projection)
    return list(cursor)


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
             'metadata.contentType': 'image/jpeg'}
    return get_imagens_query(mongodb, query)


def get_imagens_due(mongodb, due: str) -> list:
    if due is None or due == '' or len(due) < 14:
        raise ValueError('get_imagens: Informe o número da DUE'
                         ' com 14 dígitos (AABR9999999999)!')
    query = {'metadata.due': due,
             'metadata.contentType': 'image/jpeg'}
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


def get_conhecimentos_filhotes(session, numero: str) -> List[Conhecimento]:
    return session.query(Conhecimento).filter(
        Conhecimento.numeroCEMaster == numero).all()


def get_ces_empresa(session, cnpj: str, limit=40) -> List[Conhecimento]:
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos.')
    return session.query(Conhecimento).filter(
        Conhecimento.consignatario.like(cnpj[:8] + '%')). \
        order_by(Conhecimento.dataEmissao.desc()).limit(limit).all()


def get_containers_conhecimento(session, numero: str) -> List[Item]:
    return list(session.query(Item).filter(
        Item.numeroCEmercante == numero).all())


def get_ncms_conhecimento(session, numero: str) -> List[NCMItem]:
    return session.query(NCMItem).filter(
        NCMItem.numeroCEMercante == numero).all()


def get_detalhe_conhecimento(session, numeroCEmercante: str) -> dict:
    linha = dict()
    conhecimento = get_conhecimento(session, numeroCEmercante)
    linha['conhecimento'] = conhecimento
    linha['containers'] = get_containers_conhecimento(
        session,
        numeroCEmercante)
    linha['filhotes'] = get_conhecimentos_filhotes(session, numeroCEmercante)
    linha['ncms'] = get_ncms_conhecimento(session, numeroCEmercante)
    logger.info('get_laudos')
    if conhecimento:
        if conhecimento.tipoTrafego == '7':
            cnpj = conhecimento.embarcador
        else:
            cnpj = conhecimento.consignatario
        print(cnpj)
        print(conhecimento.tipoBLConhecimento)
        print(conhecimento.tipoTrafego, type(conhecimento.tipoTrafego))
        print(conhecimento.get_tipoTrafego())
        empresa = None
        if cnpj:
            try:
                if len(cnpj) == 11:
                    empresa = get_pessoa(session, cnpj)
                if not empresa:
                    empresa = get_empresa(session, cnpj)
            except ValueError:
                empresa = None
            sats = get_sats_cnpj(session, cnpj)
            linha['empresa'] = empresa
            linha['sats'] = sats
    return linha


def get_detalhes_mercante(session, ces: List[str]) -> dict:
    infoces = {}
    for numeroCEmercante in ces:
        try:
            infoces[numeroCEmercante] = get_detalhe_conhecimento(session, numeroCEmercante)
        except Exception as err:
            logger.info(err)
    return infoces


def get_due(session, numerodeclaracao: str) -> Due:
    return session.query(Due).filter(Due.numero_due == numerodeclaracao).one_or_none()


def get_itens_due(session, numerodeclaracao: str) -> List[DueItem]:
    return session.query(DueItem).filter(DueItem.nr_due == numerodeclaracao).all()


def get_dues_container(session, numero: str,
                       datainicio: datetime,
                       datafim: datetime,
                       limit=40
                       ) -> List[Due]:
    if numero is None or numero == '':
        raise ValueError('get_dues_container: Informe o número do contêiner!')
    q = session.query(Due).join(DueConteiner, Due.numero_due == DueConteiner.numero_due). \
            filter( DueConteiner.numero_conteiner == numero,
                    Due.data_criacao_due.between(datainicio, datafim)).limit(limit)
    logger.info(q.statement)
    dues = q.all()
    #dues = session.query(Due).filter(
    #    Due.data_criacao_due.between(datainicio, datafim),
    #    Due.lista_id_conteiner.like('%' + numero + '%')).limit(limit).all()
    return dues


def get_dues_empresa(session, cnpj: str, limit=40) -> List[Due]:
    if cnpj is None or len(cnpj) < 8:
        raise ValueError('get_dues: Informe o CNPJ da empresa com no mínimo 8 posições!')
    return session.query(Due).filter(Due.cnpj_estabelecimento_exportador.like(cnpj + '%')). \
        limit(limit).all()
