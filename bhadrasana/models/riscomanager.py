import json
import os
import sys

import chardet

from bhadrasana.models.apirecintos import (EventoAPIBase, AcessoVeiculo, PesagemVeiculo,
                                           InspecaoNaoInvasiva, EmbarqueDesembarque)
from bhadrasana.models.riscocorad import MatrizCorad

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
sys.path.insert(0, '../ajna_api')

from ajna_commons.flask.conf import SQL_URI
from sqlalchemy.orm import sessionmaker
from virasana.integracao.gmci_alchemy import GMCI

from collections import OrderedDict, namedtuple
from datetime import date, datetime
from typing import List

import pandas as pd
from sqlalchemy import select, and_, join, or_, create_engine, func

from ajna_commons.flask.log import logger
from bhadrasana.models.ovrmanager import get_ovr_container, get_ovr_filtro
from bhadrasana.models.rvfmanager import get_rvfs_filtro, lista_rvfovr
from bhadrasana.models.virasana_manager import get_dues_container, get_detalhes_mercante, \
    get_detalhe_conhecimento, get_due
from virasana.integracao.mercante.mercantealchemy import Conhecimento, NCMItem, \
    RiscoAtivo

CAMPOS_RISCO = {'carga':
                    [('0', 'Selecione'),
                     ('1', 'consignatario'),
                     ('2', 'identificacaoNCM'),
                     ('3', 'portoOrigemCarga'),
                     ('4', 'codigoConteiner'),
                     ('5', 'descricao'),
                     ('6', 'embarcador'),
                     ('7', 'portoDestFinal'),
                     ('8', 'recinto')
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


def container_recinto(session, recinto: int, datainicio: datetime, datafim: datetime):
    rows = session.query(GMCI).filter(and_(
        GMCI.create_date.between(datainicio, datafim),
        GMCI.cod_recinto == recinto
    )).all()
    return [row.num_conteiner for row in rows]


def mercanterisco(session, pfiltros: dict, limit=1000, operador_ou=False):
    keys = ['numeroCEmercante', 'descricao', 'embarcador', 'portoDestFinal',
            'consignatario', 'portoOrigemCarga']
    keys_ncm = ['codigoConteiner', 'identificacaoNCM']
    if operador_ou:
        operador = or_
    else:
        operador = and_
    filtros = operador()
    filtros_data = and_()
    datainicio = pfiltros.get('datainicio')
    if datainicio:
        filtros_data = and_(Conhecimento.create_date >= datainicio, filtros_data)
    datafim = pfiltros.get('datafim')
    if datafim:
        filtros_data = and_(Conhecimento.create_date <= datafim, filtros_data)
    for key in keys:
        lista = pfiltros.get(key)
        if lista is not None:
            filtro = or_(
                *[and_(getattr(Conhecimento, key).like(valor + '%')) for valor in lista]
            )
            filtros = operador(filtros, filtro)
    for key in keys_ncm:
        lista = pfiltros.get(key)
        if lista is not None:
            filtro = or_(
                *[and_(getattr(NCMItem, key).like(valor + '%')) for valor in lista]
            )
            filtros = operador(filtros, filtro)
    if pfiltros.get('recinto'):
        conteineres_gmcis = []
        for recinto in pfiltros.get('recinto'):
            conteineres_gmcis.extend(container_recinto(session, int(recinto), datainicio, datafim))
        filtros = and_(filtros, NCMItem.codigoConteiner.in_(conteineres_gmcis))
    j = join(
        Conhecimento, NCMItem,
        Conhecimento.numeroCEmercante == NCMItem.numeroCEMercante
    )
    matriz_corad = pfiltros.get('matriz_corad')
    if matriz_corad:
        j = j.join(MatrizCorad, func.substr(Conhecimento.consignatario, 1, 8) == MatrizCorad.cod_emp_interv_rad)
        filtros = and_(filtros, MatrizCorad.classificacao_aniita_imp == 1)
    sem_matriz_corad = pfiltros.get('sem_matriz_corad')
    house_unico = pfiltros.get('house_unico')
    if house_unico:
        filtros = and_(filtros, Conhecimento.tipoBLConhecimento.in_([10, 12, 15]))
    filtros = and_(filtros_data, filtros)
    # ncm_item = aliased(NCMItem)
    keys_sql = [Conhecimento.numeroCEmercante, Conhecimento.descricao,
                Conhecimento.embarcador, Conhecimento.portoDestFinal,
                Conhecimento.consignatario, Conhecimento.portoOrigemCarga, NCMItem.codigoConteiner,
                NCMItem.identificacaoNCM]
    query = select(keys_sql).select_from(j). \
        where(filtros). \
        order_by(Conhecimento.numeroCEmercante). \
        limit(limit)
    logger.info('mercanterisco - query: ' + str(query))
    logger.info('mercanterisco - params: ' + str(pfiltros))
    str_filtros = str(query) + '\n' + json.dumps(pfiltros, default=myconverter)
    logger.info(str_filtros)
    resultproxy = session.execute(query)
    result = []
    for rowproxy in resultproxy:
        row_dict = OrderedDict()
        for key in (*keys, *keys_ncm):
            for column, value in rowproxy.items():
                if key in column:
                    row_dict[key] = value
                    break
        result.append(row_dict)
    print('******************')
    print(result)
    return result, str_filtros


def recintosrisco(session, pfiltros: dict, limit=1000, operador_ou=False):
    keys = [item[1] for item in CAMPOS_RISCO['recintos']]
    if operador_ou:
        operador = or_
    else:
        operador = and_
    str_filtros = json.dumps(pfiltros, default=myconverter)
    filtros = operador()
    filtros_data = and_()
    datainicio = pfiltros.get('datainicio')
    if datainicio:
        filtros_data = and_(AcessoVeiculo.dtHrOcorrencia >= datainicio, filtros_data)
    datafim = pfiltros.get('datafim')
    if datafim:
        filtros_data = and_(AcessoVeiculo.dtHrOcorrencia <= datafim, filtros_data)
    mercadoria = pfiltros.pop('mercadoria', None)
    if mercadoria:
        filtro = or_(*[and_(AcessoVeiculo.mercadoria.like('%' + item.strip() + '%'))
                       for item in mercadoria]
                     )
        filtros = operador(filtros, filtro)
    for key in keys:
        lista = pfiltros.get(key)
        if lista is not None:
            filtro = None
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
            if filtro is not None:
                filtros = operador(filtros, filtro)
    filtros = and_(filtros_data, filtros)
    q = session.query(AcessoVeiculo).filter(
        filtros
    ).outerjoin(ConteinerUld).limit(limit)
    query = q.statement.compile()
    logger.info('recintosrisco - query: ' + str(query))
    logger.info('recintosrisco - params: ' + str_filtros)
    str_filtros = str(query) + '\n' + str_filtros
    logger.info(str_filtros)
    eventos = q.all()
    result = []
    for evento in eventos:
        linha = OrderedDict([(column.name, getattr(evento, column.name))
                             for column in evento.__table__.columns])
        # print(linha)
        # print(evento.listaConteineresUld, len(evento.listaConteineresUld))
        linha_container = {}
        for container in evento.listaConteineresUld:
            linha_container = OrderedDict([(column.name, getattr(container, column.name))
                                           for column in container.__table__.columns])
        result.append({**linha, **linha_container})
    return result, str_filtros


def save_planilharisco(lista_risco: list, save_path: str, filtros: str):
    csv_salvo = ''
    if lista_risco and len(lista_risco) > 0:
        csv_salvo = 'resultado_' \
                    + datetime.strftime(datetime.now(), '%Y-%m%dT%H%M%S') + \
                    '.csv'
        destino = os.path.join(save_path, csv_salvo)
        with open(destino, 'w', newline='') as out_file:
            if filtros:
                out_file.write(filtros + '\n')
            out_file.write(';'.join([key for key in lista_risco[0].keys()]) + '\n')
            for row in lista_risco:
                campos = [str(value).replace(';', ',') for value in row.values()]
                out_file.write(';'.join(campos) + '\n')
    return csv_salvo


def riscosativos(session, user_name):
    return session.query(RiscoAtivo). \
        filter(RiscoAtivo.user_name == user_name).all()


def insererisco(session, **kwargs):
    novorisco = RiscoAtivo(**kwargs)
    try:
        session.add(novorisco)
        session.commit()
        return True
    except Exception as err:
        session.rollback()
        raise err


def exclui_risco(session, oid: int):
    risco = session.query(RiscoAtivo).filter(RiscoAtivo.ID == oid).one()
    try:
        session.delete(risco)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err


def exclui_riscos(session):
    try:
        session.query(RiscoAtivo).delete()
        session.commit()
    except Exception as err:
        session.rollback()
        raise err


def le_csv(filename):
    with open(filename, 'rb') as f:
        result = chardet.detect(f.read())
    df = pd.read_csv(filename, sep=';', header=5, encoding=result['encoding'])
    print(df.columns)
    df['identificacaoNCM'] = df['identificacaoNCM'].astype(str)
    df = df.groupby(list(df.columns)[:-1])['identificacaoNCM'].apply(', '.join).reset_index()
    # df = df.loc[df['identificacaoNCM'].str.len() > 4]
    with open(filename, 'r') as in_file:
        for i in range(5):
            linha = in_file.readline()
    riscos_ativos = json.loads(linha)
    for key, value in riscos_ativos.items():
        if key not in ['datainicio', 'datafim']:
            riscos_ativos[key] = '1'
    print(riscos_ativos)
    return [row[1].to_dict() for row in df.iterrows()], riscos_ativos


def get_lista_csv(csvpath):
    lista_csv = os.listdir(csvpath)
    lista_csv = [os.path.join(csvpath, f)
                 for f in lista_csv
                 if '.csv' in f and 'resultado' in f]
    lista_csv.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for arquivo in lista_csv[10:]:  # Somente manter dez resultados
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


def get_eventos_conteiner(session, numero: str,
                          datainicio: datetime,
                          datafim: datetime,
                          limit=20
                          ) -> List[dict]:
    Atributo = namedtuple('Atributo', ['descricao', 'campo'])

    def lista_eventos(peventos: List[EventoAPIBase],
                      atributos_info: List[Atributo]) -> List[dict]:
        result = []
        for evento in peventos:
            linha = {'id': evento.id, 'tipo': evento.__class__.__name__,
                     'data': datetime.strftime(evento.dataHoraOcorrencia, '%d/%m/%Y %H:%M'),
                     'recinto': evento.codigoRecinto}
            info = ['%s: %s  ' % (atributo.descricao, getattr(evento, atributo.campo))
                    for atributo in atributos_info]
            linha['info'] = ' '.join(info)
            result.append(linha)
        return result

    acessos_ = session.query(AcessoVeiculo).filter(
        AcessoVeiculo.numeroConteiner == numero
    ).filter(
        AcessoVeiculo.dataHoraOcorrencia >= datainicio
    ).filter(
        AcessoVeiculo.dataHoraOcorrencia <= datafim
    ).order_by(AcessoVeiculo.dataHoraOcorrencia.desc()).limit(limit).all()
    acessos = lista_eventos(acessos_, [Atributo('Placa', 'placa'),
                                       Atributo('Nome motorista', 'nomeMotorista')])
    # print('***************************** ' + numero)
    # print(acessos)
    pesagens_ = session.query(PesagemVeiculo).filter(
        PesagemVeiculo.numeroConteiner == numero
    ).filter(
        PesagemVeiculo.dataHoraOcorrencia >= datainicio
    ).filter(
        PesagemVeiculo.dataHoraOcorrencia <= datafim
    ).order_by(PesagemVeiculo.dataHoraOcorrencia.desc()).limit(limit).all()
    pesagens = lista_eventos(pesagens_, [Atributo('Placa', 'placa'),
                                         Atributo('Peso', 'pesoBrutoBalanca'),
                                         Atributo('Tara', 'taraConjunto'), ])
    inspecoes_ = session.query(InspecaoNaoInvasiva).filter(
        InspecaoNaoInvasiva.numeroConteiner == numero
    ).filter(
        InspecaoNaoInvasiva.dataHoraOcorrencia >= datainicio
    ).filter(
        InspecaoNaoInvasiva.dataHoraOcorrencia <= datafim
    ).order_by(InspecaoNaoInvasiva.dataHoraOcorrencia.desc()).limit(limit).all()
    inspecoes = lista_eventos(inspecoes_, [Atributo('Placa', 'placa'),
                                           Atributo('Tipo de contêiner', 'tipoConteiner'),
                                           Atributo('Vazio?', 'vazio'), ])
    embarques_ = session.query(EmbarqueDesembarque).filter(
        EmbarqueDesembarque.numeroConteiner == numero
    ).filter(
        EmbarqueDesembarque.dataHoraOcorrencia >= datainicio
    ).filter(
        EmbarqueDesembarque.dataHoraOcorrencia <= datafim
    ).order_by(EmbarqueDesembarque.dataHoraOcorrencia.desc()).limit(limit).all()
    embarques = lista_eventos(embarques_, [Atributo('Conteiner', 'numeroConteiner'),
                                           Atributo('IMO Viagem Navio', 'viagem'),
                                           Atributo('Escala do Navio', 'escala'),
                                           Atributo('Peso balança', 'pesoBrutoBalanca')])

    todos_eventos = [*acessos, *pesagens, *inspecoes, *embarques]
    todos_eventos.sort(reverse=True, key=lambda x: x['data'])
    return todos_eventos


def consulta_container_objects(values: dict, session, mongodb, limit=40):
    print(values)
    numero = values.get('numerolote')
    datainicio = None
    datafim = None
    try:
        datainicio = datetime.strptime(values.get('datainicio'), '%Y-%m-%d')
        datafim = datetime.strptime(values.get('datafim'), '%Y-%m-%d')
    except ValueError:
        raise ValueError(' Data de início inválida. Formato AAAA-MM-DD')
    if numero is None or datainicio is None or datafim is None:
        raise ValueError(' Dados inválidos passados nos parâmetros.'
                         ' Parâmetros numerolote: XXXX9999999,'
                         ' datainicio, datafim: AAAA-MM-DD')
    logger.info('Consultando contêiner %s' % numero)
    logger.info('get_rvfs_filtro')
    rvfs = get_rvfs_filtro(session, {'numerolote': numero,
                                     'datainicio': datainicio,
                                     'datafim': datafim})
    logger.info('get_dues_container')
    dues = get_dues_container(mongodb, numero, datainicio, datafim, limit=limit)
    lista_numeroDUEs = [due['numero'] for due in dues]
    logger.info('get_ovr_container')
    ces, ovrs = get_ovr_container(session, numero, datainicio, datafim,
                                  lista_numeroDUEs, limit=limit)
    logger.info('get detalhes CE Mercante')
    infoces = get_detalhes_mercante(session, ces)
    logger.info('get_eventos_container')
    eventos = get_eventos_conteiner(session, numero, datainicio, datafim, limit=limit)
    return rvfs, ovrs, infoces, dues, eventos


def consulta_ce_objects(numero: str, session):
    if numero is None or len(numero) < 15:
        raise ValueError(' Dados inválidos passados nos parâmetros.'
                         ' Parâmetros numero: 999999999999999 (15 dígitos)')
    logger.info('Consultando ce %s' % numero)
    logger.info('get_rvfs_filtro')
    rvfs = get_rvfs_filtro(session, {'numeroCEmercante': numero})
    logger.info('get_ovrs_filtro')
    ovrs = get_ovr_filtro(session, {'numeroCEmercante': numero})
    print('***********ZZZ%%%***', ovrs)
    logger.info('get detalhes CE Mercante')
    infoce = get_detalhe_conhecimento(session, numero)
    return rvfs, ovrs, infoce


def consulta_due_objects(due: str, session, mongodb):
    if due is None or due == '' or len(due) < 14:
        raise ValueError('get_imagens: Informe o número da DUE'
                         ' com 14 dígitos (AABR9999999999)!')
    logger.info('Consultando due %s' % due)
    logger.info('get_ovrs_filtro')
    ovrs = get_ovr_filtro(session, {'numerodeclaracao': due})
    rvfs = []
    for ovr in ovrs:
        rvfs_ovr = lista_rvfovr(session, ovr.id)
        rvfs.extend(rvfs_ovr)
    logger.info('get detalhes DUE')
    infoce = get_due(mongodb, due)
    return rvfs, ovrs, infoce


if __name__ == '__main__':
    engine = create_engine(SQL_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    start = datetime.combine(date.today(), datetime.min.time())
    end = datetime.now()
    print(container_recinto(session, 11, start, end))
