import os
import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')

from ajna_commons.flask.log import logger
from bhadrasana.models.ovr import TGOVR
from bhadrasana.models.ovrmanager import atualiza_valortotal_tg


if __name__ == '__main__':
    # SQL_URI_STAGING = os.environ.get('SQL_URI_STAGING')  # conexao com staging
    SQL_URI = os.environ.get('SQL_URI')  # conexao com produção

    # engine = create_engine(SQL_URI_STAGING)  # staging
    engine = create_engine(SQL_URI)  # producao
    Session = sessionmaker(bind=engine)
    session = Session()

    lista_tg = session.query(TGOVR).all()

    for tg in lista_tg:
        if not tg.qtde:
            try:
                atualiza_valortotal_tg(session, tg.id)
                logger.info(f"Atualizando TG nº{tg.id} qtide = {tg.qtde} e valor total= {tg.valor}")
            except Exception as err:
                logger.error(str(err), exc_info=True)


