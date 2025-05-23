import os
import re
import urllib
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
from bhadrasana.analises.escaneamento_operador import sorteia_GMCIs
from bhadrasana.forms.exibicao_ovr import ExibicaoOVR, TipoExibicao, agrupa_ovrs
from bhadrasana.forms.filtro_container import FiltroContainerForm, FiltroCEForm, FiltroDUEForm
from bhadrasana.forms.filtro_empresa import FiltroEmpresaForm, FiltroPessoaForm
from bhadrasana.forms.ovr import OVRForm, FiltroOVRForm, HistoricoOVRForm, \
    ProcessoOVRForm, ItemTGForm, ResponsavelOVRForm, TGOVRForm, FiltroRelatorioForm, \
    FiltroMinhasOVRsForm, OKRObjectiveForm, OKRMetaForm, SetorOVRForm, EscaneamentoOperadorForm, \
    FiltroAbasForm, ResultadoOVRForm
from bhadrasana.models import delete_objeto, get_usuario, \
    usuario_tem_perfil_nome, get_filename_valido
from bhadrasana.models.laudo import get_empresa, get_empresas_nome, get_sats_cnpj, get_pessoas_nome, get_pessoa
from bhadrasana.models.ovr import OVR, OKRObjective, faseOVR
from bhadrasana.models.ovrmanager import cadastra_ovr, get_ovr, \
    get_ovr_filtro, gera_eventoovr, gera_processoovr, get_tipos_processo, lista_itemtg, \
    get_itemtg, get_recintos, \
    cadastra_itemtg, get_usuarios, atribui_responsavel_ovr, lista_tgovr, get_tgovr, \
    cadastra_tgovr, get_ovr_responsavel, Setor, importa_planilha_tg, exporta_planilhaovr, \
    get_tiposmercadoria_choice, \
    inclui_flag_ovr, exclui_flag_ovr, get_flags, informa_lavratura_auto, \
    get_relatorios_choice, \
    executa_relatorio, get_relatorio, get_itens_roteiro_checked, \
    get_flags_choice, cadastra_visualizacao, get_tipos_evento_comfase_choice, \
    get_ovr_criadaspor, get_ovr_empresa, get_tipos_evento_todos, \
    get_delta_date, exporta_planilha_tg, TipoPlanilha, \
    exclui_item_tg, get_setores_choice, get_objectives_setor, \
    executa_okr_results, gera_okrobjective, \
    exclui_okrobjective, get_key_results_choice, gera_okrmeta, exclui_okrmeta, \
    get_usuarios_setores_choice, get_setores_cpf, get_ovr_auditor, get_ovr_passagem, \
    muda_setor_ovr, get_recintos_dte, \
    excluir_processo, excluir_evento, get_ovr_visao_usuario, get_setores_cpf_choice, \
    get_processo, get_ovr_conhecimento, get_ovr_due, get_recintos_unidade, \
    calcula_tempos_por_fase, get_setores_unidade_choice, \
    get_afrfb_choice, get_ovr_one, \
    libera_ovr, get_afrfb_setores_choice, \
    get_setores_unidade, calcula_tempos_por_tipoevento, encerra_ficha, gera_resultadoovr, \
    get_resultado, excluir_resultado, get_ovr_pessoa, get_dsi_pessoa
from bhadrasana.models.ovrmanager import get_marcas_choice
from bhadrasana.models.riscomanager import consulta_container_objects, consulta_ce_objects, \
    consulta_due_objects, get_eventos_conteiner
from bhadrasana.models.rvfmanager import lista_rvfovr, programa_rvf_container, \
    get_infracoes_choice, get_ids_anexos_ordenado
from bhadrasana.models.virasana_manager import get_conhecimento, \
    get_containers_conhecimento, get_ncms_conhecimento, get_imagens_dict_container_id, \
    get_imagens_container, get_ces_empresa, \
    get_detalhes_mercante, get_imagens_conhecimento, get_imagens_due
from bhadrasana.routes.plotly_graphs import bar_plotly, burndown_plotly, gauge_plotly_plot
from bhadrasana.scripts.gera_planilha_rilo import monta_planilha_rilo
from bhadrasana.views import get_user_save_path, valid_file, csrf
from virasana.integracao.due.due_manager import get_due_view, get_dues_empresa


def do_flash(ovrs, descricao):
    if len(ovrs) > 0:
        ovrs_alerta = ['<a href="ovr?id={0}">{0}</a>'.format(oid)
                       for oid in ovrs]
        flash('Atenção!!! {} já possui Fichas: {}'.format(
            descricao, ' ,'.join(ovrs_alerta)))


def flash_alertas(session, ovr):
    if ovr.numeroCEmercante and len(ovr.numeroCEmercante) == 15:
        ovrs_conhecimento = get_ovr_conhecimento(session, ovr.numeroCEmercante)
        ovrs_conhecimento = ovrs_conhecimento - {ovr.id}
        do_flash(ovrs_conhecimento, 'CE-Mercante')
    if ovr.numerodeclaracao and len(ovr.numerodeclaracao) > 10:
        ovrs_due = get_ovr_due(session, ovr.numerodeclaracao)
        ovrs_due = ovrs_due - {ovr.id}
        do_flash(ovrs_due, 'DUE')
    if ovr.cnpj_fiscalizado and len(ovr.cnpj_fiscalizado) > 8:
        hoje = datetime.today()
        ha_seis_meses = hoje - timedelta(days=1230)
        ovrs_empresa = get_ovr_empresa(session, ovr.cnpj_fiscalizado, ha_seis_meses, hoje)
        ovrs_empresa = set([ovr.id for ovr in ovrs_empresa])
        ovrs_empresa = ovrs_empresa - {ovr.id}
        do_flash(ovrs_empresa,
                 'Empresa (mostrando 6 meses, utilize pesquisa empresa para ver mais)')


