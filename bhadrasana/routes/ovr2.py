"""Rotas da ficha de carga mais elaboradas/ com perfil especializado/de assistentes."""
import os
from datetime import datetime

from ajna_commons.flask.log import logger
from ajna_commons.utils.docx_utils import get_doc_generico_ovr
from flask import request, flash, render_template, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import redirect

from bhadrasana.docx.docx_functions import gera_comunicado_contrafacao, gera_auto_contrafacao
from bhadrasana.forms.encerramento_ovr import EncerramentoOVRForm
from bhadrasana.forms.exibicao_ovr import ExibicaoOVR, TipoExibicao
from bhadrasana.forms.ovr import FiltroDocxForm, ModeloDocxForm, HistoricoOVRForm, ProcessoOVRForm
from bhadrasana.models import get_usuario, usuario_tem_perfil_nome
from bhadrasana.models.laudo import get_empresa
from bhadrasana.models.ovr import FonteDocx, Assistente
from bhadrasana.models.ovr_dict_repr import OVRDict
from bhadrasana.models.ovrmanager import monta_ovr_dict, get_docx_choices, get_docx, \
    inclui_docx, get_ovrs_abertas_flags, get_ovr, MarcaManager, get_ids_flags_contrafacao, \
    get_tiposevento_assistente_choice, gera_eventoovr, get_tgovr_one, get_tipos_processo, \
    get_tipos_evento_comfase_choice, lista_de_rvfs_e_apreensoes, \
    lista_de_tgs_e_items
from bhadrasana.models.rvfmanager import lista_rvfovr
from bhadrasana.views import get_user_save_path, valid_file


