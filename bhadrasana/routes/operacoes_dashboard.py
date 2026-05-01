from decimal import Decimal

from flask import render_template, request
from flask_caching import Cache

from bhadrasana.models.operacoes_dashboard import listar_operacoes, monta_dashboard_operacao, monta_resumo_operacoes


# bp = Blueprint('ovr_dashboard', __name__, url_prefix='/ovr')


def dashboard_app(app):
    cache = Cache(config={
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 60,
        'CACHE_THRESHOLD': 500
    })
    cache.init_app(app)

    @app.template_filter('br_currency')
    def br_currency(value):
        if value is None:
            value = Decimal('0.00')
        return f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    @cache.memoize(timeout=60)
    @app.route('/operacoes_dashboard')
    def dashboard_operacoes():
        session = app.config.get('dbsession')
        flag_id = request.args.get('flag_id', type=int)

        operacoes = listar_operacoes(session)
        dados = None
        operacao_atual = None
        resumo_operacoes = None

        if flag_id:
            operacao_atual = next((f for f in operacoes if f.id == flag_id), None)
            if operacao_atual:
                dados = monta_dashboard_operacao(session, flag_id)
        else:
            resumo_operacoes = monta_resumo_operacoes(session)

        return render_template(
            'operacoes_dashboard.html',
            operacoes=operacoes,
            operacao_atual=operacao_atual,
            dados=dados,
            resumo_operacoes=resumo_operacoes
        )
