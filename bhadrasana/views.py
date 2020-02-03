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

import ajna_commons.flask.login as login_ajna
from ajna_commons.flask.conf import ALLOWED_EXTENSIONS, SECRET, logo
from ajna_commons.flask.log import logger
from ajna_commons.flask.user import DBUser
from flask import (Flask, flash, redirect, render_template, request,
                   url_for, jsonify)
from flask_bootstrap import Bootstrap
# from flask_cors import CORS
from flask_login import current_user, login_required
from flask_nav import Nav
from flask_nav.elements import Navbar, View
from flask_wtf.csrf import CSRFProtect

from bhadrasana.conf import APP_PATH, CSV_FOLDER
from bhadrasana.forms.riscosativos import RiscosAtivosForm
from bhadrasana.forms.rvf import RVFForm
from bhadrasana.models.mercantemanager import mercanterisco, riscosativos, \
    insererisco
from bhadrasana.models.rvfmanager import get_marcas, exclui_marca_encontrada, cadastra_rvf, inclui_marca_encontrada

app = Flask(__name__, static_url_path='/static')
csrf = CSRFProtect(app)
Bootstrap(app)
nav = Nav()
nav.init_app(app)


def configure_app(mongodb, sqlsession):
    """Configurações gerais e de Banco de Dados da Aplicação."""
    app.config['DEBUG'] = os.environ.get('DEBUG', 'None') == '1'
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
    return app


@app.before_request
def log_every_request():
    """Envia cada requisição ao log."""
    name = 'No user'
    if current_user and current_user.is_authenticated:
        name = current_user.name
        logger.info(request.url + ' - ' + name)


def allowed_file(filename):
    """Checa extensões permitidas."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """View retorna index.html ou login se não autenticado."""
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('commons.login'))


@app.route('/risco', methods=['POST', 'GET'])
@login_required
def risco():
    """Função para aplicar parâmetros de risco nas tabelas do Mercante

    Args:
    """
    dbsession = app.config.get('dbsession')
    mongodb = app.config.get('mongodb')
    static_path = os.path.join(APP_PATH,
                               app.config.get('STATIC_FOLDER', 'static'),
                               current_user.name)
    user_name = current_user.name
    user_folder = os.path.join(CSV_FOLDER, user_name)
    lista_risco = []
    if request.method == 'POST':
        try:
            riscos_ativos_form = RiscosAtivosForm(request.form)
            riscos_ativos = riscosativos(dbsession, user_name)
            ncms = [risco[1] for risco in riscos_ativos
                    if risco[0] == 'ncm']
            print(ncms)
            filtros = {}
            if riscos_ativos_form.consignatario.data is True:
                filtros['consignatario'] = ['00']
            if riscos_ativos_form.embarcador.data is True:
                filtros['embarcador'] = ['RUIAN']
            if riscos_ativos_form.portoorigem.data is True:
                filtros['portoOrigemCarga'] = ['CNXGG']
            if riscos_ativos_form.ncm.data is True:
                filtros['ncm'] = ncms  # ['8528', '3906', '4202']
            lista_risco = mercanterisco(dbsession, filtros)
            # print('***********', lista_risco)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro ao aplicar risco! ' +
                  'Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        # Salvar resultado um arquivo para donwload
        # Limita resultados em 100 linhas na tela
    else:
        riscos_ativos_form = RiscosAtivosForm()
    return render_template('aplica_risco.html',
                           oform=riscos_ativos_form,
                           lista_risco=lista_risco)


@app.route('/edita_risco', methods=['POST', 'GET'])
@login_required
def edita_risco():
    session = app.config.get('dbsession')
    user_name = current_user.name
    riscos_ativos = riscosativos(session, user_name)
    return render_template('edita_risco.html',
                           riscos_ativos=riscos_ativos)


@app.route('/inclui_risco', methods=['POST'])
@login_required
def inclui_risco():
    session = app.config.get('dbsession')
    user_name = current_user.name
    campo = request.form.get('campo')
    valor = request.form.get('valor')
    motivo = request.form.get('motivo')
    # print(user_name, campo, valor, motivo)
    insererisco(session,
                user_name=user_name,
                campo=campo,
                valor=valor,
                motivo=motivo)
    return redirect(url_for('edita_risco'))


@app.route('/rvf', methods=['POST', 'GET'])
@login_required
def rvf():
    session = app.config.get('dbsession')
    user_name = current_user.name
    marcas_encontradas = []
    if request.method == 'POST':
        try:
            rvf_form = RVFForm(request.form)
            rvf_form.validate()
            print(rvf_form.id.data)
            rvf = cadastra_rvf(session,
                               rvf_form.id.data,
                               rvf_form.descricao.data,
                               rvf_form.numeroCEmercante.data)
            rvf_form.id.data = rvf.id
            marcas_encontradas = rvf.marcasencontradas
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro ao aplicar risco! ' +
                  'Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
    else:
        rvf_form = RVFForm()
    marcas = get_marcas(session)
    print(marcas)
    print(marcas_encontradas)
    return render_template('rvf.html',
                           marcas=marcas,
                           oform=rvf_form,
                           marcas_encontradas=marcas_encontradas)

@app.route('/inclui_marca_encontrada', methods=['GET'])
@login_required
def inclui_marca():
    session = app.config.get('dbsession')
    rvf_id = request.args.get('rvf_id')
    marca_nome = request.args.get('marca_nome')
    novas_marcas = inclui_marca_encontrada(session, rvf_id, marca_nome)
    return jsonify([{'id':marca.id, 'nome': marca.nome} for marca in novas_marcas])


@app.route('/exclui_marca_encontrada', methods=['GET'])
@login_required
def exclui_marca():
    session = app.config.get('dbsession')
    rvf_id = request.args.get('rvf_id')
    marca_id = request.args.get('marca_id')
    novas_marcas = exclui_marca_encontrada(session, rvf_id, marca_id)
    return jsonify([{'id':marca.id, 'nome': marca.nome} for marca in novas_marcas])


@nav.navigation()
def mynavbar():
    """Menu da aplicação."""
    items = [View('Home', 'index'),
             View('Risco', 'risco'),
             View('Editar Riscos', 'edita_risco'),
             View('RVF', 'rvf'),
             ]
    if current_user.is_authenticated:
        items.append(View('Sair', 'commons.logout'))
    return Navbar(logo, *items)
