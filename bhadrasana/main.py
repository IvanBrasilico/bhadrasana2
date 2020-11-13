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
import os
import sys

from pymongo import MongoClient
sys.path.append('../ajna_api')
from ajna_commons.flask.conf import DATABASE, MONGODB_URI
from ajna_commons.flask.log import logger
from bhadrasana.models import db_session
from bhadrasana.routes.admin import admin_app
from bhadrasana.routes.ovr import ovr_app
from bhadrasana.routes.risco import risco_app
from bhadrasana.routes.rvf import rvf_app
from bhadrasana.views import configure_app

# print('****************************')
# print(MONGODB_URI)
conn = MongoClient(host=MONGODB_URI)
mongodb = conn[DATABASE]
MONGODB_RISCO = os.environ.get('MONGODB_RISCO')
conn_risco = MongoClient(host=MONGODB_RISCO)
mongodb_risco = conn_risco['risco']
app = configure_app(mongodb, db_session, mongodb_risco)
if os.environ.get('SESSION_COOKIE'):
    app.config.update(SESSION_COOKIE_NAME=os.environ.get('SESSION_COOKIE'))
risco_app(app)
rvf_app(app)
ovr_app(app)
admin_app(app, db_session)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
    logger.info('db_session remove')


if __name__ == '__main__':
    print('Iniciando Servidor Bhadrasana...')
    app.run(debug=app.config['DEBUG'])
