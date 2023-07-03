"""
Módulo para facilitar a auditoria da API Recintos

Permite registrar rapidamente Auditorias de API Recintos, montar termos de constatação, etc.

"""
import os
from datetime import datetime

from ajna_commons.flask.log import logger
from flask import render_template, flash, url_for, request
from flask_login import login_required, current_user
from werkzeug.utils import redirect

from bhadrasana.docx.docx_functions import gera_relatorio_apirecintos
from bhadrasana.forms.assistente_checkapi import CheckApiForm
from bhadrasana.models import get_usuario, Usuario
from bhadrasana.models.assistente_checkapi import processa_auditoria
from bhadrasana.models.ovrmanager import cadastra_ovr, atribui_responsavel_ovr, get_recintos_unidade
from bhadrasana.views import get_user_save_path


def gerar_relatorio_docx(eventos_fisico,
                         mensagens: list,
                         linhas_divergentes: list,
                         recinto: str,
                         evento: str,
                         usuario: Usuario):
    dados = {'eventos_fisico': eventos_fisico,
             'mensagens': ' '.join(mensagens),
             'linhas_divergentes': linhas_divergentes,
             'nome_fiscalizado': recinto,
             'setor': usuario.setor.nome
             }
    out_filename = 'apirecintos_{}_{}_{}.docx'.format(
        recinto,
        evento,
        datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
    )
    document = gera_relatorio_apirecintos(dados, usuario.cpf)
    document.save(os.path.join(get_user_save_path(), out_filename))
    return [out_filename]


def assistentecheckapi_app(app):
    @app.route('/assistente_checkapi', methods=['GET', 'POST'])
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
                stream_planilha = request.files.get('planilha')
                stream_json = request.files.get('eventos_json')
                eventos_fisico, mensagens, linhas_divergentes = \
                    processa_auditoria(stream_planilha, stream_json, 'MARIMEX', 'GATE')
                arquivos = gerar_relatorio_docx(eventos_fisico, mensagens,
                                                linhas_divergentes,
                                                checkapiform.recinto_id.data,
                                                checkapiform.tipoevento_id.data,
                                                usuario)
                return render_template('assistente_checkapi.html',
                                       eventos_fisico=eventos_fisico,
                                       mensagens=mensagens,
                                       linhas_divergentes=linhas_divergentes,
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
                               arquivos=arquivos,
                               linhas_diferentes=[],
                               eventos_fisico=None)

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
