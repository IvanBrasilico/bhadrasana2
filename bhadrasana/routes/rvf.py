import base64
from datetime import date, timedelta

from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import redirect

from ajna_commons.flask.log import logger
from ajna_commons.utils.images import ImageBytesTansformations
from bhadrasana.forms.filtro_rvf import FiltroRVFForm
from bhadrasana.forms.rvf import RVFForm, ImagemRVFForm, ApreensaoRVFForm
from bhadrasana.models import get_usuario_logado, get_usuario
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
    exclui_apreensao_rvf, get_peso
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
    def rvf():
        session = app.config.get('dbsession')
        get_usuario_logado(session, current_user.id)
        tiposapreensao = get_tiposapreensao_choice(session)
        apreensao_form = ApreensaoRVFForm(tiposapreensao=tiposapreensao)
        apreensoes_rvf = []
        infracoes = []
        infracoes_encontradas = []
        marcas = []
        marcas_encontradas = []
        anexos = []
        lacres_verificados = []
        arvf = None
        rvf_form = RVFForm()
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
            rvf_id = request.args.get('id')
            if rvf_id is not None:
                arvf = get_rvf(session, rvf_id)
            if arvf is not None:
                rvf_form = RVFForm(**arvf.__dict__)
                if arvf.datahora:
                    rvf_form.adata.data = arvf.datahora.date()
                    rvf_form.ahora.data = arvf.datahora.time()
                rvf_form.id.data = arvf.id
                rvf_form.peso_manifestado.data = get_peso(session,
                                                          rvf_form.numeroCEmercante.data,
                                                          rvf_form.numerolote.data)
                apreensoes_rvf = arvf.appreensoes
                infracoes_encontradas = arvf.infracoesencontradas
                marcas_encontradas = arvf.marcasencontradas
                lacres_verificados = arvf.lacresverificados
                # Temporário - para recuperar imagens "perdidas" na transição
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
                               oform=rvf_form,
                               apreensao_form=apreensao_form,
                               apreensoes=apreensoes_rvf,
                               infracoes_encontradas=infracoes_encontradas,
                               marcas_encontradas=marcas_encontradas,
                               lacres_verificados=lacres_verificados,
                               anexos=anexos)

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

    @app.route('/rvf_imgupload', methods=['POST'])
    @login_required
    def rvf_imgupload():
        db = app.config['mongo_risco']
        session = app.config.get('dbsession')
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
            inclui_imagemrvf(db, session, content, file.filename, rvf_id)
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
            try:
                image = base64.decodebytes(content.split(',')[1].encode())
            except IndexError:
                image = base64.decodebytes(content.encode())
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
            apreensao_rvf_form = ApreensaoRVFForm(request.form)
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
