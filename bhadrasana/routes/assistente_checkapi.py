"""
Módulo para facilitar a auditoria da API Recintos

Permite registrar rapidamente Auditorias de API Recintos, montar termos de constatação, etc.

"""
import os
from datetime import datetime

from ajna_commons.flask.log import logger
from flask import render_template, flash, request, url_for
from flask_login import login_required, current_user
from gridfs import GridFS
from werkzeug.utils import redirect

from bhadrasana.docx.docx_functions import gera_relatorio_apirecintos
from bhadrasana.forms.assistente_checkapi import CheckApiForm
from bhadrasana.models import get_usuario, Usuario
from bhadrasana.models.assistente_checkapi import processa_auditoria
from bhadrasana.models.ovr import Recinto, EventoOVR, TipoEventoOVR
from bhadrasana.models.ovrmanager import cadastra_ovr, atribui_responsavel_ovr, get_recintos_unidade, inclui_flag_ovr
from bhadrasana.models.rvf import RVF
from bhadrasana.views import get_user_save_path


def registra_ovr(session, recinto, evento_nome, texto_rvf=None):
    ovr_data = {
        'tipooperacao': 7,  # Vigilância
        'observacoes': f'Auditoria API Recintos {recinto.nome} automaticamente registrada.' + \
                       f'Análise do evento {evento_nome}.',
        'cnpj_fiscalizado': recinto.cnpj,
        'recinto_id': recinto.id
    }
    ovr = cadastra_ovr(session,
                       params=ovr_data,
                       user_name=current_user.name)
    atribui_responsavel_ovr(session, ovr.id, current_user.name, current_user.name)
    inclui_flag_ovr(session, ovr.id, 'API Recintos - checagem', current_user.name)
    inclui_flag_ovr(session, ovr.id, 'Conformidade', current_user.name)
    if texto_rvf:
        rvf = RVF()
        rvf.ovr_id = ovr.id
        rvf.descricao = texto_rvf
        session.add(rvf)
        try:
            session.commit()
        except:
            session.rollback()
    return ovr


def inclui_evento_ovr(db, session, ovr, motivo: str, file=None, filename=None):
    if file is None and filename is None:
        raise Exception('inclui_evento_ovr precisa de ao menos um parâmetro file ou filename')
    if file:
        filename = file.filename
        content = file.read()
        mimetype = file.mimetype
    else:
        with open(os.path.join(get_user_save_path(), filename), 'rb') as file_in:
            content = file_in.read()
            if 'docx' in filename:
                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                mimetype = 'text/xml'
    evento = EventoOVR()
    evento.ovr_id = ovr.id
    evento.user_name = current_user.name
    evento.motivo = motivo
    tipoevento = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.id == 20
    ).one()
    evento.tipoevento = tipoevento
    evento.fase = tipoevento.fase
    evento.anexo_filename = filename
    session.add(evento)
    try:
        session.commit()
        session.refresh(evento)
        fs = GridFS(db)
        fs.put(content, filename=filename,
               metadata={'ovr': str(ovr.id),
                         'evento': str(evento.id),
                         'contentType': mimetype})
    except Exception as err:
        session.rollback()
        raise err


def gerar_relatorio_docx(eventos_fisico,
                         mensagens: list,
                         linhas_divergentes: list,
                         recinto: Recinto,
                         evento_nome: str,
                         usuario: Usuario,
                         ovr=None):
    dados = {'eventos_fisico': eventos_fisico,
             'mensagens': ' '.join(mensagens),
             'linhas_divergentes': linhas_divergentes,
             'cnpj_fiscalizado': recinto.cnpj,
             'nome_fiscalizado': recinto.nome,
             'setor': usuario.setor.nome,
             'evento_nome': evento_nome
             }
    if ovr:
        dados['ovr_id'] = ovr.id
        dados['datahora'] = ovr.datahora
    out_filename = 'apirecintos_{}_{}_{}.docx'.format(
        recinto.nome,
        evento_nome,
        datetime.strftime(datetime.now(), '%Y-%m-%dT%H-%M-%S')
    )
    document = gera_relatorio_apirecintos(dados, usuario.cpf)
    document.save(os.path.join(get_user_save_path(), out_filename))
    return out_filename


def assistentecheckapi_app(app):
    @app.route('/assistente_checkapi', methods=['GET', 'POST'])
    @login_required
    def assistente_checkapi():
        title_page = 'Assistente de Auditoria API Recintos'
        session = app.config.get('dbsession')
        mongo_risco = app.config['mongo_risco']
        checkapiform = CheckApiForm()
        lista_planilhas = os.listdir('bhadrasana/static/check_api')
        print(lista_planilhas)
        try:
            usuario = get_usuario(session, current_user.name)
            recintos = get_recintos_unidade(session, usuario.setor.cod_unidade)
            tiposevento = [['1', 'AgendamentoAcessoVeiculo'], ['2', 'PesagemVeiculo']]
            checkapiform = CheckApiForm(recintos=recintos, tiposevento=tiposevento)
            if request.method == 'POST':
                checkapiform = CheckApiForm(request.form, recintos=recintos, tiposevento=tiposevento)
                checkapiform.validate()
                stream_planilha = request.files[checkapiform.planilha.name]
                # request.files.get('planilha')
                stream_json = request.files[checkapiform.eventos_json.name]
                recinto = session.query(Recinto).filter(Recinto.id == checkapiform.recinto_id.data).one()
                evento_nome = dict(checkapiform.tipoevento_id.choices).get(checkapiform.tipoevento_id.data)
                eventos_fisico, mensagens, linhas_divergentes = \
                    processa_auditoria(stream_planilha, stream_json, evento_nome)
                ovr = None
                if request.values.get('finalizar'):
                    texto_rvf = '\n'.join([*mensagens, 'Divergências:', *linhas_divergentes])
                    ovr = registra_ovr(session, recinto, evento_nome, texto_rvf)
                    inclui_evento_ovr(mongo_risco, session, ovr,
                                      motivo='Assistente API Recintos - planilha checagem',
                                      file=stream_planilha)
                arquivo = gerar_relatorio_docx(eventos_fisico, mensagens,
                                               linhas_divergentes,
                                               recinto,
                                               evento_nome,
                                               usuario, ovr)
                if request.values.get('finalizar'):
                    inclui_evento_ovr(mongo_risco, session, ovr,
                                      motivo='Assistente API Recintos - Termo de constatações',
                                      filename=arquivo)
                    return redirect(url_for('ovr', id=ovr.id))
                return render_template('assistente_checkapi.html',
                                       eventos_fisico=eventos_fisico,
                                       mensagens=mensagens,
                                       linhas_divergentes=linhas_divergentes,
                                       checkapiform=checkapiform,
                                       title_page=title_page,
                                       arquivos=[arquivo],
                                       lista_planilhas=lista_planilhas)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('assistente_checkapi.html',
                               checkapiform=checkapiform,
                               title_page=title_page,
                               arquivos=[],
                               linhas_diferentes=[],
                               eventos_fisico=None,
                               lista_planilhas=lista_planilhas)