def ovr2_app(app):
    def gerar_arquivos_docx(db, session, documento, filename, fonte_docx_id, oid):
        out_filename = '{}_{}_{}.docx'.format(
            filename,
            oid,
            datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
        )
        try:
            ovr_dict = OVRDict(fonte_docx_id).get_dict(
                db=db, session=session, id=oid)
        except NoResultFound:
            raise NoResultFound('{} {} não encontrado!'.format(
                FonteDocx(fonte_docx_id), oid))
        print(ovr_dict)
        if isinstance(ovr_dict, list):
            if len(ovr_dict) == 0:
                raise NoResultFound(f'Marcas não encontradas na ovr {oid}.')
            logger.info('Gerando marcas')
            arquivos = []
            for odict in ovr_dict:
                document = get_doc_generico_ovr(odict, documento,
                                                current_user.name)
                nome_arquivo = '%s_%s.docx' % (out_filename[:-4], odict.get('nome'))
                arquivos.append(nome_arquivo)
                document.save(os.path.join(
                    get_user_save_path(), nome_arquivo))
        else:
            document = get_doc_generico_ovr(ovr_dict, documento,
                                            current_user.name)
            document.save(os.path.join(get_user_save_path(), out_filename))
            arquivos = [out_filename]
        return arquivos

    @app.route('/exporta_docx', methods=['GET'])
    @login_required
    def exporta_docx():
        """Preenche um docx com dados da OVR"""
        session = app.config['dbsession']
        db = app.config['mongo_risco']
        try:
            ovr_id = request.values['ovr_id']
            out_filename = 'relatorio%s.docx' % ovr_id
            ovr_dict = monta_ovr_dict(db, session, int(ovr_id))
            document = get_doc_generico_ovr(ovr_dict, 'relatorio.docx')
            document.save(os.path.join(get_user_save_path(), out_filename))
            return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('gera_docx.html')

    @app.route('/gera_docx', methods=['GET', 'POST'])
    @login_required
    def gera_docx():
        """Preenche um docx com dados da Fonte especicada (OVR, RVF, etc)"""
        session = app.config['dbsession']
        db = app.config['mongo_risco']
        formdocx = FiltroDocxForm()
        modeloform = ModeloDocxForm()
        try:
            lista_docx = get_docx_choices(session)
            formdocx = FiltroDocxForm(lista_docx=lista_docx)
            if request.method == 'POST':
                formdocx = FiltroDocxForm(request.form, lista_docx=lista_docx)
                formdocx.validate()
                docx = get_docx(session, formdocx.docx_id.data)
                if request.form.get('excluir'):
                    session.delete(docx)
                    session.commit()
                    return redirect(url_for('gera_docx'))
                elif request.form.get('preencher'):
                    documento = docx.get_documento(db)
                    arquivos = gerar_arquivos_docx(db, session, documento, docx.filename,
                                                   docx.fonte_docx_id, formdocx.oid.data)
                    return render_template('gera_docx.html',
                                           formdocx=formdocx,
                                           modeloform=modeloform,
                                           arquivos=arquivos)
                elif request.form.get('visualizar'):
                    ovr_dict = OVRDict(docx.fonte_docx_id).get_dict(
                        db=db, session=session, id=formdocx.oid.data)
                    if isinstance(ovr_dict, list):
                        ovr_dict = ovr_dict[0]
                    if isinstance(ovr_dict, dict):
                        ovr_dict.pop('historico', None)
                        # ovr_dict.pop('tgs', None)
                        # for rvf in ovr_dict.get('rvfs', []):
                        #    rvf.pop('imagens', None)
                    return render_template('gera_docx.html', formdocx=formdocx,
                                           modeloform=modeloform, ovr_dict=ovr_dict)
                else:  # Baixar modelo
                    documento = docx.get_documento(db)
                    out_filename = '{}_{}.docx'.format(
                        docx.filename,
                        datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
                    )
                    with open(os.path.join(get_user_save_path(), out_filename), 'wb') as out:
                        out.write(documento.read())
                    return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('gera_docx.html', formdocx=formdocx, modeloform=modeloform)

    @app.route('/novo_docx', methods=['POST'])
    @login_required
    def novo_docx():
        """Cadastro um novo modelo docx"""
        session = app.config['dbsession']
        db = app.config['mongo_risco']
        try:
            modeloform = ModeloDocxForm(request.form)
            file = request.files.get('documento')
            if file:
                validfile, mensagem = \
                    valid_file(file, extensions=['docx'])
                if validfile:
                    if request.form.get('incluir'):  # Inclui docx no mongo
                        inclui_docx(db, session,
                                    modeloform.filename.data,
                                    modeloform.fonte_docx_id.data,
                                    file)
                    else:  # Apenas preenche para teste rápido
                        arquivos = gerar_arquivos_docx(db, session, file,
                                                       modeloform.filename.data,
                                                       modeloform.fonte_docx_id.data,
                                                       modeloform.oid.data)
                        formdocx = FiltroDocxForm()
                        return render_template('gera_docx.html',
                                               formdocx=formdocx,
                                               modeloform=modeloform,
                                               arquivos=arquivos)
                else:
                    flash(mensagem)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('gera_docx'))

    @app.route('/autos_contrafacao', methods=['GET', 'POST'])
    @login_required
    def autos_contrafacao():
        session = app.config['dbsession']
        # db = app.config['mongo_risco']
        listafichasresumo = []
        ovr = None
        rvfs = []
        marcas_dict = {}
        supervisor = False
        exibicao_ovr = ExibicaoOVR(session, TipoExibicao.Descritivo, current_user.name)
        titulos = exibicao_ovr.get_titulos()
        evento_form = HistoricoOVRForm()
        try:
            usuario = get_usuario(session, current_user.name)
            if usuario is None:
                raise Exception('Erro: Usuário não encontrado!')
            flags = get_ids_flags_contrafacao(session)
            supervisor = usuario_tem_perfil_nome(session, current_user.name, 'Supervisor')
            listafichas = get_ovrs_abertas_flags(session, current_user.name, flags)
            print('*************************', len(listafichas))
            for ovr_linha in listafichas:
                resumo = exibicao_ovr.get_linha(ovr_linha)
                listafichasresumo.append(resumo)
            ovr_id = request.args.get('ovr_id')
            if ovr_id:
                ovr = get_ovr(session, ovr_id)
                tiposevento = get_tiposevento_assistente_choice(session, Assistente.Marcas)
                evento_form = HistoricoOVRForm(ovr_id=ovr_id,
                                               tiposeventos=tiposevento,
                                               responsaveis=[usuario.cpf])
                rvfs = lista_rvfovr(session, ovr_id)
                marca_manager = MarcaManager(session)
                for rvf in rvfs:
                    marca_dict = marca_manager.get_marcas_rvf_por_representante(rvf.id)
                    marcas_dict.update(marca_dict)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('autos_contrafeitos.html',
                               titulos=titulos,
                               listaovrs=listafichasresumo,
                               marcas_dict=marcas_dict,
                               ovr=ovr,
                               rvfs=rvfs,
                               supervisor=supervisor,
                               evento_form=evento_form)

    @app.route('/comunicado_contrafacao', methods=['GET'])
    @app.route('/termo_contrafacao', methods=['GET'])
    @login_required
    def comunicado_contrafacao():
        print(request.url)
        session = app.config['dbsession']
        db = app.config['mongo_risco']
        ovr_id = request.args.get('ovr_id')
        representante_id = request.args.get('representante_id')
        try:
            usuario = get_usuario(session, current_user.name)
            if usuario is None:
                raise Exception('Erro: Usuário não encontrado!')
            if ovr_id:
                try:
                    ovr_dicts = OVRDict(FonteDocx.Marcas).get_dict(
                        db=db, session=session, id=ovr_id)
                except NoResultFound:
                    raise NoResultFound(f'Marcas não encontradas para Ficha {ovr_id}.')
                if len(ovr_dicts) == 0:
                    raise NoResultFound(f'Marcas não encontradas na ovr {ovr_id}.')
                logger.info('Gerando marcas')
                document = None
                representante_id2 = None
                for ovr_dict in ovr_dicts:
                    representante_id2 = ovr_dict.get('representante_id')
                    representante_nome = ovr_dict.get('representante_nome')
                    if representante_id2 and (str(representante_id2) == representante_id):
                        document = gera_comunicado_contrafacao(ovr_dict, current_user.name,
                                                               'termo' in request.url)
                        break
                if representante_id2 and document:
                    nome = 'Comunicado_de_Contrafacao'
                    if 'termo' in request.url:
                        nome = 'Termo de retirada de amostras'
                    out_filename = '{}_{}_{}_{}.docx'.format(
                        nome,
                        ovr_id,
                        representante_nome,
                        datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
                    )
                    document.save(os.path.join(
                        get_user_save_path(), out_filename))
                    return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('autos_contrafacao', ovr_id=ovr_id))

    @app.route('/emite_auto_contrafacao', methods=['GET'])
    @login_required
    def auto_contrafacao():
        session = app.config['dbsession']
        db = app.config['mongo_risco']
        ovr_id = None
        tg_id = request.args.get('tg_id')
        try:
            usuario = get_usuario(session, current_user.name)
            if usuario is None:
                raise Exception('Erro: Usuário não encontrado!')
            if tg_id:
                tg = get_tgovr_one(session, tg_id)
                ovr_id = tg.ovr_id
                ovr_dict = OVRDict(FonteDocx.TG_Ficha).get_dict(
                    db=db, session=session, id=tg.id)
                if ovr_dict:
                    document = gera_auto_contrafacao(ovr_dict, current_user.name)
                    nome = 'Auto de Infração'
                    out_filename = '{}_{}_{}.docx'.format(
                        nome,
                        ovr_id,
                        datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
                    )
                    document.save(os.path.join(
                        get_user_save_path(), out_filename))
                    return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('autos_contrafacao', ovr_id=ovr_id))

    @app.route('/eventoovr_assistente', methods=['POST'])
    @login_required
    def eventoovr_assistente():
        session = app.config.get('dbsession')
        ovr_id = None
        try:
            evento_form = HistoricoOVRForm(request.form)
            user_name = current_user.name
            evento = gera_eventoovr(session, dict(evento_form.data.items()),
                                    user_name=user_name)
            ovr_id = evento.ovr_id
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('autos_contrafacao', ovr_id=ovr_id))

    @app.route('/encerramento_ovr', methods=['GET', 'POST'])
    @login_required
    def encerramento_ovr():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        ovr = get_ovr(session=session, ovr_id=ovr_id)
        operacao = ovr.get_tipooperacao()
        tiposprocesso = get_tipos_processo(session=session)
        processo_form = ProcessoOVRForm(tiposprocesso=tiposprocesso)
        tiposeventos = get_tipos_evento_comfase_choice(session=session)
        historico_form = HistoricoOVRForm(tiposeventos=tiposeventos)
        encerramento_form = EncerramentoOVRForm(ovr_id)
        lista_de_tgs_items = lista_de_tgs_e_items(session, ovr_id)[0]
        total_tgs = lista_de_tgs_e_items(session, ovr_id)[1]
        lista_de_rvfs_apreensoes = lista_de_rvfs_e_apreensoes(session, ovr_id)[0]
        total_apreensoes = lista_de_rvfs_e_apreensoes(session, ovr_id)[1]
        try:
            fase = ovr.get_fase()
            usuario = get_usuario(session, current_user.name)
            auditor = get_usuario(session, ovr.cpfauditorresponsavel)
            if ovr.cnpj_fiscalizado:
                empresa = get_empresa(session=session, cnpj=ovr.cnpj_fiscalizado)
            else:
                empresa = ''
            processos = ovr.processos
            eventos = ovr.historico
            if usuario is None:
                raise Exception('Erro: Usuário não encontrado!')
            if request.method == 'POST':
                ovr_id = request.args.get('ovr_id')
                encerramento_form = EncerramentoOVRForm(request.form)
                # evento = gera_encerramentovr(session, dict(encerramento_form.data.items()),
                #                    user_name=usuario.cpf)
                # ovr_id = evento.ovr_id
                return redirect(url_for('encerramento_ovr', ovr_id=ovr_id))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('encerramento_ovr.html',
                               encerramento_form=encerramento_form,
                               ovr=ovr,
                               fase=fase,
                               usuario=usuario,
                               auditor=auditor,
                               empresa=empresa,
                               processos=processos,
                               eventos=eventos,
                               processo_form=processo_form,
                               operacao=operacao,
                               historico_form=historico_form,
                               lista_de_tgs_items=lista_de_tgs_items,
                               lista_de_rvfs_apreensoes=lista_de_rvfs_apreensoes,
                               total_apreensoes=total_apreensoes,
                               total_tgs=total_tgs)
