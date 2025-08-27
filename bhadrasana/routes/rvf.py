import base64
import os
import zipfile
from ajna_commons.flask.log import logger
from ajna_commons.utils.images import ImageBytesTansformations
from bson import ObjectId
from datetime import date, timedelta, datetime
from flask import request, flash, render_template, url_for, jsonify, send_file
from flask_login import login_required, current_user
from gridfs import GridFS
from io import BytesIO
from werkzeug.utils import redirect
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.exceptions import BadRequest

from bhadrasana.conf import APP_PATH
from bhadrasana.docx.docx_functions import gera_OVR, gera_taseda, gera_cencomm_importacao
from bhadrasana.forms.filtro_rvf import FiltroRVFForm
from bhadrasana.forms.rvf import RVFForm, ImagemRVFForm, ApreensaoRVFForm
from bhadrasana.models import get_usuario_validando, get_usuario
from bhadrasana.models.ovr_dict_repr import OVRDict
from bhadrasana.models.ovrmanager import get_marcas, get_marcas_choice
from bhadrasana.models.rvf import RVF
from bhadrasana.models.rvfmanager import get_rvfs_filtro, get_rvf, \
    get_ids_anexos_ordenado, \
    inclui_marca_encontrada, ressuscita_anexos_perdidos, \
    exclui_marca_encontrada, exclui_infracao_encontrada, inclui_infracao_encontrada, \
    get_infracoes, lista_rvfovr, cadastra_imagemrvf, get_imagemrvf_or_none, \
    cadastra_rvf, delete_imagemrvf, inclui_imagemrvf, get_imagemrvf_imagem_or_none, \
    make_and_save_transformation, exclui_lacre_verificado, \
    inclui_lacre_verificado, get_imagemrvf, inclui_nova_ordem_arquivo, \
    get_anexos_ordenado, get_tiposapreensao_choice, gera_apreensao_rvf, \
    exclui_apreensao_rvf, get_peso, rvf_ordena_imagensrvf_por_data_criacao, \
    get_anexos_mongo, get_infracoes_choice, get_k9s, inclui_k9_utilizada, exclui_k9_utilizada
from bhadrasana.views import csrf, valid_file, get_user_save_path


