from collections import OrderedDict

from ajna_commons.flask.log import logger
from sqlalchemy import select, and_, join, or_
from virasana.integracao.mercante.mercantealchemy import Conhecimento, NCMItem, RiscoAtivo

CAMPOS_RISCO = [('0', 'Selecione'),
                ('1', 'consignatario'),
                ('2', 'ncm'),
                ('3', 'portoOrigemCarga'),
                ('4', 'codigoConteiner'),
                ('5', 'descricao'),
                ('6', 'embarcador'),
                ('7', 'portoDestFinal')
                ]

def mercanterisco(session, pfiltros: dict, limit=1000):
    # conhecimentos = session.query(Conhecimento).\
    #    join(NCMItem, Conhecimento.numeroCEmercante == NCMItem.numeroCEMercante).\
    #    limit(10).all()
    keys = ['numeroCEmercante', 'descricao', 'embarcador',
            'consignatario', 'portoOrigemCarga', 'codigoConteiner', 'identificacaoNCM']
    filtros = and_()
    datainicio = pfiltros.get('datainicio')
    if datainicio:
        filtros = and_(Conhecimento.create_date >= datainicio, filtros)
    datafim = pfiltros.get('datafim')
    if datafim:
        filtros = and_(Conhecimento.create_date <= datafim, filtros)
    for key in keys:
        lista = pfiltros.get(key)
        if lista is not None:
            filtro = or_(*
                         [and_(getattr(Conhecimento, key).ilike(porto + '%'))
                          for porto in lista])
            filtros = and_(filtros, filtro)
    destinos = pfiltros.get('portoDestFinal')
    if destinos:
        filtro = or_(*
                     [and_(Conhecimento.portoDestFinal.ilike(destino + '%'))
                      for destino in destinos])
        filtros = and_(filtro, filtros)
    if pfiltros.get('ncm'):
        filtro = or_(*
                     [and_(NCMItem.identificacaoNCM.ilike(ncm + '%'))
                      for ncm in pfiltros.get('ncm')])
        filtros = and_(filtros, filtro)
    j = join(Conhecimento, NCMItem, Conhecimento.numeroCEmercante == NCMItem.numeroCEMercante)
    s = select([Conhecimento, NCMItem]).select_from(j). \
        where(filtros). \
        order_by(Conhecimento.numeroCEmercante). \
        limit(limit)
    logger.info(str(s))
    resultproxy = session.execute(s)

    result = []
    for row in resultproxy:
        result.append(OrderedDict([(key, row[key]) for key in keys]))
    return result


def riscosativos(session, user_name):
    riscosativos = session.query(RiscoAtivo). \
        filter(RiscoAtivo.user_name == user_name).all()
    return riscosativos


def insererisco(session, **kwargs):
    novorisco = RiscoAtivo(**kwargs)
    try:
        session.add(novorisco)
        session.commit()
        return True
    except Exception as err:
        session.rollback()
        raise (err)


def exclui_risco(session, id):
    risco = session.query(RiscoAtivo).filter(RiscoAtivo.ID == id).one()
    try:
        session.delete(risco)
        session.commit()
        return True
    except Exception as err:
        session.rollback()
        raise (err)
