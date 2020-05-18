import os
from datetime import date, timedelta
from datetime import datetime

import pandas as pd
import requests
from flask import (flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ajna_commons.flask.log import logger
from bhadrasana.forms.editarisco import get_edita_risco_form
from bhadrasana.forms.riscosativos import RiscosAtivosForm, RecintoRiscosAtivosForm
from bhadrasana.models.riscomanager import mercanterisco, riscosativos, \
    insererisco, exclui_risco, CAMPOS_RISCO, get_lista_csv, save_planilharisco, \
    recintosrisco
from bhadrasana.views import get_user_save_path, tmpdir


def risco_app(app):
    def append_images(lista_risco):
        lista_risco_nova = []
        for linha in lista_risco:
            ce = linha.get('numeroCEmercante')
            conteiner = linha.get('codigoConteiner')
            _id = ''
            if conteiner:
                if ce:
                    params = {'query':
                              {'metadata.carga.conhecimento.conhecimento': ce,
                               'metadata.numeroinformado': conteiner},
                          'projection': {'_id': 1}
                          }
                    r = requests.post('https://ajna.labin.rf08.srf/virasana/grid_data',
                                  json=params, verify=False)
                    lista = r.json()
                if conteiner:
                    # TODO: Em caso de não haver CE, recuperar imagem com data mais próxima
                    pass
                if lista and len(lista) > 0:
                    _id = lista[0]['_id']
            linha['_id'] = _id
            lista_risco_nova.append(linha)
        return lista_risco_nova

    def le_csv(filename):
        df = pd.read_csv(filename, sep=';',
                         header=5)
        return [row[1].to_dict() for row in df.iterrows()]

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
                        riscos_ativos_campo = [risco.valor for risco in riscos_ativos
                                               if risco.campo == fieldname]
                        filtros[fieldname] = riscos_ativos_campo
                lista_risco, str_filtros = risco_function(dbsession, filtros)
                # print('***********', lista_risco)
                destino = save_planilharisco(lista_risco, get_user_save_path(), str_filtros)
                return redirect(url_for('risco', planilha_atual=destino), code=307)
                # active_tab=active_tab))000
            except Exception as err:
                logger.error(err, exc_info=True)
                flash('Erro ao aplicar risco! '
                      'Detalhes no log da aplicação.')
                flash(str(type(err)))
                flash(str(err))
        # Em caso de exceção ou em um get aqui...
        riscos_ativos_form = FormClass(
            datainicio=date.today() - timedelta(days=5),
            datafim=date.today()
        )
        return render_template('aplica_risco.html',
                               oform=riscos_ativos_form,
                               lista_risco=[],
                               total_linhas=0,
                               csv_salvo='',
                               lista_csv=[],
                               planilha_atual='',
                               active_tab=active_tab)

    @app.route('/risco', methods=['POST', 'GET'])
    @login_required
    def risco():
        """Função para escolher parâmetros de risco e visualizar resultados."""
        dbsession = app.config.get('dbsession')
        user_name = current_user.name
        lista_risco = []
        total_linhas = 0
        csv_salvo = None
        planilha_atual = request.args.get('planilha_atual', '')
        active_tab = request.values.get('active_tab', 'carga')
        forms = {'carga': RiscosAtivosForm,
                 'recintos': RecintoRiscosAtivosForm}
        FormClass = forms[active_tab]
        if request.method == 'POST':
            riscos_ativos_form = FormClass(request.form)
        else:
            riscos_ativos_form = FormClass(request.values,
                                           datainicio=date.today() - timedelta(days=5),
                                           datafim=date.today()
                                           )
        lista_csv = get_lista_csv(get_user_save_path())
        if planilha_atual:
            csv_salvo = planilha_atual
            lista_risco = le_csv(os.path.join(get_user_save_path(), csv_salvo))
            print(lista_risco)
            total_linhas = len(lista_risco)
            # Limita resultados em 100 linhas na tela e adiciona imagens
            lista_risco = append_images(lista_risco[:100])
        return render_template('aplica_risco.html',
                               oform=riscos_ativos_form,
                               lista_risco=lista_risco,
                               total_linhas=total_linhas,
                               csv_salvo=csv_salvo,
                               lista_csv=lista_csv,
                               planilha_atual=planilha_atual,
                               active_tab=active_tab)

    @app.route('/edita_risco', methods=['POST', 'GET'])
    @login_required
    def edita_risco():
        session = app.config.get('dbsession')
        active_tab = request.args.get('active_tab', 'carga')
        user_name = current_user.name
        riscos_ativos = riscosativos(session, user_name)
        edita_risco_form = get_edita_risco_form(active_tab)
        return render_template('edita_risco.html',
                               riscos_ativos=riscos_ativos,
                               oform=edita_risco_form,
                               active_tab=active_tab)

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

    @app.route('/exclui_risco/<id>', methods=['GET'])
    @login_required
    def excluir_risco(id):
        session = app.config.get('dbsession')
        try:
            exclui_risco(session, id)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro ao incluir risco! '
                  'Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return redirect(url_for('edita_risco'))

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
                                   riscos_out_filename), 'w') as riscos_out:
                for risco in riscos_ativos:
                    linha_out = ';'.join((risco.campo, risco.valor, risco.motivo))
                    riscos_out.write(linha_out + '\n')
            return redirect('static/%s/%s' % (current_user.name, riscos_out_filename))
        except Exception as err:
            logger.warning(err, exc_info=True)
            flash(str(err))
        return redirect(url_for('edita_risco'))

    def get_csv_valido(request):
        if 'csv' not in request.files:
            flash('Arquivo não repassado')
            return False
        csvf = request.files['csv']
        if csvf.filename == '':
            flash('Nome de arquivo vazio')
            return False
        logger.info('FILE***' + csvf.filename)
        if '.' in csvf.filename and csvf.filename.rsplit('.', 1)[1].lower() == 'csv':
            return csvf
        return False

    @app.route('/importacsv', methods=['POST', 'GET'])
    @login_required
    def importacsv():
        """Importar arquivo.

        """
        print('IMPORTA CSV')
        session = app.config.get('dbsession')
        print(request.files)
        print(request.method)
        if request.method == 'POST':
            csvf = get_csv_valido(request)
            if csvf:
                filename = secure_filename(csvf.filename)
                save_name = os.path.join(tmpdir, filename)
                csvf.save(save_name)
                logger.info('CSV RECEBIDO: %s' % save_name)
                with open(save_name) as in_csv:
                    lines = in_csv.readlines()
                user_name = current_user.name
                for line in lines:
                    campo, valor, motivo = line.split(';')
                    insererisco(session,
                                user_name=user_name,
                                campo=campo,
                                valor=valor,
                                motivo=motivo)
        return redirect(url_for('edita_risco'))

    @app.route('/importa_planilha_recinto', methods=['POST', 'GET'])
    @login_required
    def importa_planilha_recinto():
        """Importar arquivo.

        """
        session = app.config.get('dbsession')
        if request.method == 'POST':
            csvf = get_csv_valido(request)
            if csvf:
                filename = secure_filename(csvf.filename)
                save_name = os.path.join(tmpdir, filename)
                csvf.save(save_name)
                logger.info('CSV RECEBIDO: %s' % save_name)
                with open(save_name) as in_csv:
                    lines = in_csv.readlines()
                user_name = current_user.name
                for line in lines:
                    campo, valor, motivo = line.split(';')
                    insererisco(session,
                                user_name=user_name,
                                campo=campo,
                                valor=valor,
                                motivo=motivo)
        return redirect(url_for('importa_planilha_recinto'))