def rvf_app(app):
    @app.route('/pesquisa_rvf', methods=['POST', 'GET'])
    @login_required
    def pesquisa_rvf():
        session = app.config.get('dbsession')
        rvfs = []
        filtro_form = FiltroRVFForm(datainicio=date.today() - timedelta(days=10),
                                    datafim=date.today())
        title_page = 'Pesquisa RVF'
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
                               rvfs=rvfs,
                               title_page=title_page)


    @app.route('/lista_rvfovr', methods=['POST', 'GET'])
    @login_required
    def listarvfovr():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        lista = lista_rvfovr(session, ovr_id)
        title_page = 'Verificações Físicas'
        return render_template('lista_rvfovr.html',
                               listarvfovr=lista,
                               ovr_id=ovr_id,
                               title_page=title_page)

    @app.route('/rvf', methods=['POST', 'GET'])
    @login_required
    def rvf():
        session = app.config.get('dbsession')
        get_usuario_validando(session, current_user.id)
        tiposapreensao = get_tiposapreensao_choice(session)
        apreensao_form = ApreensaoRVFForm(tiposapreensao=tiposapreensao)
        apreensoes_rvf = []
        infracoes = []
        infracoes_encontradas = []
        marcas = []
        marcas_encontradas = []
        anexos = []
        lacres_verificados = []
        k9s = []
        k9s_utilizados = []
        arvf = None
        rvf_form = RVFForm()
        title_page = 'RVF'
        try:
            if request.method == 'POST':
                rvf_form = RVFForm(request.form)
                rvf_form.adata.data = request.form['adata']
                rvf_form.ahora.data = request.form['ahora']
                rvf_form.validate()
                arvf = cadastra_rvf(session,
                                    user_name=current_user.name,
                                    params=dict(rvf_form.data.items()))
                session.refresh(arvf)
                return redirect(url_for('rvf', id=arvf.id))
            # ELSE
            ovr_id = request.args.get('ovr')
            if ovr_id is not None:
                arvf = cadastra_rvf(session, ovr_id=ovr_id,
                                    user_name=current_user.name)
                session.refresh(arvf)
                return redirect(url_for('rvf', id=arvf.id))
            # ELSE
            db = app.config['mongo_risco']
            marcas = get_marcas(session)
            infracoes = get_infracoes(session)
            k9s = get_k9s(session)
            rvf_id = request.args.get('id')
            title_page = 'RVF ' + rvf_id
            if rvf_id is not None:
                arvf = get_rvf(session, rvf_id)
                print('arvf.inspecaonaoinvasiva', arvf.inspecaonaoinvasiva)
            if arvf is not None:
                rvf_form = RVFForm(**arvf.__dict__)
                if arvf.datahora:
                    rvf_form.adata.data = arvf.datahora.date()
                    rvf_form.ahora.data = arvf.datahora.time()
                rvf_form.id.data = arvf.id
                rvf_form.peso_manifestado.data = get_peso(session,
                                                          rvf_form.numeroCEmercante.data,
                                                          rvf_form.numerolote.data)
                apreensoes_rvf = arvf.apreensoes
                infracoes_encontradas = arvf.infracoesencontradas
                marcas_encontradas = arvf.marcasencontradas
                lacres_verificados = arvf.lacresverificados
                k9s_utilizados = arvf.k9sutilizados
                # Temporário - para recuperar imagens 'perdidas' na transição
                ressuscita_anexos_perdidos(db, session, arvf)
                anexos = get_ids_anexos_ordenado(arvf)
                usuario = get_usuario(session, arvf.user_name)
                if usuario:
                    rvf_form.user_descricao.data = usuario.nome

        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('rvf.html',
                               infracoes=infracoes,
                               marcas=marcas,
                               k9s=k9s,
                               oform=rvf_form,
                               apreensao_form=apreensao_form,
                               apreensoes=apreensoes_rvf,
                               infracoes_encontradas=infracoes_encontradas,
                               marcas_encontradas=marcas_encontradas,
                               k9s_utilizados = k9s_utilizados,
                               lacres_verificados=lacres_verificados,
                               anexos=anexos,
                               title_page=title_page)

    @app.route('/rvf_impressao/<rvf_id>', methods=['GET'])
    @login_required
    def rvf_impressao(rvf_id):
        session = app.config.get('dbsession')
        marcas_encontradas = []
        anexos = []
        rvf = None
        try:
            rvf = get_rvf(session, rvf_id)
            if rvf is None:
                flash('rvf %s não encontrado.' % rvf_id)
                return redirect(url_for('pesquisa_rvf'))
            marcas_encontradas = rvf.marcasencontradas
            anexos = get_ids_anexos_ordenado(rvf)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(err))
        return render_template('rvf_impressao.html',
                               rvf=rvf,
                               marcas_encontradas=marcas_encontradas,
                               anexos=anexos)

    @app.route('/rvf_docx', methods=['GET', 'POST'])
    @login_required
    def rvf_OVR():
        session = app.config.get('dbsession')
        mongodb = app.config.get('mongo_risco')

        # request.values cobre GET e POST
        rvf_id = request.values.get('rvf_id')
        tipo = (request.values.get('tipo', 'OVR') or 'OVR').strip().lower()  # ovr, taseda, cencomm_rvf
        imagens_ids_str = (request.values.get('imagens_ids') or '').strip()

        try:
            rvf = get_rvf(session, rvf_id)
            if rvf is None:
                flash('rvf %s não encontrado.' % rvf_id)
                return redirect(url_for('pesquisa_rvf'))

            # Monta o dicionário-base para o gerador
            rvf_dump = OVRDict(1).monta_rvf_dict(mongodb, session, rvf_id)

            # Se receber seleção de imagens, filtra o dump
            selected_ids = set([s for s in imagens_ids_str.split(',') if s]) if imagens_ids_str else set()
            if selected_ids:
                def _img_id(img):
                    return str(
                        img.get('id')
                        or img.get('_id')
                        or img.get('imagem')
                        or img.get('codigo')
                        or img.get('url')
                        or ''
                    )

                def _filtra_imagens_em_dict(d):
                    if not isinstance(d, dict):
                        return d
                    if 'imagens' in d and isinstance(d['imagens'], list):
                        d['imagens'] = [img for img in d['imagens'] if _img_id(img) in selected_ids]
                    if 'rvfs' in d and isinstance(d['rvfs'], list):
                        for rvf_it in d['rvfs']:
                            if isinstance(rvf_it, dict) and 'imagens' in rvf_it and isinstance(rvf_it['imagens'], list):
                                rvf_it['imagens'] = [img for img in rvf_it['imagens'] if _img_id(img) in selected_ids]
                    return d

                rvf_dump = _filtra_imagens_em_dict(rvf_dump)

            # Seleciona gerador e mantém padrão de nomes anterior
            agora = datetime.strftime(datetime.now(), '%Y-%m%dT%H%M%S')
            if tipo == 'taseda':
                document = gera_taseda(rvf_dump, current_user.name)
                # mantém o padrão antigo: taseda_FCC{rvf_id}-{timestamp}.docx
                out_name = f'taseda_FCC{rvf_id}-{agora}.docx'
            elif tipo == 'cencomm_rvf':
                # Usa o modelo específico CENcomm_Importacao.docx
                document = gera_cencomm_importacao(rvf_dump, current_user.name)
                out_name = f'CENCOMM_IMPORTACAO_FCC{rvf.ovr_id}_RVF{rvf_id}_datahora{agora}.docx'
            else:
                document = gera_OVR(rvf_dump, current_user.name)
                out_name = f'OVR_FCC{rvf.ovr_id}_RVF{rvf_id}_datahora{agora}.docx'

            document.save(os.path.join(get_user_save_path(), out_name))
            return redirect('static/%s/%s' % (current_user.name, out_name))

        except Exception as err:
            logger.warning(err, exc_info=True)
            flash(str(err))
        return redirect(url_for('rvf', id=rvf_id, _scheme='https'))

    @app.route('/inclui_lacre_verificado', methods=['GET'])
    @login_required
    def inclui_lacre_():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            lacre_numero = request.args.get('lacre_numero')
            novos_lacres = inclui_lacre_verificado(session, rvf_id, lacre_numero)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': lacre.id, 'numero': lacre.numero}
                        for lacre in novos_lacres]), 201

    @app.route('/exclui_lacre_verificado', methods=['GET'])
    @login_required
    def exclui_lacre_():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            lacre_id = request.args.get('lacre_id')
            novos_lacres = exclui_lacre_verificado(session, rvf_id, lacre_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': lacre.id, 'numero': lacre.numero}
                        for lacre in novos_lacres]), 201

    @app.route('/inclui_infracao_encontrada', methods=['GET'])
    @login_required
    def inclui_infracao():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            infracao_nome = request.args.get('infracao_nome')
            novas_infracoes = inclui_infracao_encontrada(session, rvf_id, infracao_nome)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': infracao.id, 'nome': infracao.nome}
                        for infracao in novas_infracoes]), 201

    @app.route('/exclui_infracao_encontrada', methods=['GET'])
    @login_required
    def exclui_infracao():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            infracao_id = request.args.get('infracao_id')
            novas_infracoes = exclui_infracao_encontrada(session, rvf_id, infracao_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': infracao.id, 'nome': infracao.nome}
                        for infracao in novas_infracoes]), 201

    @app.route('/inclui_marca_encontrada', methods=['GET'])
    @login_required
    def inclui_marca():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            marca_nome = request.args.get('marca_nome')
            novas_marcas = inclui_marca_encontrada(session, rvf_id, marca_nome)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': marca.id, 'nome': marca.nome}
                        for marca in novas_marcas]), 201

    @app.route('/exclui_marca_encontrada', methods=['GET'])
    @login_required
    def exclui_marca():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            marca_id = request.args.get('marca_id')
            novas_marcas = exclui_marca_encontrada(session, rvf_id, marca_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': marca.id, 'nome': marca.nome}
                        for marca in novas_marcas]), 201

    @app.route('/inclui_k9_utilizada', methods=['GET'])
    @login_required
    def inclui_k9():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            k9_nome = request.args.get('k9_nome')
            k9s = inclui_k9_utilizada(session, rvf_id, k9_nome)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': k9.id, 'nome': k9.nome}
                        for k9 in k9s]), 201

    @app.route('/exclui_k9_utilizada', methods=['GET'])
    @login_required
    def exclui_k9():
        try:
            session = app.config.get('dbsession')
            rvf_id = request.args.get('rvf_id')
            k9_id = request.args.get('k9_id')
            k9s = exclui_k9_utilizada(session, rvf_id, k9_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': k9.id, 'nome': k9.nome}
                        for k9 in k9s]), 201


    @app.route('/rvf_imgupload', methods=['POST'])
    @login_required
    def rvf_imgupload():
        request.max_form_memory_size = 5 * 1024 * 1024
        db = app.config['mongo_risco']

        # 1) Logue as chaves recebidas no form e nos arquivos
        logger.debug(f"FORM keys: {list(request.form.keys())}")
        logger.debug(f"FILES keys: {list(request.files.keys())}")

        # 2) Tente extrair um inteiro de rvf_id de forma segura
        raw_rvf = request.form.get('rvf_id', '').strip()
        logger.debug(f"rvf_id raw: '{raw_rvf}'")
        try:
            rvf_id = int(raw_rvf)
        except ValueError:
            logger.error(f"rvf_id inválido: '{raw_rvf}'")
            flash("rvf_id inválido ou ausente")
            return redirect(url_for('rvf'))

        # 3) Comece o processamento
        try:
            session = app.config.get('dbsession')

            # Se não houver arquivos, avisar
            imagens = request.files.getlist('images')
            if not imagens:
                logger.error("Nenhum arquivo em request.files['images']")
                flash("Nenhuma imagem enviada")
                return redirect(url_for('rvf', id=rvf_id))

            for file in imagens:
                logger.debug(f"Arquivo recebido: {file.filename!r}, content_type={file.content_type}")
                validfile, mensagem = valid_file(file)
                if not validfile:
                    logger.error(f"Imagem inválida: {mensagem}")
                    flash(mensagem)
                    return redirect(url_for('rvf', id=rvf_id))

                content = file.read()
                inclui_imagemrvf(db, session, content, file.filename, rvf_id)

        except RequestEntityTooLarge:
            # Deixa o errorhandler de 413 tratar este caso
            raise
        except Exception as err:
            # Log completo do traceback
            logger.error("Erro em rvf_imgupload", exc_info=True)
            flash(f"Erro ao processar o upload: {err}")

        return redirect(url_for('rvf', id=rvf_id))

    # telegram - upload_foto
    @csrf.exempt
    @app.route('/api/rvf_imgupload', methods=['POST'])
    def api_rvf_imgupload():
        request.max_form_memory_size = 5 * 1024 * 1024
        db = app.config['mongo_risco']
        session = app.config.get('dbsession')
        logger.debug("→ request.max_content_length   = %r", request.max_content_length)
        logger.debug("→ request.max_form_memory_size = %r", request.max_form_memory_size)
        try:
            rvf_id = request.form.get('rvf_id')
            if rvf_id is None:
                logger.error('Informe o parâmetro rvf_id')
                return jsonify({'msg': 'Informe o parâmetro rvf_id'}), 500
            content = request.form.get('content')
            filename = request.form.get('filename')
            dataModificacao = datetime.strptime(request.form.get('dataModificacao').split('.')[0],
                                                '%Y-%m-%dT%H:%M:%S')
            print(len(filename), filename, len(content), type(content), dataModificacao)
            if content is None or len(content) < 100:
                logger.error('Imagem vazia ou inválida')
                return jsonify({'msg': 'Imagem vazia ou inválida'}), 500
            if filename is None:
                logger.error('Filename vazio')
                return jsonify({'msg': 'Informe o parâmetro filename'}), 500
            try:
                image = base64.decodebytes(content.split(',')[1].encode())
            except IndexError:
                image = base64.decodebytes(content.encode())
            inclui_imagemrvf(db, session, image, filename, rvf_id, dataModificacao)
        except RequestEntityTooLarge:
            # deixa escapar para o handler global de 413
            raise
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
        try:
            rvf_id = delete_imagemrvf(db, session, _id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify({'msg': ' RVF %s excluída' % rvf_id}), 204

    @app.route('/ver_imagens_rvf', methods=['GET'])
    @login_required
    def ver_imagens_rvf():
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
            rvf = get_rvf(session, rvf_id)
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
        db = app.config['mongo_risco']
        session = app.config.get('dbsession')
        rvf_id = None
        new_id = None
        try:
            aimagemrvf = get_imagemrvf_imagem_or_none(session, id_imagem)
            if aimagemrvf:
                rvf_id = aimagemrvf.rvf_id
                transform_function = ImageBytesTansformations.get_tranformation(
                    transformation)
                new_id = make_and_save_transformation(db, session, aimagemrvf,
                                                      transform_function)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ver_imagens_rvf',
                                rvf_id=rvf_id,
                                imagem=new_id))

    @app.route('/rvf_inclui_ordem_arquivos', methods=['GET'])
    @login_required
    def rvf_inclui_ordem_arquivos():
        session = app.config.get('dbsession')
        rvf_id = request.args.get('rvf_id')
        qttd_arq = request.args.get('qttd_arq')
        nomes_anexo = request.args.getlist('lista[]')
        oform = ImagemRVFForm()
        sucesso = False
        try:
            oform = ImagemRVFForm(request.form)
            oform.validate()
            for n in range(int(qttd_arq)):
                imagem = get_imagemrvf(session, rvf_id, nomes_anexo[n])
                sucesso = inclui_nova_ordem_arquivo(session, imagem, n + 1)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'success': False, 'msg': str(err)}), 500

        return jsonify({'success': sucesso}), 200

    @app.route('/rvf_ordena_por_data_criacao', methods=['GET'])
    @login_required
    def rvf_ordena_por_data_criacao():
        session = app.config.get('dbsession')
        rvf_id = request.args.get('rvf_id')
        try:
            rvf_ordena_imagensrvf_por_data_criacao(session, rvf_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'success': False, 'msg': str(err)}), 500
        return jsonify({'success': True}), 200

    @app.route('/rvf_galeria_imagens', methods=['GET'])
    def rvf_galeria_imagens():
        session = app.config.get('dbsession')
        anexos = []
        try:
            rvf_id = request.args.get('rvf_id')
            if not rvf_id:
                raise KeyError('Obrigatório passar parâmetro rvf_id')
            arvf = get_rvf(session, rvf_id)
            anexos = get_anexos_ordenado(arvf)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('rvf_galeria_imagens.html',
                               anexos=anexos)

    @app.route('/imagens_rvf/<rvf_id>', methods=['GET'])
    def imagens_container(rvf_id):
        session = app.config.get('dbsession')
        try:
            arvf = get_rvf(session, rvf_id)
            anexos = get_ids_anexos_ordenado(arvf)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'success': False, 'msg': str(err)}), 500
        return jsonify(anexos), 200

    @app.route('/get_rvf/<rvf_id>', methods=['GET'])
    def json_rvf(rvf_id):
        session = app.config.get('dbsession')
        try:
            arvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
            if arvf is None:
                return jsonify({'msg': 'RVF %s não encontrado' % rvf_id}), 404
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'success': False, 'msg': str(err)}), 500
        return jsonify(arvf.dump()), 200

    # telegram - edita_descricao_ficha
    @app.route('/edita_descricao_rvf', methods=['POST'])
    @csrf.exempt
    def edita_descricao_rvf():
        session = app.config.get('dbsession')
        try:
            descricao = request.form.get('descricao')
            if descricao is None:
                raise ValueError('Digite a descrição')
            try:
                rvf_id = request.form.get('rvf_id')
            except TypeError:
                raise TypeError('Informe o id do RVF')
            except ValueError:
                raise ValueError('Informe id do RVF somente com números')

            arvf = session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
            if arvf is None:
                return jsonify({'msg': 'RVF %s não encontrado' % rvf_id}), 404
            if arvf.descricao is None:
                arvf.descricao = descricao
            else:
                arvf.descricao = arvf.descricao + ' ' + descricao
            session.add(arvf)
            session.commit()
            session.refresh(arvf)
            logger.info(arvf.descricao)
            return jsonify(arvf.dump()), 201
        except Exception as err:
            logger.error(err, exc_info=True)
            return 'Erro! Detalhes no log da aplicação. ' + str(err), 500

    # telegram - Inclui descrição e peso na apreensão
    @app.route('/api/inclui_apreensao_rvf', methods=['POST'])
    @csrf.exempt
    def api_inclui_apreensao_rvf():
        session = app.config.get('dbsession')
        params = {}
        try:
            rvf_id = request.form.get('rvf_id')
        except TypeError:
            raise TypeError('Informe o id do RVF')
        except ValueError:
            raise ValueError('Informe id do RVF somente com números')
        params['rvf_id'] = rvf_id
        try:
            tipoapreensao = request.form.get('tipoapreensao')
            descricao = request.form.get('descricao')
            peso = request.form.get('peso')
            if descricao:
                params['descricao'] = descricao
            if peso:
                params['peso'] = peso
            params['tipo_id'] = tipoapreensao
            gera_apreensao_rvf(session, params)
            return jsonify({'msg': 'Sucesso!'}), 201
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': 'Erro: %s' % str(err)}), 500

    @app.route('/api/gerar_taseda', methods=['POST'])
    @csrf.exempt
    def api_gerar_taseda():
        session = app.config.get('dbsession')
        mongodb = app.config.get('mongo_risco')
        try:
            rvf_id = request.form.get('rvf_id')
        except TypeError:
            raise TypeError('Informe o id do RVF')
        except ValueError:
            raise ValueError('Informe id do RVF somente com números')
        try:
            tipo = request.form.get('tipo')
        except ValueError:
            raise ValueError('Tipo de relatório inválido')
        try:
            rvf = get_rvf(session, rvf_id)
            if rvf is None:
                raise ValueError(f'Não encontrou RVF para o id {rvf_id}')
            OVR_out_filename = '{}_FCC{}-{}.docx'.format(
                tipo, rvf_id,
                datetime.strftime(datetime.now(), '%Y-%m%dT%H%M%S'))

            rvf_dump = OVRDict(1).monta_rvf_dict(mongodb, session, rvf_id)
            document = gera_taseda(rvf_dump, rvf.user_name)
            path_to_upload = os.path.join(APP_PATH,
                                          app.config.get('STATIC_FOLDER', 'static'),
                                          rvf.user_name,
                                          OVR_out_filename)
            document.save(path_to_upload)
            return jsonify(path_to_upload), 200

            # cria arquivo na memória e disponibiliza para API e retorna em bytes na API
            # memory_file = BytesIO()
            # with open(memory_file, 'rb') as file:
            #     file.write(document)
            # memory_file.seek(0)
            #
            # return jsonify({'documento': b64encode(memory_file)}, 201)

        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': 'Erro: %s' % str(err)}), 500

    @app.route('/rvf/new', methods=['POST'])
    @csrf.exempt
    def nova_rvf_json():
        session = app.config.get('dbsession')
        try:
            cpf = request.json['cpf']
            ovr_id = request.json['ovr_id']
            orvf = cadastra_rvf(session, cpf, request.json, ovr_id)
            session.refresh(orvf)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify(orvf.dump()), 201

    @app.route('/apreensaorvf', methods=['POST'])
    @login_required
    def apreensaorvf():
        session = app.config.get('dbsession')
        rvf_id = 0
        try:
            rvf_id = request.form['rvf_id']
            tiposapreensao = get_tiposapreensao_choice(session)
            apreensao_rvf_form = ApreensaoRVFForm(request.form, tiposapreensao=tiposapreensao)
            apreensao_rvf_form.validate()
            gera_apreensao_rvf(session, dict(apreensao_rvf_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('rvf', id=rvf_id))

    @app.route('/exclui_apreensao', methods=['GET'])
    @login_required
    def exclui_apreensao_():
        try:
            session = app.config.get('dbsession')
            apreensao_id = request.args.get('apreensao_id')
            apreensoes = exclui_apreensao_rvf(session, apreensao_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'peso': apreensao.get_peso(),
                         'descricao': apreensao.descricao,
                         'tipo': apreensao.tipo.descricao}
                        for apreensao in apreensoes]), 201

    @app.route('/apreensaorvf_json', methods=['POST'])
    @login_required
    def apreensaorvf_json():
        session = app.config.get('dbsession')
        try:
            apreensao_rvf_form = ApreensaoRVFForm(request.json)
            apreensao_rvf_form.validate()
            apreensao_rvf = gera_apreensao_rvf(session,
                                               dict(apreensao_rvf_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify(apreensao_rvf.dump()), 201

    @app.route('/rvf_download_imagens', methods=['GET', 'POST'])
    def rfv_download_imagens():
        session = app.config.get('dbsession')
        db = app.config['mongo_risco']
        rvf_id = request.args.get('rvf_id')
        rvf = get_rvf(session, rvf_id)
        result = get_anexos_mongo(db, rvf)
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for grid_out in result:
                zf.writestr(grid_out.filename, grid_out.read())
        memory_file.seek(0)
        return send_file(memory_file, download_name='imagens.zip', as_attachment=True)

    @app.route('/registrar_rvf', methods=['POST', 'GET'])
    @login_required
    def registrar_rvf():
        session = app.config.get('dbsession')
        mongodb = app.config.get('mongo_risco')
        ovr_id = request.args.get('ovr_id')
        get_usuario_validando(session, current_user.id)
        marcas = get_marcas_choice(session)
        infracoes = get_infracoes_choice(session)
        rvf_form = RVFForm(marcas=marcas, infracoes=infracoes)
        tiposapreensao = get_tiposapreensao_choice(session)
        apreensao_form = ApreensaoRVFForm(tiposapreensao=tiposapreensao)

        if request.method == 'POST':
            rvf_params = request.get_json()
            ovr_id = rvf_params['ovr_id']
            lacres = rvf_params['lacresVerificados']
            infracoes = rvf_params['infracoesEncontradas']
            marcas = rvf_params['marcasEncontradas']
            apreensoes = rvf_params['apreensoesObtidas']
            imagens = rvf_params['imagensRecebidas']
            new_rvf = cadastra_rvf(session,
                                   user_name=current_user.name,
                                   params=rvf_params)
            session.refresh(new_rvf)

            for lacre in lacres:
                inclui_lacre_verificado(session, new_rvf.id, lacre)
            for infracao in infracoes:
                inclui_infracao_encontrada(session, new_rvf.id, infracao)
            for marca in marcas:
                inclui_marca_encontrada(session, new_rvf.id, marca)
            for apreensao in apreensoes:
                apreensao['rvf_id'] = new_rvf.id
                gera_apreensao_rvf(session, apreensao)
            for imagem in imagens:
                content = base64.b64decode(imagem['content'].split(',')[1])
                filename = imagem['name']
                dataModificacao = datetime.now()
                rvf_id = new_rvf.id
                inclui_imagemrvf(mongodb, session, content,
                                              filename, rvf_id, dataModificacao)

            return jsonify({'id': new_rvf.id}), 200

        return render_template('registrar_rvf.html',
                               ovr_id=ovr_id,
                               rvf_form=rvf_form,
                               apreensao_form=apreensao_form)

    @app.route('/consultar_rvf', methods=['GET'])
    @login_required
    def consultar_rvf():
        session = app.config.get('dbsession')
        mongodb = app.config.get('mongo_risco')
        get_usuario_validando(session, current_user.id)
        ovr_id = request.args.get('ovr_id')
        rvf_id = request.args.get('id')
        rvf = get_rvf(session, rvf_id)

        lacres_da_rvf = []
        for lacre_verificado in rvf.lacresverificados:
            lacres_da_rvf.append(lacre_verificado.numero)
        infracoes_da_rvf = []
        for infracao in rvf.infracoesencontradas:
            infracoes_da_rvf.append(infracao.nome)
        marcas_da_rvf = []
        for marca in rvf.marcasencontradas:
            marcas_da_rvf.append(marca.nome)
        apreensoes_da_rvf = []
        for apreensao in rvf.apreensoes:
            apreensoes_da_rvf.append(apreensao)

        fs = GridFS(mongodb)
        imagens_da_rvf = []
        for imagem in rvf.imagens:
            grid_out = fs.get(ObjectId(imagem.imagem))
            imagem_bytes = grid_out.read()
            imagem_string = str(base64.b64encode(imagem_bytes)).split('\'')[1]
            imagens_da_rvf.append(imagem_string)

        return render_template('consultar_rvf.html',
                               ovr_id=ovr_id,
                               rvf=rvf,
                               lacres_da_rvf=lacres_da_rvf,
                               infracoes_da_rvf=infracoes_da_rvf,
                               marcas_da_rvf=marcas_da_rvf,
                               apreensoes_da_rvf=apreensoes_da_rvf,
                               imagens_da_rvf=imagens_da_rvf
                               )
