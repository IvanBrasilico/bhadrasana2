from datetime import date, timedelta

from bson import ObjectId
from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required
from gridfs import GridFS
from werkzeug.utils import redirect

from ajna_commons.flask.log import logger
from ajna_commons.models.bsonimage import BsonImage
from bhadrasana.forms.filtro_rvf import FiltroRVFForm
from bhadrasana.forms.rvf import RVFForm
from bhadrasana.models.rvfmanager import get_rvfs_filtro, cadastra_rvf, get_rvf_ovr, \
    get_rvf, get_marcas, get_ids_anexos, inclui_marca_encontrada, \
    exclui_marca_encontrada, exclui_infracao_encontrada, inclui_infracao_encontrada, \
    get_infracoes


def rvf_app(app):
    @app.route('/pesquisa_rvf', methods=['POST', 'GET'])
    @login_required
    def pesquisa_rvf():
        session = app.config.get('dbsession')
        rvfs = []
        filtro_form = FiltroRVFForm(datainicio=date.today() - timedelta(days=10),
                                    datafim=date.today())
        try:
            if request.method == 'POST':
                filtro_form = FiltroRVFForm(request.form)
                filtro_form.validate()
                rvfs = get_rvfs_filtro(session, dict(filtro_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('pesquisa_rvf.html',
                               oform=filtro_form,
                               rvfs=rvfs)

    @app.route('/rvf', methods=['POST', 'GET'])
    @login_required
    def rvf():
        session = app.config.get('dbsession')
        infracoes = []
        infracoes_encontradas = []
        marcas = []
        marcas_encontradas = []
        anexos = []
        rvf = None
        rvf_form = RVFForm()
        try:
            if request.method == 'POST':
                rvf_form = RVFForm(request.form)
                rvf_form.adata.data = request.form['adata']
                rvf_form.ahora.data = request.form['ahora']
                rvf_form.validate()
                rvf = cadastra_rvf(session, dict(rvf_form.data.items()))
                return redirect(url_for('rvf', id=rvf.id))
            # ELSE
            db = app.config['mongo_risco']
            marcas = get_marcas(session)
            infracoes = get_infracoes(session)
            rvf_id = request.args.get('id')
            if rvf_id is not None:
                rvf = get_rvf(session, rvf_id)
            else:
                ovr_id = request.args.get('ovr')
                if ovr_id is not None:
                    rvf = get_rvf_ovr(session, ovr_id=ovr_id)
                    if rvf is None:
                        rvf = cadastra_rvf(session, ovr_id=ovr_id)
            if rvf is not None:
                rvf_form = RVFForm(**rvf.__dict__)
                if rvf.datahora:
                    rvf_form.adata.data = rvf.datahora.date()
                    rvf_form.ahora.data = rvf.datahora.time()
                rvf_form.id.data = rvf.id
                infracoes_encontradas = rvf.infracoesencontradas
                marcas_encontradas = rvf.marcasencontradas
                anexos = get_ids_anexos(db, rvf)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('rvf.html',
                               infracoes=infracoes,
                               marcas=marcas,
                               oform=rvf_form,
                               infracoes_encontradas=infracoes_encontradas,
                               marcas_encontradas=marcas_encontradas,
                               anexos=anexos)

    @app.route('/rvf_impressao/<id>', methods=['GET'])
    @login_required
    def rvf_impressao(id):
        session = app.config.get('dbsession')
        db = app.config['mongo_risco']
        marcas_encontradas = []
        anexos = []
        rvf = None
        rvf = get_rvf(session, id)
        if rvf is None:
            flash('rvf %s não encontrado.' % id)
            return redirect(url_for('pesquisa_rvf'))
        marcas_encontradas = rvf.marcasencontradas
        anexos = get_ids_anexos(db, rvf)
        return render_template('rvf_impressao.html',
                               rvf=rvf,
                               marcas_encontradas=marcas_encontradas,
                               anexos=anexos)

    @app.route('/inclui_infracao_encontrada', methods=['GET'])
    @login_required
    def inclui_Infracao():
        session = app.config.get('dbsession')
        rvf_id = request.args.get('rvf_id')
        infracao_nome = request.args.get('infracao_nome')
        novas_infracoes = inclui_infracao_encontrada(session, rvf_id, infracao_nome)
        return jsonify([{'id': infracao.id, 'nome': infracao.nome}
                        for infracao in novas_infracoes])

    @app.route('/exclui_infracao_encontrada', methods=['GET'])
    @login_required
    def exclui_Infracao():
        session = app.config.get('dbsession')
        rvf_id = request.args.get('rvf_id')
        infracao_id = request.args.get('infracao_id')
        novas_infracoes = exclui_infracao_encontrada(session, rvf_id, infracao_id)
        return jsonify([{'id': infracao.id, 'nome': infracao.nome}
                        for infracao in novas_infracoes])

    @app.route('/inclui_marca_encontrada', methods=['GET'])
    @login_required
    def inclui_marca():
        session = app.config.get('dbsession')
        rvf_id = request.args.get('rvf_id')
        marca_nome = request.args.get('marca_nome')
        novas_marcas = inclui_marca_encontrada(session, rvf_id, marca_nome)
        return jsonify([{'id': marca.id, 'nome': marca.nome} for marca in novas_marcas])

    @app.route('/exclui_marca_encontrada', methods=['GET'])
    @login_required
    def exclui_marca():
        session = app.config.get('dbsession')
        rvf_id = request.args.get('rvf_id')
        marca_id = request.args.get('marca_id')
        novas_marcas = exclui_marca_encontrada(session, rvf_id, marca_id)
        return jsonify([{'id': marca.id, 'nome': marca.nome} for marca in novas_marcas])

    def allowed_file(filename, extensions):
        """Checa extensões permitidas."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in extensions

    def valid_file(file, extensions=['jpg', 'jpeg']):
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

    @app.route('/rvf_imgupload', methods=['POST'])
    @login_required
    def rvf_imgupload():
        db = app.config['mongo_risco']
        fs = GridFS(db)
        rvf_id = request.form.get('rvf_id')
        if rvf_id is None:
            flash('Escolha um RVF antes')
            return redirect(url_for('rvf'))
        for file in request.files.getlist('images'):
            print('Arquivo:', file)
            validfile, mensagem = valid_file(file)
            if not validfile:
                flash(mensagem)
                print('Não é válido %s' % mensagem)
                return redirect(url_for('rvf', id=rvf_id))
            content = file.read()
            bson_img = BsonImage()
            bson_img.set_campos(file.filename, content, rvf_id=rvf_id)
            bson_img.tomongo(fs)
        return redirect(url_for('rvf', id=rvf_id))

    @app.route('/exclui_anexo')
    def exclui_anexo():
        """Exclui _id de fs.files

        """
        _id = request.args.get('_id')
        db = app.config['mongo_risco']
        grid_out = db['fs.files'].find_one({'_id': ObjectId(_id)})
        rvf_id = grid_out['metadata']['rvf_id']
        db['fs.files'].delete_one({'_id': ObjectId(_id)})
        return redirect(url_for('rvf', id=rvf_id))
