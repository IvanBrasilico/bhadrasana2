import datetime

from ajna_commons.flask.log import logger
from bhadrasana.forms.ovr import OVRForm, FiltroOVRForm, HistoricoOVRForm, ProcessoOVRForm
from bhadrasana.models.ovrmanager import cadastra_ovr, get_ovr, \
    get_ovr_filtro, gera_eventoovr, get_tipos_evento, delete_objeto, gera_processoovr, get_tipos_processo
from flask import request, flash, render_template, url_for, jsonify
from flask_login import login_required, current_user
from virasana.integracao.mercante.mercantealchemy import Conhecimento
from werkzeug.utils import redirect


def ovr_app(app):
    @app.route('/ovr', methods=['POST', 'GET'])
    @login_required
    def ovr():
        session = app.config.get('dbsession')
        listahistorico = []
        processos = []
        ovr_form = OVRForm()
        tiposeventos = get_tipos_evento(session)
        tiposprocesso = get_tipos_processo(session)
        historico_form = HistoricoOVRForm(tiposeventos=tiposeventos)
        processo_form = ProcessoOVRForm(tiposprocesso=tiposprocesso)
        conhecimento = None
        try:
            if request.method == 'POST':
                ovr_form = OVRForm(request.form)
                ovr_form.adata.data = request.form.get('adata')
                ovr_form.ahora.data = request.form.get('ahora')
                ovr_form.validate()
                ovr = cadastra_ovr(session,
                                   dict(ovr_form.data.items()))
                return redirect(url_for('ovr', id=ovr.id))
            else:
                ovr_id = request.args.get('id')
                if ovr_id is not None:
                    ovr = get_ovr(session, ovr_id)
                    if ovr is not None:
                        ovr_form = OVRForm(**ovr.__dict__)
                        conhecimento = session.query(Conhecimento).filter(
                            Conhecimento.numeroCEmercante == ovr.numeroCEmercante
                        ).one_or_none()
                        ovr_form.id.data = ovr.id
                        listahistorico = ovr.historico
                        processos = ovr.processos
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('ovr.html',
                               oform=ovr_form,
                               conhecimento=conhecimento,
                               historico_form=historico_form,
                               processo_form=processo_form,
                               listahistorico=listahistorico,
                               processos=processos)

    @app.route('/pesquisa_ovr', methods=['POST', 'GET'])
    @login_required
    def pesquisa_ovr():
        session = app.config.get('dbsession')
        user_name = current_user.name
        ovrs = []
        tiposeventos = get_tipos_evento(session)
        filtro_form = FiltroOVRForm(
            datainicio=datetime.date.today() - datetime.timedelta(days=10),
            datafim=datetime.date.today(),
            tiposeventos=tiposeventos
        )
        filtro_form.tipoevento.choices = tiposeventos
        try:
            if request.method == 'POST':
                filtro_form = FiltroOVRForm(request.form, tiposeventos=tiposeventos)
                filtro_form.tipoevento.choices = tiposeventos
                filtro_form.validate()
                ovrs = get_ovr_filtro(session, dict(filtro_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('pesquisa_ovr.html',
                               oform=filtro_form,
                               ovrs=ovrs)

    @app.route('/movimentaovr', methods=['POST'])
    @login_required
    def movimentaovr():
        session = app.config.get('dbsession')
        ovr_id = request.form['ovr_id']
        historico_ovr_form = HistoricoOVRForm(request.form)
        gera_eventoovr(session, dict(historico_ovr_form.data.items()))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/processoovr', methods=['POST'])
    @login_required
    def processoovr():
        session = app.config.get('dbsession')
        ovr_id = request.form['ovr_id']
        processo_ovr_form = ProcessoOVRForm(request.form)
        gera_processoovr(session, dict(processo_ovr_form.data.items()))
        return redirect(url_for('ovr', id=ovr_id))

    @app.route('/excluiobjeto/<classname>/<id>', methods=['POST'])
    @login_required
    def excluiobjeto(classname, id):
        session = app.config.get('dbsession')
        delete_objeto(session, classname, id)
        return jsonify({'msg': 'Excluído'}), 200
