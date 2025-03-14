import os
from datetime import date, timedelta
from datetime import datetime

from dateutil import parser
from flask import (flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required
from werkzeug.datastructures import MultiDict
from werkzeug.utils import secure_filename

from ajna_commons.flask.log import logger
from bhadrasana.forms.editarisco import get_edita_risco_form
from bhadrasana.forms.riscosativos import RiscosAtivosForm, RecintoRiscosAtivosForm
from bhadrasana.models.importa_planilha_recintos import processa_planilha
from bhadrasana.models.riscomanager import mercanterisco, riscosativos, \
    insererisco, exclui_risco, CAMPOS_RISCO, get_lista_csv, save_planilharisco, \
    recintosrisco, CAMPOS_FILTRO_IMAGEM, exclui_riscos, le_csv
from bhadrasana.views import get_user_save_path, tmpdir


def get_planilha_valida(request, anexo_name='csv',
                        extensoes=['csv', 'xls', 'ods', 'xlsx']):
    planilha = request.files.get(anexo_name)
    if planilha is None:
        flash('Arquivo não repassado')
    if planilha.filename == '':
        flash('Nome de arquivo vazio')
    else:
        if '.' in planilha.filename:
            extensao = planilha.filename.rsplit('.', 1)[1].lower()
            if extensao in extensoes:
                return planilha
        flash('Extensão %s inválida/desconhecida' % extensao)
    return None


def risco_app(app):
    def append_images(mongodb, lista_risco, active_tab):
        lista_risco_nova = []
        campos_filtro = CAMPOS_FILTRO_IMAGEM[active_tab]
        campo_cemercante = campos_filtro.get('campo_cemercante')
        campo_container = campos_filtro.get('campo_container')
        campo_data = campos_filtro.get('campo_data')
        logger.info('Filtros: %s ' % campos_filtro)
        for linha in lista_risco:
            _id = ''
            conteiner = linha.get(campo_container)
            if conteiner:
                if campo_cemercante:
                    ce = linha.get(campo_cemercante)
                    params = {'query':
                                  {'metadata.carga.conhecimento.conhecimento': str(ce),
                                   'metadata.numeroinformado': conteiner},
                              'projection': {'_id': 1}
                              }
                elif campo_data:
                    # TODO: Em caso de não haver CE, recuperar imagem com data + próxima
                    data = linha.get(campo_data)
                    # logger.info('Entrou no campo data... %s ' % data)
                    # logger.info('Tipo do campo data... %s ' % type(data))
                    if isinstance(data, str):
                        data = parser.parse(linha.get(campo_data))
                    inicio = data - timedelta(days=2)
                    fim = data + timedelta(days=2)
                    params = {'query':
                                  {'metadata.numeroinformado': conteiner,
                                   'metadata.dataescaneamento': {'$gte': inicio,
                                                                 '$lte': fim}},
                              'projection': {'_id': 1}
                              }
                else:
                    raise NotImplementedError('Não foram definidos campos mínimos.'
                                              'append_images active_tab %s ' % active_tab
                                              )
                # print(params)
                # logger.info(params)
                # r = requests.post('https://ajna.labin.rf08.srf/virasana/grid_data',
                #                  json=params, verify=False)
                # print(r.text)
                # lista = r.json()
                cursor = mongodb['fs.files'].find(params['query'], params['projection'])
                lista = list(cursor)
                # print(lista)
                if lista and len(lista) > 0:
                    _id = lista[0]['_id']
            linha['Imagem'] = _id
            lista_risco_nova.append(linha)
        return lista_risco_nova

    @app.route('/aplica_risco', methods=['POST', 'GET'])
    def aplica_risco():
        """Função para escolher parâmetros de risco e visualizar resultados."""
        dbsession = app.config.get('dbsession')
        user_name = current_user.name
        active_tab = request.values.get('active_tab', 'carga')
        forms = {'carga': RiscosAtivosForm,
                 'recintos': RecintoRiscosAtivosForm}
        dict_risco_function = {'carga': mercanterisco,
                               'recintos': recintosrisco}
        FormClass = forms[active_tab]
        risco_function = dict_risco_function[active_tab]
        planilha_atual = ''
        if request.method == 'POST':
            try:
                riscos_ativos_form = FormClass(request.form)
                riscos_ativos_form.planilha_atual = ''
                riscos_ativos = riscosativos(dbsession, user_name)
                filtros = {}
                filtros['datainicio'] = riscos_ativos_form.datainicio.data
                filtros['datafim'] = riscos_ativos_form.datafim.data
                for fieldname, value in riscos_ativos_form.data.items():
                    if value is True:
                        if fieldname in riscos_ativos_form.campos_ativadores: # Filtros booleanos simples
                            filtros[fieldname] = True
                        else:  # Filtros ativodos, carregar valor específico
                            riscos_ativos_campo = [risco.valor for risco in riscos_ativos
                                                   if risco.campo == fieldname]
                            filtros[fieldname] = riscos_ativos_campo
                lista_risco, str_filtros = risco_function(
                    dbsession, filtros, operador_ou=riscos_ativos_form.operadorOU.data)
                # print('***********', lista_risco)
                if not lista_risco or len(lista_risco) == 0:
                    raise ValueError('Não foram encontrados resultados para o filtro!!')
                planilha_atual = save_planilharisco(lista_risco, get_user_save_path(),
                                                    str_filtros)
                return redirect(url_for('risco',
                                        planilha_atual=planilha_atual,
                                        active_tab=active_tab))
            except Exception as err:
                logger.error(err, exc_info=True)
                flash('Erro ao aplicar risco! '
                      'Detalhes no log da aplicação.')
                flash(str(type(err)))
                flash(str(err))
        # Em caso de exceção ou em um get aqui...
        riscos_ativos_form = FormClass(
            datainicio=date.today() - timedelta(days=5),
            datafim=date.today())
        return render_template('aplica_risco.html',
                               oform=riscos_ativos_form,
                               lista_risco=[],
                               total_linhas=0,
                               csv_salvo='',
                               lista_csv=[],
                               planilha_atual=planilha_atual,
                               active_tab=active_tab)

    @app.route('/risco', methods=['POST', 'GET'])
    @login_required
    def risco():
        """Função para escolher parâmetros de risco e visualizar resultados."""
        mongodb = app.config['mongodb']
        lista_risco = []
        total_linhas = 0
        csv_salvo = None
        planilha_atual = request.args.get('planilha_atual', '')
        active_tab = request.values.get('active_tab', 'carga')
        forms = {'carga': RiscosAtivosForm,
                 'recintos': RecintoRiscosAtivosForm}
        FormClass = forms[active_tab]
        riscos_ativos_form = FormClass()
        title_page = 'Risco'
        if request.method == 'GET':
            riscos_ativos_form = FormClass(request.values,
                                           datainicio=date.today() - timedelta(days=5),
                                           datafim=date.today()
                                           )
        lista_csv = get_lista_csv(get_user_save_path())
        if planilha_atual:
            csv_salvo = planilha_atual
            lista_risco, riscos_ativos = le_csv(os.path.join(get_user_save_path(), csv_salvo))
            riscos_ativos_form = FormClass(MultiDict(riscos_ativos))
            # print(lista_risco)
            total_linhas = len(lista_risco)
            # Limita resultados em 100 linhas na tela e adiciona imagens
            lista_risco = append_images(mongodb, lista_risco[:100], active_tab)
        return render_template('aplica_risco.html',
                               oform=riscos_ativos_form,
                               lista_risco=lista_risco,
                               total_linhas=total_linhas,
                               csv_salvo=csv_salvo,
                               lista_csv=lista_csv,
                               planilha_atual=planilha_atual,
                               active_tab=active_tab,
                               title_page=title_page)

    @app.route('/edita_risco', methods=['POST', 'GET'])
    @login_required
    def edita_risco():
        session = app.config.get('dbsession')
        active_tab = request.args.get('active_tab', 'carga')
        user_name = current_user.name
        riscos_ativos = riscosativos(session, user_name)
        edita_risco_form = get_edita_risco_form(active_tab)
        title_page = 'Edita Risco'
        return render_template('edita_risco.html',
                               riscos_ativos=riscos_ativos,
                               oform=edita_risco_form,
                               active_tab=active_tab,
                               title_page=title_page)

    @app.route('/inclui_risco', methods=['POST'])
    @login_required
    def inclui_risco():
        session = app.config.get('dbsession')
        user_name = current_user.name
        campoid = request.form.get('campo')
        active_tab = request.form.get('active_tab', 'carga')
        if campoid == '0':
            flash('Selecionar campo')
            return redirect(url_for('edita_risco'))
        campo = dict(CAMPOS_RISCO[active_tab])[campoid]
        valor = request.form.get('valor')
        motivo = request.form.get('motivo')
        # print(user_name, campo, valor, motivo)
        try:
            insererisco(session,
                        user_name=user_name,
                        campo=campo,
                        valor=valor,
                        motivo=motivo)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro ao incluir risco! '
                  'Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))

        return redirect(url_for('edita_risco', active_tab=active_tab))

    @app.route('/exclui_risco/<id>/<active_tab>', methods=['GET'])
    @login_required
    def excluir_risco(id, active_tab):
        session = app.config.get('dbsession')
        try:
            exclui_risco(session, id)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro ao excluir risco! '
                  'Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('edita_risco', active_tab=active_tab))

    @app.route('/limpa_riscos', methods=['POST'])
    @login_required
    def excluir_riscos():
        session = app.config.get('dbsession')
        active_tab = request.form.get('active_tab')
        try:
            exclui_riscos(session)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro ao excluir risco! '
                  'Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('edita_risco', active_tab=active_tab))

    @app.route('/exporta_csv', methods=['POST', 'GET'])
    @login_required
    def exporta_csv():
        """Grava em arquivo parâmetros ativos.

        """
        session = app.config.get('dbsession')
        try:
            riscos_out_filename = 'riscos_ativos' + \
                                  datetime.strftime(datetime.now(), '%Y-%m%dT%H%M%S') + \
                                  '.csv'
            riscos_ativos = riscosativos(session, current_user.name)
            with open(os.path.join(get_user_save_path(),
                                   riscos_out_filename), 'w', newline='') as riscos_out:
                for risco in riscos_ativos:
                    linha_out = ';'.join((risco.campo, risco.valor, risco.motivo))
                    riscos_out.write(linha_out + '\n')
            return redirect('static/%s/%s' % (current_user.name, riscos_out_filename))
        except Exception as err:
            logger.warning(err, exc_info=True)
            flash(str(err))
        return redirect(url_for('edita_risco'))

    @app.route('/importacsv', methods=['POST', 'GET'])
    @login_required
    def importacsv():
        """Importar arquivo com parâmetros ativos.
        """
        session = app.config.get('dbsession')
        if request.method == 'POST':
            try:
                csvf = get_planilha_valida(request, 'csv', ['csv'])
                if csvf:
                    filename = secure_filename(csvf.filename)
                    save_name = os.path.join(tmpdir, filename)
                    csvf.save(save_name)
                    logger.info('CSV RECEBIDO: %s' % save_name)
                    with open(save_name, errors='replace') as in_csv:
                        lines = in_csv.readlines()
                    user_name = current_user.name
                    for line in lines:
                        try:
                            linha = line.split(';')
                            if len(linha) < 2:  # Pula linhas vazias
                                continue
                            if len(linha) == 2:
                                campo, valor = linha
                                motivo = ''
                            else:
                                campo, valor, motivo = linha
                        except Exception as err:
                            logger.error(err, exc_info=True)
                            continue
                        insererisco(session,
                                    user_name=user_name,
                                    campo=campo,
                                    valor=valor,
                                    motivo=motivo)
            except Exception as err:
                logger.error(err, exc_info=True)
                flash(str(err))
        return redirect(url_for('edita_risco'))

    @app.route('/importa_planilha_recinto', methods=['POST', 'GET'])
    @login_required
    def importa_planilha_recinto():
        """Importar arquivo de eventos de recintos.
        """
        title_page = 'Importa Planilha Recinto'
        if request.method == 'POST':
            planilha = get_planilha_valida(request, 'planilha')
            if planilha:
                filename = secure_filename(planilha.filename)
                save_name = os.path.join(tmpdir, filename)
                planilha.save(save_name)
                logger.info('Planilha recebida: %s' % save_name)
                sucesso, msg = processa_planilha(save_name)
                if sucesso:
                    flash('Planilha recebida com %s linhas. Processando...' % msg)
                else:
                    flash('Erro: %s' % msg)
        return render_template('importa_planilha_recinto.html',
                               title_page=title_page)
