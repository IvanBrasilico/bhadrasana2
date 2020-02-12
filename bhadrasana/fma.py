import datetime

from ajna_commons.flask.log import logger
from bhadrasana.forms.fma import FMAForm, FiltroFMAForm, HistoricoFMAForm
from bhadrasana.models.fmamanager import Enumerado, cadastra_fma, get_fma, \
    get_fma_filtro, movimenta_fma
from flask import request, flash, render_template, url_for
from flask_login import login_required, current_user
from werkzeug.utils import redirect


def fma_app(app):
    @app.route('/fma', methods=['POST', 'GET'])
    @login_required
    def fma():
        session = app.config.get('dbsession')
        listahistorico = []
        fma = None
        fma_form = FMAForm()
        historico_form = HistoricoFMAForm()
        historico_form.status.choices = Enumerado.tipoStatusFMA()
        try:
            if request.method == 'POST':
                fma_form = FMAForm(request.form)
                fma_form.adata.data = request.form.get('adata')
                fma_form.ahora.data = request.form.get('ahora')
                fma_form.validate()
                fma = cadastra_fma(session,
                                   dict(fma_form.data.items()))
            else:
                fma_id = request.args.get('id')
                if fma_id is not None:
                    fma = get_fma(session, fma_id)
                    if fma is not None:
                        fma_form = FMAForm(**fma.__dict__)
                        if fma.datahora:
                            fma_form.adata.data = fma.datahora.date()
                            fma_form.ahora.data = fma.datahora.time()
            if fma:
                fma_form.id.data = fma.id
                historico_form.fma_id.data = fma_id
                listahistorico = fma.historico
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('fma.html',
                               oform=fma_form,
                               historico_form=historico_form,
                               listahistorico=listahistorico)

    @app.route('/pesquisa_fma', methods=['POST', 'GET'])
    @login_required
    def pesquisa_fma():
        session = app.config.get('dbsession')
        user_name = current_user.name
        fmas = []
        filtro_form = FiltroFMAForm(
            datainicio=datetime.date.today() - datetime.timedelta(days=10),
            datafim=datetime.date.today()
        )
        filtro_form.status.choices = Enumerado.tipoStatusFMA()
        try:
            if request.method == 'POST':
                filtro_form = FiltroFMAForm(request.form)
                filtro_form.status.choices = Enumerado.tipoStatusFMA()
                filtro_form.validate()
                fmas = get_fma_filtro(session, dict(filtro_form.data.items()))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(type(err))
            flash(err)
        return render_template('pesquisa_fma.html',
                               oform=filtro_form,
                               fmas=fmas)

    @app.route('/movimentafma', methods=['POST'])
    @login_required
    def movimentafma():
        session = app.config.get('dbsession')
        fma_id = request.form['fma_id']
        historico_fma_form = HistoricoFMAForm(request.form)
        movimenta_fma(session, dict(historico_fma_form.data.items()))
        return redirect(url_for('fma', id=fma_id))
