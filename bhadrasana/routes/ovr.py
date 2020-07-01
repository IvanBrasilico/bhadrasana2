import datetime
import os
from _collections import defaultdict
from decimal import Decimal
from typing import Tuple

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from gridfs import GridFS
from werkzeug.utils import redirect

from ajna_commons.flask.log import logger
from bhadrasana.forms.exibicao_ovr import ExibicaoOVR, TipoExibicao
from bhadrasana.forms.filtro_container import FiltroContainerForm
from bhadrasana.forms.filtro_empresa import FiltroEmpresaForm
from bhadrasana.forms.ovr import OVRForm, FiltroOVRForm, HistoricoOVRForm, \
    ProcessoOVRForm, ItemTGForm, ResponsavelOVRForm, TGOVRForm, FiltroRelatorioForm, \
    FiltroMinhasOVRsForm
from bhadrasana.models import delete_objeto, get_usuario
from bhadrasana.models.laudo import get_empresa, get_empresas_nome, get_sats_cnpj
from bhadrasana.models.ovr import ItemTG, OVR
from bhadrasana.models.ovrmanager import cadastra_ovr, get_ovr, \
    get_ovr_filtro, gera_eventoovr, gera_processoovr, get_tipos_processo, lista_itemtg, \
    get_itemtg, get_recintos, \
    cadastra_itemtg, get_usuarios, atribui_responsavel_ovr, lista_tgovr, get_tgovr, \
    cadastra_tgovr, get_ovr_responsavel, importa_planilha, exporta_planilhaovr, \
    get_tiposmercadoria_choice, \
    inclui_flag_ovr, exclui_flag_ovr, get_flags, informa_lavratura_auto, \
    get_relatorios_choice, \
    executa_relatorio, get_relatorio, get_afrfb, get_itens_roteiro_checked, \
    get_flags_choice, cadastra_visualizacao, get_tipos_evento_comfase_choice, \
    get_ovr_container, get_ovr_criadaspor, get_ovr_empresa, get_tipos_evento_todos, \
    desfaz_ultimo_eventoovr
from bhadrasana.models.ovrmanager import get_marcas_choice
from bhadrasana.models.riscomanager import get_eventos_conteiner, \
    consulta_container_objects
from bhadrasana.models.rvfmanager import lista_rvfovr, programa_rvf_container, \
    get_infracoes_choice, get_rvfs_filtro
