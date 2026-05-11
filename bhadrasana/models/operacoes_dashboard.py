from collections import Counter
from decimal import Decimal

from sqlalchemy.orm import selectinload

from bhadrasana.models.ovr import Flag, OVR


def listar_operacoes(session):
    flags = (
        session.query(Flag)
        .filter(Flag.nome.like('Operação%'))
        .order_by(Flag.nome)
        .all()
    )

    pendentes = type('FlagVirtual', (), {
        'id': -1,
        'nome': 'Fichas pendentes**'
    })()

    return [pendentes] + flags


def listar_ovrs_com_pendencias(session):
    ovrs = (
        session.query(OVR)
        .outerjoin(Flag, OVR.flags)
        .filter(~Flag.nome.like('Operação%'))
        .filter(OVR.fase < 3)  # Ver faseOVR em models/ovr.py
        .filter(OVR.tipooperacao == 1)  # Ver tipoOperacao em models/ovr.py
        .group_by(OVR.id)
        .options(
            selectinload(OVR.flags),
            selectinload(OVR.tgs),
            selectinload(OVR.rvfs),
            selectinload(OVR.recinto),
            selectinload(OVR.setor),
            selectinload(OVR.responsavel),
        )
        .order_by(OVR.datahora.desc())
        .all()
    )
    return ovrs


def monta_dashboard_operacao(session, flag_id):
    if flag_id == -1:
        ovrs = listar_ovrs_com_pendencias(session)
    else:
        ovrs = (
            session.query(OVR)
            .join(OVR.flags)
            .filter(Flag.id == flag_id)
            .options(
                selectinload(OVR.flags),
                selectinload(OVR.tgs),
                selectinload(OVR.rvfs),
                selectinload(OVR.recinto),
                selectinload(OVR.setor),
                selectinload(OVR.responsavel),
            )
            .order_by(OVR.datahora.desc())
            .all()
        )

    status_counter = inicializa_counter()
    ce_mercantes = set()
    containers = set()
    total_apreendido = Decimal('0.00')
    rvfs_resumo = []
    ovrs_resumo = []

    for ovr in ovrs:
        status = ovr_dashboard_status(ovr)

        status_counter[status] += 1

        if ovr.numeroCEmercante:
            ce_mercantes.add(ovr.numeroCEmercante)

        valor_tgs = Decimal('0.00')
        for tg in ovr.tgs:
            if tg.valor:
                valor_tgs += tg.valor
                total_apreendido += tg.valor

        for rvf in ovr.rvfs:
            if rvf.numerolote:
                containers.add(rvf.numerolote)
            rvfs_resumo.append({
                'id': rvf.id,
                'ovr_id': ovr.id,
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
            'fase': ovr.get_fase(),
            'responsavel': ovr.responsavel.nome if ovr.responsavel else '',
            'setor': ovr.setor.nome if ovr.setor else '',
            'recinto': ovr.recinto.nome if ovr.recinto else '',
            'qtd_rvfs': len(ovr.rvfs),
            'qtd_tgs': len(ovr.tgs),
            'valor_tgs': valor_tgs,
            'flags': [f.nome for f in ovr.flags],
        })

    return {
        'ovrs': ovrs_resumo,
        'rvfs': rvfs_resumo,
        'ces_mercantes': sorted(ce_mercantes),
        'containers': sorted(containers),
        'total_apreendido': total_apreendido,
        'status_totais': dict(status_counter),
        'total_ovrs': len(ovrs_resumo),
        'total_rvfs': len(rvfs_resumo),
        'total_ces': len(ce_mercantes),
        'total_containers': len(containers),
    }


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
    if ovr.fase > 3:
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


def monta_resumo_operacoes(session):
    operacoes = listar_operacoes(session)
    resumo = []

    for operacao in operacoes:
        dados = monta_dashboard_operacao(session, operacao.id)
        resumo.append({
            'flag_id': operacao.id,
            'nome': operacao.nome,
            'total_ovrs': dados['total_ovrs'],
            'total_rvfs': dados['total_rvfs'],
            'total_ces': dados['total_ces'],
            'total_containers': dados['total_containers'],
            'total_apreendido': dados['total_apreendido'],
            'status_totais': dados['status_totais'],
        })

    return resumo
