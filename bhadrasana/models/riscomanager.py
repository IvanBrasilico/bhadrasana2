import json
import os
from collections import OrderedDict, namedtuple
from datetime import date, datetime
from typing import List

from sqlalchemy import select, and_, join, or_

from ajna_commons.flask.log import logger
from ajnaapi.recintosapi.models import AcessoVeiculo, ConteinerUld, PesagemVeiculo, \
    EventoBase, Semirreboque
from virasana.integracao.mercante.mercantealchemy import Conhecimento, NCMItem, \
    RiscoAtivo

CAMPOS_RISCO = {'carga':
                    [('0', 'Selecione'),
                     ('1', 'consignatario'),
                     ('2', 'ncm'),
                     ('3', 'portoOrigemCarga'),
                     ('4', 'codigoConteiner'),
                     ('5', 'descricao'),
                     ('6', 'embarcador'),
                     ('7', 'portoDestFinal')
                     ],
                'recintos':
                    [('0', 'Selecione'),
                     ('1', 'cnpjTransportador'),
                     ('2', 'motorista_cpf'),
                     ('3', 'login'),
                     ('4', 'mercadoria'),
                     ('5', 'portoDescarga'),
                     ('6', 'destinoCarga'),
                     ('7', 'imoNavio'),
                     ]
                }

CAMPOS_FILTRO_IMAGEM = {
    'carga':
        {'campo_container': 'codigoConteiner',
         'campo_cemercante': 'numeroCEmercante'},
    'recintos':
        {'campo_container': 'num',
         'campo_data': 'dtHrOcorrencia'},
}


def myconverter(o):
    if isinstance(o, datetime):
        return o.__str__()  # datetime.strftime(o, '%Y%m%d %x')
    if isinstance(o, date):
        return o.__str__()  # datetime.strftime(o, '%Y%m%d %x')


def mercanterisco(session, pfiltros: dict, limit=1000):
    keys = ['numeroCEmercante', 'descricao', 'embarcador', 'portoDestFinal',
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
                *[and_(getattr(Conhecimento, key).like(porto + '%')) for porto in lista]
            )
            filtros = and_(filtros, filtro)
    if pfiltros.get('ncm'):
        filtro = or_(
            *[and_(NCMItem.identificacaoNCM.like(ncm + '%'))
              for ncm in pfiltros.get('ncm')]
        )
        filtros = and_(filtros, filtro)
    j = join(
        Conhecimento, NCMItem,
        Conhecimento.numeroCEmercante == NCMItem.numeroCEMercante
    )
    query = select([Conhecimento, NCMItem]).select_from(j). \
        where(filtros). \
        order_by(Conhecimento.numeroCEmercante). \
        limit(limit)
    logger.info('mercanterisco - query: ' + str(query))
    logger.info('mercanterisco - params: ' + str(pfiltros))
    str_filtros = str(query) + '\n' + json.dumps(pfiltros, default=myconverter)
    logger.info(str_filtros)
    resultproxy = session.execute(query)
    result = []
    for row in resultproxy:
        result.append(OrderedDict([(key, row[key]) for key in keys]))
    return result, str_filtros


def recintosrisco(session, pfiltros: dict, limit=1000):
    keys = [item[1] for item in CAMPOS_RISCO['recintos']]
    str_filtros = json.dumps(pfiltros, default=myconverter)
    filtros = and_()
    datainicio = pfiltros.get('datainicio')
    if datainicio:
        filtros = and_(AcessoVeiculo.dtHrOcorrencia >= datainicio, filtros)
    datafim = pfiltros.get('datafim')
    if datafim:
        filtros = and_(AcessoVeiculo.dtHrOcorrencia <= datafim, filtros)
    mercadoria = pfiltros.pop('mercadoria', None)
    if mercadoria:
        filtros = or_(*[and_(AcessoVeiculo.mercadoria.like('%' + item.strip() + '%'))
                        for item in mercadoria]
                      )
    for key in keys:
        lista = pfiltros.get(key)
        if lista is not None:
            if hasattr(AcessoVeiculo, key):
                filtro = or_(
                    *[and_(getattr(AcessoVeiculo, key).like(item.strip() + '%'))
                      for item in lista]
                )
            if hasattr(ConteinerUld, key):
                filtro = or_(
                    *[and_(getattr(ConteinerUld, key).like(item.strip() + '%'))
                      for item in lista]
                )
            filtros = and_(filtros, filtro)
    q = session.query(AcessoVeiculo).filter(
        filtros
    ).outerjoin(ConteinerUld).limit(limit)
    query = q.statement.compile()
    str_filtros = str(query) + '\n' + str_filtros
    logger.info(str_filtros)
    eventos = q.all()
    result = []
    for evento in eventos:
        linha = OrderedDict([(column.name, getattr(evento, column.name))
                             for column in evento.__table__.columns])
        print(linha)
        print(evento.listaConteineresUld, len(evento.listaConteineresUld))
        for container in evento.listaConteineresUld:
            linha_container = OrderedDict([(column.name, getattr(container, column.name))
                                           for column in container.__table__.columns])
        result.append({**linha, **linha_container})
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
            if filtros:
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


def get_eventos_conteiner(session, numero: str) -> List[dict]:
    Atributo = namedtuple('Atributo', ['descricao', 'campo'])

    def lista_eventos(eventos: List[EventoBase],
                      atributos_info: List[Atributo]) -> List[dict]:
        result = []
        for evento in eventos:
            linha = {}
            linha['id'] = evento.idEvento
            linha['tipo'] = 'AcessoVeiculo'
            linha['data'] = datetime.strftime(evento.dtHrOcorrencia, '%d/%m/%Y %H:%M')
            linha['recinto'] = evento.recinto
            linha['cpf'] = evento.cpfOperOcor
            info = ['%s: %s  ' % (atributo.descricao, getattr(evento, atributo.campo))
                    for atributo in atributos_info]
            linha['info'] = ' '.join(info)
            result.append(linha)
        return result

    eventos = session.query(AcessoVeiculo).join(ConteinerUld).filter(
        ConteinerUld.num == numero).all()
    acessos = lista_eventos(eventos, [Atributo('Placa', 'placa'),
                                      Atributo('Motorista', 'motorista_nome')])
    eventos = session.query(PesagemVeiculo).join(Semirreboque).filter(
        PesagemVeiculo.numConteinerUld == numero).all()
    pesagens = lista_eventos(eventos, [Atributo('Placa', 'placa'),
                                       Atributo('Peso', 'pesoBrutoBalanca'),
                                       Atributo('Tara', 'taraConjunto'), ])

    return [*acessos, *pesagens]
