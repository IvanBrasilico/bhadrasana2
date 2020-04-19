import base64
import io
from datetime import date, timedelta

from PIL import Image
from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from gridfs import GridFS
from werkzeug.utils import redirect

from ajna_commons.flask.log import logger
from ajna_commons.models.bsonimage import BsonImage
from ajna_commons.utils.images import PIL_tobytes, ImageBytesTansFormations
from bhadrasana.forms.filtro_rvf import FiltroRVFForm
from bhadrasana.forms.rvf import RVFForm, ImagemRVFForm
from bhadrasana.models.ovrmanager import get_marcas, get_marcas_choice
from bhadrasana.models.rvfmanager import get_rvfs_filtro, get_rvf, get_ids_anexos_ordenado, \
    inclui_marca_encontrada, ressuscita_anexos_perdidos, \
    exclui_marca_encontrada, exclui_infracao_encontrada, inclui_infracao_encontrada, \
    get_infracoes, lista_rvfovr, cadastra_imagemrvf, get_imagemrvf_or_none, cadastra_rvf, delete_imagemrvf, \
    inclui_imagemrvf, get_imagemrvf_imagem_or_none, make_and_save_transformation
from bhadrasana.views import csrf, valid_file


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
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_rvf.html',
                               oform=filtro_form,
                               rvfs=rvfs)

    @app.route('/lista_rvfovr', methods=['POST', 'GET'])
    @login_required
    def listarvfovr():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        lista = lista_rvfovr(session, ovr_id)
        return render_template('lista_rvfovr.html',
                               listarvfovr=lista,
                               ovr_id=ovr_id)

    @app.route('/rvf', methods=['POST', 'GET'])
    @login_required
    def _rvf():
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
                # Temporário - para recuperar imagens "perdidas" na transição
                ressuscita_anexos_perdidos(db, session, rvf)
                anexos = get_ids_anexos_ordenado(rvf)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('rvf.html',
                               infracoes=infracoes,
                               marcas=marcas,
                               oform=rvf_form,
                               infracoes_encontradas=infracoes_encontradas,
                               marcas_encontradas=marcas_encontradas,
                               anexos=anexos)

    @app.route('/rvf_impressao/<rvf_id>', methods=['GET'])
    @login_required
    def rvf_impressao(rvf_id):
        session = app.config.get('dbsession')
        db = app.config['mongo_risco']
        marcas_encontradas = []
        anexos = []
        rvf = None
        try:
            rvf = get_rvf(session, rvf_id)
            if rvf is None:
                flash('rvf %s não encontrado.' % rvf_id)
                return redirect(url_for('pesquisa_rvf'))
            marcas_encontradas = rvf.marcasencontradas
            # Temporário - para recuperar imagens "perdidas" na transição
            ressuscita_anexos_perdidos(db, session, rvf)
            anexos = get_ids_anexos_ordenado(rvf)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(err))
        return render_template('rvf_impressao.html',
                               rvf=rvf,
                               marcas_encontradas=marcas_encontradas,
                               anexos=anexos)

    @app.route('/inclui_infracao_encontrada', methods=['GET'])
    @login_required
    def inclui_infracao():
        session = app.config.get('dbsession')
        rvf_id = request.args.get('rvf_id')
        infracao_nome = request.args.get('infracao_nome')
        novas_infracoes = inclui_infracao_encontrada(session, rvf_id, infracao_nome)
        return jsonify([{'id': infracao.id, 'nome': infracao.nome}
                        for infracao in novas_infracoes])

    @app.route('/exclui_infracao_encontrada', methods=['GET'])
    @login_required
    def exclui_infracao():
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
        session = app.config.get('dbsession')
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
            inclui_imagemrvf(db, session, image, filename, rvf_id)
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
        session = app.config.get('dbsession')
        rvf_id = delete_imagemrvf(db, session, _id)
        return redirect(url_for('rvf', id=rvf_id))

    @app.route('/ver_imagens_rvf', methods=['GET'])
    @login_required
    def ver_imagens_rvf():
        db = app.config['mongo_risco']
        session = app.config.get('dbsession')
        rvf_id = None
        idimagemativa = None
        anexos = []
        marcas = get_marcas_choice(session)
        oform = ImagemRVFForm(marcas=marcas)
        try:
            rvf_id = request.args.get('rvf_id')
            idimagemativa = request.args.get('imagem')
            if rvf_id is None:
                raise Exception('RVF não informado!!!')
            # Temporário - para recuperar imagens "perdidas" na transição
            rvf = get_rvf(session, rvf_id)
            ressuscita_anexos_perdidos(db, session, rvf)
            anexos = get_ids_anexos_ordenado(rvf)
            aimagemrvf = get_imagemrvf_or_none(session, rvf_id, idimagemativa)
            if aimagemrvf is not None:
                oform = ImagemRVFForm(**aimagemrvf.__dict__, marcas=marcas)
            oform.rvf_id.data = rvf_id
            oform.imagem.data = idimagemativa
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('imagens_rvf.html',
                               rvf_id=rvf_id,
                               oform=oform,
                               imagemativa=idimagemativa,
                               anexos=anexos)

    @app.route('/imagemrvf', methods=['POST'])
    @login_required
    def imagemrvf():
        session = app.config.get('dbsession')
        oform = ImagemRVFForm()
        try:
            oform = ImagemRVFForm(request.form)
            oform.validate()
            cadastra_imagemrvf(session, dict(oform.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ver_imagens_rvf',
                                rvf_id=oform.rvf_id.data,
                                imagem=oform.imagem.data))

    @app.route('/transformimagemrvf/<id_imagem>/<transformation>', methods=['GET'])
    @login_required
    def transformimagemrvf(id_imagem, transformation):
        def rotate(image_bytes):
            pil_img = Image.open(io.BytesIO(image_bytes))
            pil_img = pil_img.transpose(Image.ROTATE_90)
            return PIL_tobytes(pil_img)

        db = app.config['mongo_risco']
        session = app.config.get('dbsession')
        rvf_id = None
        new_id = None
        try:
            imagemrvf = get_imagemrvf_imagem_or_none(session, id_imagem)
            if imagemrvf:
                rvf_id = imagemrvf.rvf_id
                transform_function = ImageBytesTansFormations.get_tranformation(
                    transformation)
                new_id = make_and_save_transformation(db, session, imagemrvf,
                                                      transform_function)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ver_imagens_rvf',
                                rvf_id=rvf_id,
                                imagem=new_id))
