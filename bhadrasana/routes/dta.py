from ajna_commons.flask.log import logger
from bhadrasana.forms.dta import AnexoForm
from bhadrasana.models.dtamanager import lista_anexos, get_anexo, edita_anexo
from flask import request, render_template, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import redirect


def dta_app(app):
    @app.route('/transito', methods=['GET', 'POST'])
    def transito():
        user_name = current_user.name
        session = app.config.get('dbsession')
        dta_id = request.args.get('dta_id', 1)
        anexo_id = request.args.get('item_id')
        oform = AnexoForm()
        try:
            listaanexos = lista_anexos(session, dta_id)
            if anexo_id and anexo_id is not None:
                anexo = get_anexo(session, anexo_id)
                oform = AnexoForm(**anexo.__dict__)
        except Exception as err:
            flash(err)
            logger.error(err, exc_info=True)
        return render_template('dta_anexos.html',
                               listaanexos=listaanexos,
                               oform=oform)

    @app.route('/anexo', methods=['POST'])
    @login_required
    def anexo():
        session = app.config.get('dbsession')
        anexo_form = AnexoForm(request.form)
        anexo_form.validate()
        anexo = edita_anexo(session, dict(anexo_form.data.items()))
        return redirect(url_for('transito', dta_id=anexo.dta_id))
