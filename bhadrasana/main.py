"""
Bhadrasana.

Módulo Bhadrasana - AJNA
========================

Interface do Usuário - WEB
--------------------------

Módulo responsável por gerenciar bases de dados importadas/acessadas pelo AJNA,
administrando estas e as cruzando com parâmetros de risco.

Serve para a administração, pré-tratamento e visualização dos dados importados,
assim como para acompanhamento de registros de log e detecção de problemas nas
conexões internas.

Adicionalmente, permite o merge entre bases, navegação de bases, e
a aplicação de filtros/parâmetros de risco.
"""
from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ajna_commons.flask.conf import DATABASE, MONGODB_URI, SQL_URI
from bhadrasana.routes.dta import dta_app
from bhadrasana.routes.ovr import ovr_app
from bhadrasana.views import configure_app

conn = MongoClient(host=MONGODB_URI)
mongodb = conn[DATABASE]
mongodb_risco = conn['risco']
engine = create_engine(SQL_URI)
Session = sessionmaker(bind=engine)
session = Session()
app = configure_app(mongodb, session, mongodb_risco)
ovr_app(app)
dta_app(app)

if __name__ == '__main__':
    print('Iniciando Servidor Bhadrasana...')
    app.run(debug=app.config['DEBUG'])
