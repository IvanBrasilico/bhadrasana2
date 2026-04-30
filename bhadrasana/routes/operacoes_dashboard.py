from decimal import Decimal

from flask import Blueprint, render_template, request

from bhadrasana.models.operacoes_dashboard import listar_operacoes, monta_dashboard_operacao

#bp = Blueprint('ovr_dashboard', __name__, url_prefix='/ovr')


#@bp.app_template_filter('br_currency')
#def br_currency(value):
#    if value is None:
#        value = Decimal('0.00')
#    return f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def dashboard_app(app):
    @app.route('/operacoes/dashboard')
    def dashboard_operacoes():
        session = app.config.get('dbsession')
        flag_id = request.args.get('flag_id', type=int)

        operacoes = listar_operacoes(session)
        dados = None
        operacao_atual = None

        if flag_id:
            operacao_atual = next((f for f in operacoes if f.id == flag_id), None)
            if operacao_atual:
                dados = monta_dashboard_operacao(session, flag_id)

        return render_template(
            'operacoes_dashboard.html',
            operacoes=operacoes,
            operacao_atual=operacao_atual,
            dados=dados
        )
