"""Funções para selecionar, dentre as GMCIs previstas, contêineres a escanear

Sorteia GMCIs por Terminal.
Consulta Manifesto para saber Operador.
Monta texto para e-mail.
"""
import random
import sys
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from bhadrasana.models.ovr import Recinto

sys.path.append('.')
sys.path.append('../ajna_docs/commons')
sys.path.append('../virasana')

from ajna_commons.flask.conf import SQL_URI
from virasana.integracao.gmci_alchemy import GMCI

SQL_CONTEINERES_GMCIS = \
    """SELECT codigoTerminalDescarregamento as Operador, dataInicioOperacao as Data,
     numero as Manifesto, c.numeroCEmercante as CEMercante, codigoConteiner as Contêiner
     FROM manifestosresumo m
     INNER JOIN conhecimentosresumo c ON c.manifestoCE = m.numero
     INNER JOIN itensresumo i ON i.numeroCEmercante = c.numeroCEmercante
     where i.codigoConteiner in (%s)
     AND i.dataAtualizacao > '%s'
    """


def get_dict_operador_recinto(dbsession):
    recintos = dbsession.query(Recinto).filter(
        Recinto.cod_carga.isnot(None)).all()
    return {recinto.cod_carga: recinto.nome for recinto in recintos}


def get_dict_codigos_recinto(dbsession, codigos):
    recintos = dbsession.query(Recinto).filter(
        Recinto.cod_dte.in_(codigos)).all()
    return {recinto.cod_dte: recinto.nome for recinto in recintos}



def sorteia_GMCIs(dbsession: Session, recintos: List[int],
                  start: datetime, end: datetime, qtde=10) -> dict:
    """Retorna dicionário contendo campos, agrupado por nome do Recinto.

    O valor do dicionário é uma lista de dicts contendo os nomes de campso e  valores
    """
    gmcis = dbsession.query(GMCI).filter(
        GMCI.cod_recinto.in_(recintos)).filter(
        GMCI.datahora.between(start, end)
    ).all()
    gmcis = random.sample(gmcis, qtde)
    gmcis_conteineres = [gmci.num_conteiner for gmci in gmcis]
    cod_recintos_nome_dict = get_dict_codigos_recinto(dbsession, recintos)
    conteiner_recinto_dict = {gmci.num_conteiner: cod_recintos_nome_dict[gmci.cod_recinto]
                              for gmci in gmcis}
    print(gmcis_conteineres)
    sql = SQL_CONTEINERES_GMCIS % ('\'' + '\', \''.join(gmcis_conteineres) + '\'', '2020-10-01')
    print(sql)
    rs = dbsession.execute(sql)
    operadores_recintos = get_dict_operador_recinto(dbsession)
    keys = rs.keys()
    result = defaultdict(list)
    for row in rs.fetchall():
        nome_operador = operadores_recintos[row[0]]
        nome_recinto = conteiner_recinto_dict[row['Contêiner']]
        linha = OrderedDict([(key, value) for key, value in zip(rs.keys(), row)])
        linha['Recinto Destino'] = nome_recinto
        result[nome_operador].append(linha)
    return result


if __name__ == '__main__':  # pragma: no cover
    engine = create_engine(SQL_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    end = datetime.now()
    start = end - timedelta(hours=48)
    print(start, end)
    gmcis = sorteia_GMCIs(session, [50, 52], start, end)
    print(gmcis)
