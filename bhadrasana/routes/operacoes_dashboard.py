from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from flask import render_template, request
from flask_caching import Cache

from bhadrasana.models.operacoes_dashboard import ID_SEM_OPERACAO, listar_operacoes, \
    monta_detalhe_operacao, monta_resumo_operacoes

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


def anos_do_atalho(hoje: Optional[date] = None) -> list:
    """O atalho de ano do período: o ano atual e os cinco anteriores, como (ano, rótulo)."""
    ano_atual = (hoje or date.today()).year
    return [(ano_atual, f'Ano atual ({ano_atual})')] + \
        [(ano, str(ano)) for ano in range(ano_atual - 1, ano_atual - 6, -1)]


def ano_inteiro(inicio: Optional[date], fim: Optional[date]) -> Optional[int]:
    """O ano, quando o período é de 01/01 a 31/12 dele (para marcar o atalho na tela)."""
    if inicio and fim and inicio.year == fim.year and \
            (inicio.month, inicio.day, fim.month, fim.day) == (1, 1, 12, 31):
        return inicio.year
    return None


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

        # "Fichas sem operação informada" só existe com o período preenchido
        operacoes = listar_operacoes(session, com_sem_operacao=bool(inicio or fim))
        dados = None
        resumo = None

        # flag_id desconhecido (ou a categoria sem operação sem período): mostra o resumo
        operacao_atual = next((f for f in operacoes if f.id == flag_id), None) if flag_id else None
        if operacao_atual:
            dados = monta_detalhe_operacao(session, flag_id, inicio, fim)
        else:
            resumo = monta_resumo_operacoes(session, inicio, fim)

        # o período vai junto nos links das operações (só os lados preenchidos)
        periodo = {nome: valor.isoformat()
                   for nome, valor in zip(PARAMETROS_PERIODO, (inicio, fim)) if valor}
        # o "Sem filtro" fica na Operação, menos na categoria que só existe com período
        flag_sem_filtro = None
        if operacao_atual and operacao_atual.id != ID_SEM_OPERACAO:
            flag_sem_filtro = operacao_atual.id
        return render_template(
            'operacoes_dashboard.html',
            operacoes=operacoes,
            operacao_atual=operacao_atual,
            dados=dados,
            resumo=resumo,
            periodo=periodo,
            descricao_periodo=descreve_periodo(inicio, fim),
            anos=anos_do_atalho(),
            ano_selecionado=ano_inteiro(inicio, fim),
            flag_sem_filtro=flag_sem_filtro,
        )
