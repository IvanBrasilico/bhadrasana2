"""
Módulo para facilitar a auditoria da API Recintos

Permite registrar rapidamente Auditorias de API Recintos, montar termos de constatação, etc.

"""
from ajna_commons.flask.log import logger
from flask import render_template, flash, url_for, request
from flask_login import login_required, current_user
from werkzeug.utils import redirect

from bhadrasana.forms.assistente_checkapi import CheckApiForm
from bhadrasana.models import get_usuario
from bhadrasana.models.ovrmanager import cadastra_ovr, atribui_responsavel_ovr, get_recintos_unidade


def assistentecheckapi_app(app):
    @app.route('/assistente_checkapi', methods=['GET'])
    @login_required
    def assistente_checkapi():
        title_page = 'Assistente de Auditoria API Recintos'
        session = app.config.get('dbsession')
        checkapiform = CheckApiForm()
        arquivos = []
        try:
            usuario = get_usuario(session, current_user.name)
            recintos = get_recintos_unidade(session, usuario.setor.cod_unidade)
            tiposevento = [['1', 'AgendamentoAcessoVeiculo']]
            checkapiform = CheckApiForm(recintos=recintos, tiposevento=tiposevento)
            if request.method == 'POST':
                checkapiform = CheckApiForm(request.form, recintos=recintos, tiposevento=tiposevento)
                checkapiform.validate()

                return render_template('assistente_checkapi.html',
                                       checkapiform=checkapiform,
                                       title_page=title_page,
                                       arquivos=arquivos)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('assistente_checkapi.html',
                               checkapiform=checkapiform,
                               title_page=title_page,
                               arquivos=arquivos)

    @app.route('/nova_auditoria', methods=['POST'])
    @login_required
    def nova_auditoria():
        title_page = 'Assistente de Auditoria API Recintos'
        mongodb = app.config['mongodb']
        mongo_risco = app.config['mongo_risco']
        session = app.config.get('dbsession')
        recinto = request.form.get('recinto')
        tipoevento = request.form.get('tipoevento')
        try:
            ovr_data = {
                'tipooperacao': 7,  # Vigilância
                'observacoes': f'Auditoria API Recintos {recinto} automaticamente registrada.' + \
                               f'Análise do evento {tipoevento}'
            }
            ovr = None
            if ovr is None:
                ovr = cadastra_ovr(session,
                                   params=ovr_data,
                                   user_name=current_user.name)
                atribui_responsavel_ovr(session, ovr.id, current_user.name, current_user.name)
            return redirect(url_for('ovr', id=ovr.id))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('index.html',
                               title_page=title_page)
