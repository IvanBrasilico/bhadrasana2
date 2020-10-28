"""Funções para selecionar, dentre as GMCIs previstas, contêineres a escanear

Sorteia GMCIs por Terminal.
Consulta Manifesto para saber Operador.
Monta texto para e-mail.
"""
import sys
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

sys.path.append('.')
sys.path.append('../ajna_docs/commons')
sys.path.append('../virasana')

from ajna_commons.flask.conf import SQL_URI
from virasana.integracao.gmci_alchemy import GMCI


def sorteia_GMCIs(dbssession: Session, recinto: int,
                  start: datetime, end: datetime) -> List[GMCI]:
    gmci = dbssession.query(GMCI).filter(GMCI.cod_recinto == recinto).all()


if __name__ == '__main__':  # pragma: no cover
    engine = create_engine(SQL_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    end = datetime.now()
    start = end - timedelta(hours=48)
    print(start, end)
    gmcis = sorteia_GMCIs(session, 70, start, end)
    print(gmcis)

"""
SELECT * FROM manifestosresumo where numero in
(
SELECT manifestoCE FROM conhecimentosresumo where numeroCEmercante in (
select numeroCEmercante from itensresumo where codigoConteiner in ('MNBU0510060', 'HLBU3008020', 'HLBU2603796', 'TCNU2730934'))
)
AND dataAtualizacao > '2020-10-01'
"""
