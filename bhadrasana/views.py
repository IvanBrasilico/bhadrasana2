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
from datetime import datetime

import pandas as pd
import requests
from flask import (Flask, flash, redirect, render_template, request,
                   url_for, Response)
from flask_bootstrap import Bootstrap
# from flask_cors import CORS
from flask_login import current_user, login_required
from flask_nav import Nav
from flask_nav.elements import Navbar, View
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

import ajna_commons.flask.login as login_ajna
from ajna_commons.flask.conf import ALLOWED_EXTENSIONS, SECRET, logo
from ajna_commons.flask.log import logger
from ajna_commons.flask.user import DBUser
from ajna_commons.utils.images import mongo_image
from bhadrasana.conf import APP_PATH
from bhadrasana.forms.editarisco import get_edita_risco_form
from bhadrasana.forms.riscosativos import RiscosAtivosForm
from bhadrasana.models.riscomanager import mercanterisco, riscosativos, \
    insererisco, exclui_risco, CAMPOS_RISCO, get_lista_csv

tmpdir = tempfile.mkdtemp()

app = Flask(__name__, static_url_path='/static')
csrf = CSRFProtect(app)
Bootstrap(app)
nav = Nav()
nav.init_app(app)


def configure_app(mongodb, sqlsession, mongo_risco):
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
    app.config['mongo_risco'] = mongo_risco
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


def append_images(lista_risco):
    lista_risco_nova = []
    for linha in lista_risco:
        ce = linha.get('numeroCEmercante')
        conteiner = linha.get('codigoConteiner')
        if ce and conteiner:
            params = {'query':
                          {'metadata.carga.conhecimento.conhecimento': ce,
                           'metadata.numeroinformado': conteiner},
                      'projection': {'_id': 1}
                      }
            r = requests.post('https://ajna.labin.rf08.srf/virasana/grid_data',
                              json=params, verify=False)
            lista = r.json()
            _id = ''
            if lista and len(lista) > 0:
                _id = lista[0]['_id']
            linha['_id'] = _id
            lista_risco_nova.append(linha)
    return lista_risco_nova


def le_csv(filename):
    df = pd.read_csv(filename, sep=';',
                     header=5, encoding='windows-1252')
    return [row[1].to_dict() for row in df.iterrows()]


@app.route('/risco', methods=['POST', 'GET'])
@login_required
def risco():
    """Função para aplicar parâmetros de risco nas tabelas do Mercante

    Args:
    """
    dbsession = app.config.get('dbsession')
    user_name = current_user.name
    lista_risco = []
    csv_salvo = None
    planilha_atual = ''
    lista_csv = get_lista_csv(get_user_save_path())
    if request.method == 'POST':
        try:
            riscos_ativos_form = RiscosAtivosForm(request.form)
            riscos_ativos_form.planilha_atual = ''
            riscos_ativos = riscosativos(dbsession, user_name)
            filtros = {}
            filtros['datainicio'] = riscos_ativos_form.datainicio.data
            filtros['datafim'] = riscos_ativos_form.datafim.data
            for fieldname, value in riscos_ativos_form.data.items():
                if value is True:
                    riscos_ativos_campo = [risco.valor for risco in riscos_ativos
                                           if risco.campo == fieldname]
                    filtros[fieldname] = riscos_ativos_campo
            lista_risco, str_filtros = mercanterisco(dbsession, filtros)
            # print('***********', lista_risco)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro ao aplicar risco! '
                  'Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        # Salvar resultado um arquivo para donwload
        # Limita resultados em 100 linhas na tela
        if lista_risco and len(lista_risco) > 0:
            csv_salvo = 'resultado_' \
                        + datetime.strftime(datetime.now(), '%Y-%m%dT%H%M%S') + \
                        '.csv'
            with open(os.path.join(get_user_save_path(), csv_salvo), 'w') as out_file:
                out_file.write(str_filtros + '\n')
                out_file.write(';'.join([key for key in lista_risco[0].keys()]) + '\n')
                for row in lista_risco:
                    campos = [str(value).replace(';', ',') for value in row.values()]
                    out_file.write(';'.join(campos) + '\n')
    else:
        riscos_ativos_form = RiscosAtivosForm()
        planilha_atual = request.args.get('planilha_atual', '')
        if planilha_atual:
            csv_salvo = planilha_atual
            lista_risco = le_csv(os.path.join(get_user_save_path(), csv_salvo))
    total_linhas = len(lista_risco)
    lista_risco = append_images(lista_risco[:100])
    return render_template('aplica_risco.html',
                           oform=riscos_ativos_form,
                           lista_risco=lista_risco,
                           total_linhas=total_linhas,
                           csv_salvo=csv_salvo,
                           lista_csv=lista_csv,
                           planilha_atual=planilha_atual)


