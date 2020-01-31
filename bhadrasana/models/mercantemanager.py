from sqlalchemy import select, and_, join, or_
from virasana.integracao.mercante.mercantealchemy import Conhecimento, NCMItem, RiscoAtivo


def mercanterisco(session, pfiltros: dict):
    # conhecimentos = session.query(Conhecimento).\
    #    join(NCMItem, Conhecimento.numeroCEmercante == NCMItem.numeroCEMercante).\
    #    limit(10).all()
    keys = ['dataEmissao', 'numeroCEmercante', 'consignatario', 'descricao',
            'embarcador', 'portoOrigemCarga', 'codigoConteiner', 'identificacaoNCM']
    portosorigem = pfiltros.get('portoOrigemCarga')
    filtros = and_()
    for key in keys:
        lista = pfiltros.get(key)
        if lista is not None:
            filtro = or_(*
                         [and_(getattr(Conhecimento, key).ilike(porto + '%'))
                          for porto in lista])
            filtros = and_(filtros, filtro)
    if pfiltros.get('ncm'):
        filtro = or_(*
                     [and_(NCMItem.identificacaoNCM.ilike(ncm + '%'))
                      for ncm in pfiltros.get('ncm')])
        filtros = and_(filtros, filtro)
    j = join(Conhecimento, NCMItem, Conhecimento.numeroCEmercante == NCMItem.numeroCEMercante)
    s = select([Conhecimento, NCMItem]).select_from(j). \
        where(filtros). \
        order_by(Conhecimento.numeroCEmercante, NCMItem.numeroSequencialItemCarga). \
        limit(100)
    resultproxy = session.execute(s)

    result = []
    for row in resultproxy:
        print(row)
        print(list(row.keys()))
        print(dir(row))
        result.append({key: row[key] for key in keys})
    return result


def riscosativos(session, user_name):
    riscosativos = session.query(RiscoAtivo).\
        filter(RiscoAtivo.user_name == user_name).all()
    return [(risco.campo, risco.valor, risco.motivo)
            for risco in riscosativos]


def insererisco(session, **kwargs):
    novorisco = RiscoAtivo(**kwargs)
    try:
        session.add(novorisco)
        session.commit()
        return True
    except:
        session.rollout()
        return False
