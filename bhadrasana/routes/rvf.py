import base64
from datetime import date, timedelta

from ajna_commons.flask.log import logger
from ajna_commons.models.bsonimage import BsonImage
from bhadrasana.forms.filtro_rvf import FiltroRVFForm
from bhadrasana.forms.rvf import RVFForm, ImagemRVFForm
from bhadrasana.models.ovrmanager import get_marcas, get_marcas_choice
from bhadrasana.models.rvfmanager import get_rvfs_filtro, get_rvf, get_ids_anexos, inclui_marca_encontrada, \
    exclui_marca_encontrada, exclui_infracao_encontrada, inclui_infracao_encontrada, \
    get_infracoes, lista_rvfovr, cadastra_imagemrvf, get_imagemrvf_or_none, cadastra_rvf
from bhadrasana.views import csrf
from bson import ObjectId
from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from gridfs import GridFS
from werkzeug.utils import redirect


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

    @app.route('/lista_rvfovr', methods=['POST', 'GET'])
    @login_required
    def listarvfovr():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        listarvfovr = lista_rvfovr(session, ovr_id)
        return render_template('lista_rvfovr.html',
                               listarvfovr=listarvfovr,
                               ovr_id=ovr_id)

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
                print(dict(rvf_form.data.items()))
                rvf_form.validate()
                print(dict(rvf_form.data.items()))
                rvf = cadastra_rvf(session,
                                   user_name=current_user.name,
                                   params=dict(rvf_form.data.items()))
                session.refresh(rvf)
                return redirect(url_for('rvf', id=rvf.id))
            # ELSE
            ovr_id = request.args.get('ovr')
            if ovr_id is not None:
                rvf = cadastra_rvf(session, ovr_id=ovr_id,
                                   user_name=current_user.name)
                session.refresh(rvf)
                return redirect(url_for('rvf', id=rvf.id))
            # ELSE
            db = app.config['mongo_risco']
            marcas = get_marcas(session)
            infracoes = get_infracoes(session)
            rvf_id = request.args.get('id')
            if rvf_id is not None:
                rvf = get_rvf(session, rvf_id)
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

    @csrf.exempt
    @app.route('/api/rvf_imgupload', methods=['POST'])
    def api_rvf_imgupload():
        db = app.config['mongo_risco']
        fs = GridFS(db)
        try:
            rvf_id = request.form.get('rvf_id')
            if rvf_id is None:
                logger.error('Informe o parâmetro rvf_id')
                return jsonify({'msg': 'Informe o parâmetro rvf_id'}), 500
            content = request.form.get('content')
            filename = request.form.get('filename')
            print(len(filename), filename, len(content), type(content))
            if content is None or len(content) < 100:
                logger.error('Imagem vazia ou inválida')
                return jsonify({'msg': 'Imagem vazia ou inválida'}), 500
            if filename is None:
                logger.error('Filename vazio')
                return jsonify({'msg': 'Informe o parâmetro filename'}), 500
            image = base64.decodebytes(content.split(',')[1].encode())
            bson_img = BsonImage()
            bson_img.set_campos(filename, image, rvf_id=rvf_id)
            bson_img.tomongo(fs)
            print(rvf_id, filename)
        except Exception as err:
            logger.error(str(err), exc_info=True)
            return jsonify({'msg': 'Erro: %s' % str(err)}), 500
        return jsonify({'msg': 'imagens incluídas'}), 201

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

    @app.route('/ver_imagens_rvf', methods=['GET'])
    @login_required
    def ver_imagens_rvf():
        session = app.config.get('dbsession')
        db = app.config['mongo_risco']
        rvf_id = None
        imagemativa = None
        anexos = []
        marcas = get_marcas_choice(session)
        oform = ImagemRVFForm(marcas=marcas)
        try:
            rvf_id = request.args.get('rvf_id')
            imagemativa = request.args.get('imagem')
            if rvf_id is None:
                raise Exception('RVF não informado!!!')
            rvf = get_rvf(session, rvf_id)
            imagemrvf = get_imagemrvf_or_none(session, rvf_id, imagemativa)
            if imagemrvf is not None:
                oform = ImagemRVFForm(**imagemrvf.__dict__, marcas=marcas)
            anexos = get_ids_anexos(db, rvf)
            oform.rvf_id.data = rvf_id
            oform.imagem.data = imagemativa
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('imagens_rvf.html',
                               rvf_id=rvf_id,
                               oform=oform,
                               imagemativa=imagemativa,
                               anexos=anexos)

    @app.route('/imagemrvf', methods=['POST'])
    @login_required
    def imagemrvf():
        session = app.config.get('dbsession')
        try:
            oform = ImagemRVFForm(request.form)
            oform.validate()
            cadastra_imagemrvf(session, dict(oform.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return redirect(url_for('ver_imagens_rvf',
                                rvf_id=oform.rvf_id.data,
                                imagem=oform.imagem.data))