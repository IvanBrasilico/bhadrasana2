import os
import time
from _collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Tuple

import pandas as pd
from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from gridfs import GridFS
from werkzeug.utils import redirect

from ajna_commons.flask.log import logger
from bhadrasana.docx.docx_functions import get_doc_generico_ovr
from bhadrasana.forms.exibicao_ovr import ExibicaoOVR, TipoExibicao
from bhadrasana.forms.filtro_container import FiltroContainerForm
from bhadrasana.forms.filtro_empresa import FiltroEmpresaForm
from bhadrasana.forms.ovr import OVRForm, FiltroOVRForm, HistoricoOVRForm, \
    ProcessoOVRForm, ItemTGForm, ResponsavelOVRForm, TGOVRForm, FiltroRelatorioForm, \
    FiltroMinhasOVRsForm, OKRObjectiveForm, OKRMetaForm, SetorOVRForm, FiltroDocxForm, \
    ModeloDocxForm
from bhadrasana.models import delete_objeto, get_usuario
from bhadrasana.models.laudo import get_empresa, get_empresas_nome, get_sats_cnpj
from bhadrasana.models.ovr import OVR, OKRObjective
from bhadrasana.models.ovr_dict_repr import OVRDict
from bhadrasana.models.ovrmanager import cadastra_ovr, get_ovr, \
    get_ovr_filtro, gera_eventoovr, gera_processoovr, get_tipos_processo, lista_itemtg, \
    get_itemtg, get_recintos, \
    cadastra_itemtg, get_usuarios, atribui_responsavel_ovr, lista_tgovr, get_tgovr, \
    cadastra_tgovr, get_ovr_responsavel, importa_planilha_tg, exporta_planilhaovr, \
    get_tiposmercadoria_choice, \
    inclui_flag_ovr, exclui_flag_ovr, get_flags, informa_lavratura_auto, \
    get_relatorios_choice, \
    executa_relatorio, get_relatorio, get_afrfb, get_itens_roteiro_checked, \
    get_flags_choice, cadastra_visualizacao, get_tipos_evento_comfase_choice, \
    get_ovr_criadaspor, get_ovr_empresa, get_tipos_evento_todos, \
    desfaz_ultimo_eventoovr, get_delta_date, exporta_planilha_tg, TipoPlanilha, \
    exclui_item_tg, get_setores, get_objectives_setor, executa_okr_results, gera_okrobjective, \
    exclui_okrobjective, get_key_results_choice, gera_okrmeta, exclui_okrmeta, \
    get_usuarios_setores, get_setores_cpf, get_ovr_auditor, get_ovr_passagem, muda_setor_ovr, \
    monta_ovr_dict, get_docx, inclui_docx, get_docx_choices
from bhadrasana.models.ovrmanager import get_marcas_choice
from bhadrasana.models.riscomanager import consulta_container_objects
from bhadrasana.models.rvfmanager import lista_rvfovr, programa_rvf_container, \
    get_infracoes_choice
from bhadrasana.models.virasana_manager import get_conhecimento, \
    get_containers_conhecimento, get_ncms_conhecimento, get_imagens_dict_container_id, \
    get_imagens_container, get_dues_empresa, get_ces_empresa, \
    get_due, get_detalhes_mercante
from bhadrasana.routes.plotly_graphs import bar_plotly, gauge_plotly, burndown_plotly
from bhadrasana.scripts.gera_planilha_rilo import monta_planilha_rilo
from bhadrasana.views import get_user_save_path, valid_file, csrf