from bhadrasana.models.virasana_manager import get_conhecimento, \
    get_containers_conhecimento, get_ncms_conhecimento, get_imagens_dict_container_id, \
    get_imagens_container, get_dues_container, get_dues_empresa, get_ces_empresa, \
    get_due, get_detalhes_mercante
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
                        fiscalizado = get_empresa(session, ovr.cnpj_fiscalizado)
                        if fiscalizado:
                            ovr_form.nome_fiscalizado.data = fiscalizado.nome
                        if ovr.tipooperacao != 0:
                            historico_form.user_name.render_kw = {'disabled': 'disabled'}
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
                               due=due)

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
        ovrs = []
        tiposeventos = get_tipos_evento_todos(session)
        recintos = get_recintos(session)
        flags = get_flags_choice(session)
        infracoes = get_infracoes_choice(session)
        filtro_form = FiltroOVRForm(
            datainicio=datetime.date.today() - datetime.timedelta(days=10),
            datafim=datetime.date.today(),
            tiposeventos=tiposeventos,
            recintos=recintos,
            flags=flags,
            infracoes=infracoes
        )
        try:
            if request.method == 'POST':
                logger.info('Consulta de Ficha: ' + str(dict(request.form.items())))
                filtro_form = FiltroOVRForm(request.form, tiposeventos=tiposeventos,
                                            recintos=recintos, flags=flags,
                                            infracoes=infracoes)
                filtro_form.validate()
                logger.info('filtro_form data: ' + str(dict(filtro_form.data.items())))
                ovrs = get_ovr_filtro(session, current_user.name,
                                      dict(filtro_form.data.items()),
                                      filtrar_setor=False)
                # print('******', ovrs)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('pesquisa_ovr.html',
                               oform=filtro_form,
                               ovrs=ovrs)

    @app.route('/ovrs_meus_setores', methods=['GET', 'POST'])
    @app.route('/ovrs_criador', methods=['GET', 'POST'])
    @app.route('/minhas_ovrs', methods=['GET', 'POST'])
    @login_required
    def minhas_ovrs():
        TABS = ('minhas_ovrs', 'ovrs_meus_setores', 'ovrs_criador')
        session = app.config.get('dbsession')
        listasovrs = defaultdict(list)
        titulos_exibicao = []
        today = datetime.date.today()
        inicio = datetime.date(year=today.year, month=today.month, day=1)
        active_tab = request.args.get('active_tab')
        if active_tab is None or active_tab not in TABS:
            if 'minhas_ovrs' in request.url:
                active_tab = 'minhas_ovrs'
            elif 'ovrs_meus_setores' in request.url:
                active_tab = 'ovrs_meus_setores'
            else:
                active_tab = 'ovrs_criador'
        if request.method == 'POST':
            oform = FiltroMinhasOVRsForm(request.form, active_tab=active_tab)
        else:
            oform = FiltroMinhasOVRsForm(datainicio=inicio,
                                         datafim=datetime.date.today(),
                                         active_tab=active_tab)
        responsaveis = get_usuarios(session)
        responsavel_form = ResponsavelOVRForm(responsaveis=responsaveis,
                                              responsavel=current_user.name)
        historico_ovr_form = HistoricoOVRForm(
            tiposeventos=get_tipos_evento_comfase_choice(session))
        try:
            oform.validate()
            if active_tab == 'minhas_ovrs':
                ovrs = get_ovr_responsavel(session, current_user.name)
            elif active_tab == 'ovrs_meus_setores':
                ovrs = get_ovr_filtro(session, current_user.name,
                                      dict(oform.data.items()))
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
                    datahora = datetime.datetime.strftime(linha[0], '%d/%m/%Y %H:%M')
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
        linhas = []
        sql = ''
        plot = ''
        today = datetime.date.today()
        inicio = datetime.date(year=today.year, month=today.month, day=1)
        filtro_form = FiltroRelatorioForm(
            datainicio=inicio,
            datafim=datetime.date.today(),
            relatorios=lista_relatorios,
        )
        try:
            if request.method == 'POST':
                filtro_form = FiltroRelatorioForm(request.form,
                                                  relatorios=lista_relatorios)
                filtro_form.validate()
                relatorio = get_relatorio(session, int(filtro_form.relatorio.data))
                if relatorio is None:
                    raise ValueError('Relatório %s não encontrado' %
                                     filtro_form.relatorio.data)
                sql = relatorio.sql
                linhas = executa_relatorio(session, current_user.name,
                                           relatorio,
                                           filtro_form.datainicio.data,
                                           filtro_form.datafim.data,
                                           filtrar_setor=False)
                plot = bar_plotly(linhas, relatorio.nome)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('relatorios.html',
                               oform=filtro_form,
                               linhas=linhas,
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

    @app.route('/responsavelovr_minhasovrs', methods=['POST'])
    @app.route('/eventoovr_minhasovrs', methods=['POST'])
    @login_required
    def atribuirresponsavel_minhasovrs():
        session = app.config.get('dbsession')
        try:
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
            return redirect(url_for('minhas_ovrs', active_tab=active_tab))
        except Exception as err:
            logger.error(err, exc_info=True)
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
        ovr_id = request.form['ovr_id']
        processo_ovr_form = ProcessoOVRForm(request.form)
        processo_ovr_form.validate()
        gera_processoovr(session, dict(processo_ovr_form.data.items()))
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
            cadastra_itemtg(session, dict(itemtg_form.data.items()))
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
            itemtg = session.query(ItemTG).filter(ItemTG.id == int(id)).one_or_none()
            setattr(itemtg, campo, valor)
            session.add(itemtg)
            session.commit()
        except Exception as err:
            logger.error(err, exc_info=True)
            return {'error': str(err), 'msg': 'Erro!'}, 500
        return {'msg': 'Modificado com sucesso'}, 200

    @app.route('/importaplanilhatg', methods=['POST'])
    @login_required
    def importa_planilha_tg():
        try:
            session = app.config.get('dbsession')
            tg_id = request.form['tg_id']
            tg = get_tgovr(session, tg_id)
            planilha = request.files['planilha']
            importa_planilha(session, tg, planilha)
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

    def bar_plotly(linhas: list, nome: str) -> str:
        """Renderiza gráfico no plotly e serializa via HTTP/HTML."""
        meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
        try:
            # Converter decimal para float
            linhas_float = []
            for linha in linhas[1:]:
                linha_float = []
                for item in linha:
                    if isinstance(item, Decimal):
                        linha_float.append(float(item))
                    else:
                        linha_float.append(item)
                linhas_float.append(linha_float)
            df = pd.DataFrame(linhas_float, columns=linhas[0])
            df['strmes'] = df['Mês'].apply(lambda x: meses[int(x)])
            df['Ano e Mês'] = df['strmes'].astype(str) + ' de ' + df['Ano'].astype(str)
            df = df.drop(columns=['Ano', 'Mês', 'strmes'])
            df = df.groupby(['Ano e Mês']).sum()
            df = df.reset_index()
            # print(linhas)
            print(df.head())
            # print(df.dtypes)
            x = df['Ano e Mês'].tolist()
            df = df.drop(columns=['Ano e Mês'])
            numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
            data = [go.Bar(x=x, y=df[column].tolist(), name=column)
                    for column in numeric_columns]
            plot = plotly.offline.plot({
                'data': data,
                'layout': go.Layout(title=nome + ' soma mensal',
                                    xaxis=go.layout.XAxis(type='category'))
            },
                show_link=False,
                output_type='div',
                image_width=400)
            return plot
        except Exception as err:
            logger.log(str(err), exc_info=True)
            return ''

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
            datainicio=datetime.date.today() - datetime.timedelta(days=10),
            datafim=datetime.date.today()
        )
        try:
            if request.method == 'POST':
                filtro_form = FiltroContainerForm(request.form)
                filtro_form.validate()
                logger.info('Consultando contêiner %s' % filtro_form.numerolote.data)
                logger.info('get_rvfs_filtro')
                rvfs = get_rvfs_filtro(session, dict(filtro_form.data.items()))
                logger.info('get_dues_container')
                dues = get_dues_container(mongodb,
                                          filtro_form.numerolote.data)
                lista_numeroDUEs = [due['numero'] for due in dues]
                logger.info('get_ovr_container')
                ces, ovrs = get_ovr_container(session, filtro_form.numerolote.data,
                                              filtro_form.datainicio.data,
                                              filtro_form.datafim.data,
                                              lista_numeroDUEs)
                logger.info('get detalhes CE Mercante')
                infoces = get_detalhes_mercante(session, ces)
                logger.info('get_eventos_container')
                eventos = get_eventos_conteiner(session,
                                                filtro_form.numerolote.data)
                logger.info('get_imagens_container')
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

        Dentro do intervalo de datas, traz lista de ojetos do sistema que contenham
        alguma referência ao contêiner.
        """
        session = app.config.get('dbsession')
        mongodb = app.config['mongodb']
        try:
            rvfs, ovrs, infoces, dues, eventos = \
                consulta_container_objects(request, session, mongodb)
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
            datainicio=datetime.date.today() - datetime.timedelta(days=10),
            datafim=datetime.date.today()
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
                datahora = datetime.datetime.strftime(linha[0], '%d/%m/%Y %H:%M')
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
                    dataescaneamento = datetime.datetime.strftime(data, '%d/%m/%Y %H:%M')
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
