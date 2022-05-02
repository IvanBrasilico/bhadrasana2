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
import io
import json
import os
import tempfile
from datetime import date

import ajna_commons.flask.login as login_ajna
import pandas as pd
import plotly
import plotly.graph_objs as go
from PIL import Image
from ajna_commons.flask.conf import ALLOWED_EXTENSIONS, SECRET, logo
from ajna_commons.flask.log import logger
from ajna_commons.flask.user import DBUser
from ajna_commons.utils.images import mongo_image, PIL_tobytes
from flask import (Flask, redirect, render_template, request,
                   url_for, Response, jsonify)
from flask_bootstrap import Bootstrap
# from flask_cors import CORS
from flask_login import current_user
from flask_nav import Nav
from flask_nav.elements import Navbar, View, Separator, Subgroup
from flask_wtf.csrf import CSRFProtect
from plotly.subplots import make_subplots

from bhadrasana.conf import APP_PATH
from bhadrasana.models import get_usuario_telegram, Usuario, get_usuario, Setor
from bhadrasana.models.ovr import OKRObjective
from bhadrasana.models.ovrmanager import get_ovr_responsavel, \
    executa_okr_results
from bhadrasana.routes.plotly_graphs import gauge_plotly


tmpdir = tempfile.mkdtemp()

app = Flask(__name__, static_url_path='/static')
csrf = CSRFProtect(app)
Bootstrap(app)
nav = Nav()
nav.init_app(app)


def configure_app(mongodb, sqlsession, mongo_risco):
    """Configurações gerais e de Banco de Dados da Aplicação."""

    @app.route('/bhadrasana2/login', methods=['GET', 'POST'])
    def bhadrasana_login():
        return login_ajna.login_view(request)

    login_ajna.login_manager.login_view = 'bhadrasana_login'
    app.config['REMEMBER_COOKIE_PATH'] = '/bhadrasana2'

    app.config['DEBUG'] = os.environ.get('DEBUG', 'None') == '1'
    print(app.debug)
    if app.config['DEBUG'] is True:
        app.jinja_env.auto_reload = True
        app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.secret_key = SECRET
    app.config['SECRET_KEY'] = SECRET
    app.config['SESSION_TYPE'] = 'filesystem'
    login_ajna.configure(app)
    print('Setando dbsession fora...')

    DBUser.alchemy_class = Usuario
    # Para usar MySQL como base de Usuários ativar a variável de ambiente SQL_USER
    if os.environ.get('SQL_USER'):
        DBUser.dbsession = sqlsession
    else:
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


def valid_file(file, extensions=['jpg', 'jpeg', 'png']):
    """Valida arquivo passado e retorna validade e mensagem."""
    if not file or file.filename == '' or not allowed_file(file.filename, extensions):
        if not file:
            mensagem = 'Arquivo nao informado'
        elif not file.filename:
            mensagem = 'Nome do arquivo vazio'
        else:
            mensagem = 'Nome de arquivo não permitido: ' + \
                       file.filename
            # print(file)
        return False, mensagem
    return True, None


def convert_value(value):
    """Tenta converter valor de qualquer tipo para float.

        Tenta converter valor de qualquer tipo para float, se falhar retorna
        uma str com tipo de falha. Em sucesso, retorna float.
    """
    if not value:
        return 'Valor Nulo'
    try:
        return float(value)
    except Exception as err:
        return 'Erro na conversão: %s' % str(err)


@app.template_filter()
def sem_casa_decimal(value):
    value = convert_value(value)
    if isinstance(value, str):
        logger.error('sem_casa_decimal: %s' % value)
        return value
    return '{0:,.0f}'.format(value).replace(',', 'X'). \
        replace('.', ',').replace('X', '.')


@app.template_filter()
def uma_casa_decimal(value):
    value = convert_value(value)
    if isinstance(value, str):
        logger.error('uma_casa_decimal: %s' % value)
        return value
    return '{0:,.1f}'.format(value).replace(',', 'X'). \
        replace('.', ',').replace('X', '.')


@app.template_filter()
def duas_casas_decimais(value):
    value = convert_value(value)
    if isinstance(value, str):
        logger.error('uma_casa_decimal: %s' % value)
        return value
    return '{0:,.2f}'.format(value).replace(',', 'X'). \
        replace('.', ',').replace('X', '.')


@app.template_filter()
def moeda(value):
    value = convert_value(value)
    if isinstance(value, str):
        logger.error('moeda: %s' % value)
        return value
    return 'R$ {:,.2f}'.format(float(value)).replace(',', 'X'). \
        replace('.', ',').replace('X', '.')


@app.template_filter()
def mascara_cpf_cnpj(value):
    if value:
        if len(value) == 11:
            return value[:3] + '.' + value[3:6] + '.' + value[6:9] + '-' + value[9:]
        elif len(value) == 14:
            return value[:2] + '.' + value[2:5] + '.' + value[5:8] + '/' + \
                   value[8:12] + '-' + value[12:]
    else:
        return 'Não informado'
    return value


@app.template_filter()
def mascara_nao_informado(value):
    if value:
        return value
    else:
        return 'Não informado'


