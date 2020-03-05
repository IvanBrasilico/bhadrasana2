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
import tempfile

from flask import (Flask, redirect, render_template, request,
                   url_for, Response)
from flask_bootstrap import Bootstrap
# from flask_cors import CORS
from flask_login import current_user
from flask_nav import Nav
from flask_nav.elements import Navbar, View
from flask_wtf.csrf import CSRFProtect

import ajna_commons.flask.login as login_ajna
from ajna_commons.flask.conf import ALLOWED_EXTENSIONS, SECRET, logo
from ajna_commons.flask.log import logger
from ajna_commons.flask.user import DBUser
from ajna_commons.utils.images import mongo_image
from bhadrasana.conf import APP_PATH

tmpdir = tempfile.mkdtemp()

app = Flask(__name__, static_url_path='/static')
csrf = CSRFProtect(app)
Bootstrap(app)
nav = Nav()
nav.init_app(app)


def configure_app(mongodb, sqlsession, mongo_risco):
    """Configurações gerais e de Banco de Dados da Aplicação."""
    app.config['DEBUG'] = os.environ.get('DEBUG', 'None') == '1'
    print(app.debug)
    if app.config['DEBUG'] is True:
        app.jinja_env.auto_reload = True
        app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.secret_key = SECRET
    app.config['SECRET_KEY'] = SECRET
    app.config['SESSION_TYPE'] = 'filesystem'
    login_ajna.configure(app)
    DBUser.dbsession = mongodb
    app.config['dbsession'] = sqlsession
    app.config['mongodb'] = mongodb
    app.config['mongo_risco'] = mongo_risco
    login_ajna.login_manager.login_view = 'bhadrasana2/login'
    return app


@app.before_request
def log_every_request():
    """Envia cada requisição ao log."""
    name = 'No user'
    if current_user and current_user.is_authenticated:
        name = current_user.name
        logger.info(request.url + ' - ' + name)


def get_user_save_path():
    user_save_path = os.path.join(APP_PATH,
                                  app.config.get('STATIC_FOLDER', 'static'),
                                  current_user.name)
    if not os.path.exists(user_save_path):
        os.mkdir(user_save_path)
    return user_save_path


def allowed_file(filename, extensions=ALLOWED_EXTENSIONS):
    """Checa extensões permitidas."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in extensions


@app.route('/')
def index():
    """View retorna index.html ou login se não autenticado."""
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('commons.login'))


@app.route('/image/<_id>')
def image_id(_id):
    """Recupera a imagem do banco e serializa para stream HTTP.

    """
    db = app.config['mongo_risco']
    image = mongo_image(db, _id)
    if image:
        return Response(response=image, mimetype='image/jpeg')
    return 'Sem Imagem'


@nav.navigation()
def mynavbar():
    """Menu da aplicação."""
    items = [View('Home', 'index'),
             View('Risco', 'risco'),
             View('Editar Riscos', 'edita_risco'),
             View('RVF', 'pesquisa_rvf'),
             # View('FMA', 'pesquisa_fma'),
             View('OVR', 'pesquisa_ovr'),
             View('Minhas OVRs', 'minhas_ovrs'),
             # View('Avaliar PDFs trânsito', 'transito'),
             ]
    if current_user.is_authenticated:
        items.append(View('Sair', 'commons.logout'))
    return Navbar(logo, *items)
