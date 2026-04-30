from collections import Counter
from decimal import Decimal

from sqlalchemy.orm import selectinload

from bhadrasana.models.ovr import Flag, OVR


def listar_operacoes(session):
    return (
        session.query(Flag)
        .filter(Flag.nome.like('Operação%'))
        .order_by(Flag.nome)
        .all()
    )

def monta_dashboard_operacao(session, flag_id):
    ovrs = (
        session.query(OVR)
        .join(OVR.flags)
        .filter(Flag.id == flag_id)
        .options(
            selectinload(OVR.flags),
            selectinload(OVR.tgs),
            selectinload(OVR.rvfs),  # após criar relationship
            selectinload(OVR.recinto),
            selectinload(OVR.setor),
            selectinload(OVR.responsavel),
        )
        .order_by(OVR.datahora.desc())
        .all()
    )

    status_counter = Counter()
    ce_mercantes = set()
    containers = set()
    total_apreendido = Decimal('0.00')
    rvfs_resumo = []
    ovrs_resumo = []

    for ovr in ovrs:
        tem_rvf = bool(ovr.rvfs)
        tem_tg = bool(ovr.tgs)

        if tem_tg:
            status = 'Mercadoria informada'
        elif tem_rvf:
            status = 'Aguardando conclusão'
        else:
            status = 'Selecionado'

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