@app.route('/')
def index():
    """View retorna index.html ou login se não autenticado."""
    if current_user.is_authenticated:
        session = app.config.get('dbsession')
        datas_objective = ''
        ovrs = get_ovr_responsavel(session, current_user.id)
        liberadas = sum([ovr.fase == 0 for ovr in ovrs])
        ativas = sum([ovr.fase == 1 for ovr in ovrs])
        supensas = sum([ovr.fase == 2 for ovr in ovrs])
        df = pd.DataFrame({
            'Fase': ['Liberada', 'Ativa', 'Suspensa'],
            'Qtde': [liberadas, ativas, supensas],
        })
        fig = make_subplots(rows=2, cols=3, horizontal_spacing=0.1,
                            specs=[[{"type": "pie"}, {"type": "indicator"}, {"type": "indicator"}],
                                   [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]])
        fichas_pie = go.Pie(labels=df.Fase.values, values=df.Qtde.values,
                            textinfo='label+value',
                            insidetextorientation='radial',
                            title='Resumo das minhas Fichas')
        row = 1
        col = 1
        fig.add_trace(fichas_pie, row=row, col=col)
        usuario = get_usuario(session, current_user.name)
        setor_id = usuario.setor_id
        objective = session.query(OKRObjective).filter(OKRObjective.setor_id == setor_id). \
            order_by(OKRObjective.id.desc()).first()
        if not objective:
            setor = session.query(Setor).filter(Setor.id == setor_id).one()
            if setor.pai_id:
                objective = session.query(OKRObjective).filter(OKRObjective.setor_id == setor.pai_id). \
                    order_by(OKRObjective.id.desc()).first()
        if objective:
            results = executa_okr_results(session, objective)
            for result in results[:5]:
                delta = ((date.today() - objective.inicio.date()) /
                         (objective.fim - objective.inicio)) * result.ameta
                indicator = gauge_plotly(result.result.nome, result.ameta,
                                         sum([row['result'] for row in result.resultados]),
                                         delta)
                col += 1
                if col > 3:
                    col = 1
                    row += 1
                fig.add_trace(indicator, row=row, col=col)
        fig.update_layout(
            # grid={'rows': 2, 'columns': 3, 'pattern': "independent"},
            margin=dict(r=0, t=0, b=0, l=0),
        )
        fig.update(layout_showlegend=False)
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return render_template('index.html', plots=[], objective=objective, graphJSON=graphJSON)
    else:
        return redirect(url_for('commons.login'))


def image_id(db, _id):
    """Recupera a imagem do banco e serializa para stream HTTP.

    """
    image = mongo_image(db, _id)
    try:
        size = request.args.get('size')
        if size:
            width, height = map(int, size.split(','))
            pil_img = Image.open(io.BytesIO(image))
            pil_img.thumbnail((width, height))
            image = PIL_tobytes(pil_img)
    except Exception as err:
        logger.error('Erro ao processar parâmetro size em /image: %s' % str(err))

    if image:
        return Response(response=image, mimetype='image/jpeg')
    return 'Sem Imagem'


@app.route('/image/<_id>')
def foto(_id):
    db = app.config['mongo_risco']
    return image_id(db, _id)


@app.route('/scan/<_id>')
def scan(_id):
    db = app.config['mongodb']
    return image_id(db, _id)


@app.route('/anexo_filename')
def anexo_filename():
    """Recupera anexo do banco e retorna campo filename

    """
    db = app.config['mongo_risco']
    filtro = {'metadata.' + key: value for key, value in request.args.items()}
    row = db['fs.files'].find_one(filtro)
    if row:
        return row['filename']
    return 'Sem Anexo'


@app.route('/anexo')
def anexo():
    """Recupera aenxo do banco e serializa para stream HTTP.

    """
    db = app.config['mongo_risco']
    filtro = {'metadata.' + key: value for key, value in request.args.items()}
    row = db['fs.files'].find_one(filtro)
    if row:
        _id = row['_id']
        mimetype = row.get('metadata').get('contentType') or 'image/jpeg'
        image = mongo_image(db, _id)
        print(mimetype)
        if image:
            return Response(response=image, mimetype=mimetype)
    return 'Sem Anexo'


@app.route('/tui-image-editor')
def tui_image_editor():
    """Exibe o editor Open Source JS (licença MIT) TUI Image Editor."""
    return render_template('tui_image_editor.html')


@app.route('/image-editor/<_id>')
def image_editor(_id):
    """Exibe o editor Open Source JS (licença MIT) FileRobot."""
    return render_template('filerobot.html', _id=_id)


@app.route('/get_cpf_telegram/<telegram_user>')
def get_cpf_telegram(telegram_user):
    """Exibe o editor Open Source JS (licença MIT) FileRobot."""
    session = app.config.get('dbsession')
    user = get_usuario_telegram(session, telegram_user)
    if user is None:
        return jsonify({'cpf': None}), 404
    return jsonify({'cpf': user.cpf}), 200


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
                 Separator(),
                 View('Assistente de Contrafação', 'autos_contrafacao'),
             ),
             Subgroup(
                 'Administração/exportações',
                 View('Exporta Planilha CEN Rilo', 'exporta_cen_rilo'),
                 View('Gerador de documentos docx', 'gera_docx'),
                 View('Lista para escaneamento no Operador', 'escaneamento_operador'),
                 View('Assistente de TG', 'assistente_tg'),
                 Separator(),
                 View('Importa planilhas recintos', 'importa_planilha_recinto'),
                 View('Administração', 'admin.index'),
             )]
    if current_user.is_authenticated:
        items.append(View('Sair (%s)' % current_user.id, 'commons.logout'))
    return Navbar(logo, *items)