def ovr_app(app):
    def trata_ovr(request, ovr_id):
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        listahistorico = []
        processos = []
        tiposeventos = get_tipos_evento_comfase_choice(session)
        recintos = get_recintos(session)
        responsaveis = get_usuarios(session)
        ovr_form = OVRForm(tiposeventos=tiposeventos, recintos=recintos,
                           numeroCEmercante=request.args.get('numeroCEmercante'))
        tiposprocesso = get_tipos_processo(session)
        flags = get_flags(session)
        historico_form = HistoricoOVRForm(tiposeventos=tiposeventos,
                                          responsaveis=responsaveis,
                                          user_name=current_user.name)
        processo_form = ProcessoOVRForm(tiposprocesso=tiposprocesso)
        responsavel_form = ResponsavelOVRForm(responsaveis=responsaveis,
                                              responsavel=current_user.name)
        listasetores = get_setores(session)
        setor_ovr_form = SetorOVRForm(setores=listasetores)
        conhecimento = None
        ncms = []
        containers = []
        flags_ovr = []
        itens_roteiro = []
        due = {}
        ovr = OVR()
        qtdervfs = 0
        qtdeimagens = 0
        try:
            if request.method == 'POST':
                ovr_form = OVRForm(request.form)
                ovr_form.adata.data = request.form.get('adata')
                ovr_form.ahora.data = request.form.get('ahora')
                ovr_form.validate()
                # print(ovr_form.data.items())
                ovr = cadastra_ovr(session,
                                   dict(ovr_form.data.items()),
                                   user_name=current_user.name)
                return redirect(url_for('ovr', id=ovr.id))
            else:
                if ovr_id is not None:
                    ovr = get_ovr(session, ovr_id)
                    if ovr is not None:
                        ovr_form = OVRForm(**ovr.__dict__,
                                           tiposeventos=tiposeventos,
                                           recintos=recintos)
                        try:
                            conhecimento = get_conhecimento(session,
                                                            ovr.numeroCEmercante)
                            containers = get_containers_conhecimento(
                                session,
                                ovr.numeroCEmercante)
                            ncms = get_ncms_conhecimento(session, ovr.numeroCEmercante)
                        except Exception as err:
                            logger.info(err)
                            pass
                        due = get_due(mongodb, ovr.numerodeclaracao)
                        # Extrai informacoes da OVR
                        # Registra Visualização
                        cadastra_visualizacao(session, ovr, current_user.id)
                        ovr_form.id.data = ovr.id
                        listahistorico = ovr.historico
                        processos = ovr.processos
                        flags_ovr = ovr.flags
                        itens_roteiro = get_itens_roteiro_checked(session, ovr)
                        rvfs = lista_rvfovr(session, ovr_id)
                        qtdervfs = len(rvfs)
                        for rvf in rvfs:
                            qtdeimagens += len(rvf.imagens)
                        usuario = get_usuario(session, ovr.user_name)
                        if usuario:
                            ovr_form.user_descricao.data = usuario.nome
                        auditor = get_usuario(session, ovr.cpfauditorresponsavel)
                        if auditor:
                            ovr_form.auditor_descricao.data = auditor.nome
                        if ovr.setor:
                            ovr_form.setor_descricao.data = ovr.setor.nome
                        fiscalizado = get_empresa(session, ovr.cnpj_fiscalizado)
                        if fiscalizado:
                            ovr_form.nome_fiscalizado.data = fiscalizado.nome
                        # Desabiltar edição de Usuário ao informar Evento
                        historico_form.user_name.render_kw = {'disabled': 'disabled'}
                        if ovr_form.dataentrada.data and ovr.setor_id == '2':
                            if get_delta_date(ovr_form.adata.data,
                                              ovr_form.dataentrada.data) >= 90:
                                flash('Alerta: Diferença entre Data de Emissão e '
                                      'Data da Entrada da Carga maior que 90 dias!')
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('ovr.html',
                               ovr=ovr,
                               oform=ovr_form,
                               conhecimento=conhecimento,
                               ncms=ncms,
                               containers=containers,
                               qtdervfs=qtdervfs,
                               qtdeimagens=qtdeimagens,
                               historico_form=historico_form,
                               processo_form=processo_form,
                               responsavel_form=responsavel_form,
                               listahistorico=listahistorico,
                               processos=processos,
                               flags=flags,
                               flags_ovr=flags_ovr,
                               itens_roteiro=itens_roteiro,
                               due=due,
                               setor_ovr_form=setor_ovr_form)

    @app.route('/ovr/<id>', methods=['POST', 'GET'])
    @login_required
    def ovr_id(id):
        return trata_ovr(request, id)

    @app.route('/ovr', methods=['POST', 'GET'])
    @login_required
    def ovr():
        id = request.args.get('id')
        return trata_ovr(request, id)

    @app.route('/inclui_flag_ovr', methods=['GET'])
    @login_required
    def inclui_flag():
        try:
            session = app.config.get('dbsession')
            ovr_id = request.args.get('ovr_id')
            flag_nome = request.args.get('flag_nome')
            novas_flags = inclui_flag_ovr(session, ovr_id, flag_nome)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': flag.id, 'nome': flag.nome}
                        for flag in novas_flags]), 201

    @app.route('/exclui_flag_ovr', methods=['GET'])
    @login_required
    def exclui_flag():
        try:
            session = app.config.get('dbsession')
            ovr_id = request.args.get('ovr_id')
            flag_id = request.args.get('flag_id')
            novas_flags = exclui_flag_ovr(session, ovr_id, flag_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify([{'id': flag.id, 'nome': flag.nome}
                        for flag in novas_flags]), 201

    @app.route('/pesquisa_ovr', methods=['POST', 'GET'])
    @login_required
    def pesquisa_ovr():
        session = app.config.get('dbsession')
        LIMIT = 200
        titulos_exibicao = []
        listaovrs = []
        tiposeventos = get_tipos_evento_todos(session)
        recintos = get_recintos(session)
        flags = get_flags_choice(session)
        infracoes = get_infracoes_choice(session)
        lista_setores = get_setores(session)
        filtro_form = FiltroOVRForm(
            datainicio=date.today() - timedelta(days=10),
            datafim=date.today(),
            tiposeventos=tiposeventos,
            recintos=recintos,
            flags=flags,
            infracoes=infracoes,
            setores=lista_setores
        )
        responsaveis = get_usuarios(session)
        responsavel_form = ResponsavelOVRForm(responsaveis=responsaveis,
                                              responsavel=current_user.name)
        historico_ovr_form = HistoricoOVRForm(
            tiposeventos=get_tipos_evento_comfase_choice(session))
        try:
            usuario = get_usuario(session, current_user.name)
            if usuario is None:
                raise Exception('Erro: Usuário não encontrado!')
            filtro_form.setor_id.data = usuario.setor_id
            if request.method == 'POST':
                logger.info('Consulta de Ficha: ' + str(dict(request.form.items())))
                filtro_form = FiltroOVRForm(request.form, tiposeventos=tiposeventos,
                                            recintos=recintos, flags=flags,
                                            infracoes=infracoes, setores=lista_setores)
                filtro_form.validate()
                logger.info('filtro_form data: ' + str(dict(filtro_form.data.items())))
                ovrs = get_ovr_filtro(session,
                                      pfiltro=dict(filtro_form.data.items()),
                                      limit=LIMIT)
                # print('******', ovrs)
                tipoexibicao = int(filtro_form.tipoexibicao.data)
                exibicao = ExibicaoOVR(session, tipoexibicao, current_user.id)
                titulos_exibicao = exibicao.get_titulos()
                listaovrs = [exibicao.get_linha(ovr) for ovr in ovrs]
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_ovr.html',
                               oform=filtro_form,
                               limit=LIMIT,
                               titulos=titulos_exibicao,
                               listaovrs=listaovrs,
                               responsavel_form=responsavel_form,
                               historico_form=historico_ovr_form)

    @app.route('/ovrs_meus_setores', methods=['GET', 'POST'])
    @app.route('/ovrs_criador', methods=['GET', 'POST'])
    @app.route('/ovrs_passagem', methods=['GET', 'POST'])
    @app.route('/ovrs_auditor', methods=['GET', 'POST'])
    @app.route('/minhas_ovrs', methods=['GET', 'POST'])
    @login_required
    def minhas_ovrs():
        TABS = ('minhas_ovrs', 'ovrs_meus_setores', 'ovrs_criador',
                'ovrs_passagem', 'ovrs_auditor')
        session = app.config.get('dbsession')
        listasovrs = defaultdict(list)
        titulos_exibicao = []
        today = date.today()
        inicio = date(year=today.year, month=today.month, day=1)
        active_tab = request.args.get('active_tab')
        print(request.url)
        if active_tab is None or active_tab not in TABS:
            tab_url = request.url.split('/')[-1]
            print(tab_url)
            if tab_url in TABS:
                active_tab = tab_url
            else:
                active_tab = 'ovrs_criador'
        if request.method == 'POST':
            oform = FiltroMinhasOVRsForm(request.form, active_tab=active_tab)
        else:
            oform = FiltroMinhasOVRsForm(datainicio=inicio,
                                         datafim=date.today(),
                                         active_tab=active_tab)
        responsaveis = get_usuarios(session)
        responsavel_form = ResponsavelOVRForm(responsaveis=responsaveis,
                                              responsavel=current_user.name)
        setores = get_setores_cpf(session, current_user.name)
        responsaveis_setor = get_usuarios_setores(session, setores)
        responsavel_form_setor = ResponsavelOVRForm(responsaveis=responsaveis_setor,
                                                    responsavel=current_user.name)
        historico_ovr_form = HistoricoOVRForm(
            tiposeventos=get_tipos_evento_comfase_choice(session))
        try:
            oform.validate()
            if active_tab == 'minhas_ovrs':
                ovrs = get_ovr_responsavel(session, current_user.name)
            elif active_tab == 'ovrs_meus_setores':
                ovrs = get_ovr_filtro(session,
                                      dict(oform.data.items()),
                                      user_name=current_user.name)
            elif active_tab == 'ovrs_auditor':
                ovrs = get_ovr_auditor(session, current_user.name)
            elif active_tab == 'ovrs_passagem':
                ovrs = get_ovr_passagem(session, current_user.name)
            else:
                ovrs = get_ovr_criadaspor(session, current_user.name)
            exibicao = ExibicaoOVR(session, int(oform.tipoexibicao.data), current_user.id)
            titulos_exibicao = exibicao.get_titulos()
            for ovr in ovrs:
                exibicao_ovr = exibicao.get_linha(ovr)
                listasovrs[str(ovr.fase) + '-' + ovr.get_fase()].append(exibicao_ovr)
                # listasovrs[str(ovr.fase) + '-' + ovr.get_fase()].append(ovr)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('minhas_ovrs.html',
                               oform=oform,
                               titulos=titulos_exibicao,
                               listasovrs=listasovrs,
                               active_tab=active_tab,
                               responsavel_form_setor=responsavel_form_setor,
                               responsavel_form=responsavel_form,
                               historico_form=historico_ovr_form)

    @app.route('/minhas_fichas_text', methods=['GET'])
    def minhas_fichas_text():
        session = app.config.get('dbsession')
        try:
            # TODO: Login substituir cpf por current_user
            cpf = request.args['cpf']
            ovrs = get_ovr_responsavel(session, cpf)
            if len(ovrs) == 0:
                result = 'Sem Fichas atribuídas para o Usuário {}'.format(cpf)
            else:
                exibicao = ExibicaoOVR(session, TipoExibicao.Descritivo, cpf)
                result = []
                result.append('\t'.join(exibicao.get_titulos()))
                for ovr in ovrs:
                    id, visualizado, linha = exibicao.get_linha(ovr)
                    datahora = datetime.strftime(linha[0], '%d/%m/%Y %H:%M')
                    linha_str = [str(item) for item in linha[1:]]
                    exibicao_ovr = str(id) + '\t' + datahora + '\t' + '\t'.join(linha_str)
                    result.append(exibicao_ovr)
        except Exception as err:
            logger.error(err, exc_info=True)
            return 'Erro! Detalhes no log da aplicação.' + str(err)
        return '\n'.join(result)

    @app.route('/relatorios', methods=['GET', 'POST'])
    @login_required
    def ver_relatorios():
        session = app.config.get('dbsession')
        lista_relatorios = get_relatorios_choice(session)
        lista_setores = get_setores(session)
        linhas = []
        linhas_formatadas = []
        sql = ''
        plot = ''
        today = date.today()
        inicio = date(year=today.year, month=today.month, day=1)
        usuario = get_usuario(session, current_user.name)
        filtro_form = FiltroRelatorioForm(
            datainicio=inicio,
            datafim=date.today(),
            relatorios=lista_relatorios,
            setores=lista_setores
        )
        filtro_form.setor_id.data = usuario.setor_id
        try:
            if request.method == 'POST':
                filtro_form = FiltroRelatorioForm(request.form,
                                                  relatorios=lista_relatorios,
                                                  setores=lista_setores)
                filtro_form.validate()
                relatorio = get_relatorio(session, int(filtro_form.relatorio.data))
                if relatorio is None:
                    raise ValueError('Relatório %s não encontrado' %
                                     filtro_form.relatorio.data)
                sql = relatorio.sql
                linhas = executa_relatorio(session,
                                           relatorio,
                                           filtro_form.datainicio.data,
                                           filtro_form.datafim.data,
                                           setor_id=filtro_form.setor_id.data)
                plot = bar_plotly(linhas, relatorio.nome)
                linhas_formatadas = formata_linhas_relatorio(linhas)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('relatorios.html',
                               oform=filtro_form,
                               linhas=linhas_formatadas,
                               sql=sql,
                               plot=plot)

    @app.route('/responsavelovr', methods=['POST'])
    @login_required
    def atribuirresponsavel():
        session = app.config.get('dbsession')
        ovr_id = None
        try:
            responsavel_ovr_form = ResponsavelOVRForm(request.form)
            ovr_id = responsavel_ovr_form.ovr_id.data
            atribui_responsavel_ovr(session,
                                    ovr_id=ovr_id,
                                    responsavel=responsavel_ovr_form.responsavel.data
                                    )
            return redirect(url_for('ovr', id=ovr_id))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/auditorresponsavelovr', methods=['POST'])
    @login_required
    def atribuir_auditor_responsavel():
        session = app.config.get('dbsession')
        ovr_id = None
        try:
            responsavel_ovr_form = ResponsavelOVRForm(request.form)
            ovr_id = responsavel_ovr_form.ovr_id.data
            atribui_responsavel_ovr(session,
                                    ovr_id=ovr_id,
                                    responsavel=responsavel_ovr_form.responsavel.data,
                                    auditor=True
                                    )
            return redirect(url_for('ovr', id=ovr_id))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/mudasetorficha', methods=['POST'])
    @login_required
    def mudasetorficha():
        session = app.config.get('dbsession')
        ovr_id = None
        try:
            setor_ovr_form = SetorOVRForm(request.form)
            ovr_id = setor_ovr_form.ovr_id.data
            muda_setor_ovr(session,
                           ovr_id=ovr_id,
                           setor_id=setor_ovr_form.setor.data,
                           user_name=current_user.name
                           )
            return redirect(url_for('ovr', id=ovr_id))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/responsavelovr_minhasovrs', methods=['POST'])
    @app.route('/eventoovr_minhasovrs', methods=['POST'])
    @login_required
    def atribuirresponsavel_minhasovrs():
        session = app.config.get('dbsession')
        active_tab = None
        try:
            logger.info(request.form)
            cpf_responsavel = request.form.get('responsavel')
            if cpf_responsavel is None or \
                    cpf_responsavel == 'None':
                cpf_responsavel = current_user.name
            motivo = request.form.get('motivo')
            tipoevento_id = request.form.get('tipoevento_id')
            active_tab = request.form.get('active_tab')
            for ovr_id in request.form.getlist('rowid'):
                if 'eventoovr' in request.url:
                    gera_eventoovr(session,
                                   {'ovr_id': ovr_id,
                                    'motivo': motivo,
                                    'tipoevento_id': tipoevento_id},
                                   user_name=cpf_responsavel)
                else:
                    atribui_responsavel_ovr(session, ovr_id=ovr_id,
                                            responsavel=cpf_responsavel)
            if active_tab and active_tab == 'pesquisa_ovr':
                return jsonify({'msg': 'Sucesso!'}), 201
            return redirect(url_for('minhas_ovrs', active_tab=active_tab))
        except Exception as err:
            logger.error(err, exc_info=True)
            if active_tab and active_tab == 'pesquisa_ovr':
                return jsonify({'msg': 'Erro: {}'.format(str(err))}), 500
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('minhas_ovrs', active_tab=active_tab))

    @app.route('/informalavraturaauto', methods=['POST'])
    @login_required
    def informalavraturaauto():
        session = app.config.get('dbsession')
        ovr_id = 0
        try:
            print(request.form)
            responsavel_ovr_form = ResponsavelOVRForm(request.form)
            responsavel_ovr_form.validate()
            ovr_id = responsavel_ovr_form.ovr_id.data
            informa_lavratura_auto(session,
                                   ovr_id=ovr_id,
                                   responsavel=responsavel_ovr_form.responsavel.data
                                   )
        except Exception as err:
            logger.error(str(err), exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/movimentaovr', methods=['POST'])
    @login_required
    def movimentaovr():
        session = app.config.get('dbsession')
        ovr_id = request.form['ovr_id']
        historico_ovr_form = HistoricoOVRForm(request.form)
        user_name = None
        try:
            if historico_ovr_form.user_name.data is None or \
                    historico_ovr_form.user_name.data == 'None':
                user_name = current_user.name
            evento = gera_eventoovr(session, dict(historico_ovr_form.data.items()),
                                    user_name=user_name)
            # TODO: Mover para ação específica ou para gera_eventoovr
            session.refresh(evento)
            db = app.config['mongo_risco']
            fs = GridFS(db)
            file = request.files.get('anexo')
            if file:
                print('Arquivo:', file)
                validfile, mensagem = \
                    valid_file(file, extensions=['pdf', 'jpg', 'png'])
                if not validfile:
                    flash(mensagem)
                    print('Não é válido %s' % mensagem)
                content = file.read()
                fs.put(content, filename=file.filename,
                       metadata={'ovr': str(ovr_id),
                                 'evento': str(evento.id),
                                 'contentType': file.mimetype})
                evento.anexo_filename = file.filename
                session.add(evento)
                session.commit()
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/desfazer_ultimo_eventoovr', methods=['POST'])
    @login_required
    def desfazer_ultimo_eventoovr():
        session = app.config.get('dbsession')
        ovr_id = None
        try:
            ovr_id = request.form['ovr_id']
            desfaz_ultimo_eventoovr(session, ovr_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/processoovr', methods=['POST'])
    @login_required
    def processoovr():
        session = app.config.get('dbsession')
        try:
            ovr_id = request.form['ovr_id']
            processo_ovr_form = ProcessoOVRForm(request.form)
            processo_ovr_form.validate()
            gera_processoovr(session, dict(processo_ovr_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/lista_tgovr', methods=['GET'])
    @login_required
    def listatgovr():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        item_id = request.args.get('item_id')
        listatgovr = []
        oform = TGOVRForm()
        try:
            listatgovr = lista_tgovr(session, ovr_id)
            marcas = get_marcas_choice(session)
            tipos = get_tiposmercadoria_choice(session)
            lista_afrfb = get_afrfb(session)
            if item_id:
                tgovr = get_tgovr(session, item_id)
                oform = TGOVRForm(**tgovr.__dict__, marcas=marcas,
                                  tiposmercadoria=tipos, lista_afrfb=lista_afrfb)
            else:
                oform = TGOVRForm(ovr_id=ovr_id, marcas=marcas,
                                  tiposmercadoria=tipos, lista_afrfb=lista_afrfb)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('lista_tgovr.html',
                               listatgovr=listatgovr,
                               oform=oform)

    @app.route('/tgovr', methods=['POST'])
    @login_required
    def tgovr():
        session = app.config.get('dbsession')
        item_id = None
        try:
            # print(request.form)
            tgovr_form = TGOVRForm(request.form)
            tgovr_form.validate()
            tgovr = cadastra_tgovr(session,
                                   dict(tgovr_form.data.items()),
                                   current_user.name)
            session.refresh(tgovr)
            ovr_id = tgovr.ovr_id
            item_id = tgovr.id
        except Exception as err:
            flash(str(err))
            logger.error(err, exc_info=True)
            ovr_id = request.form.get('ovr_id')
        return redirect(url_for('listatgovr',
                                ovr_id=ovr_id,
                                item_id=item_id))

    @app.route('/lista_itemtg', methods=['GET'])
    @login_required
    def listaitemtg():
        session = app.config.get('dbsession')
        itemtg = None
        listaitemtg = []
        try:
            marcas = get_marcas_choice(session)
            oform = ItemTGForm(marcas=marcas)
            tg_id = request.args.get('tg_id')
            if tg_id is None:
                raise KeyError('Ocorreu um erro: parâmetro tg_id'
                               'é necessário nesta tela.')
            item_id = request.args.get('item_id')
            listaitemtg = lista_itemtg(session, tg_id)
            if item_id:
                itemtg = get_itemtg(session, item_id)
                oform = ItemTGForm(**itemtg.__dict__, marcas=marcas)
            if itemtg is None:
                oform = ItemTGForm(tg_id=tg_id, marcas=marcas)
                max_numero_itemtg = 0
                if listaitemtg and len(listaitemtg) > 0:
                    max_numero_itemtg = max([item.numero for item in listaitemtg])
                oform.numero.data = max_numero_itemtg + 1
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            # flash(str(type(err))
            flash(str(err))
        return render_template('lista_itemtg.html',
                               listaitemtg=listaitemtg,
                               oform=oform)

    @app.route('/itemtg', methods=['POST'])
    @login_required
    def itemtg():
        session = app.config.get('dbsession')
        try:
            itemtg_form = ItemTGForm(request.form)
            itemtg_form.validate()
            tg_id = request.form.get('tg_id')
            if not cadastra_itemtg(session, dict(itemtg_form.data.items())):
                flash('Favor preencher os campos obrigatórios.')
                listaitemtg = lista_itemtg(session, tg_id)
                return render_template('lista_itemtg.html',
                                       listaitemtg=listaitemtg,
                                       oform=itemtg_form)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            # flash(str(type(err))
            flash(str(err))
        return redirect(url_for('listaitemtg', tg_id=tg_id))

    @app.route('/edita_itemtg', methods=['GET'])
    @login_required
    def edita_itemtg():
        session = app.config.get('dbsession')
        try:
            id = request.args.get('id')
            campo = request.args.get('campo')
            valor = request.args.get('valor')
            if cadastra_itemtg(session, {'id': id, campo: valor}) is None:
                flash('Os campos de preenchimentos obrigatório estão em branco!')
        except Exception as err:
            logger.error(err, exc_info=True)
            return {'error': str(err), 'msg': 'Erro!'}, 500
        return {'msg': 'Modificado com sucesso'}, 200

    @app.route('/exclui_itemtg', methods=['GET'])
    @login_required
    def exclui_itemtg():
        session = app.config.get('dbsession')
        try:
            tg_id = request.args.get('tg_id')
            itemtg_id = request.args.get('itemtg_id')
            if itemtg_id is None or tg_id is None:
                raise KeyError('Ocorreu um erro: parâmetros tg_id e itemtg_id '
                               'são necessários nesta tela.')
            logger.info('>>>>> Excluiu ItemTG id: %s' % itemtg_id)
            exclui_item_tg(session, tg_id, itemtg_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash(str(err))
        return redirect(url_for('listaitemtg', tg_id=tg_id))

    @app.route('/exclui_todos_itens', methods=['GET'])
    @login_required
    def exclui_todos_itens():
        session = app.config.get('dbsession')
        try:
            tg_id = request.args.get('tg_id')
            if tg_id is None:
                raise KeyError('Ocorreu um erro: parâmetro tg_id '
                               ' é necessário nesta tela.')
            print('>>>>>> Exclui todos os itens do tg %s ' % tg_id)
            exclui_item_tg(session, tg_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash(str(err))
        return redirect(url_for('listaitemtg', tg_id=tg_id))

    @app.route('/importaplanilhatg', methods=['POST'])
    @login_required
    def importa_planilhatg():
        try:
            session = app.config.get('dbsession')
            tg_id = request.form['tg_id']
            tg = get_tgovr(session, tg_id)
            planilha = request.files['planilha']
            alertas = importa_planilha_tg(session, tg, planilha)
            if alertas:
                flash(alertas)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('listaitemtg', tg_id=tg_id))

    @app.route('/exportaplanilhatg', methods=['GET'])
    @login_required
    def exporta_planilhatg():
        """Exporta tabelão de OVRs do Setor com pivot table."""
        tg_id = None
        try:
            session = app.config.get('dbsession')
            tg_id = request.args.get('tg_id')
            if not tg_id:
                raise KeyError('Deve ser informado o id do TG (tg_id)')
            formato = request.args.get('formato')
            if not formato:
                formato = 'Safira'
            tg = get_tgovr(session, tg_id)
            out_filename = 'tg_{}_{}.xls'.format(
                tg.numerotg_alnum,
                datetime.strftime(datetime.now(), '%Y-%M-%HT%m:%s'))
            print(formato)
            exporta_planilha_tg(tg,
                                os.path.join(get_user_save_path(), out_filename),
                                TipoPlanilha[formato])
            return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('listaitemtg', tg_id=tg_id))

    @app.route('/exportaplanilhaovr', methods=['GET'])
    @login_required
    def exporta_planilha_ovr():
        """Exporta tabelão de OVRs do Setor com pivot table."""
        try:
            session = app.config.get('dbsession')
            out_filename = 'planilha_ovr1.csv'
            exporta_planilhaovr(session,
                                current_user.name,
                                os.path.join(get_user_save_path(), out_filename))
            return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('minhas_ovrs'))

    @app.route('/excluiobjeto/<classname>/<id>', methods=['POST'])
    @login_required
    def excluiobjeto(classname, id):
        session = app.config.get('dbsession')
        delete_objeto(session, classname, id)
        return jsonify({'msg': 'Excluído'}), 200

    def formata_linhas_relatorio(rows: list) -> list:
        formated_rows = []
        for row in rows:
            formated_cols = []
            for col in row:
                # logger.info(str(col) + str(type(col)))
                if isinstance(col, Decimal):
                    fcol = '{:,.2f}'.format(float(col))
                    fcol = fcol.replace(',', '-').replace('.', ',').replace('-', '.')
                    formated_cols.append(fcol)
                else:
                    formated_cols.append(col)
            formated_rows.append(formated_cols)
        return formated_rows

    @app.route('/programa_rvf_ajna')
    @login_required
    def programa_rvf_ajna():
        """Tela para exibição de um CE Mercante do GridFS.

        Exibe o CE Mercante e os arquivos associados a ele.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        mongo_risco = app.config['mongo_risco']
        ovr = None
        conhecimento = None
        containers = []
        containers_com_rvf = {}
        imagens = {}
        due = {}
        try:
            ovr_id = request.args.get('ovr_id')
            ovr = get_ovr(session, ovr_id)
            if ovr is None or ovr.id is None:
                raise KeyError('OVR não encontrada')
            container = request.args.get('container')
            if container:
                programa_rvf_container(
                    mongodb, mongo_risco, session,
                    ovr, container, imagens.get(container)
                )
                return redirect(url_for('programa_rvf_ajna', ovr_id=ovr_id))
            imagens = get_imagens_dict_container_id(mongodb, ovr.numeroCEmercante,
                                                    ovr.numerodeclaracao)
            conhecimento = get_conhecimento(session, ovr.numeroCEmercante)
            due = get_due(mongodb, ovr.numerodeclaracao)
            containers = get_containers_conhecimento(session, ovr.numeroCEmercante)
            lista_rvf = lista_rvfovr(session, ovr_id)
            if lista_rvf:
                containers_com_rvf = {rvf.numerolote: rvf.id for rvf in lista_rvf}
            for container in containers:
                if imagens.get(container.codigoConteiner) is None:
                    logger.warning(
                        'Alerta: Container {} OVR {} não possui imagem!!!'.format(
                            container.codigoConteiner, ovr_id)
                    )
        except Exception as err:
            flash(str(err))
            logger.error(str(err), exc_info=True)
        return render_template('programa_rvf_ajna.html',
                               ovr=ovr,
                               conhecimento=conhecimento,
                               due=due,
                               containers=containers,
                               containers_com_rvf=containers_com_rvf,
                               imagens=imagens)

    @app.route('/consulta_container', methods=['GET', 'POST'])
    @login_required
    def consulta_container():
        """Tela para consulta única de número de contêiner

        Dentro do intervalo de datas, traz lista de ojetos do sistema que contenham
        alguma referência ao contêiner.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        ovrs = []
        rvfs = []
        infoces = {}
        dues = []
        eventos = []
        imagens = []
        filtro_form = FiltroContainerForm(
            datainicio=date.today() - timedelta(days=10),
            datafim=date.today()
        )
        try:
            if request.method == 'POST':
                filtro_form = FiltroContainerForm(request.form)
                filtro_form.validate()
                rvfs, ovrs, infoces, dues, eventos = \
                    consulta_container_objects(request.form, session, mongodb)
                imagens = get_imagens_container(mongodb,
                                                filtro_form.numerolote.data)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_container.html',
                               oform=filtro_form,
                               rvfs=rvfs,
                               ovrs=ovrs,
                               infoces=infoces,
                               dues=dues,
                               eventos=eventos,
                               imagens=imagens)

    @app.route('/consulta_conteiner_text', methods=['POST'])
    # @login_required
    @csrf.exempt
    def consulta_conteiner_text():
        """Tela para consulta única de número de contêiner

        Dentro do intervalo de seis meses, traz lista de ojetos do sistema que contenham
        alguma referência ao contêiner.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        try:
            numerolote = request.form['numerolote']
            datafim = datetime.strftime(datetime.today(), '%Y-%m-%d')
            datainicio = datetime.strftime(
                datetime.today() - timedelta(days=180), '%Y-%m-%d')
            rvfs, ovrs, infoces, dues, eventos = \
                consulta_container_objects({'numerolote': numerolote,
                                            'datainicio': datainicio,
                                            'datafim': datafim},
                                           session, mongodb)
        except Exception as err:
            logger.error(err, exc_info=True)
            return 'Erro! Detalhes no log da aplicação.\n' + str(err)
        return render_template('pesquisa_container.txt',
                               rvfs=rvfs,
                               ovrs=ovrs,
                               infoces=infoces,
                               dues=dues,
                               eventos=eventos)

    @app.route('/consulta_empresa', methods=['GET', 'POST'])
    @login_required
    def consulta_empresa():
        """Tela para consulta única de Empresa

        Dentro do intervalo de datas, traz lista de ojetos do sistema que contenham
        alguma referência ao CNPJ da Empresa. Permite encontrar CNPJ através do nome.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        empresas_qtdeovrs = []
        ovrs = []
        sats = []
        infoces = {}
        dues = []
        eventos = []
        imagens = []
        filtro_form = FiltroEmpresaForm(
            datainicio=date.today() - timedelta(days=10),
            datafim=date.today()
        )
        try:
            if request.method == 'POST':
                filtro_form = FiltroEmpresaForm(request.form)
                filtro_form.validate()
                if filtro_form.nome.data and not filtro_form.cnpj.data:
                    logger.info('Consultando empresa por nome %s' % filtro_form.nome.data)
                    cnpj_candidatos = get_empresas_nome(session, filtro_form.nome.data)
                    for empresa in cnpj_candidatos:
                        ovrs = get_ovr_empresa(session, empresa.cnpj)
                        empresas_qtdeovrs.append({'empresa': empresa,
                                                  'qtdeovrs': len(ovrs)})
                else:
                    logger.info('Consultando empresa %s' % filtro_form.cnpj.data)
                    empresa = get_empresa(session, filtro_form.cnpj.data)
                    logger.info('get_dues_empresa')
                    dues = get_dues_empresa(mongodb,
                                            filtro_form.cnpj.data)
                    logger.info('get_ovr_empresa')
                    ovrs = get_ovr_empresa(session, filtro_form.cnpj.data)
                    empresas_qtdeovrs = [{'empresa': empresa, 'qtdeovrs': len(ovrs)}]
                    logger.info('get CEs da Empresa')
                    conhecimentos = get_ces_empresa(session, filtro_form.cnpj.data)
                    listaCE = [ce.numeroCEmercante for ce in conhecimentos]
                    logger.info('get detalhes CE Mercante')
                    infoces = get_detalhes_mercante(session, listaCE)
                    logger.info('get SATs')
                    sats = get_sats_cnpj(session, filtro_form.cnpj.data)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_empresa.html',
                               oform=filtro_form,
                               empresas_qtdeovrs=empresas_qtdeovrs,
                               ovrs=ovrs,
                               sats=sats,
                               infoces=infoces,
                               dues=dues,
                               eventos=eventos,
                               imagens=imagens)

    @app.route('/consulta_empresa_text/<cnpj>', methods=['GET'])
    # @login_required
    @csrf.exempt
    def consulta_empresa_text(cnpj):
        """Tela para consulta única de Empresa

        Dentro do intervalo de datas, traz lista de ojetos do sistema que contenham
        alguma referência ao CNPJ da Empresa. Permite encontrar CNPJ através do nome.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        try:
            logger.info('Consultando empresa %s' % cnpj)
            empresa = get_empresa(session, cnpj)
            logger.info('get_dues_empresa')
            dues = get_dues_empresa(mongodb,
                                    cnpj)
            logger.info('get_ovr_empresa')
            ovrs = get_ovr_empresa(session, cnpj)
            empresas_qtdeovrs = [{'empresa': empresa, 'qtdeovrs': len(ovrs)}]
            logger.info('get CEs Empresa')
            conhecimentos = get_ces_empresa(session, cnpj)
            listaCE = [ce.numeroCEmercante for ce in conhecimentos]
            logger.info('get detalhes CE Mercante')
            infoces = get_detalhes_mercante(session, listaCE)
            logger.info('get SATs')
            sats = get_sats_cnpj(session, cnpj)
        except Exception as err:
            logger.error(err, exc_info=True)
            return 'Erro! Detalhes no log da aplicação.\n' + str(err), 500
        return render_template('pesquisa_empresa.txt',
                               empresas_qtdeovrs=empresas_qtdeovrs,
                               ovrs=ovrs,
                               sats=sats,
                               infoces=infoces,
                               dues=dues)

    @app.route('/minhas_fichas_json', methods=['GET'])
    def minhas_fichas_json():
        session = app.config.get('dbsession')
        try:
            # TODO: Login substituir cpf por current_user
            cpf = request.args['cpf']
            ovrs = get_ovr_responsavel(session, cpf)
            if len(ovrs) == 0:
                return jsonify(
                    {'msg': 'Sem Fichas atribuídas para o Usuário {}'.format(cpf)}), 404
            exibicao = ExibicaoOVR(session, TipoExibicao.Descritivo, cpf)
            chaves = exibicao.get_titulos()
            result = []
            for ovr in ovrs:
                id, visualizado, linha = exibicao.get_linha(ovr)
                datahora = datetime.strftime(linha[0], '%d/%m/%Y %H:%M')
                linha_dict = {chaves[0]: id, chaves[1]: datahora}
                for key, value in zip(chaves[2:], linha[1:]):
                    linha_dict[key] = value
                result.append(linha_dict)
        except Exception as err:
            logger.error(err, exc_info=True)
            return 'Erro! Detalhes no log da aplicação.' + str(err)
        return jsonify(result), 200

    @app.route('/get_ovr/<ovr_id>', methods=['GET'])
    def json_ovr(ovr_id):
        session = app.config.get('dbsession')
        aovr = session.query(OVR).filter(OVR.id == ovr_id).one_or_none()
        if aovr is None:
            return jsonify({'msg': 'OVR %s não encontrado' % ovr_id}), 404
        dump = aovr.dump()
        dump['rvfs'] = []
        rvfs = lista_rvfovr(session, ovr_id)
        for arvf in rvfs:
            dump['rvfs'].append(arvf.dump())
        return jsonify(dump), 200

    @app.route('/escaneamentos_conteiner/<numero>', methods=['GET'])
    def escaneamentos_container(numero) -> Tuple[list, int]:
        mongodb = app.config['mongodb']
        try:
            imagens = get_imagens_container(mongodb, numero)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        if len(imagens) == 0:
            return jsonify([]), 404
        result = []
        for imagem in imagens:
            _id = str(imagem['_id'])
            dataescaneamento = None
            metadata = imagem.get('metadata')
            if metadata:
                data = metadata.get('dataescaneamento')
                if data:
                    dataescaneamento = datetime.strftime(data, '%d/%m/%Y %H:%M')
            result.append({'_id': _id, 'dataescaneamento': dataescaneamento})
        return jsonify(result), 200

    @app.route('/ovr/new', methods=['POST'])
    @csrf.exempt
    def nova_ovr_json():
        session = app.config.get('dbsession')
        try:
            cpf = request.json['cpf']
            ovr = cadastra_ovr(session, request.json, cpf)
            session.refresh(ovr)
            atribui_responsavel_ovr(session, ovr.id, cpf)
            session.refresh(ovr)
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': str(err)}), 500
        return jsonify(ovr.dump()), 201

    @app.route('/ver_okrs', methods=['GET'])
    @login_required
    def ver_okrs():
        session = app.config.get('dbsession')
        id_objetivo = request.args.get('objetivo')
        setor_id = request.args.get('setor_id')
        plot_type = request.args.get('plot_type', 0)
        objective = None
        objectives = []
        results = []
        plots = []
        today = date.today()
        lista_key_results = get_key_results_choice(session)
        okrmeta_form = OKRMetaForm(key_results=lista_key_results)
        lista_setores = get_setores(session)
        okrobjective_form = OKRObjectiveForm(setores=lista_setores)
        try:
            if id_objetivo is not None:
                objective = session.query(OKRObjective). \
                    filter(OKRObjective.id == int(id_objetivo)).one()
                setor_id = objective.setor_id
                results = executa_okr_results(session, objective)
                plots = []
                for result in results:
                    if plot_type == '1':
                        plot = burndown_plotly(result)
                    else:
                        delta = ((today - objective.inicio.date()) /
                                 (objective.fim - objective.inicio)) * result.ameta
                        plot = gauge_plotly(result.result.nome, result.ameta,
                                            sum([row['result'] for row in result.resultados]),
                                            delta)
                    plots.append(plot)
            if setor_id is None:
                usuario = get_usuario(session, current_user.name)
                setor_id = usuario.setor_id
            okrobjective_form.setor_id.data = setor_id
            objectives = get_objectives_setor(session, setor_id)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('ver_okrs.html',
                               objective=objective,
                               objectives=objectives,
                               results=results,
                               plots=plots,
                               okrmeta_form=okrmeta_form,
                               okrobjective_form=okrobjective_form)

    @app.route('/okrobjective', methods=['POST'])
    @login_required
    def okrobjective():
        session = app.config.get('dbsession')
        objective_id = None
        setor_id = None
        lista_setores = get_setores(session)
        try:
            okrobjective_form = OKRObjectiveForm(request.form, setores=lista_setores)
            # usuario = get_usuario(session, current_user.name)
            # okrobjective_form.setor_id.data = usuario.setor_id
            okrobjective_form.validate()
            objective = gera_okrobjective(session, dict(okrobjective_form.data.items()))
            objective_id = objective.id
            setor_id = objective.setor_id
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ver_okrs', objetivo=objective_id, setor_id=setor_id))

    @app.route('/exclui_okrobjective', methods=['GET'])
    @login_required
    def exclui_objective():
        session = app.config.get('dbsession')
        objective_id = request.args.get('objective_id')
        try:
            exclui_okrobjective(session, int(objective_id))
        except Exception as err:
            logger.error(err, exc_info=True)
            jsonify({'msg': str(err)}), 500
        return jsonify({'msg': 'Excluído'}), 201

    @app.route('/okrmeta', methods=['POST'])
    @login_required
    def okrmeta():
        session = app.config.get('dbsession')
        objective_id = None
        lista_key_results = get_key_results_choice(session)
        try:
            okrmeta_form = OKRMetaForm(request.form, key_results=lista_key_results)
            okrmeta_form.validate()
            okrmeta = gera_okrmeta(session, dict(okrmeta_form.data.items()))
            objective_id = okrmeta.objective_id
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ver_okrs', objetivo=objective_id))

    @app.route('/exclui_okrmeta', methods=['GET'])
    @login_required
    def exclui_meta():
        session = app.config.get('dbsession')
        meta_id = request.args.get('meta_id')
        try:
            exclui_okrmeta(session, int(meta_id))
        except Exception as err:
            logger.error(err, exc_info=True)
            jsonify({'msg': str(err)}), 500
        return jsonify({'msg': 'Excluído'}), 201

    @app.route('/exporta_cen_rilo', methods=['GET', 'POST'])
    @login_required
    def exporta_cen_rilo():
        """Exporta tabelão de OVRs do Setor com pivot table."""
        session = app.config.get('dbsession')
        today = date.today()
        inicio = date(year=today.year, month=today.month, day=1)
        filtro_form = FiltroRelatorioForm()
        try:
            usuario = get_usuario(session, current_user.name)
            lista_setores = get_setores(session)
            filtro_form = FiltroRelatorioForm(
                datainicio=inicio,
                datafim=date.today(),
                setores=lista_setores
            )
            filtro_form.setor_id.data = usuario.setor_id
            if request.method == 'POST':
                filtro_form = FiltroRelatorioForm(request.form, setores=lista_setores)
                filtro_form.validate()
                timestamp = time.time()
                out_filename = 'rilo-' + str(timestamp) + '.xlsx'
                dict_planilha = monta_planilha_rilo(filtro_form.datainicio.data,
                                                    filtro_form.datafim.data,

                                                    filtro_form.setor_id.data)
                print(dict_planilha)
                df = pd.DataFrame.from_dict(dict_planilha)
                print(df.head())
                df.to_csv(os.path.join(get_user_save_path(), out_filename), index=False)
                return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('cen_rilo.html', oform=filtro_form)

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
                    out_filename = '{}_{}_{}.docx'.format(
                        docx.filename,
                        formdocx.oid.data,
                        datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
                    )
                    ovr_dict = OVRDict(docx.fonte_docx_id).get_dict(
                        db=db, session=session, id=formdocx.oid.data)
                    # print(ovr_dict)
                    document = get_doc_generico_ovr(ovr_dict, documento)
                    document.save(os.path.join(get_user_save_path(), out_filename))
                else:
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
                    inclui_docx(db, session,
                                modeloform.filename.data,
                                modeloform.fonte_docx_id.data,
                                file)
                else:
                    flash(mensagem)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('gera_docx'))
