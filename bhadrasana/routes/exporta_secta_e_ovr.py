"""
Módulo para facilitar o agrupamento e exportação das OVRs mensais :-p

Permite visualizar a produção mensal, e traduzir para linguagem/código do Secta e-OVR

"""
from ajna_commons.flask.log import logger
from flask import render_template, flash, request
from flask_login import login_required


def eovr_app(app):
    @app.route('/eovr', methods=['GET'])
    @login_required
    def nova_inspecaonaoinvasiva(_id):
        title_page = 'Assistente de Exportação para OVR'
        session = app.config.get('dbsession')
        ano = request.values.get('ano', 2023)
        mes = request.values.get('mes', 3)
        try:
            return render_template(f'eovr.html?ano={ano}&mes={mes}',
                                   title_page=title_page)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('eovr.html',
                               title_page=title_page)
