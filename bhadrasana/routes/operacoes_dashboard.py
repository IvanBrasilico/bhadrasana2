from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from flask import render_template, request
from flask_caching import Cache

from bhadrasana.models.operacoes_dashboard import listar_operacoes, monta_dashboard_operacao, monta_resumo_operacoes

# bp = Blueprint('ovr_dashboard', __name__, url_prefix='/ovr')

# O período de abertura da Ficha (OVR.datahora), na query string: as datas do
# <input type="date"> (AAAA-MM-DD)
PARAMETROS_PERIODO = ('abertura_inicio', 'abertura_fim')


def data_do_parametro(nome: str) -> Optional[date]:
    """A data AAAA-MM-DD do parâmetro; vazio ou inválido = sem esse lado do período."""
    valor = (request.args.get(nome) or '').strip()
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date() if valor else None
    except ValueError:
        return None


def periodo_de_abertura():
    """(início, fim) da abertura da Ficha pedidos na tela; trocados se vierem invertidos.

    (None, None) = sem filtro, o padrão."""
    inicio, fim = (data_do_parametro(nome) for nome in PARAMETROS_PERIODO)
    if inicio and fim and inicio > fim:
        inicio, fim = fim, inicio
    return inicio, fim


def descreve_periodo(inicio: Optional[date], fim: Optional[date]) -> str:
    if inicio and fim:
        return f'de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}'
    if inicio:
        return f'a partir de {inicio:%d/%m/%Y}'
    if fim:
        return f'até {fim:%d/%m/%Y}'
    return 'Sem filtro'


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
        inicio, fim = periodo_de_abertura()

        operacoes = listar_operacoes(session)
        dados = None
        operacao_atual = None
        resumo_operacoes = None

        if flag_id:
            operacao_atual = next((f for f in operacoes if f.id == flag_id), None)
            if operacao_atual:
                dados = monta_dashboard_operacao(session, flag_id, inicio, fim)
        else:
            resumo_operacoes = monta_resumo_operacoes(session, inicio, fim)

        # o período vai junto nos links das operações (só os lados preenchidos)
        periodo = {nome: valor.isoformat()
                   for nome, valor in zip(PARAMETROS_PERIODO, (inicio, fim)) if valor}
        return render_template(
            'operacoes_dashboard.html',
            operacoes=operacoes,
            operacao_atual=operacao_atual,
            dados=dados,
            resumo_operacoes=resumo_operacoes,
            periodo=periodo,
            descricao_periodo=descreve_periodo(inicio, fim),
        )