@app.route('/edita_risco', methods=['POST', 'GET'])
@login_required
def edita_risco():
    session = app.config.get('dbsession')
    user_name = current_user.name
    riscos_ativos = riscosativos(session, user_name)
    edita_risco_form = get_edita_risco_form()
    return render_template('edita_risco.html',
                           riscos_ativos=riscos_ativos,
                           oform=edita_risco_form)


@app.route('/inclui_risco', methods=['POST'])
@login_required
def inclui_risco():
    session = app.config.get('dbsession')
    user_name = current_user.name
    campoid = request.form.get('campo')
    if campoid == '0':
        flash('Selecionar campo')
        return redirect(url_for('edita_risco'))
    campo = dict(CAMPOS_RISCO)[campoid]
    valor = request.form.get('valor')
    motivo = request.form.get('motivo')
    # print(user_name, campo, valor, motivo)
    try:
        insererisco(session,
                    user_name=user_name,
                    campo=campo,
                    valor=valor,
                    motivo=motivo)
    except Exception as err:
        logger.error(err, exc_info=True)
        flash('Erro ao incluir risco! '
              'Detalhes no log da aplicação.')
        flash(str(type(err)))
        flash(str(err))

    return redirect(url_for('edita_risco'))


@app.route('/exclui_risco/<id>', methods=['GET'])
@login_required
def excluir_risco(id):
    session = app.config.get('dbsession')
    try:
        exclui_risco(session, id)
    except Exception as err:
        logger.error(err, exc_info=True)
        flash('Erro ao incluir risco! '
              'Detalhes no log da aplicação.')
        flash(str(type(err)))
        flash(str(err))
    return redirect(url_for('edita_risco'))


@app.route('/exporta_csv', methods=['POST', 'GET'])
@login_required
def exporta_csv():
    """Grava em arquivo parâmetros ativos.

    """
    session = app.config.get('dbsession')
    try:
        riscos_out_filename = 'riscos_ativos' + \
                              datetime.strftime(datetime.now(), '%Y-%m%dT%H%M%S') + \
                              '.csv'
        riscos_ativos = riscosativos(session, current_user.name)
        with open(os.path.join(get_user_save_path(),
                               riscos_out_filename), 'w') as riscos_out:
            for risco in riscos_ativos:
                linha_out = ';'.join((risco.campo, risco.valor, risco.motivo))
                riscos_out.write(linha_out + '\n')
        return redirect('static/%s/%s' % (current_user.name, riscos_out_filename))
    except Exception as err:
        logger.warning(err, exc_info=True)
        flash(str(err))
    return redirect(url_for('edita_risco'))


def get_csv_valido(request):
    if 'csv' not in request.files:
        flash('Arquivo não repassado')
        return False
    csvf = request.files['csv']
    if csvf.filename == '':
        flash('Nome de arquivo vazio')
        return False
    logger.info('FILE***' + csvf.filename)
    if '.' in csvf.filename and csvf.filename.rsplit('.', 1)[1].lower() == 'csv':
        return csvf
    return False


@app.route('/importacsv', methods=['POST', 'GET'])
@login_required
def importacsv():
    """Importar arquivo.

    """
    print('IMPORTA CSV')
    session = app.config.get('dbsession')
    print(request.files)
    print(request.method)
    if request.method == 'POST':
        csvf = get_csv_valido(request)
        if csvf:
            filename = secure_filename(csvf.filename)
            save_name = os.path.join(tmpdir, filename)
            csvf.save(save_name)
            logger.info('CSV RECEBIDO: %s' % save_name)
            with open(save_name) as in_csv:
                lines = in_csv.readlines()
            user_name = current_user.name
            for line in lines:
                campo, valor, motivo = line.split(';')
                insererisco(session,
                            user_name=user_name,
                            campo=campo,
                            valor=valor,
                            motivo=motivo)
    return redirect(url_for('edita_risco'))


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
