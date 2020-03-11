import json
import os
from collections import OrderedDict
from datetime import date, datetime

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


def myconverter(o):
    if isinstance(o, datetime):
        return o.__str__()  # datetime.strftime(o, '%Y%m%d %x')
    if isinstance(o, date):
        return o.__str__()  # datetime.strftime(o, '%Y%m%d %x')


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
            filtro = or_(
                *[and_(getattr(Conhecimento, key).ilike(porto + '%')) for porto in lista]
            )
            filtros = and_(filtros, filtro)
    destinos = pfiltros.get('portoDestFinal')
    if destinos:
        filtro = or_(
            *[and_(Conhecimento.portoDestFinal.ilike(destino + '%'))
              for destino in destinos]
        )
        filtros = and_(filtro, filtros)
    if pfiltros.get('ncm'):
        filtro = or_(
            *[and_(NCMItem.identificacaoNCM.ilike(ncm + '%'))
              for ncm in pfiltros.get('ncm')]
        )
        filtros = and_(filtros, filtro)
    j = join(
        Conhecimento, NCMItem,
        Conhecimento.numeroCEmercante == NCMItem.numeroCEMercante
    )
    s = select([Conhecimento, NCMItem]).select_from(j). \
        where(filtros). \
        order_by(Conhecimento.numeroCEmercante). \
        limit(limit)
    logger.info(str(s))
    logger.info(str(pfiltros))
    str_filtros = str(s) + '\n' + json.dumps(pfiltros, default=myconverter)
    logger.info(str_filtros)
    resultproxy = session.execute(s)

    result = []
    for row in resultproxy:
        result.append(OrderedDict([(key, row[key]) for key in keys]))

    return result, str_filtros


def save_planilharisco(lista_risco: list, save_path: str, filtros: str):
    destino = ''
    csv_salvo = ''
    if lista_risco and len(lista_risco) > 0:
        csv_salvo = 'resultado_' \
                    + datetime.strftime(datetime.now(), '%Y-%m%dT%H%M%S') + \
                    '.csv'
        destino = os.path.join(save_path, csv_salvo)
        with open(destino, 'w') as out_file:
            out_file.write(filtros + '\n')
            out_file.write(';'.join([key for key in lista_risco[0].keys()]) + '\n')
            for row in lista_risco:
                campos = [str(value).replace(';', ',') for value in row.values()]
                out_file.write(';'.join(campos) + '\n')
    return csv_salvo


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


def get_lista_csv(csvpath):
    lista_csv = os.listdir(csvpath)
    lista_csv = [os.path.join(csvpath, f)
                 for f in lista_csv
                 if '.csv' in f and 'resultado' in f]
    lista_csv.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for arquivo in lista_csv[4:]:  # Somente manter cinco resultados
        print('Excluir... %s' % arquivo)
        os.remove(arquivo)
        lista_csv.remove(arquivo)
    lista_comentada = []
    for arquivo in lista_csv:
        with open(arquivo, 'r') as in_file:
            for i in range(5):
                linha = in_file.readline()
        lista_comentada.append((os.path.basename(arquivo), linha))
    return lista_comentada
