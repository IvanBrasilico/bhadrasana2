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

from flask_login import current_user
from pymongo import MongoClient

from bhadrasana.routes.apirecintos import apirecintos_app
from bhadrasana.routes.assistente_checkapi import assistentecheckapi_app

sys.path.append('../ajna_api')
from ajna_commons.flask.conf import DATABASE, MONGODB_URI, logo
from ajna_commons.flask.log import logger
from bhadrasana.models import db_session
from bhadrasana.routes.admin import admin_app
from bhadrasana.routes.ovr import ovr_app
from bhadrasana.routes.ovr2 import ovr2_app
from bhadrasana.routes.risco import risco_app
from bhadrasana.routes.rvf import rvf_app
from bhadrasana.routes.assistentetg import assistentetg_app
from bhadrasana.routes.assistente_ini import assistenteini_app
from bhadrasana.routes.exporta_secta_e_ovr import eovr_app
from bhadrasana.views import configure_app
from flask_nav import Nav
from flask_nav.elements import Navbar, View, Separator, Subgroup

# print('****************************')
# print(MONGODB_URI)
conn = MongoClient(host=MONGODB_URI)
mongodb = conn[DATABASE]
MONGODB_RISCO = os.environ.get('MONGODB_RISCO')
conn_risco = MongoClient(host=MONGODB_RISCO)
mongodb_risco = conn_risco['risco']
app = configure_app(mongodb, db_session, mongodb_risco)

# ————— Override da Request para aceitar uploads grandes no Werkzeug 1.0.1 —————
from flask import Request
from werkzeug.formparser import FormDataParser

class LargeUploadRequest(Request):
    """
    Subclasse de Request que injeta no FormDataParser um teto maior
    (lendo de app.config['MAX_FORM_MEMORY_SIZE']).
    """
    def _load_form_data(self):
        # pega do config ou usa 100 MB por default
        max_mem = self.app.config.get('MAX_FORM_MEMORY_SIZE', 100 * 1024 * 1024)
        parser = FormDataParser(max_form_memory_size=max_mem)
        # parseia o body (multipart/form-data)
        self._cached_data = parser.parse(
            self.environ['wsgi.input'],
            self.mimetype_params.get('boundary', ''),
            self.content_length
        )
        # chama o parser original para restante do fluxo
        return super()._load_form_data()

# aplica a subclasse no Flask
app.request_class = LargeUploadRequest
# ————————————————————————————————————————————————————————————————

# —————— Forçar limites de upload no Flask/Werkzeug ——————
app.config['MAX_CONTENT_LENGTH']   = 50 * 1024 * 1024   # 50 MB
app.config['MAX_FORM_MEMORY_SIZE'] = 100 * 1024 * 1024  # 100 MB para o parser multipart
# ————————————————————————————————————————————————————————

if os.environ.get('SESSION_COOKIE'):
    app.config.update(SESSION_COOKIE_NAME=os.environ.get('SESSION_COOKIE'))
risco_app(app)
rvf_app(app)
ovr_app(app)
ovr2_app(app)
admin_app(app, db_session)
assistentetg_app(app)
assistenteini_app(app)
assistentecheckapi_app(app)
eovr_app(app)
apirecintos_app(app)

nav = Nav()
nav.init_app(app)


class ForceHttpsRedirects:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        environ['wsgi.url_scheme'] = 'https'
        return self.app(environ, start_response)


if os.environ.get('DEBUG') != '1':
    # Add middleware to force all redirects to https
    app.wsgi_app = ForceHttpsRedirects(app.wsgi_app)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
    logger.info('db_session remove')




@nav.navigation()
def mynavbar():
    """Menu da aplicação."""
    items = [View('Home', 'index'),
             View('Risco', 'risco'),
             View('Editar Riscos', 'edita_risco'),
             View('Pesquisa Fichas', 'pesquisa_ovr'),
             View('Minhas Fichas', 'minhas_ovrs'),
             View('Kanban', 'fichas_em_abas'),
             Subgroup(
                 'Pesquisas/relatórios',
                 View('Pesquisa Contêiner', 'consulta_container'),
                 View('Pesquisa CE Mercante', 'consulta_ce'),
                 View('Pesquisa DUE', 'consulta_due'),
                 View('Pesquisa Empresa', 'consulta_empresa'),
                 View('Pesquisa Pessoa', 'consulta_pessoa'),
                 View('Pesquisa Verificações físicas', 'pesquisa_rvf'),
                 Separator(),
                 View('Relatórios', 'ver_relatorios'),
                 View('Painel de OKRs', 'ver_okrs'),
             ),
             Subgroup(
                 'Adm - assistentes - integração',
                 View('Administração', 'admin.index'),
                 Separator(),
                 View('Gerador de documentos docx', 'gera_docx'),
                 View('Lista para escaneamento no Operador', 'escaneamento_operador'),
                 Separator(),
                 View('Assistente de exportação para e-OVR', 'exporta_e_ovr'),
                 View('Assistente de Contrafação', 'autos_contrafacao'),
                 View('Assistente de TG', 'assistente_tg'),
                 View('Assistente de Auditoria API Recintos', 'assistente_checkapi'),
                 Separator(),
                 View('Exporta Planilha CEN Rilo', 'exporta_cen_rilo'),
                 View('Importa planilhas recintos', 'importa_planilha_recinto'),
             )]
    if current_user.is_authenticated:
        items.append(View('Sair (%s)' % current_user.id, 'commons.logout'))
    return Navbar(logo, *items)


if __name__ == '__main__':
    print('Iniciando Servidor Bhadrasana...')
    app.run(debug=app.config['DEBUG'])
