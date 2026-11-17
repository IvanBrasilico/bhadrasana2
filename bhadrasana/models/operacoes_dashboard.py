"""Módulo para permitir visualizar "Operações" de importação pendentes.

"Operações" são grupos de Fichas (Operações no Secta e-OVR*) que se conectam, por exemplo, ao
mesmo grupo econômico ou à mesma pesquisa e seleção.

Note-se que o nome da classe "OVR" na verdade mudou para Ficha, sendo que OVR também é um conjunto de Fichas.

A OVR é um conjunto de Fichas no tempo e motivo (Tipo Fichas de importação de um mês). Já a "Operação" é um
conjunto de Fichas conectadas por um nexo.

As Fichas que não estão em nenhuma operação mas não estão concluídas serão exibidas na Operação virtual "Pendentes"
para controle.

No Secta e-OVR, OVR é a autorização para fiscalização, alocando equipe em alvo(s), Operação ou atividade é
a fiscalização de um endereço/alvo, e cada operação pode ter n relatórios do Secta vinculados.

Não há no Fichas a figura do OVR, pela própria dinâmica da operação portuária, pois não há necessidade de
autorização prévia para uma fiscalização em zona primária, a autorização é dada pela própria portaria de
atribuições. E as operações/atividades/fichas são realizadas de forma constante pelas equipes permanentemente
alocadas. Assim, a solução para se adequar à Portaria de OVR é agrupar as fiscalizações finalizadas naquele mês
 em OVRs conforme tipo e/ou equipe.

 "Operação" neste dashboard é o sentido corrente, que seria um conjunto de fiscalizações.

O dashboard pode ser filtrado pelo período de ABERTURA da Ficha (`OVR.datahora`, 09/11/2026):
`inicio` e `fim` são datas, os dois dias inclusive; sem eles (o padrão), sem filtro.

Com o período preenchido (17/11/2026) entra a categoria virtual "Fichas sem operação informada": as
Fichas fora de qualquer Operação, com status Concluída, e com resultado REGISTRADO no período
(`ResultadoOVR.create_date`). Só ela usa a data do resultado. Como as pendentes são as não
concluídas, as duas categorias não se cruzam.

O total do resumo conta cada Ficha uma vez; as Fichas que aparecem em mais de uma linha (em duas
Operações) são listadas para o usuário conferir e corrigir.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, exists
from sqlalchemy.orm import selectinload

from bhadrasana.models.laudo import Empresa
from bhadrasana.models.ovr import Flag, OVR, ResultadoOVR, TipoResultado, flags_table
from virasana.integracao.mercante.mercantealchemy import Conhecimento, NCMItem

ID_PENDENTES = -1
ID_SEM_OPERACAO = -2
# status (fase) Concluída: ver faseOVR em models/ovr.py
FASE_CONCLUIDA = 3
# CEs e CNPJs por consulta (IN): a conhecimentosresumo tem dezenas de milhões de linhas, a
# consulta vai sempre pela chave
TAMANHO_LOTE = 500
# NCMs exibidas por CE; as demais ficam no title
MAXIMO_NCMS = 15


def condicoes_periodo(coluna, inicio: Optional[date] = None, fim: Optional[date] = None) -> list:
    """`coluna` de `inicio` a `fim`, os dois dias inteiros; sem um deles, o lado fica aberto."""
    condicoes = []
    if inicio:
        condicoes.append(coluna >= datetime.combine(inicio, time.min))
    if fim:
        condicoes.append(coluna < datetime.combine(fim + timedelta(days=1), time.min))
    return condicoes


def filtra_abertura(query, inicio: Optional[date] = None, fim: Optional[date] = None):
    """As Fichas abertas (`OVR.datahora`) de `inicio` a `fim`, os dois dias inteiros.

    Sem um deles, aquele lado fica aberto; sem os dois, a consulta não muda."""
    return query.filter(*condicoes_periodo(OVR.datahora, inicio, fim))


def flag_virtual(id: int, nome: str):
    return type('FlagVirtual', (), {'id': id, 'nome': nome})()


def listar_operacoes(session, com_sem_operacao: bool = False):
    """As Operações (flags "Operação…") e, antes delas, as categorias virtuais.

    `com_sem_operacao`: inclui "Fichas sem operação informada" (só com o período preenchido)."""
    flags = (
        session.query(Flag)
        .filter(Flag.nome.like('Operação%'))
        .order_by(Flag.nome)
        .all()
    )
    virtuais = [flag_virtual(ID_PENDENTES, 'Fichas pendentes**')]
    if com_sem_operacao:
        virtuais.append(flag_virtual(ID_SEM_OPERACAO, 'Fichas sem operação informada***'))
    return virtuais + flags


def em_operacao():
    """A Ficha tem alguma flag "Operação…" (subconsulta correlacionada com OVR)."""
    # a coluna da Ficha na tabela de ligação chama-se rvf_id (ver flags_table em models/ovr.py)
    return exists().where(and_(flags_table.c.rvf_id == OVR.id,
                               flags_table.c.flag_id == Flag.id,
                               Flag.nome.like('Operação%')))


def carrega_relacoes(query):
    return query.options(
        selectinload(OVR.flags),
        selectinload(OVR.tgs),
        selectinload(OVR.rvfs),
        selectinload(OVR.recinto),
        selectinload(OVR.setor),
        selectinload(OVR.responsavel),
        selectinload(OVR.resultados),
    )


def listar_ovrs_com_pendencias(session, inicio: Optional[date] = None, fim: Optional[date] = None):
    """Fichas não concluídas que não estão em nenhuma Operação, com ou sem outras flags.

    Por subconsulta (09/11/2026): o filtro antigo, na junção com as flags, deixava de fora a Ficha
    sem nenhuma flag (nome nulo) e punha nas pendentes a Ficha de uma Operação que tivesse outra
    flag (a linha da outra flag passava)."""
    consulta = (
        session.query(OVR)
        .filter(~em_operacao())
        .filter(OVR.fase < 3)  # Ver faseOVR em models/ovr.py
        # .filter(OVR.tipooperacao == 1)  # Ver tipoOperacao em models/ovr.py
    )
    consulta = carrega_relacoes(filtra_abertura(consulta, inicio, fim))
    return consulta.order_by(OVR.datahora.desc()).all()


def listar_fichas_sem_operacao(session, inicio: Optional[date] = None, fim: Optional[date] = None):
    """Fichas Concluídas fora de qualquer Operação com resultado registrado de `inicio` a `fim`.

    Só o status Concluída (decisão do usuário, 17/11/2026): Arquivada e as não concluídas ficam
    de fora, mesmo com resultado. Vale a data do registro do resultado
    (`ResultadoOVR.create_date`), não a da abertura. Sem período, nada: seriam todas as Fichas
    concluídas da história."""
    if not (inicio or fim):
        return []
    com_resultado_no_periodo = exists().where(and_(
        ResultadoOVR.ovr_id == OVR.id,
        *condicoes_periodo(ResultadoOVR.create_date, inicio, fim)))
    consulta = (session.query(OVR)
                .filter(~em_operacao())
                .filter(OVR.fase == FASE_CONCLUIDA)
                .filter(com_resultado_no_periodo))
    return carrega_relacoes(consulta).order_by(OVR.datahora.desc()).all()


def fichas_da_categoria(session, flag_id, inicio: Optional[date] = None,
                        fim: Optional[date] = None):
    """As Fichas de uma Operação (flag) ou de uma categoria virtual, no período."""
    if flag_id == ID_PENDENTES:
        return listar_ovrs_com_pendencias(session, inicio, fim)
    if flag_id == ID_SEM_OPERACAO:
        return listar_fichas_sem_operacao(session, inicio, fim)
    consulta = filtra_abertura(session.query(OVR).join(OVR.flags).filter(Flag.id == flag_id),
                               inicio, fim)
    return carrega_relacoes(consulta).order_by(OVR.datahora.desc()).all()


def monta_detalhe_operacao(session, flag_id,
                           inicio: Optional[date] = None, fim: Optional[date] = None) -> dict:
    """A tela da Operação: o mesmo de `monta_dashboard_operacao` mais os fiscalizados (nome pela
    navi_cnpj) e a descrição e as NCMs dos CEs, que o resumo não usa."""
    dados = monta_dashboard_operacao(session, flag_id, inicio, fim)
    acrescenta_fiscalizados(session, dados)
    acrescenta_conhecimentos(session, dados)
    return dados


def monta_dashboard_operacao(session, flag_id,
                             inicio: Optional[date] = None, fim: Optional[date] = None):
    """Os números e as listas de uma Operação (ou categoria virtual) no período."""
    ovrs = fichas_da_categoria(session, flag_id, inicio, fim)

    status_counter = inicializa_counter()
    ce_mercantes = set()
    containers = set()
    total_tgs = Decimal('0.00')
    total_multas = Decimal('0.00')
    total_perdimentos = Decimal('0.00')
    rvfs_resumo = []
    ovrs_resumo = []

    total_concluidas = 0
    for ovr in ovrs:
        if ovr.fase >= 3:
            total_concluidas += 1
        status = ovr_dashboard_status(ovr)

        status_counter[status] += 1

        if ovr.numeroCEmercante:
            ce_mercantes.add(ovr.numeroCEmercante)

        valor_tgs = Decimal('0.00')
        for tg in ovr.tgs:
            if tg.valor:
                valor_tgs += tg.valor
                total_tgs += tg.valor

        valor_multas = Decimal('0.00')
        for resultado in ovr.resultados:
            if resultado.tipo_resultado not in (TipoResultado.Apreensao.value,
                                                TipoResultado.Perdimento.value, TipoResultado.Sancao.value):
                if resultado.valor:
                    valor_multas += resultado.valor
                    total_multas += resultado.valor

        valor_perdimentos = Decimal('0.00')
        for resultado in ovr.resultados:
            if resultado.tipo_resultado == TipoResultado.Perdimento.value:
                if resultado.valor:
                    valor_perdimentos += resultado.valor
                    total_perdimentos += resultado.valor

        for rvf in ovr.rvfs:
            if rvf.numerolote:
                containers.add(rvf.numerolote)
            rvfs_resumo.append({
                'id': rvf.id,
                'ovr_id': ovr.id,
                'ce': limpa_ce(rvf.numeroCEmercante) or limpa_ce(ovr.numeroCEmercante),
                'datahora': rvf.datahora or rvf.create_date,
                'numerolote': rvf.numerolote,
                'descricao': rvf.descricao[:180] if rvf.descricao else '',
                'peso': rvf.peso,
                'volume': rvf.volume,
                'inspecaonaoinvasiva': rvf.inspecaonaoinvasiva,
            })

        ovrs_resumo.append({
            'id': ovr.id,
            'numero': ovr.get_numero(),
            'ano': ovr.get_ano(),
            'tipooperacao': ovr.get_tipooperacao(),
            'datahora': ovr.datahora,
            'status_dashboard': status,
            'numeroCEmercante': ovr.numeroCEmercante,
            'cnpj_fiscalizado': so_digitos(ovr.cnpj_fiscalizado),
            'concluida': ovr.fase >= 3,
            'fase': ovr.get_fase(),
            'responsavel': ovr.responsavel.nome if ovr.responsavel else '',
            'setor': ovr.setor.nome if ovr.setor else '',
            'recinto': ovr.recinto.nome if ovr.recinto else '',
            'qtd_rvfs': len(ovr.rvfs),
            'qtd_tgs': len(ovr.tgs),
            'valor_tgs': valor_tgs,
            'valor_multas': valor_multas,
            'valor_perdimentos': valor_perdimentos,
            'flags': [f.nome for f in ovr.flags],
        })

    if len(ovrs_resumo) > 0:
        percentual_conclusao = total_concluidas / len(ovrs_resumo)
    else:
        percentual_conclusao = 0

    return {
        'ovrs': ovrs_resumo,
        'rvfs': rvfs_resumo,
        'ces_mercantes': sorted(ce_mercantes),
        'containers': sorted(containers),
        'total_tgs': total_tgs,
        'status_totais': dict(status_counter),
        'total_ovrs': len(ovrs_resumo),
        'total_concluidas': total_concluidas,
        'total_rvfs': len(rvfs_resumo),
        'total_ces': len(ce_mercantes),
        'percentual_conclusao': percentual_conclusao,
        'total_containers': len(containers),
        'total_multas': total_multas,
        'total_perdimentos': total_perdimentos,
    }


def so_digitos(valor: Optional[str]) -> str:
    return ''.join(c for c in (valor or '') if c.isdigit())


def limpa_ce(valor: Optional[str]) -> str:
    return (valor or '').strip()


def em_lotes(valores: list, tamanho: int = TAMANHO_LOTE):
    for inicio in range(0, len(valores), tamanho):
        yield valores[inicio:inicio + tamanho]


def nomes_das_empresas(session, documentos) -> dict:
    """Nome (navi_cnpj) de cada CNPJ: pelo CNPJ exato e, se não achar, pela raiz (o primeiro
    estabelecimento na ordem do CNPJ, como `laudo.get_empresa`). CPF (11 dígitos) não tem nome: a
    navi_cnpj só tem CNPJ, e a raiz do CPF acharia uma empresa errada."""
    cnpjs = sorted({doc for doc in documentos if doc and len(doc) >= 8 and len(doc) != 11})
    nomes = {}
    for lote in em_lotes(cnpjs):
        for cnpj, nome in session.query(Empresa.cnpj, Empresa.nome).filter(Empresa.cnpj.in_(lote)):
            nomes[cnpj] = nome
    for cnpj in cnpjs:
        if cnpj not in nomes:
            linha = (session.query(Empresa.nome)
                     .filter(Empresa.cnpj.like(cnpj[:8] + '%'))
                     .order_by(Empresa.cnpj).first())
            if linha:
                nomes[cnpj] = linha.nome
    return nomes


def acrescenta_fiscalizados(session, dados: dict):
    """Os fiscalizados da Operação (CNPJ, nome, quantidade de Fichas), do que tem mais Fichas
    para o que tem menos; '' = Ficha sem fiscalizado informado, por último. Também põe o nome em
    cada Ficha."""
    contagem = Counter(ovr['cnpj_fiscalizado'] for ovr in dados['ovrs'])
    nomes = nomes_das_empresas(session, contagem)
    for ovr in dados['ovrs']:
        ovr['fiscalizado_nome'] = nomes.get(ovr['cnpj_fiscalizado'], '')

    def ordem(item):
        documento, qtd = item
        return -qtd, documento == '', documento

    dados['fiscalizados'] = [
        {'cnpj': cnpj, 'nome': nomes.get(cnpj, ''), 'qtd_fichas': qtd}
        for cnpj, qtd in sorted(contagem.items(), key=ordem)
    ]


def lista_ncms(ncms) -> dict:
    """As NCMs em ordem, com as `MAXIMO_NCMS` primeiras para a tela e o total."""
    todas = sorted(ncms)
    return {'exibidas': todas[:MAXIMO_NCMS], 'todas': todas,
            'restantes': max(0, len(todas) - MAXIMO_NCMS)}


def fichas_de_cada_ce(dados: dict) -> dict:
    """CE → Fichas: o CE da Ficha e o de cada RVF dela."""
    fichas_por_ce = defaultdict(set)
    ligacoes = [(limpa_ce(ovr['numeroCEmercante']), ovr['id']) for ovr in dados['ovrs']] + \
        [(rvf['ce'], rvf['ovr_id']) for rvf in dados['rvfs']]
    for ce, id_ficha in ligacoes:
        if ce:
            fichas_por_ce[ce].add(id_ficha)
    return fichas_por_ce


def descricoes_dos_ces(session, ces: list) -> dict:
    """CE → descrição da mercadoria no Mercante (só os CEs que estão lá)."""
    descricoes = {}
    for lote in em_lotes(ces):
        consulta = (session.query(Conhecimento.numeroCEmercante, Conhecimento.descricao)
                    .filter(Conhecimento.numeroCEmercante.in_(lote)))
        for ce, descricao in consulta:
            descricoes[limpa_ce(ce)] = (descricao or '').strip()
    return descricoes


def ncms_dos_ces(session, ces: list) -> dict:
    """CE → contêiner → NCMs declaradas (ncmitemresumo)."""
    ncms_por_conteiner = defaultdict(lambda: defaultdict(set))
    for lote in em_lotes(ces):
        consulta = (session.query(NCMItem.numeroCEMercante, NCMItem.codigoConteiner,
                                  NCMItem.identificacaoNCM)
                    .filter(NCMItem.numeroCEMercante.in_(lote)))
        for ce, conteiner, ncm in consulta:
            if ncm and ncm.strip():
                conteiner = (conteiner or '').strip().upper()
                ncms_por_conteiner[limpa_ce(ce)][conteiner].add(ncm.strip())
    return ncms_por_conteiner


def acrescenta_conhecimentos(session, dados: dict):
    """Descrição e NCMs declaradas no Mercante.

    Em cada RVF: a descrição do CE e as NCMs declaradas para o contêiner dela (todas as do CE se
    o contêiner não tiver NCM no CE). Em `conhecimentos`: cada CE da Operação, com as Fichas, a
    descrição e todas as NCMs (cobre as Fichas sem RVF)."""
    fichas_por_ce = fichas_de_cada_ce(dados)
    ces = sorted(fichas_por_ce)
    descricoes = descricoes_dos_ces(session, ces)
    ncms_por_conteiner = ncms_dos_ces(session, ces)

    def ncms_do_ce(ce):
        return set().union(*ncms_por_conteiner.get(ce, {}).values())

    for rvf in dados['rvfs']:
        ce = rvf['ce']
        conteiner = (rvf['numerolote'] or '').strip().upper()
        do_conteiner = ncms_por_conteiner.get(ce, {}).get(conteiner)
        rvf['ce_descricao'] = descricoes.get(ce, '')
        rvf['ce_ncms'] = lista_ncms(do_conteiner or ncms_do_ce(ce))
    dados['conhecimentos'] = [
        {'ce': ce, 'fichas': sorted(fichas_por_ce[ce]), 'descricao': descricoes.get(ce, ''),
         'no_mercante': ce in descricoes, 'ncms': lista_ncms(ncms_do_ce(ce))}
        for ce in ces
    ]


class MockOVR():
    def __init__(self):
        self.fase = 0
        self.tgs = []
        self.rvfs = []

    def get_fase(self):
        return 'Arquivada'


def inicializa_counter():
    """Replica as situações de ovr_dashboard_status para capturar as descrições possíveis."""
    counter = Counter()
    ovr = MockOVR()
    ovr.fase = 4
    counter[ovr_dashboard_status(ovr)] = 0
    ovr.fase = 1
    counter[ovr_dashboard_status(ovr)] = 0
    ovr.rvfs = [0]
    counter[ovr_dashboard_status(ovr)] = 0
    ovr.tgs = [0]
    counter[ovr_dashboard_status(ovr)] = 0
    return counter


def ovr_dashboard_status(ovr):
    if ovr.fase >= 3:  # Ver faseOVR em models/ovr.py 3 - Concluída 4 - Arquivada
        return ovr.get_fase()
    tem_rvf = bool(ovr.rvfs)
    tem_tg = bool(ovr.tgs)
    if tem_tg:
        status = 'Mercadorias já informadas*'
    elif tem_rvf:
        status = 'Aguardando saneamento(s)'
    else:
        status = 'Selecionado ainda sem aberturas'
    return status


def monta_resumo_operacoes(session, inicio: Optional[date] = None,
                           fim: Optional[date] = None) -> dict:
    """O resumo de cada Operação e categoria virtual (`linhas`), o total com cada Ficha uma vez
    só (`totais`) e as Fichas que estão em mais de uma linha (`repetidas`), para o usuário
    conferir.

    "Fichas sem operação informada" só entra com o período preenchido."""
    operacoes = listar_operacoes(session, com_sem_operacao=bool(inicio or fim))
    linhas = []
    fichas = {}
    linhas_da_ficha = defaultdict(list)
    ces, containers = set(), set()

    for operacao in operacoes:
        dados = monta_dashboard_operacao(session, operacao.id, inicio, fim)
        linhas.append({
            'flag_id': operacao.id,
            'nome': operacao.nome,
            'total_ovrs': dados['total_ovrs'],
            'percentual_conclusao': int(dados['percentual_conclusao'] * 100),
            'total_rvfs': dados['total_rvfs'],
            'total_ces': dados['total_ces'],
            'total_containers': dados['total_containers'],
            'total_tgs': dados['total_tgs'],
            'total_multas': dados['total_multas'],
            'total_perdimentos': dados['total_perdimentos'],
            'status_totais': dados['status_totais'],
        })
        for ovr in dados['ovrs']:
            fichas[ovr['id']] = ovr
            linhas_da_ficha[ovr['id']].append(operacao.nome)
        ces.update(dados['ces_mercantes'])
        containers.update(dados['containers'])

    return {
        'linhas': linhas,
        'totais': totaliza_fichas(fichas.values(), ces, containers),
        'repetidas': [
            {'id': id_ficha, 'datahora': fichas[id_ficha]['datahora'],
             'fase': fichas[id_ficha]['fase'], 'linhas': nomes}
            for id_ficha, nomes in sorted(linhas_da_ficha.items()) if len(nomes) > 1
        ],
    }


def totaliza_fichas(fichas, ces: set, containers: set) -> dict:
    """Totais do resumo com cada Ficha contada uma vez (`fichas`: as Fichas distintas)."""
    fichas = list(fichas)
    concluidas = sum(1 for ovr in fichas if ovr['concluida'])
    return {
        'total_ovrs': len(fichas),
        'percentual_conclusao': int(concluidas / len(fichas) * 100) if fichas else 0,
        'total_rvfs': sum(ovr['qtd_rvfs'] for ovr in fichas),
        'total_ces': len(ces),
        'total_containers': len(containers),
        'total_tgs': sum((ovr['valor_tgs'] for ovr in fichas), Decimal('0.00')),
        'total_multas': sum((ovr['valor_multas'] for ovr in fichas), Decimal('0.00')),
        'total_perdimentos': sum((ovr['valor_perdimentos'] for ovr in fichas), Decimal('0.00')),
    }