def ovr_app(app):
    def trata_ovr(request, ovr_id):
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        listahistorico = []
        processos = []
        resultados = []
        conhecimento = None
        ncms = []
        containers = []
        flags_ovr = []
        itens_roteiro = []
        due = None
        ovr = OVR()
        qtdervfs = 0
        qtdeimagens = 0
        flags = []
        whatsapp_text = ''
        ovr_form = OVRForm()
        historico_form = HistoricoOVRForm()
        processo_form = ProcessoOVRForm()
        resultado_form = ResultadoOVRForm()
        responsavel_form = ResponsavelOVRForm()
        setor_ovr_form = SetorOVRForm()
        if ovr_id:
            title_page = 'FICHA ' + ovr_id
        else:
            title_page = 'NOVA FICHA'
        try:
            tiposeventos = get_tipos_evento_comfase_choice(session)
            usuario = get_usuario(session, current_user.name)
            recintos = get_recintos_unidade(session, usuario.setor.cod_unidade)
            listasetores = get_setores_unidade_choice(session, usuario.setor.cod_unidade)
            ids_setores_usuario = [setor.id for setor in get_setores_cpf(session, usuario.cpf)]
            responsaveis = get_usuarios_setores_choice(session, ids_setores_usuario)
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
            setor_ovr_form = SetorOVRForm(setores=listasetores)
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
                        # Mostra alertas de provável Ficha duplicada
                        flash_alertas(session, ovr)
                        # Registra Visualização
                        cadastra_visualizacao(session, ovr, current_user.id)
                        # Extrai informacoes da OVR
                        if ovr.numeroCEmercante:
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
                        if ovr.numerodeclaracao:
                            due = get_due_view(session, ovr.numerodeclaracao)
                        logger.info(f'{due}, {type(due)}')
                        ovr_form.id.data = ovr.id
                        listahistorico = ovr.historico
                        processos = ovr.processos
                        resultados = ovr.resultados
                        flags_ovr = ovr.flags
                        if flags_ovr is not None and len(flags_ovr) <= 0:
                            flash('Dica: adicione um "flag" em Alertas/Observações importantes,'
                                  ' especialmente o motivo de seleção. Isto facilitará as buscas e estatísticas!')
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
                        # Desabiltar edição de Usuário ao informar Evento
                        historico_form.user_name.render_kw = {'disabled': 'disabled'}
                        if ovr_form.dataentrada.data and ovr.setor_id == '2':
                            if get_delta_date(ovr_form.adata.data,
                                              ovr_form.dataentrada.data) >= 90:
                                flash('Alerta: Diferença entre Data de Emissão e '
                                      'Data da Entrada da Carga maior que 90 dias!')
                        try:
                            fiscalizado = None
                            if ovr.cnpj_fiscalizado and len(ovr.cnpj_fiscalizado) == 11:
                                fiscalizado = get_pessoa(session, ovr.cnpj_fiscalizado)
                            if not fiscalizado:
                                fiscalizado = get_empresa(session, ovr.cnpj_fiscalizado)
                            if fiscalizado:
                                ovr_form.nome_fiscalizado.data = fiscalizado.nome
                        except ValueError as err:
                            flash(err)
                        if ovr.fase > 3:
                            historico_form.meramente_informativo.data = True
                            historico_form.meramente_informativo.render_kw = {'read_only': ''}
                        whatsapp_text = f'Ficha {ovr.id}\n{ovr.observacoes}\n' + \
                                        f'https://ajna1.rfoc.srf/bhadrasana2/ovr?id={ovr.id} \n'
                        rvfs = lista_rvfovr(session, ovr.id)
                        if rvfs and len(rvfs) > 0:
                            primeira_rvf = rvfs[0]
                            anexos = get_ids_anexos_ordenado(primeira_rvf)
                            if anexos and len(anexos) > 0:
                                primeiro_anexo = anexos[0]
                                whatsapp_text = whatsapp_text + \
                                                f'https://ajna1.rfoc.srf/bhadrasana2/image/{primeiro_anexo}'
                        whatsapp_text = urllib.parse.quote(whatsapp_text)
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
                               resultado_form=resultado_form,
                               responsavel_form=responsavel_form,
                               listahistorico=listahistorico,
                               processos=processos,
                               resultados=resultados,
                               flags=flags,
                               flags_ovr=flags_ovr,
                               itens_roteiro=itens_roteiro,
                               due=due,
                               setor_ovr_form=setor_ovr_form,
                               title_page=title_page,
                               whatsapp_text=whatsapp_text)

    @app.route('/ovr/<id>', methods=['POST', 'GET'])
    @login_required
    def ovr_id(id):
        return trata_ovr(request, id)

    @app.route('/ovr', methods=['POST', 'GET'])
    @csrf.exempt
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
            novas_flags = inclui_flag_ovr(session, ovr_id, flag_nome, current_user.name)
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
        LIMIT_EXPORTAR = 1_000
        titulos_exibicao = []
        listaovrs = []
        listaagrupada = {}
        tiposeventos = get_tipos_evento_todos(session)
        recintos = get_recintos(session)
        flags = get_flags_choice(session)
        infracoes = get_infracoes_choice(session)
        usuario = get_usuario(session, current_user.name)
        lista_setores = get_setores_unidade_choice(session, usuario.setor.cod_unidade)
        setores = get_setores_unidade(session, usuario.setor.cod_unidade)
        usuarios = get_usuarios_setores_choice(session, setores)
        auditores = get_afrfb_setores_choice(session, setores)
        title_page = 'Pesquisa Fichas'
        filtro_form = FiltroOVRForm(
            datainicio=date.today() - timedelta(days=10),
            datafim=date.today(),
            tiposeventos=tiposeventos,
            recintos=recintos,
            flags=flags,
            infracoes=infracoes,
            setores=lista_setores,
            responsaveis=usuarios,
            auditores=auditores
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
                                            infracoes=infracoes, setores=lista_setores,
                                            responsaveis=usuarios, auditores=auditores)
                filtro_form.validate()
                logger.info('filtro_form data: ' + str(dict(filtro_form.data.items())))
                limite = LIMIT_EXPORTAR if request.form.get('exportar') else LIMIT
                ovrs = get_ovr_filtro(session,
                                      pfiltro=dict(filtro_form.data.items()),
                                      limit=LIMIT)
                # print('******', ovrs)
                tipoexibicao = int(filtro_form.tipoexibicao.data)
                exibicao = ExibicaoOVR(session, tipoexibicao, current_user.id)
                titulos_exibicao = exibicao.get_titulos()
                listaovrs = [exibicao.get_linha(ovr) for ovr in ovrs]
                print(request.form)
                listaagrupada = agrupa_ovrs(ovrs, listaovrs, filtro_form.agruparpor.data)
                if request.form.get('exportar') is not None:
                    linhas = []
                    # linhas.append(titulos_exibicao)
                    for grupo, sub_listaovrs in listaagrupada.items():
                        for linha in listaovrs:
                            linhas.append([grupo, linha[0], *linha[2]])
                    print(linhas)
                    df = pd.DataFrame(linhas)
                    df.columns = ['Grupo', *titulos_exibicao]
                    out_filename = '{}_{}.xlsx'.format('PesquisaFicha_',
                                                      datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
                                                      )
                    df.to_excel(os.path.join(get_user_save_path(), out_filename), index=False)
                    return redirect('static/%s/%s' % (current_user.name, out_filename))
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
                               listaagrupada=listaagrupada,
                               responsavel_form=responsavel_form,
                               historico_form=historico_ovr_form,
                               title_page=title_page)

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
        title_page = 'Minhas Fichas'
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
        responsaveis_setor = get_usuarios_setores_choice(session, setores)
        responsavel_form_setor = ResponsavelOVRForm(responsaveis=responsaveis_setor,
                                                    responsavel=current_user.name)
        historico_ovr_form = HistoricoOVRForm(
            tiposeventos=get_tipos_evento_comfase_choice(session))
        try:
            oform.validate()
            if active_tab == 'minhas_ovrs':
                ovrs = get_ovr_responsavel(session, current_user.name, oform.orfas.data)
            elif active_tab == 'ovrs_meus_setores':
                title_page = 'Fichas dos Meus Setores'
                ovrs = get_ovr_filtro(session,
                                      dict(oform.data.items()),
                                      user_name=current_user.name)
            elif active_tab == 'ovrs_auditor':
                title_page = 'Fichas Sou Auditor Responsável'
                ovrs = get_ovr_auditor(session, current_user.name)
            elif active_tab == 'ovrs_passagem':
                title_page = 'Fichas que passaram por mim'
                ovrs = get_ovr_passagem(session, current_user.name,
                                        oform.datainicio.data, oform.datafim.data)
            else:
                title_page = 'Fichas criadas por mim'
                ovrs = get_ovr_criadaspor(session, current_user.name,
                                          oform.datainicio.data, oform.datafim.data)
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
                               historico_form=historico_ovr_form,
                               title_page=title_page)

    # telegram - Minhas Fichas
    @app.route('/minhas_fichas_text', methods=['GET'])
    def minhas_fichas_text():
        session = app.config.get('dbsession')
        try:
            # TODO: Login substituir cpf por current_user
            cpf = request.args['cpf']
            ovrs = get_ovr_responsavel(session, cpf, False)
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
        lista_setores = get_setores_choice(session)
        linhas = []
        linhas_formatadas = []
        sql = ''
        plot = ''
        today = date.today()
        inicio = date(year=today.year, month=today.month, day=1)
        usuario = get_usuario(session, current_user.name)
        title_page = 'Relatórios'
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
                if request.form.get('exportar') is not None:
                    df = pd.DataFrame(linhas[1:], columns=linhas[0])
                    out_filename = '{}_{}.xlsx'.format(f'Relatorios_{relatorio.nome}',
                                                       datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
                                                       )
                    out_filename = get_filename_valido(out_filename)
                    df.to_excel(os.path.join(get_user_save_path(), out_filename), index=False)
                    return redirect('static/%s/%s' % (current_user.name, out_filename))
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
                               plot=plot,
                               title_page=title_page)

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
                                    responsavel=responsavel_ovr_form.responsavel.data,
                                    user_name=current_user.name
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
                                    user_name=current_user.name,
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

            # 🆕 Pega os novos dados do formulário
            responsavel_cpf = request.form.get('responsavel') or None
            motivo = request.form.get('motivo_setor', '').strip()

            # 🆕 Passa tudo para a função
            muda_setor_ovr(
                session,
                ovr_id=ovr_id,
                setor_id=setor_ovr_form.setor.data,
                user_name=current_user.name,
                responsavel_cpf=responsavel_cpf,
                motivo=motivo
            )

            flash("Ficha transferida com sucesso.")

        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))

        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/usuarios_por_setor')
    @login_required
    def usuarios_por_setor():
        session = app.config.get('dbsession')
        setor_id = request.args.get('setor_id')

        try:
            print(f"Recebido setor_id: {setor_id}")

            if not setor_id:
                return jsonify({'usuarios': []})

            setor_id = int(setor_id)
            print(f"Convertido para inteiro: {setor_id}")

            # 🛠️ Recupera o setor do banco
            setor = session.query(Setor).filter_by(id=setor_id).first()
            if not setor:
                print("Setor não encontrado!")
                return jsonify({'usuarios': []})

            # Passa o objeto setor como lista
            usuarios = get_usuarios_setores_choice(session, [setor])
            print(f"Usuários encontrados: {usuarios}")

            return jsonify({
                'usuarios': [{'cpf': cpf, 'nome': nome} for cpf, nome in usuarios]
            })

        except Exception as e:
            print(f"Erro na rota /usuarios_por_setor: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'usuarios': []}), 500



    @app.route('/libera_ficha', methods=['GET'])
    @login_required
    def libera_ficha():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        try:
            ovr = get_ovr_one(session, ovr_id)
            libera_ovr(session, ovr_id=ovr.id, user_name=current_user.name)
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
                                   user_name=current_user.name)
                else:
                    atribui_responsavel_ovr(session, ovr_id=ovr_id,
                                            responsavel=cpf_responsavel,
                                            user_name=current_user.name)
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
                                   responsavel=responsavel_ovr_form.responsavel.data,
                                   user_name=current_user.name
                                   )
        except Exception as err:
            logger.error(str(err), exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/eventoovr', methods=['POST'])
    @login_required
    def movimentaovr():
        session = app.config.get('dbsession')
        ovr_id = request.form['ovr_id']
        historico_ovr_form = HistoricoOVRForm(request.form)
        user_name = current_user.name
        try:
            # print(historico_ovr_form.data.items(), user_name)
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
        # return redirect(request.referrer)
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
        # return redirect(request.referrer)
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/api/processoovr', methods=['POST'])
    @csrf.exempt
    @login_required
    def processoovr_api():
        session = app.config.get('dbsession')
        try:
            ovr_id = request.form['ovr_id']
            processo_ovr_form = ProcessoOVRForm(request.form)
            processo_ovr_form.validate()
            gera_processoovr(session, dict(processo_ovr_form.data.items()))
            return jsonify({'msg': 'Sucesso!'}), 201
        except Exception as err:
            logger.error(err, exc_info=True)
            return jsonify({'msg': 'Erro: %s' % str(err)}), 500

    @app.route('/resultadoovr', methods=['POST'])
    @login_required
    def resultadoovr():
        session = app.config.get('dbsession')
        try:
            ovr_id = request.form['ovr_id']
            resultado_ovr_form = ResultadoOVRForm(request.form)
            resultado_ovr_form.validate()
            gera_resultadoovr(session, dict(resultado_ovr_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        # return redirect(request.referrer)
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/exclui_resultado')
    @login_required
    def exclui_resultado():
        session = app.config.get('dbsession')
        ovr_id = None
        resultado_id = request.args.get('resultado_id')
        try:
            resultado = get_resultado(session, resultado_id)
            ovr_id = resultado.ovr.id
            excluir_resultado(session, resultado, current_user.name)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/exclui_processo')
    @login_required
    def exclui_processo():
        session = app.config.get('dbsession')
        ovr_id = None
        processo_id = request.args.get('processo_id')
        try:
            processo = get_processo(session, processo_id)
            ovr_id = processo.ovr.id
            excluir_processo(session, processo, current_user.name)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/exclui_evento')
    @login_required
    def exclui_evento():
        session = app.config.get('dbsession')
        ovr_id = request.args.get('ovr_id')
        evento_id = request.args.get('evento_id')
        try:
            excluir_evento(session, evento_id, current_user.name)
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
        title_page = 'Termos de Guarda'
        try:
            listatgovr = lista_tgovr(session, ovr_id)
            marcas = get_marcas_choice(session)
            tipos = get_tiposmercadoria_choice(session)
            usuario = get_usuario(session, current_user.name)
            lista_afrfb = get_afrfb_choice(session, usuario.setor.cod_unidade)
            if item_id:
                tgovr = get_tgovr(session, item_id)
                oform = TGOVRForm(**tgovr.__dict__, marcas=marcas,
                                  tiposmercadoria=tipos, lista_afrfb=lista_afrfb)
            else:
                oform = TGOVRForm(ovr_id=ovr_id, marcas=marcas,
                                  tiposmercadoria=tipos, lista_afrfb=lista_afrfb,
                                  afrfb=current_user.name)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('lista_tgovr.html',
                               listatgovr=listatgovr,
                               oform=oform,
                               title_page=title_page)

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
            title_page = 'TG ' + tg_id
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
                               oform=oform,
                               title_page=title_page)

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
            logger.info(f'Abrindo planilha {planilha}')
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
            out_filename = 'tg_{}_{}.xlsx'.format(
                tg.numerotg_alnum,
                datetime.strftime(datetime.now(), '%Y_%m_%dT%H_%M_%S'))
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
        linha_totais = [0. for r in range(len(rows[0]) - 2)]
        for row in rows:
            for ind, col in enumerate(list(row)[2:]):
                if isinstance(col, Decimal) or isinstance(col, float):
                    try:
                        valor_col = float(col)
                        linha_totais[ind] += valor_col
                    except Exception as err:
                        logger.error(str(err))
                if isinstance(col, int):
                    linha_totais[ind] = int(linha_totais[ind]) + col
        rows_copy = rows.copy()
        rows_copy.append(['--', '--', *linha_totais])
        for row in rows_copy:
            formated_cols = []
            for ind, col in enumerate(row):
                # logger.info(str(col) + str(type(col)))
                if isinstance(col, Decimal) or isinstance(col, float):
                    try:
                        valor_col = float(col)
                        if not valor_col:
                            fcol = '-'
                        else:
                            fcol = '{:,.2f}'.format(valor_col)
                            fcol = fcol.replace(',', '-').replace('.', ',').replace('-', '.')
                    except Exception as err:
                        fcol = '-'
                        logger.error(str(err))
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
        due = None
        try:
            ovr_id = request.args.get('ovr_id')
            ovr = get_ovr(session, ovr_id)
            if ovr is None or ovr.id is None:
                raise KeyError('OVR não encontrada')
            imagens = get_imagens_dict_container_id(mongodb, ovr.numeroCEmercante,
                                                    ovr.numerodeclaracao)
            container = request.args.get('container')
            if container:
                programa_rvf_container(
                    mongodb, mongo_risco, session,
                    ovr, container, imagens.get(container)
                )
                return redirect(url_for('programa_rvf_ajna', ovr_id=ovr_id))
            conhecimento = get_conhecimento(session, ovr.numeroCEmercante)
            due = get_due_view(session, ovr.numerodeclaracao)
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
        # Limitar resultados de todas as pesquisas (exceto OVRs) em 40 linhas
        limit = 20
        ovrs = []
        rvfs = []
        infoces = {}
        dues = []
        eventos = []
        imagens = []
        filtro_form = FiltroContainerForm()
        title_page = 'Pesquisa Contêiner'
        try:
            filtro_form = FiltroContainerForm(request.values)
            if filtro_form.numerolote.data:
                rvfs, ovrs, infoces, dues, eventos = \
                    consulta_container_objects(session,
                                               filtro_form.numerolote.data,
                                               filtro_form.datainicio.data,
                                               filtro_form.datafim.data,
                                               limit=limit)
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
                               imagens=imagens,
                               limit=limit,
                               title_page=title_page)

    @app.route('/consulta_ce', methods=['GET', 'POST'])
    @login_required
    def consulta_ce():
        """Tela para consulta única de número de CE-Mercante

        Dentro do intervalo de datas, traz lista de ojetos do sistema que contenham
        alguma referência ao contêiner.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        ovrs = []
        rvfs = []
        infoce = {}
        imagens = []
        filtro_form = FiltroCEForm()
        title_page = 'Pesquisa CE'
        try:
            filtro_form = FiltroCEForm(request.form)
            if request.method == 'POST' and filtro_form.validate():
                return redirect(
                    f'consulta_ce?numeroCEmercante={filtro_form.numeroCEmercante.data}')
            if request.method == 'GET':
                filtro_form = FiltroCEForm(request.args)
                if filtro_form.numeroCEmercante.data:
                    rvfs, ovrs, infoce = \
                        consulta_ce_objects(filtro_form.numeroCEmercante.data, session)
                    imagens = get_imagens_conhecimento(mongodb, filtro_form.numeroCEmercante.data)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_ce.html',
                               oform=filtro_form,
                               rvfs=rvfs,
                               ovrs=ovrs,
                               infoce=infoce,
                               imagens=imagens,
                               title_page=title_page)

    @app.route('/consulta_due', methods=['GET', 'POST'])
    @login_required
    def consulta_due():
        """Tela para consulta única de número de DUE

        Dentro do intervalo de datas, traz lista de ojetos do sistema que contenham
        alguma referência ao contêiner.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        ovrs = []
        rvfs = []
        due = None
        imagens = []
        filtro_form = FiltroDUEForm()
        title_page = 'Pesquisa DUE'
        try:
            filtro_form = FiltroDUEForm(request.values)
            if filtro_form.numero.data:
                rvfs, ovrs, due = \
                    consulta_due_objects(filtro_form.numero.data, session, mongodb)
                imagens = get_imagens_due(mongodb, filtro_form.numero.data)
                logger.info(f'DUE: {due.numero_due} Tipo: {type(due)} repr: {due}')
                logger.info(f'DUE Itens: {due.itens}')
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_due.html',
                               oform=filtro_form,
                               rvfs=rvfs,
                               ovrs=ovrs,
                               due=due,
                               imagens=imagens,
                               title_page=title_page)

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
                                           session, mongodb, limit=10)
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
        limit = 50
        empresas_qtdeovrs = []
        ovrs = []
        sats = []
        infoces = {}
        dues = []
        eventos = []
        imagens = []
        title_page = 'Pesquisa Empresa'
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
                                            filtro_form.cnpj.data, limit=limit)
                    logger.info('get_ovr_empresa')
                    ovrs = get_ovr_empresa(session, filtro_form.cnpj.data)
                    empresas_qtdeovrs = [{'empresa': empresa, 'qtdeovrs': len(ovrs)}]
                    logger.info('get CEs da Empresa')
                    conhecimentos = get_ces_empresa(session, filtro_form.cnpj.data, limit=limit)
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
                               imagens=imagens,
                               limit=limit,
                               title_page=title_page)

    @app.route('/consulta_pessoa', methods=['GET', 'POST'])
    @login_required
    def consulta_pessoa():
        """Tela para consulta única de Pessoa

        Dentro do intervalo de datas, traz lista de ojetos do sistema que contenham
        alguma referência ao CPF da Pessoa. Permite encontrar CPF através do nome.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        limit = 50
        pessoas_qtdeovrs = []
        ovrs = []
        dsis = []
        conhecimentos = []
        infoces = {}
        title_page = 'Pesquisa Pessoa Física'
        filtro_form = FiltroPessoaForm(
            datainicio=date.today() - timedelta(days=10),
            datafim=date.today()
        )
        try:
            if request.method == 'POST':
                filtro_form = FiltroPessoaForm(request.form)
                filtro_form.validate()
                if filtro_form.nome.data and not filtro_form.cpf.data:
                    logger.info('Consultando pessoa por nome %s' % filtro_form.nome.data)
                    cpfs_candidatos = get_pessoas_nome(session, filtro_form.nome.data)
                    for pessoa in cpfs_candidatos:
                        ovrs = get_ovr_pessoa(session, pessoa.cpf)
                        pessoas_qtdeovrs.append({'pessoa': pessoa,
                                                 'qtdeovrs': len(ovrs)})
                else:
                    logger.info('Consultando pessoa %s' % filtro_form.cpf.data)
                    pessoa = get_pessoa(session, filtro_form.cpf.data)
                    logger.info('get Fichas')
                    ovrs = get_ovr_pessoa(session, pessoa.cpf)
                    logger.info('get CEs da Pessoa')
                    conhecimentos = get_ces_empresa(session, filtro_form.cpf.data, limit=limit)
                    listaCE = [ce.numeroCEmercante for ce in conhecimentos]
                    logger.info('get detalhes CE Mercante')
                    infoces = get_detalhes_mercante(session, listaCE)
                    logger.info('get DSIs')
                    dsis = get_dsi_pessoa(session, pessoa.cpf)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_pessoa.html',
                               oform=filtro_form,
                               pessoas_qtdeovrs=pessoas_qtdeovrs,
                               ovrs=ovrs,
                               conhecimentos=conhecimentos,
                               infoces=infoces,
                               dsis=dsis,
                               limit=limit,
                               title_page=title_page)

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
            dues = get_dues_empresa(mongodb, cnpj)
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

    # telegram - Mostra Ficha
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
            atribui_responsavel_ovr(session, ovr.id, cpf, cpf)
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
        lista_setores = get_setores_choice(session)
        okrobjective_form = OKRObjectiveForm(setores=lista_setores)
        title_page = 'Painel OKRs'
        try:
            if id_objetivo is not None:
                objective = session.query(OKRObjective). \
                    filter(OKRObjective.id == int(id_objetivo)).one_or_none()
                if objective is not None:
                    setor_id = objective.setor_id
                    results = executa_okr_results(session, objective)
                    plots = []
                    for result in results:
                        if plot_type == '1':
                            plot = burndown_plotly(result)
                        else:
                            try:
                                delta = ((today - objective.inicio.date()) /
                                         (objective.fim - objective.inicio)) * result.ameta
                            except:
                                print(objective.fim)
                                print(objective.inicio)
                                print(result.ameta)
                                delta = 0.
                            plot = gauge_plotly_plot(result.result.nome, result.ameta,
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
                               okrobjective_form=okrobjective_form,
                               title_page=title_page)

    @app.route('/okrobjective', methods=['POST'])
    @login_required
    def okrobjective():
        session = app.config.get('dbsession')
        objective_id = None
        setor_id = None
        lista_setores = get_setores_choice(session)
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

    @app.route('/exclui_okrobjective/<objetivo_id>', methods=['POST'])
    @login_required
    def exclui_objective(objetivo_id):
        session = app.config.get('dbsession')
        setor_id = request.form.get('setor_id')

        try:
            exclui_okrobjective(session, int(objetivo_id))
            flash(f'Objetivo {objetivo_id} excluído')
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ver_okrs', setor_id=setor_id))

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

    @app.route('/exclui_okrmeta/<metaid>', methods=['POST'])
    @login_required
    def exclui_meta(metaid):
        session = app.config.get('dbsession')
        setor_id = request.form.get('setor_id')
        objective_id = request.form.get('objective_id')
        try:
            exclui_okrmeta(session, int(metaid))
            flash(f'Meta {metaid} excluída')
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('ver_okrs', objetivo=objective_id, setor_id=setor_id))

    @app.route('/exporta_cen_rilo', methods=['GET', 'POST'])
    @login_required
    def exporta_cen_rilo():
        """Exporta tabelão de OVRs do Setor com pivot table."""
        session = app.config.get('dbsession')
        today = date.today()
        inicio = date(year=today.year, month=today.month, day=1)
        filtro_form = FiltroRelatorioForm()
        title_page = 'Exporta Planilha CEN Rilo'
        try:
            usuario = get_usuario(session, current_user.name)
            lista_setores = get_setores_choice(session)
            filtro_form = FiltroRelatorioForm(
                datainicio=inicio,
                datafim=date.today(),
                setores=lista_setores
            )
            filtro_form.setor_id.data = usuario.setor_id
            if request.method == 'POST':
                filtro_form = FiltroRelatorioForm(request.form, setores=lista_setores)
                filtro_form.validate()
                out_filename = \
                    f'rilo_{datetime.strftime(filtro_form.datainicio.data, "%Y-%m-%d")} a ' \
                    f'{datetime.strftime(filtro_form.datafim.data, "%Y-%m-%d")}_' \
                    f'{datetime.strftime(datetime.now(), "%y-%m-%dT%H-%M-%S")}.xlsx'
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
        return render_template('cen_rilo.html', oform=filtro_form, title_page=title_page)

    @app.route('/escaneamento_operador', methods=['GET', 'POST'])
    @login_required
    def escaneamento_operador():
        session = app.config['dbsession']
        gmcis = []
        escaneamento_form = EscaneamentoOperadorForm()
        title_page = 'Lista para Escaneamento no Operador'
        try:
            recintos = get_recintos_dte(session)
            if request.method == 'POST':
                end = datetime.now()
                start = end - timedelta(days=7)
                escaneamento_form = EscaneamentoOperadorForm(request.form, recintos=recintos)
                if escaneamento_form.validate():
                    qtde = escaneamento_form.qtde.data
                    lista_recintos = []
                    for recinto in escaneamento_form.lista_recintos.data.split(','):
                        try:
                            lista_recintos.append(int(recinto))
                        except ValueError:
                            pass
                    logger.info('Usuário %s escolheu %s escaneamentos_operador de GMCIS de %s a %s'
                                % (current_user.name, qtde, start, end))
                    gmcis = sorteia_GMCIs(session, lista_recintos, start, end, qtde)
                else:
                    flash(escaneamento_form.errors)
            else:
                escaneamento_form = EscaneamentoOperadorForm(recintos=recintos)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('escaneamento_operador.html',
                               filtro_form=escaneamento_form,
                               gmcis=gmcis,
                               title_page=title_page)

    # kanban
    @app.route('/fichas_em_abas', methods=['GET', 'POST'])
    @login_required
    def fichas_em_abas():
        session = app.config['dbsession']
        listasficharesumo = []
        filtroform = FiltroAbasForm()
        supervisor = False
        temposmedios_por_fase = {}
        title_page = 'Kanban'
        try:
            usuario = get_usuario(session, current_user.name)
            if usuario is None:
                raise Exception('Erro: Usuário não encontrado!')
            # Setores do Usuário???
            setores = get_setores_cpf_choice(session, current_user.id)
            # Ou permitir visualizar todos os Setores
            setores = get_setores_choice(session)
            flags = get_flags_choice(session)
            supervisor = usuario_tem_perfil_nome(session, current_user.name, 'Supervisor')
            if request.method == 'POST':
                # print(request.form)
                filtroform = FiltroAbasForm(request.form, setores=setores, flags=flags)
                if filtroform.validate():
                    lista_flags = filtroform.flags_id.data
                    if 99 in lista_flags:
                        lista_flags = None
                    lista_tipos = filtroform.tipooperacao_id.data
                    if 99 in lista_tipos:
                        lista_tipos = None
                    listaficharesumo = get_ovr_visao_usuario(session,
                                                             filtroform.datainicio.data,
                                                             filtroform.datafim.data,
                                                             current_user.id,
                                                             setor_id=filtroform.setor_id.data,
                                                             lista_flags=lista_flags,
                                                             lista_tipos=lista_tipos)
                    temposmedios_por_fase = calcula_tempos_por_fase(listaficharesumo)
                    print(temposmedios_por_fase)
                    listasficharesumo = {}
                    for fase in faseOVR:
                        listasficharesumo[fase] = defaultdict(list)
                    exibicao_ovr = ExibicaoOVR(session, TipoExibicao.Resumo, current_user.id)
                    for ovr in listaficharesumo:
                        resumo = exibicao_ovr.get_OVR_resumo_html(ovr, mercante=False,
                                                                  fiscalizado=True,
                                                                  responsaveis=True,
                                                                  responsabilidade=True,
                                                                  trabalho=True)
                        responsavel_cpf = ovr.responsavel_cpf if ovr.responsavel_cpf \
                            else ' Nenhum'
                        listasficharesumo[ovr.get_fase()][responsavel_cpf]. \
                            append({'id': ovr.id, 'resumo': resumo})
                    # Ordenar por usuário
                    for fase in faseOVR:
                        if listasficharesumo.get(fase):
                            _ordenado = [[k, v] for k, v in listasficharesumo[fase].items()]
                            _ordenado = sorted(_ordenado, key=lambda x: x[0])
                            listasficharesumo[fase] = dict(_ordenado)
                else:
                    flash(filtroform.errors)
            else:
                today = date.today()
                start = today - timedelta(days=62)
                inicio = date(year=start.year, month=start.month, day=1)
                filtroform = FiltroAbasForm(datainicio=inicio,
                                            datafim=today,
                                            setores=setores,
                                            flags=flags,
                                            supervisor=supervisor)
                # filtroform.setor_id.data = usuario.setor_id
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('fichas_em_abas.html',
                               oform=filtroform,
                               listafases=faseOVR,
                               listasficharesumo=listasficharesumo,
                               temposmedios_por_fase=temposmedios_por_fase,
                               supervisor=supervisor,
                               title_page=title_page)

    # kanban
    @app.route('/fichas_em_abas2', methods=['GET', 'POST'])
    @login_required
    def fichas_em_abas2():
        session = app.config['dbsession']
        listasficharesumo = []
        filtroform = FiltroAbasForm()
        supervisor = False
        temposmedios_por_fase = {}
        tipos_presentes = []
        try:
            usuario = get_usuario(session, current_user.name)
            if usuario is None:
                raise Exception('Erro: Usuário não encontrado!')
            # Setores do Usuário???
            setores = get_setores_cpf_choice(session, current_user.id)
            # Ou permitir visualizar todos os Setores
            setores = get_setores_choice(session)
            flags = get_flags_choice(session)
            supervisor = usuario_tem_perfil_nome(session, current_user.name, 'Supervisor')
            if request.method == 'POST':
                # print(request.form)
                filtroform = FiltroAbasForm(request.form, setores=setores, flags=flags)
                if filtroform.validate():
                    lista_flags = filtroform.flags_id.data
                    if 99 in lista_flags:
                        lista_flags = None
                    lista_tipos = filtroform.tipooperacao_id.data
                    if 99 in lista_tipos:
                        lista_tipos = None
                    listaficharesumo = get_ovr_visao_usuario(session,
                                                             filtroform.datainicio.data,
                                                             filtroform.datafim.data,
                                                             current_user.id,
                                                             setor_id=filtroform.setor_id.data,
                                                             lista_flags=lista_flags,
                                                             lista_tipos=lista_tipos)
                    listaficharesumo = [ovr for ovr in listaficharesumo if ovr.fase in (1, 2)]
                    temposmedios_por_fase = calcula_tempos_por_tipoevento(listaficharesumo)
                    listasficharesumo = {}
                    tipos_presentes = set([ovr.tipoevento for ovr in listaficharesumo])
                    tipos_presentes = sorted(tipos_presentes, key=lambda x: x.ordem)
                    tipos_presentes = [tipo for tipo in tipos_presentes]
                    for tipoevento in tipos_presentes:
                        listasficharesumo[tipoevento] = defaultdict(list)
                    exibicao_ovr = ExibicaoOVR(session, TipoExibicao.Resumo, current_user.id)
                    for ovr in listaficharesumo:
                        resumo = exibicao_ovr.get_OVR_resumo_html(ovr, mercante=False,
                                                                  fiscalizado=True,
                                                                  responsaveis=True,
                                                                  responsabilidade=True,
                                                                  trabalho=True)
                        responsavel_cpf = ovr.responsavel_cpf if ovr.responsavel_cpf \
                            else ' Nenhum'
                        listasficharesumo[ovr.tipoevento][responsavel_cpf]. \
                            append({'id': ovr.id, 'resumo': resumo})
                    # Ordenar por usuário
                    for tipoevento in tipos_presentes:
                        if listasficharesumo.get(tipoevento):
                            _ordenado = [[k, v] for k, v in listasficharesumo[tipoevento].items()]
                            _ordenado = sorted(_ordenado, key=lambda x: x[0])
                            listasficharesumo[tipoevento] = dict(_ordenado)
                else:
                    flash(filtroform.errors)
            else:
                today = date.today()
                start = today - timedelta(days=62)
                inicio = date(year=start.year, month=start.month, day=1)
                filtroform = FiltroAbasForm(datainicio=inicio,
                                            datafim=today,
                                            setores=setores,
                                            flags=flags,
                                            supervisor=supervisor)
                # filtroform.setor_id.data = usuario.setor_id
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('fichas_em_abas2.html',
                               oform=filtroform,
                               listafases=faseOVR,
                               listasficharesumo=listasficharesumo,
                               temposmedios_por_fase=temposmedios_por_fase,
                               supervisor=supervisor,
                               tipos_presentes=tipos_presentes)

    @app.route('/ficha/summary/<oid>', methods=['GET', 'POST'])
    @login_required
    def ficha_summary(oid):
        session = app.config['dbsession']
        try:
            exibicao_ovr = ExibicaoOVR(session, TipoExibicao.Resumo, current_user.id)
            ovr = get_ovr(session, oid)
            resumo_html = exibicao_ovr.get_OVR_resumo(ovr, mercante=False,
                                                      mostra_ovr=True, eventos=True)
            resumo_texto = '\n'.join(resumo_html)
            resumo_texto = re.sub(re.compile('<.*?>'), ' ', resumo_texto)
            return resumo_texto
        except Exception as err:
            logger.error(err, exc_info=True)
            return 'Erro! Detalhes no log da aplicação: %s' % err

    @app.route('/pesquisa_simples', methods=['GET', 'POST'])
    @login_required
    def pesquisa_simples():
        session = app.config.get('dbsession')
        if request.method == 'POST':
            objeto_a_pesquisar = request.form.get('objeto_a_pesquisar')
            if objeto_a_pesquisar == 'ficha':
                termo_a_pesquisar = request.form.get('termo_a_pesquisar')
                resultado = session.query(OVR).filter(OVR.id == termo_a_pesquisar).one_or_none()
            if objeto_a_pesquisar == 'ce':
                termo_a_pesquisar = request.form.get('termo_a_pesquisar')
                # ovrs = get_ovr_filtro(session=session, pfiltro=termo_a_pesquisar)
                # rvfs = get_rvfs_filtro(session=session, pfiltro=termo_a_pesquisar)
                # if ovrs:
                #     resultado == ovrs
                # if rvfs:
                #     resultado == rvfs

        return render_template('pesquisa_simples.html', resultado=resultado)

    @app.route('/encerrar_ficha', methods=['GET', 'POST'])
    @login_required
    def encerrar_ficha():
        session = app.config.get('dbsession')
        ovr_id = request.values.get('ovr_id')
        usuario = get_usuario(session, current_user.name)
        user_name = usuario.cpf
        try:
            encerra_ficha(session, ovr_id, user_name)
            flash(f'Ficha nº {ovr_id} encerrada com sucesso!')
        except Exception as err:
            logger.error('Erro ao encerrar a ficha')
            logger.error(str(err))
            flash('Ficha não encerrada. ' + str(err))
        return redirect(url_for('ovr', id=ovr_id))

    # telegram - Minhas Fichas
    @app.route('/api/minhas_verificacoes', methods=['GET'])
    def api_minhas_verificacoes():
        session = app.config.get('dbsession')
        try:
            cpf = request.args['cpf']
            ovrs = get_ovr_responsavel(session, cpf, False)
            if len(ovrs) == 0:
                result = 'Sem Verificações atribuídas para o Usuário {}'.format(cpf)
            else:
                # cria dicionario result
                # chave = RVF e valor = conteiner
                result = {}
                # percorre ovrs e lista RVFs
                for aovr in ovrs:
                    rvfs = lista_rvfovr(session, aovr.id)
                    # adiciona ao result uma tupla com o id de cada RVF e o conteiner
                    for rvf in rvfs:
                        if rvf.numerolote:
                            result[str(rvf.id)] = str(rvf.numerolote)

        except Exception as err:
            logger.error(err, exc_info=True)
            return 'Erro! Detalhes no log da aplicação.' + str(err)
        return jsonify(result), 200

    def get_eventos_resumo(session, request):
        numero = request.args['numero']
        data = request.args['data']
        fim = datetime.strptime(data, '%Y-%m-%d %H:%M:%S') + timedelta(days=5)
        inicio = fim - timedelta(days=30)
        logger.info(f'get_eventos_resumo numero:{numero}, inicio:{inicio}, fim:{fim}')
        return get_eventos_conteiner(session, numero, inicio, fim)

    # Resumo de Eventos da API próximos de um escaneamento
    @app.route('/eventos_resumo', methods=['GET'])
    def eventos_resumo():
        session = app.config.get('dbsession')
        eventos = []
        try:
            eventos = get_eventos_resumo(session, request)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('diveventos.html', eventos=eventos)

    @app.route('/eventos_resumo_text', methods=['GET'])
    def eventos_resumo_text():
        session = app.config.get('dbsession')
        eventos = []
        try:
            eventos = get_eventos_resumo(session, request)
        except Exception as err:
            return 'Erro! Detalhes no log da aplicação.' + str(err), 500
        linhas = [(f'Data:{evento.get("data")} Recinto: {evento.get("recinto")} '
                   f'Tipo: {evento.get("tipo")} Info: {evento.get("info")}')
                  for evento in eventos]
        return '<br>'.join(linhas), 200

    @app.route('/eventos_resumo_json', methods=['GET'])
    def eventos_resumo_json():
        session = app.config.get('dbsession')
        eventos = []
        try:
            eventos = get_eventos_resumo(session, request)
        except Exception as err:
            return jsonify({'msg': 'Erro! Detalhes no log da aplicação.' + str(err)}), 500
        return jsonify(eventos), 200
