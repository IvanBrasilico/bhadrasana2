import io
import sys
from sqlite3 import OperationalError

from gridfs import GridFS
from sqlalchemy.orm.exc import NoResultFound
from virasana.integracao.bagagens.viajantesalchemy import DSI

sys.path.append('.')
sys.path.append('../ajna_docs/commons')
sys.path.append('../virasana')
sys.path.insert(0, '../ajna_api')

from collections import OrderedDict, defaultdict
from datetime import timedelta, datetime
from enum import Enum
from typing import List, Tuple, Set

import numpy as np
import pandas as pd
import sqlalchemy
from sqlalchemy import and_, text, or_, func
from sqlalchemy.orm import Session

from ajna_commons.models.bsonimage import BsonImage
from ajna_commons.flask.log import logger
from ajna_commons.utils.images import mongo_image
from bhadrasana.models import Usuario, Setor, EBloqueado, ESomenteUsuarioResponsavel, \
    usuario_tem_perfil_nome, ENaoAutorizado
from bhadrasana.models import handle_datahora, ESomenteMesmoUsuario, gera_objeto, \
    get_usuario_validando
from bhadrasana.models.filtros_ficha import FiltrosFicha
from bhadrasana.models.laudo import get_empresa
from bhadrasana.models.ovr import FonteDocx, Representacao, RepresentanteMarca, Assistente, \
    TiposEventoAssistente, ResultadoOVR
from bhadrasana.models.ovr import OVR, EventoOVR, TipoEventoOVR, ProcessoOVR, \
    TipoProcessoOVR, ItemTG, Recinto, TGOVR, Marca, Enumerado, TipoMercadoria, \
    EventoEspecial, Flag, Relatorio, RoteiroOperacaoOVR, flags_table, VisualizacaoOVR, \
    OKRObjective, OKRResultMeta, OKRResult, ModeloDocx
from bhadrasana.models.rvf import Infracao, infracoesencontradas_table, RVF
from bhadrasana.models.virasana_manager import get_conhecimento
from virasana.integracao.mercante.mercantealchemy import Item


def get_recintos_unidade(session, cod_unidade: str) -> List[Tuple[int, str]]:
    recintos = session.query(Recinto).filter(Recinto.cod_unidade == cod_unidade).all()
    recintos_list = [(recinto.id, f'{recinto.nome} ({recinto.cod_dte})') for recinto in recintos]
    return sorted(recintos_list, key=lambda x: x[1])


def get_recintos(session) -> List[Tuple[int, str]]:
    recintos = session.query(Recinto).all()
    recintos_list = [(recinto.id, f'{recinto.nome} ({recinto.cod_dte})') for recinto in recintos]
    return sorted(recintos_list, key=lambda x: x[1])


def get_recintos_dte(session) -> List[Tuple[int, str]]:
    recintos = session.query(Recinto).filter(Recinto.cod_dte.isnot(None)).all()
    recintos_list = [(recinto.cod_dte, f'{recinto.nome} ({recinto.cod_dte})')
                     for recinto in recintos]
    return sorted(recintos_list, key=lambda x: x[1])


def get_tipos_evento(session) -> List[Tuple[int, str]]:
    tiposeventos = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.eventoespecial.is_(None)).order_by(
        TipoEventoOVR.nome
    ).all()
    return [(tipo.id, tipo.nome) for tipo in tiposeventos]


def get_tipos_evento_todos(session) -> List[Tuple[int, str]]:
    tiposeventos = session.query(TipoEventoOVR).order_by(
        TipoEventoOVR.nome
    ).all()
    return [(tipo.id, tipo.nome) for tipo in tiposeventos]


def get_tipos_evento_comfase_choice(session) -> List[Tuple[int, str]]:
    tiposeventos = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.eventoespecial.is_(None)).order_by(
        TipoEventoOVR.nome
    ).all()
    return [(tipo.id, tipo.nome + ' - ' + Enumerado.faseOVR(tipo.fase))
            for tipo in tiposeventos]


def get_tipos_processo(session) -> List[Tuple[int, str]]:
    tiposprocesso = session.query(TipoProcessoOVR).all()
    return [(tipo.id, tipo.descricao) for tipo in tiposprocesso]


def get_relatorios_choice(session) -> List[Tuple[int, str]]:
    relatorios = session.query(Relatorio).order_by(Relatorio.nome).all()
    return [(relatorio.id, relatorio.nome) for relatorio in relatorios]


def get_relatorio(session, relatorio_id: int) -> Relatorio:
    return session.query(Relatorio).filter(Relatorio.id == relatorio_id).one_or_none()


def executa_relatorio(session, relatorio: Relatorio,
                      data_inicial: datetime, data_final: datetime,
                      user_name: str = None, setor_id: str = None):
    params = {'datainicio': data_inicial, 'datafim': data_final + timedelta(days=1)}
    if setor_id:
        setores = get_setores_filhos_recursivo_id(session, setor_id)
        params['setor_id'] = [setor_id, *[setor.id for setor in setores]]
    elif user_name:
        setores = get_setores_cpf(session, user_name)
        params['setor_id'] = [setor.id for setor in setores]
    logger.info('Rodando relatório {} com parâmetros {}'.format(relatorio.nome, params))
    # (datetime.strftime(data_inicial, '%Y-%m-%d'),
    # datetime.strftime(data_final, '%Y-%m-%d'))
    sql_query = text(relatorio.sql)
    result = []
    try:
        result_proxy = session.execute(sql_query, params)
    except TypeError as err:
        logger.error('Erro em executa_relatorio: %s' % err)
        result_proxy = session.execute(sql_query)
    names = result_proxy.keys()
    rows = result_proxy.fetchall()
    if relatorio.id == 8:  # Do pivot for better visualization
        df_eventos_especiais = pd.DataFrame(rows, columns=names)
        df_eventos_especiais = df_eventos_especiais.pivot_table(
            index=['Ano', 'Mês', 'cpf', 'nome'],
            columns='Ação', values='qtde'
        ).fillna(0).reset_index()
        names = df_eventos_especiais.columns
        print(df_eventos_especiais.dtypes)
        rows = df_eventos_especiais.values.tolist()

    result.append(names)
    result.extend(rows)

    return result


def cadastra_ovr(session, params: dict, user_name: str) -> OVR:
    usuario = get_usuario_validando(session, user_name)
    ovr = get_ovr(session, params.get('id'))
    valida_mesmo_responsavel_ovr_user_name(session, ovr, user_name)
    if not ovr.user_name:
        ovr.setor_id = usuario.setor_id
        ovr.user_name = usuario.cpf
    if ovr.fase > 2:
        raise EBloqueado()
    for key, value in params.items():
        if value and value != 'None':
            setattr(ovr, key, value)
    ovr.datahora = handle_datahora(params)
    # Atribuir CNPJ do Mercante caso não informado expressamente
    if not ovr.cnpj_fiscalizado:
        if ovr.numeroCEmercante:
            try:
                conhecimento = get_conhecimento(session,
                                                ovr.numeroCEmercante)
                if conhecimento:
                    ovr.cnpj_fiscalizado = conhecimento.consignatario
            except OperationalError:
                pass
            except Exception as err:
                logger.error(str(err), exc_info=True)
    try:
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        logger.error('Erro cadastra_ovr: %s' % str(err))
        logger.error(ovr.__dict__)
        raise err
    return ovr


def get_ovr(session, ovr_id: int = None) -> OVR:
    if ovr_id is None:
        ovr = OVR()
        return ovr
    ovr = session.query(OVR).filter(OVR.id == ovr_id).one_or_none()
    if ovr is None:
        return get_ovr(session)
    return ovr


def get_ovr_one(session, ovr_id: int = None) -> OVR:
    try:
        return session.query(OVR).filter(OVR.id == ovr_id).one()
    except NoResultFound:
        raise NoResultFound(f'OVR {ovr_id} não encontrada.')


def get_ovr_responsavel(session, user_name: str, orfas=True) -> List[OVR]:
    """Pegar OVRs que estejam com Usuário como responsável ou sem responsável nos setores"""
    usuario = get_usuario_validando(session, user_name)
    if orfas:
        return session.query(OVR).filter(or_(
            OVR.responsavel_cpf == user_name,
            and_(OVR.responsavel_cpf.is_(None), OVR.setor_id == usuario.setor_id)
        )).all()
    else:
        return session.query(OVR).filter(or_(
            OVR.responsavel_cpf == user_name,
        )).all()


def get_ovr_responsavel_setores(session, user_name: str, setores: List[Setor]) -> List[OVR]:
    """Pegar OVRs que estejam com Usuário como responsável ou sem responsável nos setores"""
    setores_ids = [setor.id for setor in setores]
    return session.query(OVR).filter(or_(
        OVR.responsavel_cpf == user_name,
        and_(OVR.responsavel_cpf.is_(None), OVR.setor_id.in_(setores_ids))
    )).all()


def get_ovr_auditor(session, user_name: str) -> List[OVR]:
    return session.query(OVR).filter(OVR.cpfauditorresponsavel == user_name). \
        filter(OVR.fase < 3).all()


def get_ovr_passagem(session, user_name: str,
                     datainicio: datetime, datafim: datetime) -> List[OVR]:
    datafim = datafim + timedelta(days=1)
    eventos = session.query(EventoOVR).filter(
        EventoOVR.user_name == user_name).all()
    ids_ovrs = [evento.ovr_id for evento in eventos]
    return session.query(OVR).filter(OVR.id.in_(ids_ovrs)). \
        filter(OVR.datahora.between(datainicio, datafim)).all()


def get_ovr_criadaspor(session, user_name: str,
                       datainicio: datetime, datafim: datetime) -> List[OVR]:
    datafim = datafim + timedelta(days=1)
    return session.query(OVR).filter(OVR.user_name == user_name). \
        filter(OVR.datahora.between(datainicio, datafim)).all()


def get_ovr_visao_usuario(session, datainicio: datetime,
                          datafim: datetime, usuario_cpf: str, setor_id: str = None,
                          lista_flags: list = None,
                          lista_tipos: list = None) -> List[OVR]:
    """Traz todas que for importante visualizar, de acordo com o perfil.

    Mostra se usuário criou, se é responsável, ou se é auditor responsável

    Se usuário for Supervisor, mostra todos do Setor escolhido também
    """
    usuario = get_usuario_validando(session, usuario_cpf)
    datafim = datafim + timedelta(days=1)
    if setor_id is None or setor_id == 'None':
        print('Usuario')
        filtro = or_(OVR.user_name == usuario_cpf,
                     OVR.responsavel_cpf == usuario_cpf,
                     OVR.cpfauditorresponsavel == usuario_cpf,
                     and_(OVR.responsavel_cpf.is_(None), OVR.setor_id == usuario.setor_id)
                     )
    else:
        print('Setor')
        # Mudança: dar opção a qualquer Usuário visualizar o Setor
        #  if usuario_tem_perfil_nome(session, usuario_cpf, 'Supervisor'):
        filtro = or_(OVR.setor_id == setor_id)
    if lista_tipos:
        filtro = and_(filtro, OVR.tipooperacao.in_(lista_tipos))
    if lista_flags:
        q = session.query(OVR).join(
            flags_table).filter(flags_table.c.flag_id.in_(lista_flags)). \
            filter(filtro).filter(OVR.datahora.between(datainicio, datafim)). \
            order_by(OVR.datahora)
    else:
        q = session.query(OVR).filter(filtro) \
            .filter(OVR.datahora.between(datainicio, datafim)).order_by(OVR.datahora)
    logger.info('get_ovr_visao_usuario - query' + str(q) + ' params: ' +
                f' user {usuario_cpf} Setor {setor_id} De {datainicio} a {datafim}')
    return q.all()


def get_ovrs_abertas_flags(session, usuario_cpf: str, lista_flags: list) -> List[OVR]:
    """Traz ovrs nas primeiras fases com flags e responsabilidade do usuário."""
    filtro = or_(OVR.responsavel_cpf == usuario_cpf,
                 OVR.cpfauditorresponsavel == usuario_cpf)
    q = session.query(OVR).join(
        flags_table).filter(flags_table.c.flag_id.in_(lista_flags)). \
        filter(filtro).order_by(OVR.datahora)
    logger.info(f'get_ovrs_abertas_flags - query: {str(q)} params: {usuario_cpf}, {lista_flags}')
    return q.all()


def calcula_tempos_por_fase(listafichas: List[OVR]) -> dict:
    """Recebe lista de OVRs, percorre calculando tempo de acordo com a fase.

    Retorna dicionário descrição da fase: tempo total em dias e quantidade de fichas

    :param listafichas: lista de OVRs
    """
    totaldays = defaultdict(int)
    qtdeovrs = defaultdict(int)
    result = {}

    for ovr in listafichas:
        if ovr.fase in (0, 1, 2):  # Ficha em adamento, calcular dias em aberto até hoje
            totaldays[ovr.fase] += (datetime.today() - ovr.datahora).days
            qtdeovrs[ovr.fase] += 1
        else:  # Ficha fechada, calcula dias até o último evento
            if len(ovr.historico) > 0:
                totaldays[ovr.fase] += (ovr.historico[-1].create_date - ovr.datahora).days
                qtdeovrs[ovr.fase] += 1
    for fase, qtde in qtdeovrs.items():
        result[Enumerado.faseOVR(fase)] = totaldays[fase], qtde
    return result


def calcula_tempos_por_tipoevento(listafichas: List[OVR]) -> dict:
    """Recebe lista de OVRs, percorre calculando tempo de acordo com a fase.

    Retorna dicionário descrição da fase: tempo total em dias e quantidade de fichas

    :param listafichas: lista de OVRs
    """
    totaldays = defaultdict(int)
    qtdeovrs = defaultdict(int)
    result = {}
    for ovr in listafichas:
        if len(ovr.historico) > 1:
            totaldays[ovr.tipoevento.nome] += \
                (datetime.today() - ovr.historico[-1].create_date).days
            qtdeovrs[ovr.tipoevento.nome] += 1
    for tipoevento_nome, qtde in qtdeovrs.items():
        result[tipoevento_nome] = totaldays[tipoevento_nome], qtde
    return result


def get_ovr_conhecimento(session, numero: str) -> Set[int]:
    """Retorna ids unicos de ovrs onde CE mercante foi cadastrado."""
    ovrs_conhecimento = get_ovr_filtro(
        session, {'numeroCEmercante': numero})
    return set([ovr.id for ovr in ovrs_conhecimento])


def get_ovr_due(session, numero: str) -> Set[int]:
    """Retorna ids unicos de ovrs onde DUE for cadastrada."""
    ovrs_due = get_ovr_filtro(
        session, {'numerodeclaracao': numero})
    return set([ovr.id for ovr in ovrs_due])


def get_ovr_filtro(session,
                   pfiltro: dict = None,
                   user_name: str = None,
                   limit=200) -> List[OVR]:
    filtro = and_()
    tables = []
    if user_name:
        ids_setores = [setor.id for setor in get_setores_cpf(session, user_name)]
        logger.info('Setores:' + str(ids_setores))
        expr = OVR.setor_id.in_(ids_setores)
        logger.info(expr.compile(compile_kwargs={"literal_binds": True}))
        filtro = and_(OVR.setor_id.in_(ids_setores))
        logger.info('Setores filtro:' + str(filtro))
    if pfiltro and isinstance(pfiltro, dict):
        if pfiltro.get('datainicio'):
            filtro = and_(OVR.datahora >= pfiltro.get('datainicio'), filtro)
        datafim = pfiltro.get('datafim')
        if datafim:
            datafim = datafim + timedelta(days=1)
            filtro = and_(OVR.datahora <= datafim, filtro)
        if pfiltro.get('numeroCEmercante'):
            filtro = and_(
                or_(
                    OVR.numeroCEmercante.like(
                        pfiltro.get('numeroCEmercante') + '%'),
                    RVF.numeroCEmercante.like(
                        pfiltro.get('numeroCEmercante') + '%')
                ),
                filtro)
            tables.append(RVF)
        if pfiltro.get('cnpj_fiscalizado'):
            filtro = and_(OVR.cnpj_fiscalizado.like(
                pfiltro.get('cnpj_fiscalizado')[:8] + '%'),
                filtro)
        if pfiltro.get('numero'):
            filtro = and_(OVR.numero.like(pfiltro.get('numero') + '%'), filtro)
        if pfiltro.get('observacoes'):
            # PEsquisa em observacoes, mas também em descrição da RVF e campos mercante e contêiner
            # Busca por campo observações, número da declaração e número do CE Mercante na Ficha
            # e número do Contêiner, número do CE Mercante e descrição na RVF.
            busca = '%' + pfiltro.get('observacoes').strip() + '%'
            filtro = and_(
                or_(OVR.observacoes.like(busca),
                    OVR.numerodeclaracao.like(busca),
                    OVR.numeroCEmercante.like(busca),
                    RVF.numeroCEmercante.like(busca),
                    RVF.numerolote.like(busca),
                    RVF.descricao.like(busca)
                ),
                filtro)
            tables.append(RVF)
        if pfiltro.get('numerodeclaracao'):
            filtro = and_(OVR.numerodeclaracao.like(
                pfiltro.get('numerodeclaracao') + '%'), filtro)
        if pfiltro.get('tipooperacao') and pfiltro.get('tipooperacao') != 'None':
            filtro = and_(OVR.tipooperacao == int(pfiltro.get('tipooperacao')), filtro)
        if pfiltro.get('fase') and pfiltro.get('fase') != 'None':
            filtro = and_(OVR.fase == int(pfiltro.get('fase')), filtro)
        if pfiltro.get('tipoevento_id') and pfiltro.get('tipoevento_id') != 'None':
            filtro = and_(OVR.tipoevento_id == int(pfiltro.get('tipoevento_id')), filtro)
        if pfiltro.get('teveevento') and pfiltro.get('teveevento') != 'None':
            q = session.query(EventoOVR).filter(
                EventoOVR.tipoevento_id == int(pfiltro.get('teveevento')))
            if pfiltro.get('usuarioevento') and pfiltro.get('usuarioevento') != 'None':
                q = q.filter(EventoOVR.user_name == pfiltro.get('usuarioevento'))
            eventos = q.all()
            ids_ovrs = [evento.ovr_id for evento in eventos]
            filtro = and_(OVR.id.in_(ids_ovrs), filtro)
        if pfiltro.get('responsavel_cpf') and pfiltro.get('responsavel_cpf') != 'None':
            filtro = and_(OVR.responsavel_cpf == pfiltro.get('responsavel_cpf'), filtro)
        cpfauditorresponsavel = pfiltro.get('cpfauditorresponsavel')
        if cpfauditorresponsavel and cpfauditorresponsavel != 'None':
            filtro = and_(OVR.cpfauditorresponsavel == cpfauditorresponsavel, filtro)
        if pfiltro.get('recinto_id') and pfiltro.get('recinto_id') != 'None':
            filtro = and_(OVR.recinto_id == int(pfiltro.get('recinto_id')), filtro)
        if pfiltro.get('flag_id') and pfiltro.get('flag_id') != 'None':
            filtro = and_(Flag.id == int(pfiltro.get('flag_id')), filtro)
            tables.extend([flags_table, Flag])
        # TODO: E se selecionar flags E infracoes????
        if pfiltro.get('infracao_id') and pfiltro.get('infracao_id') != 'None':
            filtro = and_(Infracao.id == int(pfiltro.get('infracao_id')), filtro)
            tables.extend([RVF, infracoesencontradas_table, Infracao])
        setor_id = pfiltro.get('setor_id')
        if setor_id and setor_id != 'None':
            setores = get_setores_filhos_recursivo_id(session, setor_id)
            ids_setores = [setor_id, *[setor.id for setor in setores]]
            filtro = and_(OVR.setor_id.in_(ids_setores), filtro)
        numeroprocesso = pfiltro.get('numeroprocesso')
        if numeroprocesso and len(numeroprocesso) >= 4:
            numerolimpo = ''.join([s for s in numeroprocesso if s.isnumeric()])
            filtro = and_(ProcessoOVR.numerolimpo.like('%' + numerolimpo + '%'), filtro)
            tables.append(ProcessoOVR)
        # TODO: Passar todos os ifs para métodos da classe FiltrosFicha
        filtros_ficha = FiltrosFicha(pfiltro, tables, filtro)
        filtros_ficha.process()
        tables = filtros_ficha.tables
        filtro = filtros_ficha.filtro
        print(tables)
    logger.info('get_ovr_filtro - pfiltro - ' + str(pfiltro))
    logger.info('get_ovr_filtro - filtro - ' + str(filtro))
    q = session.query(OVR)
    if len(tables) > 0:
        already_in_join = set()
        for table in tables:
            if table in already_in_join:
                continue
            q = q.join(table, isouter=True)
            already_in_join.add(table)
        # ovrs = q.filter(filtro).limit(100).all()
    logger.info('get_ovr_filtro - query ' + str(q))
    ovrs = q.filter(filtro).limit(limit).all()
    return [ovr for ovr in ovrs]


def get_ovr_container(session, numerolote: str,
                      datainicio: datetime = None,
                      datafim: datetime = None,
                      lista_numeroDUEs=[],
                      limit=40) -> Tuple[List[str], List[OVR]]:
    numerolote = numerolote.strip().upper()
    # Lista CEs
    if datafim:
        datafim = datafim + timedelta(days=1)
    if datainicio:
        datainicio = datainicio - timedelta(seconds=1)
    if datainicio and datafim:
        filtro_ces = and_(Item.dataAtualizacao.between(datainicio, datafim),
                          Item.codigoConteiner.like(numerolote))
    elif datafim:
        filtro_ces = and_(Item.dataAtualizacao <= datafim,
                          Item.codigoConteiner.like(numerolote))
    elif datainicio:
        filtro_ces = and_(Item.dataAtualizacao >= datainicio,
                          Item.codigoConteiner.like(numerolote))
    else:
        filtro_ces = and_(Item.codigoConteiner.like(numerolote))
    q = session.query(Item).filter(filtro_ces). \
        order_by(Item.dataAtualizacao.desc()).limit(limit)
    logger.info(f'{str(q)} - {datainicio} - {datafim} - {numerolote}')
    itens = q.all()
    listaCE = [item.numeroCEmercante for item in itens]
    # Filtra OVRs
    filtro_data = and_()
    if datainicio:
        filtro_data = and_(OVR.datahora >= datainicio, filtro_data)
    if datafim:
        filtro_data = and_(OVR.datahora <= datafim, filtro_data)
    filtro = and_(filtro_data,
                  or_(
                      OVR.numeroCEmercante.in_(listaCE),
                      OVR.numerodeclaracao.in_(lista_numeroDUEs)
                  ))
    q = session.query(OVR).filter(filtro)
    logger.info(f'{str(q)} - {datainicio} - {datafim} - {listaCE} - {lista_numeroDUEs}')
    ovrs = q.all()
    return listaCE, [ovr for ovr in ovrs]


def get_ovr_empresa(session, cnpj: str,
                    datainicio: datetime = None,
                    datafim: datetime = None) -> List[OVR]:
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos. '
                         'Informou: %s' % cnpj)
    filtro_data = and_()
    if datainicio:
        filtro_data = and_(OVR.datahora >= datainicio, filtro_data)
    if datafim:
        datafim = datafim + timedelta(days=1)
        filtro_data = and_(OVR.datahora <= datafim, filtro_data)
    # Filtra OVRs
    filtro = and_(filtro_data, OVR.cnpj_fiscalizado.like(cnpj[:8] + '%'))
    ovrs = session.query(OVR).filter(filtro).all()
    return [ovr for ovr in ovrs]


def get_ovr_pessoa(session, cpf: str,
                    datainicio: datetime = None,
                    datafim: datetime = None) -> List[OVR]:
    if not cpf or len(cpf) < 8:
        raise ValueError('CPF deve ser informado com mínimo de 11 dígitos. '
                         'Informou: %s' % cpf)
    filtro_data = and_()
    if datainicio:
        filtro_data = and_(OVR.datahora >= datainicio, filtro_data)
    if datafim:
        datafim = datafim + timedelta(days=1)
        filtro_data = and_(OVR.datahora <= datafim, filtro_data)
    # Filtra OVRs
    filtro = and_(filtro_data, OVR.cnpj_fiscalizado == cpf)
    ovrs = session.query(OVR).filter(filtro).all()
    return [ovr for ovr in ovrs]



def get_dsi_pessoa(session, cpf: str,
                    datainicio: datetime = None,
                    datafim: datetime = None) -> List[DSI]:
    if not cpf or len(cpf) < 11:
        raise ValueError('CPF deve ser informado com mínimo de 11 dígitos. '
                         'Informou: %s' % cpf)
    filtro_data = and_()
    if datainicio:
        filtro_data = and_(DSI.data_registro >= datainicio, filtro_data)
    if datafim:
        datafim = datafim + timedelta(days=1)
        filtro_data = and_(DSI.data_registro <= datafim, filtro_data)
    # Filtra CPF
    filtro = and_(filtro_data, DSI.consignatario == cpf)
    dsis = session.query(DSI).filter(filtro).all()
    return [dsi for dsi in dsis]


def get_flags(session) -> List[Flag]:
    flags = session.query(Flag).all()
    return [flag for flag in flags]


def get_flags_choice(session) -> List[Tuple[int, str]]:
    flags = session.query(Flag).all()
    return [(flag.id, flag.nome) for flag in flags]


def get_ids_flags_contrafacao(session) -> List[int]:
    flags = get_flags(session)
    return [flag.id for flag in flags if 'contraf' in flag.nome.lower()]


def inclui_flag_ovr(session, ovr_id, flag_nome, user_name) -> List[Flag]:
    valida_mesmo_responsavel_user_name(session, ovr_id, user_name)
    flag = session.query(Flag).filter(
        Flag.nome == flag_nome).one_or_none()
    # logger.info(flag, flag_nome)
    if flag:
        return gerencia_flag_ovr(session, ovr_id, flag.id, inclui=True)
    return []


def exclui_flag_ovr(session, ovr_id, flag_id) -> List[Flag]:
    return gerencia_flag_ovr(session, ovr_id, flag_id, inclui=False)


def gerencia_flag_ovr(session, ovr_id, flag_id, inclui=True) -> List[Flag]:
    ovr = session.query(OVR).filter(OVR.id == ovr_id).one_or_none()
    if ovr:
        flag = session.query(Flag).filter(
            Flag.id == flag_id).one_or_none()
        if flag:
            if inclui:
                ovr.flags.append(flag)
            else:
                ovr.flags.remove(flag)
            try:
                session.commit()
            except Exception as err:
                session.rollback()
                raise err
            return ovr.flags
    return []


def atribui_responsavel_ovr(session, ovr_id: int,
                            responsavel: str, user_name: str,
                            auditor=False) -> OVR:
    """Atualiza campo responsável na OVR. Gera evento correspondente.

    :param session: Conexão com banco SQLAlchemy
    :param ovr_id: ID da OVR a atribuir responsável
    :param responsavel: CPF do novo responsável
    :param user_name: CPF do responsável atual
    :return: OVR modificado
    """
    try:
        ovr = get_ovr(session, ovr_id)
        # Se Usuário for Supervisor E está nos seus Setores, pode atribuir à vontade.
        # Senão, precisa ser responsável atual
        checar = True
        if usuario_tem_perfil_nome(session, user_name, 'Supervisor'):
            setores = get_setores_cpf(session, user_name)
            for setor in setores:
                if ovr.setor_id == setor.id:
                    print('Checagem de setor OK:', ovr.setor_id, setor)
                    checar = False
                    break
        if checar:
            valida_mesmo_responsavel_user_name(session, ovr_id, user_name)
        if auditor:
            tipoevento = session.query(TipoEventoOVR).filter(
                TipoEventoOVR.eventoespecial == EventoEspecial.AuditorResponsavel.value).first()
            if ovr.cpfauditorresponsavel is None:
                responsavel_anterior = 'Nenhum'
            else:
                responsavel_anterior = ovr.cpfauditorresponsavel
        else:
            tipoevento = session.query(TipoEventoOVR).filter(
                TipoEventoOVR.eventoespecial == EventoEspecial.Responsavel.value).first()
            if ovr.responsavel_cpf is None:
                responsavel_anterior = 'Nenhum'
            else:
                responsavel_anterior = ovr.responsavel_cpf
        evento_params = {'tipoevento_id': tipoevento.id,
                         'motivo': f'De: {responsavel_anterior} Para: {responsavel}',
                         'user_name': responsavel,  # Novo Responsável
                         'ovr_id': ovr.id,
                         }
        evento = gera_eventoovr(session, evento_params, commit=False,
                                user_name=user_name, valida_usuario=False)
        # Só pode editar a ovr após gerar evento para não dar problema de permissão
        if auditor:
            ovr.cpfauditorresponsavel = responsavel  # Novo Auditor
        else:
            ovr.responsavel_cpf = responsavel  # Novo responsavel
        session.add(evento)
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return ovr


def muda_setor_ovr(session, ovr_id: int,
                   setor_id: str, user_name: str) -> OVR:
    """Atualiza campo setor na OVR. Gera evento correspondente.

    Regras: somente responsável ou Supervisor pode chamar,
    ovr "liberada" - fase 0 ou sem responsável não possuem restrição

    :param session: Conexão com banco SQLAlchemy
    :param ovr_id: ID da OVR a atribuir responsável
    :param setor_id: ID do novo setor
    :return: OVR modificado
    """
    try:
        ovr = get_ovr(session, ovr_id)
        tipoevento = session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == EventoEspecial.MudancaSetor.value).first()
        evento_params = {'tipoevento_id': tipoevento.id,
                         'motivo': 'Setor Anterior: ' + ovr.setor.nome,
                         'user_name': user_name,  # Responsável pela mudança
                         'ovr_id': ovr.id,
                         }
        evento = gera_eventoovr(session, evento_params, commit=False, user_name=user_name)
        ovr.tipoevento_id = tipoevento.id
        ovr.setor_id = setor_id
        ovr.responsavel_cpf = None
        ovr.fase = 0
        session.add(evento)
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return ovr


def libera_ovr(session, ovr_id: int, user_name: str) -> OVR:
    """Atualiza campo responsavel na OVR. Gera evento correspondente.

    Regras: somente responsável ou Supervisor pode liberar,
    ovr "liberada" - fase 0 ou sem responsável não possuem restrição

    :param session: Conexão com banco SQLAlchemy
    :param ovr_id: ID da OVR a atribuir responsável
    :return: OVR modificado
    """
    try:
        ovr = get_ovr(session, ovr_id)
        tipoevento = session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == EventoEspecial.Responsavel.value).first()
        evento_params = {'tipoevento_id': tipoevento.id,
                         'motivo': f'Liberada por {ovr.responsavel_cpf}',
                         'user_name': user_name,  # Responsável pela mudança
                         'meramente_informativo': True,
                         'ovr_id': ovr.id,
                         }
        # Validar se é responsável ou Supervisor ANTES de mudar, pois
        # quando mudar não será mais validado
        valida_mesmo_responsavel_ovr_user_name(session, ovr, user_name)
        # ovr.tipoevento_id = tipoevento.id
        ovr.responsavel_cpf = None
        evento = gera_eventoovr(session, evento_params, commit=False, user_name=user_name)
        session.add(evento)
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return ovr


def informa_lavratura_auto(session, ovr_id: int,
                           responsavel: str, user_name: str) -> OVR:
    """Atualiza campo responsável na OVR. Gera evento correspondente.

    :param session: Conexão com banco SQLAlchemy
    :param ovr_id: ID da OVR a informar lavratura
    :param responsavel: CPF do responsável pela lavratura
    :param user_name: CPF do usuário que está informando
    :return: OVR modificado
    """
    try:
        ovr = get_ovr(session, ovr_id)
        tipoevento = session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == EventoEspecial.Autuacao.value).first()
        if tipoevento is None:
            raise Exception('Não há evento de lavratura cadastrado na Base!!')
        evento_params = {'tipoevento_id': tipoevento.id,
                         'motivo': 'Ficha encerrada, auto lavrado',
                         'user_name': responsavel,  # Responsável pela lavratura
                         'ovr_id': ovr.id,
                         }
        evento = gera_eventoovr(session, evento_params, commit=False, user_name=user_name)
        # Deixa Ficha na carga do Auditor que lavrou o Auto, para controle deste
        ovr.responsavel_cpf = responsavel
        session.add(evento)
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return ovr


def get_tipoevento_id(session, evento_especial):
    tipoevento = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.eventoespecial == evento_especial).first()
    return tipoevento.id


def gera_eventoovr(session, params: dict, commit=True, user_name=None,
                   valida_usuario=True) -> EventoOVR:
    evento = EventoOVR()
    for key, value in params.items():
        setattr(evento, key, value)
    if valida_usuario and not evento.meramente_informativo:
        valida_mesmo_responsavel_user_name(session, evento.ovr_id, user_name)
    if user_name:
        evento.user_name = user_name
    tipoevento = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.id == int(evento.tipoevento_id)
    ).one()
    evento.tipoevento = tipoevento
    evento.fase = tipoevento.fase
    try:
        ovr = get_ovr(session, evento.ovr_id)
        # Nao e permitido evento comum nestas fases, pois mudaria status
        if ovr.fase >= 3:  # Concluida, arquivada
            if not evento.tipoevento.eventoespecial == EventoEspecial.Responsavel.value and \
                    not evento.meramente_informativo:
                raise ENaoAutorizado('Ficha arquivada. Para informar Evento comum, '
                                     'é necessário que Supervisor atribua primeiro.')
        if not evento.meramente_informativo:
            ovr.fase = evento.fase
            ovr.tipoevento_id = evento.tipoevento_id
        session.add(ovr)
        session.add(evento)
        if commit:
            session.commit()
    except Exception as err:
        session.rollback()
        raise err

    return evento


def valida_mesmo_responsavel_ovr_user_name(session, ovr: OVR, user_name: str):
    # Se tiver algum responsável, deve ser o mesmo.
    # Se responsável for nulo, qualquer usuário pode agir
    print()
    print(f'CPF do responsável pela ficha: {ovr.responsavel_cpf}')
    print(f'Usuário logado: {user_name}')
    print(f'Fase da ficha: {ovr.fase}')

    # logger.info('******** %s ' % ovr.responsavel_cpf)
    if ovr.fase > 0 and ovr.responsavel_cpf \
            and ovr.responsavel_cpf != user_name:
        print()
        print(f'CPF do responsável pela ficha: {ovr.responsavel_cpf}')
        print(f'Usuário logado: {user_name}')
        print(f'Fase da ficha: {ovr.fase}')
        raise ESomenteUsuarioResponsavel()


def valida_mesmo_responsavel_user_name(session, ovr_id: int, user_name: str):
    ovr = session.query(OVR).filter(OVR.id == ovr_id).one_or_none()
    if ovr is None:
        raise Exception(f'OVR {ovr_id} inexistente.')
    valida_mesmo_responsavel_ovr_user_name(session, ovr, user_name)


def valida_mesmo_responsavel(session, params):
    user_name = params['user_name']
    ovr_id = params['ovr_id']
    valida_mesmo_responsavel_user_name(session, ovr_id, user_name)


def mesmo_responsavel(func):
    def wrapper(*args, **kwargs):
        print(args)
        print(kwargs)
        valida_mesmo_responsavel(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


@mesmo_responsavel
def gera_processoovr(session, params) -> ProcessoOVR:
    numero = params.get('numero_processo')
    if numero:
        params['numerolimpo'] = ''.join([s for s in numero if s.isnumeric()])
        params['numero'] = params['numero_processo']
    return gera_objeto(ProcessoOVR(),
                       session, params)


@mesmo_responsavel
def gera_resultadoovr(session, params) -> ResultadoOVR:
    ovr = get_ovr_one(session, params['ovr_id'])
    params['cpf_auditor'] = ovr.cpfauditorresponsavel
    return gera_objeto(ResultadoOVR(),
                       session, params)


def get_resultado(session, resultado_id: int) -> ResultadoOVR:
    resultado = session.query(ResultadoOVR). \
        filter(ResultadoOVR.id == resultado_id).one_or_none()
    if resultado is None:
        raise KeyError(f'resultado {resultado_id} não encontrado')
    return resultado


def excluir_resultado(session, resultado: ResultadoOVR, user_cpf):
    ovr = resultado.ovr
    if ovr.responsavel_cpf != user_cpf:
        raise ESomenteUsuarioResponsavel()
    session.delete(resultado)
    try:
        session.commit()
        return ovr
    except Exception as err:
        logger.error(err, exc_info=True)
        session.rollback()



def get_processo(session, processo_id: int) -> ProcessoOVR:
    processo = session.query(ProcessoOVR). \
        filter(ProcessoOVR.id == processo_id).one_or_none()
    if processo is None:
        raise KeyError(f'Processo {processo_id} não encontrado')
    return processo


def excluir_processo(session, processo: ProcessoOVR, user_cpf):
    ovr = processo.ovr
    if ovr.responsavel_cpf != user_cpf:
        raise ESomenteUsuarioResponsavel()
    session.delete(processo)
    try:
        session.commit()
        return ovr
    except Exception as err:
        logger.error(err, exc_info=True)
        session.rollback()


def excluir_evento(session, evento_id, user_cpf):
    evento = session.query(EventoOVR). \
        filter(EventoOVR.id == evento_id).one_or_none()
    if evento.tipoevento.eventoespecial is not None:
        raise Exception('Este Evento não pode ser desfeito!!')
    ovr = evento.ovr
    if not evento.meramente_informativo and ovr.responsavel_cpf != user_cpf:
        raise ESomenteUsuarioResponsavel()
    if evento.user_name != user_cpf:
        raise ESomenteMesmoUsuario()
    # evento.excluido = True
    session.delete(evento)
    if not evento.meramente_informativo:
        ultimo_evento = ovr.historico[-1]
        if ultimo_evento.id == evento.id:
            if len(ovr.historico) > 1:
                penultimo_evento = ovr.historico[-2]
                ovr.fase = penultimo_evento.fase
                ovr.tipoevento_id = penultimo_evento.tipoevento_id
                session.add(ovr)
            else:
                ovr.fase = 0
                ovr.tipoevento_id = None
                session.add(ovr)
    try:
        session.commit()
    except Exception as err:
        logger.error(err, exc_info=True)
        session.rollback()


def cadastra_tgovr(session, params, user_name: str) -> TGOVR:
    usuario = get_usuario_validando(session, user_name)
    tgovr = get_tgovr(session, params.get('id'))
    if tgovr.ovr_id is not None:
        ovr = get_ovr(session, tgovr.ovr_id)
    else:
        ovr = get_ovr(session, params.get('ovr_id'))
    if ovr and ovr.fase > 2:
        raise EBloqueado()
    get_usuario_validando(session, user_name)
    valida_mesmo_responsavel_ovr_user_name(session, ovr, user_name)
    if not tgovr.user_name:
        tgovr.user_name = usuario.cpf
    if tgovr.id is None and params.get('ovr_id') is not None:
        # Está incluindo Novo TG e informando ovr
        tipoevento = session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == EventoEspecial.TG.value).first()
        evento_params = {'tipoevento_id': tipoevento.id,
                         'motivo': 'Inseriu TG ',
                         'user_name': tgovr.user_name,
                         'ovr_id': params['ovr_id']
                         }
        evento = gera_eventoovr(session, evento_params, commit=False, user_name=user_name)
        session.add(evento)
    return gera_objeto(tgovr,
                       session, params)


def lista_tgovr(session, ovr_id) -> List[TGOVR]:
    try:
        ovr_id = int(ovr_id)
    except (ValueError, TypeError):
        return []
    tgs = session.query(TGOVR).filter(TGOVR.ovr_id == ovr_id).all()
    atualiza_unidade_tg(session, tgs)
    return tgs


def atualiza_valortotal_tg(session, tg_id: int):
    """ Atualiza os valores Qtde e Valor do TG com o somatório das Quantidades e dos Valores
     de todos os Itens desse TG"""
    tg = session.query(TGOVR).filter(TGOVR.id == tg_id).one_or_none()
    total_qtde = session.query(func.sum(ItemTG.qtde)). \
        filter(ItemTG.tg_id == tg.id).scalar()
    total_valor = session.query(func.sum(ItemTG.valor * ItemTG.qtde)). \
        filter(ItemTG.tg_id == tg.id).scalar()
    tg.qtde = total_qtde
    tg.valor = total_valor
    # print(total_qtde, total_valor)
    session.add(tg)
    session.commit()


def atualiza_unidade_tg(session, tgs: list):
    """ Atualiza o campo unidade da capa do TG com base nas unidades dos itens
            Todos itens UN => 0
            Todos itens KG => 1
            Sem itens no TG => 2
            Mix de UN com KG => 2
    """
    unidade_medida = Enumerado.index_unidadeMedida(' ')
    for item in tgs:
        tg = session.query(TGOVR).filter(TGOVR.id == item.id).one_or_none()
        try:
            lista_itens = session.query(ItemTG).filter(ItemTG.tg_id == tg.id).all()
            for i, item_tg in enumerate(lista_itens):
                if i == 0:
                    unidade_medida = item_tg.unidadedemedida
                else:
                    if not item_tg.unidadedemedida == unidade_medida:
                        unidade_medida = Enumerado.index_unidadeMedida(' ')
        except Exception as err:
            logger.error('TG sem itens ', err)
            tg.unidadedemedida = unidade_medida
        tg.unidadedemedida = unidade_medida
        session.add(tg)
        session.commit()


def get_tgovr_one(session, tg_id: int) -> TGOVR:
    try:
        return session.query(TGOVR).filter(TGOVR.id == tg_id).one()
    except NoResultFound:
        raise NoResultFound(f'TG {tg_id} não encontrada.')


def get_tgovr(session, tg_id: int = None) -> TGOVR:
    if tg_id is None or tg_id == 'None':
        tgovr = TGOVR()
        print('Criando TGOVR zerado...')
        return tgovr
    return session.query(TGOVR).filter(TGOVR.id == tg_id).one_or_none()


def valida_novo_itemtg(params: dict) -> List:
    required_keys = ['descricao', 'valor', 'qtde']
    invalid_keys = []
    for required_key in required_keys:
        if not params[required_key]:
            logger.error(f'A chave "{required_key}" '
                         'do ItemTG é obrigatória mas está vazia.')
            invalid_keys.append(required_key)
    return invalid_keys


def cadastra_itemtg(session, params: dict) -> ItemTG:
    item_tg = get_itemtg(session, params.get('id'))
    if len(valida_novo_itemtg(params)) != 0:
        return None
    item_tg = gera_objeto(item_tg,
                          session, params)
    atualiza_valortotal_tg(session, item_tg.tg_id)
    return item_tg


def lista_itemtg(session, tg_id: str) -> List[ItemTG]:
    try:
        tg_id = int(tg_id)
    except (ValueError, TypeError):
        return []
    return session.query(ItemTG).filter(ItemTG.tg_id == tg_id).all()


def get_itemtg(session, itemid: int = None) -> ItemTG:
    if itemid is None or itemid == 'None':
        itemtg = ItemTG()
        print('Criando ItemTG zerado...')
        return itemtg
    return session.query(ItemTG).filter(ItemTG.id == itemid).one_or_none()


def get_itemtg_numero(session, tg: TGOVR, numero: int) -> ItemTG:
    """Retorna ItemTG do TG e numero passados. Se não existir, retorna ItemTG vazio."""
    itemtg = session.query(ItemTG).filter(ItemTG.tg_id == tg.id).filter(
        ItemTG.numero == numero).one_or_none()
    if itemtg is None:
        itemtg = ItemTG()
    return itemtg


def get_itemtg_descricao_qtde_modelo(session, tg: TGOVR,
                                     descricao: str, qtde: str, modelo: str) -> ItemTG:
    """Retorna ItemTG do TG e descricao e qtde passados OU ItemTG vazio."""
    itemtg = session.query(ItemTG).filter(
        ItemTG.tg_id == tg.id
    ).filter(
        ItemTG.descricao == descricao
    ).filter(
        ItemTG.qtde == qtde
    ).filter(
        ItemTG.modelo == modelo
    ).one_or_none()
    if itemtg is None:
        itemtg = ItemTG()
    return itemtg


def exclui_item_tg(session, tg_id: str, itemtg_id=None):
    """Exclui um ItemTG específico ou todos ItemTG do TG"""
    if itemtg_id:
        try:
            itemtg_id = int(itemtg_id)
        except (ValueError, TypeError) as err:
            logger.error('Não foi possível converter para int' % err)
        # print(f">>>>>>>>>>>>>>>>> Será excluido o item {itemtg_id}")
        session.query(ItemTG).filter(
            ItemTG.id == itemtg_id
        ).delete()
    else:
        try:
            tg_id = int(tg_id)
        except (ValueError, TypeError) as err:
            logger.error('Não foi possível converter para int' % err)
        # print(f">>>>>>>>>>>>>>>>> Serão excluídos todos itens do tg: {tg_id}")
        session.query(ItemTG).filter(
            ItemTG.tg_id == tg_id
        ).delete()

    session.commit()
    atualiza_valortotal_tg(session, tg_id)
    return []


# TODO: mover Setores e Usuários daqui e do models/ovr para módulos específicos
def get_usuarios(session) -> List[Tuple[str, str]]:
    usuarios = session.query(Usuario).all()
    usuarios_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(usuarios_list, key=lambda x: x[1])


def valida_lista_setores(setores: list):
    """Trata lista tanto de Setor quando de id. Dá exceção em outro caso"""
    if not setores or not isinstance(setores, list) or len(setores) == 0:
        raise ValueError('get_usuarios_setores precisa de uma lista!!')
    if isinstance(setores[0], Setor):
        ids_setores = [setor.id for setor in setores]
    elif isinstance(setores[0], str):
        ids_setores = setores
    else:
        raise NotImplementedError('get_usuarios_setores recebeu uma lista de setores'
                                  'que não consegue entender!!')
    return ids_setores


def get_usuarios_setores_choice(session, setores: list) -> List[Tuple[str, str]]:
    ids_setores = valida_lista_setores(setores)
    usuarios = session.query(Usuario).filter(Usuario.setor_id.in_(ids_setores)).all()
    usuarios_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(usuarios_list, key=lambda x: x[1])


def get_afrfb_setores(session, setores: list) -> List[Usuario]:
    ids_setores = valida_lista_setores(setores)
    return session.query(Usuario).filter(Usuario.cargo == 0). \
        filter(Usuario.setor_id.in_(ids_setores)).all()


def get_afrfb(session, cod_unidade: str) -> List[Usuario]:
    setores = get_setores_unidade(session, cod_unidade)
    return get_afrfb_setores(session, setores)


def get_afrfb_choice(session, cod_unidade: str) -> List[Tuple[str, str]]:
    usuarios = get_afrfb(session, cod_unidade)
    usuarios_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(usuarios_list, key=lambda x: x[1])


def get_afrfb_setores_choice(session, setores: list) -> List[Tuple[str, str]]:
    usuarios = get_afrfb_setores(session, setores)
    usuarios_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(usuarios_list, key=lambda x: x[1])


def usuario_index(usuarios: list, pcpf: str) -> int:
    """Percorre a lista e retorna o índice do cpf ou -1

    :param usuarios: lista [cpf, nome] conforme get_usuarios
    :param pcpf: cpf do usuário atual / a pesquisar
    """
    index = -1
    pcpf = pcpf.strip()
    for ind, tuple in enumerate(usuarios):
        if pcpf == tuple.cpf.strip():
            index = ind
            break
    return index


def get_setores_filhos_id(session, setor_id: str) -> List[Setor]:
    return session.query(Setor).filter(Setor.pai_id == setor_id).all()


def get_setores_filhos(session, setor: Setor) -> List[Setor]:
    return get_setores_filhos_id(session, setor.id)


def get_setores_filhos_recursivo_id(session, setor_id: str) -> List[Setor]:
    setores_total = []
    setores_filhos = get_setores_filhos_id(session, setor_id)
    # print([setor.nome for setor in setores_filhos])
    if setores_filhos:
        setores_total.extend(setores_filhos)
    for setor in setores_filhos:
        setores_filhos = get_setores_filhos_recursivo_id(session, setor.id)
        setores_total.extend(setores_filhos)

    return setores_total


def get_setores_filhos_recursivo(session, setor: Setor) -> List[Setor]:
    return get_setores_filhos_recursivo_id(session, setor.id)


def get_setores(session) -> List[Setor]:
    return session.query(Setor).all()


def get_setores_unidade(session, cod_unidade: str) -> List[Setor]:
    return session.query(Setor).filter(Setor.cod_unidade == cod_unidade).all()


def get_setores_choice(session) -> List[Tuple[str, str]]:
    setores = session.query(Setor).all()
    setores_list = [(setor.id, setor.nome) for setor in setores]
    return sorted(setores_list, key=lambda x: x[1])


def get_setores_unidade_choice(session, cod_unidade: str) -> List[Setor]:
    setores = get_setores_unidade(session, cod_unidade)
    setores_list = [(setor.id, setor.nome) for setor in setores]
    return sorted(setores_list, key=lambda x: x[1])


def get_setores_usuario(session, usuario: Usuario) -> List[Setor]:
    setores = [usuario.setor]
    setores_filhos = get_setores_filhos_recursivo(session, usuario.setor)
    if setores_filhos:
        setores.extend(setores_filhos)
    return setores
    # setores_list = [(setor.id, setor.nome) for setor in setores]
    # return sorted(setores_list, key=lambda x: x[1])


def get_setores_cpf(session, cpf_usuario: str) -> List[Setor]:
    usuario = session.query(Usuario).filter(Usuario.cpf == cpf_usuario).one_or_none()
    # print(usuario, type(usuario))
    if usuario is None:
        return []
    return get_setores_usuario(session, usuario)


def get_setores_cpf_choice(session, cpf_usuario: str) -> List[Tuple[str, str]]:
    setores = get_setores_cpf(session, cpf_usuario)
    setores_list = [(setor.id, setor.nome) for setor in setores]
    return sorted(setores_list, key=lambda x: x[1])


def get_ovrs_setor(session, setor: Setor) -> list:
    setores = get_setores_filhos_recursivo(session, setor)
    ids_setores = [setor.id for setor in setores]
    ovrs = session.query(OVR).filter(OVR.setor_id.in_(ids_setores)).all()
    return [ovr for ovr in ovrs]


def get_marcas(session):
    marcas = session.query(Marca).all()
    return [marca for marca in marcas]


def get_marcas_choice(session):
    marcas = session.query(Marca).all()
    return [(marca.id, marca.nome) for marca in marcas]


def get_roteirosoperacao(session, tipooperacao: int) -> List[RoteiroOperacaoOVR]:
    return session.query(RoteiroOperacaoOVR) \
        .filter(RoteiroOperacaoOVR.tipooperacao == tipooperacao) \
        .order_by(RoteiroOperacaoOVR.ordem).all()


def get_itens_roteiro_checked(session, ovr: OVR) -> List[Tuple[str, str, bool]]:
    roteiros = get_roteirosoperacao(session, ovr.tipooperacao)
    ids_evento_na_ovr = set([evento.tipoevento.id for evento in ovr.historico])
    itens_roteiro = []
    for roteiro in roteiros:
        item_roteiro = (roteiro.descricao,
                        roteiro.tipoevento.nome,
                        roteiro.tipoevento_id in ids_evento_na_ovr)
        itens_roteiro.append(item_roteiro)
    return itens_roteiro


def get_tiposmercadoria_choice(session):
    tipos = session.query(TipoMercadoria).all()
    return [(tipo.id, tipo.nome) for tipo in tipos]


order_secta = ('TIPO', 'NCM', 'MARCA', 'MODELO', 'OBSERVAÇÃO',
               'UNIDADE', 'QUANTIDADE', 'VALOR')

de_para = OrderedDict([
    ('descricao', ['Descrição', 'TIPO', 'Tipo de Produto', 'Marca da Mercadoria',
                   'Modelo da Mercadoria', 'Observações da Mercadoria']),
    ('Taxa de Câmbio', ['Taxa de Câmbio']),
    ('ncm', ['Código NCM', 'NCM']),
    ('contramarca', ['Marca', 'MARCA', 'Marca da Mercadoria']),
    ('modelo', ['Modelo', 'MODELO', 'Modelo da Mercadoria']),
    ('unidadedemedida', ['Unid. Medida', 'UNIDADE', 'Unidade de Medida da Mercadoria']),
    ('procedencia', ['País Procedência', '*****']),  # Não utilizado ainda
    ('origem', ['País Origem', '***']),  # Não utilizado ainda
    ('moeda', ['Moeda', '****']),  # Não utilizado ainda
    ('qtde', ['Quantidade', 'QUANTIDADE', 'Quantidade da Mercadoria']),
    ('valor', ['Valor Unitário', 'VALOR', 'Valor Item']),
])


def procura_chave_lower(akey: str, original: dict):
    result = None
    lower_key = akey.lower()
    original_lower_keys = []
    original_keys = []
    for k in original.keys():
        if isinstance(k, str):
            original_lower_keys.append(k.lower())
        else:
            original_lower_keys.append(k)
        original_keys.append(k)
    try:
        ind = original_lower_keys.index(lower_key)
        return original.get(original_keys[ind])
    except ValueError:
        pass
    return result


def recupera_taxa_cambio(original):
    try:
        return float(original.get('Taxa de Câmbio'))
    except (ValueError, TypeError) as err:
        print('....................', err)
        return 1


def muda_chaves(original: dict) -> dict:
    new_dict = {}
    print(original)
    for key, alternative_keys in de_para.items():
        for alternative_key in alternative_keys:
            if original.get(alternative_key):
                if key == 'descricao':
                    if not original.get(alternative_key) == '*[OUTROS (DEMAIS TIPOS)]':
                        if new_dict.get(key):
                            new_dict[key] += ' ' + str(original.get(alternative_key))
                        else:
                            new_dict[key] = original.get(alternative_key)
                else:
                    new_dict[key] = original.get(alternative_key)
            else:
                valor = procura_chave_lower(alternative_key, original)
                if valor:
                    new_dict[key] = valor
    print(new_dict)
    return new_dict


def importa_planilha_tg(session, tg: TGOVR, afile) -> str:
    if isinstance(afile, str):
        lfilename = afile
    else:
        lfilename = afile.filename
    if 'csv' in lfilename:
        df = pd.read_csv(afile, sep=';',
                         header=1, encoding='windows-1252')
    elif '.xlsx' in lfilename:
        df = pd.read_excel(afile, engine='openpyxl')
    elif '.xls' in lfilename:
        df = pd.read_excel(afile)
    elif '.ods' in lfilename:
        df = pd.read_excel(afile, engine='odf')
    else:
        raise Exception('Extensão de arquivo desconhecida! Conheço .csv, .ods e .xls')
    print(df.head())
    df = df.replace({np.nan: None})
    alertas = dict()
    index = 0
    try:
        for index, original_row in df.iterrows():
            row = muda_chaves(original_row)
            if index == 0:
                campos_faltantes = set(de_para.keys()) - set(row.keys())
                if campos_faltantes:
                    for campo in campos_faltantes:
                        alternativas = ', '.join(de_para[campo])
                        alertas[campo] = f'Campo {campo}({alternativas}) não encontrado.'
            if row.get('descricao') is None:
                logger.info('Abortando linha {} da planilha {}'
                            'devido descrição vazia'.format(index, lfilename))
                continue
            numero = row.get('numero')
            if numero:
                itemtg = get_itemtg_numero(session, tg, numero)
            else:
                try:
                    itemtg = get_itemtg_descricao_qtde_modelo(
                        session, tg,
                        row['descricao'], row['qtde'], row.get('modelo'))
                except sqlalchemy.orm.exc.MultipleResultsFound:
                    logger.info('Abortando edição de linha {} da planilha {}'
                                'devido não ser único'.format(index, lfilename))
                    continue
                itemtg.numero = index
            itemtg.tg_id = tg.id
            itemtg.descricao = row['descricao'].strip()
            itemtg.qtde = row['qtde']
            try:
                unidade = row['unidadedemedida'].strip()
                itemtg.unidadedemedida = Enumerado. \
                    index_unidadeMedida(row['unidadedemedida'].strip().upper())
                print(itemtg.unidadedemedida)
            except ValueError as err:
                itemtg.unidadedemedida = Enumerado.index_unidadeMedida('UN')
                print(err, unidade)
            itemtg.modelo = row.get('modelo')
            itemtg.contramarca = row.get('marca')
            ncm = row.get('ncm')
            if ncm:
                ncm = str(ncm)
                itemtg.ncm = ''.join([s for s in ncm if s.isnumeric()])[:8]
            else:
                if alertas.get('ncm') is None:
                    alertas['ncm'] = 'Campo ncm ({}) não encontrado.'. \
                        format(de_para.get('ncm'))
            valor = row.get('valor')
            if valor:
                if isinstance(valor, str):
                    valor = float(valor)
                itemtg.valor = valor * recupera_taxa_cambio(row)
            else:
                itemtg.valor = 0
                if alertas.get('valor') is None:
                    alertas['valor'] = 'Campo valor ({}) não encontrado.'. \
                        format(de_para.get('valor'))
            session.add(itemtg)
        session.commit()
        atualiza_valortotal_tg(session, tg.id)
        if len(alertas) > 0:
            return ' '.join([v for k, v in alertas.items()])
        return ''
    except KeyError as err:
        if index == 0:
            raise KeyError(
                'Campo não encontrado. Campos obrigatórios na planilha são '
                'numero, descricao, qtde e unidademedida. Opcionais ncm e valor.'
                'Erro: %s' % str(err))
        else:
            raise KeyError('Erro na coluna {} linha {}'.format(str(err), index))


class TipoPlanilha(Enum):
    Safira = 0
    Secta = 1


def exporta_planilha_tg(tg: TGOVR, filename: str,
                        formato: TipoPlanilha = TipoPlanilha.Safira):
    itens = []
    item = ItemTG()
    print(formato)
    for item in tg.itenstg:
        dumped_item = item.dump()
        print(dumped_item)
        dumped_item_titulospadrao = OrderedDict()
        for key, value in dumped_item.items():
            titulospadrao = de_para.get(key)
            if titulospadrao:
                dumped_item_titulospadrao[titulospadrao[formato.value]] = value
        itens.append(dumped_item_titulospadrao)
        print(dumped_item_titulospadrao)
        if formato == TipoPlanilha.Secta:
            dumped_item_titulospadrao['VALOR'] = dumped_item_titulospadrao['VALOR'] + 'R'
    # print(itens)
    df = pd.DataFrame(itens)
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, step=1)
    if formato == TipoPlanilha.Secta:
        df = df.reindex(order_secta, axis=1)
    df.to_excel(filename)


def exporta_planilhaovr(session: Session, user_name: str, filename: str):
    """
    Gera tabelão de OVRs (Tabela Gerencial EQODI) com pivot table

    :param session: Conexão SQLAlchemy ao Banco de Dados
    :param user_name: Nome do Usuário
    :param filename: Nome do arquivo a gerar com caminho completo
    """
    sql_processos = """
        SELECT o.id, tipoprocesso_id, p.numero FROM
        ovr_ovrs o inner join ovr_processos p on o.id = p.ovr_id
        """
    sql_ovrs = 'SELECT * FROM ovr_ovrs'  # nosec
    processsos = pd.read_sql(sql_processos, session.get_bind())
    processsos = processsos.pivot(index='id', columns='tipoprocesso_id',
                                  values='numero')
    processsos = processsos.fillna('').reset_index()
    ovrs = pd.read_sql(sql_ovrs, session.get_bind())
    df = pd.merge(ovrs, processsos, how='outer', on='id')
    df.to_csv(filename)


def cadastra_visualizacao(session, ovr: OVR, user_name: str) -> VisualizacaoOVR:
    visualizacao = VisualizacaoOVR()
    return gera_objeto(visualizacao, session,
                       {'ovr_id': ovr.id,
                        'user_name': user_name}
                       )


def get_visualizacoes(session, ovr, user_name) -> List[VisualizacaoOVR]:
    return session.query(VisualizacaoOVR).filter(VisualizacaoOVR.ovr_id == ovr.id). \
        filter(VisualizacaoOVR.user_name == user_name).all()


def get_delta_date(start, end):
    start_date = datetime(year=start.year, month=start.month, day=start.day)
    end_date = datetime(year=end.year, month=end.month, day=end.day)
    return (end_date - start_date).days


def get_objectives_setor(session, setor_id: int):
    setores = get_setores_filhos_recursivo_id(session, setor_id)
    ids_setores = [setor_id, *[setor.id for setor in setores]]
    return session.query(OKRObjective).filter(OKRObjective.setor_id.in_(ids_setores))


def executa_okr_results(session, objective: OKRObjective) -> List[OKRResultMeta]:
    params = {'datainicio': objective.inicio, 'datafim': objective.fim + timedelta(days=1)}
    setores = get_setores_filhos_recursivo_id(session, objective.setor_id)
    params['setor_id'] = [objective.setor_id, *[setor.id for setor in setores]]
    logger.info(params)
    resultados = objective.key_results
    for key_result in objective.key_results:
        sql_query = text(key_result.result.sql)
        try:
            result_proxy = session.execute(sql_query, params)
            medicoes = [row for row in result_proxy]
            key_result.resultados = medicoes
        except Exception as err:
            logger.error('Erro em executa_relatorio: %s' % err)
        logger.info(params)
        logger.info(sql_query)
    return resultados


def gera_okrobjective(session, params) -> OKRObjective:
    okrobjective = None
    okrid = params.get('id')
    if okrid:
        okrobjective = session.query(OKRObjective). \
            filter(OKRObjective.id == okrid).one_or_none()
    if okrobjective is None:
        okrobjective = OKRObjective()
    return gera_objeto(okrobjective,
                       session, params)


def exclui_okrobjective(session, okrid):
    okrobjective = session.query(OKRObjective). \
        filter(OKRObjective.id == okrid).one()
    session.delete(okrobjective)
    try:
        session.commit()
    except Exception as err:
        logger.error(err, exc_info=True)
        session.rollback()


def get_key_results(session) -> List[OKRResult]:
    return session.query(OKRResult).all()


def get_key_results_choice(session) -> List[Tuple[int, str]]:
    key_results = get_key_results(session)
    return [(kr.id, kr.nome) for kr in key_results]


def gera_okrmeta(session, params) -> OKRResultMeta:
    okrresultmeta = None
    metaid = params.get('id')
    if metaid:
        okrresultmeta = session.query(OKRResultMeta). \
            filter(OKRResultMeta.id == metaid).one_or_none()
    if okrresultmeta is None:
        okrresultmeta = OKRResultMeta()
    return gera_objeto(okrresultmeta,
                       session, params)


def exclui_okrmeta(session, metaid):
    okrmeta = session.query(OKRResultMeta). \
        filter(OKRResultMeta.id == metaid).one()
    session.delete(okrmeta)
    try:
        session.commit()
    except Exception as err:
        logger.error(err, exc_info=True)
        session.rollback()


def monta_ovr_dict(db, session, ovr_id: id,
                   explode=True, rvfs=True, imagens=True) -> dict:
    """Retorna um dicionário com conteúdo do OVR, inclusive imagens."""
    ovr = get_ovr(session, ovr_id)
    ovr_dict = ovr.dump(explode=explode)
    if rvfs:
        lista_rvfs = session.query(RVF).filter(RVF.ovr_id == ovr_id).all()
        rvfs_dicts = [rvf.dump(explode=True) for rvf in lista_rvfs]
        ovr_dict['rvfs'] = rvfs_dicts
        empresa = get_empresa(session, ovr.cnpj_fiscalizado)
        ovr_dict['nome_fiscalizado'] = empresa.nome
        ovr_dict['marcas'] = []
        for rvf_dict in rvfs_dicts:
            ovr_dict['marcas'].extend(rvf_dict['marcasencontradas'])
        if imagens:
            lista_imagens = []
            for rvf_dict in rvfs_dicts:
                for imagem_dict in rvf_dict['imagens']:
                    image = mongo_image(db, imagem_dict['imagem'])
                    imagem_dict['content'] = io.BytesIO(image)
                    lista_imagens.append(imagem_dict)
            ovr_dict['imagens'] = lista_imagens
    return ovr_dict


def get_lista_docx(session) -> List[ModeloDocx]:
    return session.query(ModeloDocx).all()


def get_docx_choices(session) -> List[Tuple[int, str]]:
    return [(modelo.id, modelo.filename + ' - ' + FonteDocx(modelo.fonte_docx_id).name)
            for modelo in get_lista_docx(session)]


def get_docx_or_none(session, docx_id: int) -> ModeloDocx:
    return session.query(ModeloDocx).filter(
        ModeloDocx.id == docx_id).one_or_none()


def get_docx(session, docx_id: int) -> ModeloDocx:
    return session.query(ModeloDocx).filter(
        ModeloDocx.id == docx_id).one()


def inclui_docx(mongodb, session, filename: str, fonte_docx_id: int, image):
    bson_img = BsonImage()
    bson_img.set_campos(filename, image.read())
    fs = GridFS(mongodb)
    _id = bson_img.tomongo(fs)
    # print(rvf_id, filename)
    docx = ModeloDocx()
    try:
        docx.filename = filename
        docx._id = str(_id)
        docx.fonte_docx_id = fonte_docx_id
        session.add(docx)
        session.commit()
    except Exception as err:
        session.rollback()
        logger.error(err, exc_info=True)
        raise err


class Manager():

    def __init__(self, dbsession):
        self.session = dbsession


class MarcaManager(Manager):
    def get_marcas(self):
        marcas = self.session.query(Marca).all()
        return [marca for marca in marcas]

    def get_marcas_choice(self):
        marcas = self.session.query(Marca).all()
        return [(marca.id, marca.nome) for marca in marcas]

    def get_representantes_ativos_marca(self, marca_id) -> List[RepresentanteMarca]:
        representantes = self.session.query(Representacao.representante_id).filter(
            Representacao.inicio <= datetime.today()
        ).filter(
            Representacao.fim.is_(None)
        ).filter(
            Representacao.marca_id == marca_id
        ).all()
        representantes = [r[0] for r in representantes]
        return self.session.query(RepresentanteMarca).filter(
            RepresentanteMarca.id.in_(representantes)).all()

    def get_marcas_ativas_representante(self, representante_id) -> List[Marca]:
        marcas_representadas = self.session.query(Representacao.marca_id).filter(
            Representacao.inicio <= datetime.today()
        ).filter(
            Representacao.fim.is_(None)
        ).filter(
            Representacao.representante_id == representante_id
        ).all()
        marcas = [r[0] for r in marcas_representadas]
        return self.session.query(Marca).filter(Marca.id.in_(marcas)).all()

    def get_marcas_rvf_por_representante(self, rvf_id: int):
        result = defaultdict(list)
        rvf = self.session.query(RVF).filter(RVF.id == rvf_id).one_or_none()
        if rvf is not None:
            marcas_representadas = set()
            for marca in rvf.marcasencontradas:
                representantes = self.get_representantes_ativos_marca(marca.id)
                for representante in representantes:
                    result[representante].append(marca)
                    marcas_representadas.add(marca)
            result[None] = set(rvf.marcasencontradas) - marcas_representadas
        return result


def get_tiposevento_assistente(session, assistente: Assistente) -> List[TipoEventoOVR]:
    return session.query(TipoEventoOVR).join(TiposEventoAssistente). \
        filter(TiposEventoAssistente.assistente == assistente.value).all()


def get_tiposevento_assistente_choice(session, assistente: Assistente) -> List[Tuple[int, str]]:
    tipos = get_tiposevento_assistente(session, assistente)
    return [(tipo.id, tipo.nome) for tipo in tipos]


def lista_de_tgs_e_items(session, ovr_id):
    """ Retorna a quatidade total e valor total de cada item do TG por NCM.
    Se o TG não tiver item, retorna a quantidde total e valor total do TG.
    """
    lista_de_tgs_items = {}
    valor_total = 0
    total_tgs = {}
    ovr_lista_tgs = lista_tgovr(session, ovr_id)
    for tg in ovr_lista_tgs:
        valor = 0
        lista_de_tgs_items[tg.id] = {}
        lista_de_tgs_items[tg.id]['container'] = tg.numerolote
        lista_de_tgs_items[tg.id]['descricao'] = tg.descricao
        for item in tg.itenstg:
            try:
                qtde = item.qtde
                valor_total = float(qtde * item.valor)
                if total_tgs.get('valor_total'):
                    total_tgs['valor_total'] += valor_total
                else:
                    total_tgs['valor_total'] = valor_total
                if lista_de_tgs_items[tg.id].get('valor'):
                    valor = lista_de_tgs_items[tg.id].get('valor') + \
                            float(item.valor * qtde)
                else:
                    lista_de_tgs_items[tg.id]['valor'] = {}
                    valor = float(item.valor * qtde)
                lista_de_tgs_items[tg.id]['valor'] = valor
            except TypeError:
                pass
    return lista_de_tgs_items, total_tgs


def lista_de_rvfs_e_apreensoes(session, ovr_id):
    """ Retorna a quatidade total e valor total de cada tipo de apreensão por RVF."""
    lista_de_rvfs_apreensoes = {}
    total_apreensoes = {}
    ovr_lista_rvfs = session.query(RVF).filter(RVF.ovr_id == int(ovr_id)).all()
    peso_total_apreensao = 0
    for rvf in ovr_lista_rvfs:
        peso = 0
        lista_de_rvfs_apreensoes[rvf.id] = {}
        lista_de_rvfs_apreensoes[rvf.id]['container'] = rvf.numerolote
        lista_de_rvfs_apreensoes[rvf.id]['descricao'] = rvf.descricao
        lista_de_rvfs_apreensoes[rvf.id]['imagens'] = rvf.imagens
        lista_de_rvfs_apreensoes[rvf.id]['apreensoes'] = {}
        for apreensao in rvf.apreensoes:
            try:
                tipo_apreensao = apreensao.tipo.descricao
                if total_apreensoes.get(tipo_apreensao):
                    peso_total_apreensao = total_apreensoes.get(tipo_apreensao) + \
                                           float(apreensao.peso)
                else:
                    peso_total_apreensao = float(apreensao.peso)
                total_apreensoes[tipo_apreensao] = peso_total_apreensao
                if lista_de_rvfs_apreensoes[rvf.id]['apreensoes'].get(tipo_apreensao):
                    peso = lista_de_rvfs_apreensoes[rvf.id]['apreensoes'].get(tipo_apreensao) + \
                           float(apreensao.peso)
                else:
                    peso = float(apreensao.peso)
                lista_de_rvfs_apreensoes[rvf.id]['apreensoes'][tipo_apreensao] = peso
            except TypeError:
                pass
    return lista_de_rvfs_apreensoes, total_apreensoes


def encerra_ficha(session, ovr_id: int, user_name: str) -> EventoOVR:
    ovr = get_ovr(session, ovr_id)
    if len(ovr.resultados) > 0:
        if ovr.cpfauditorresponsavel is None:
            raise Exception('Erro ao encerrar a ficha. Ficha com resultado, '
                            'mas sem auditor definido.')
        params = {'ovr_id': ovr_id,
                  'tipoevento_id': get_tipoevento_id(
                      session, EventoEspecial.EncerramentoComResultado.value),
                  'motivo': 'Encerramento com resultado'}
    else:
        params = {'ovr_id': ovr_id,
                  'tipoevento_id': get_tipoevento_id(
                      session, EventoEspecial.EncerramentoSemResultado.value),
                  'motivo': 'Encerramento sem resultado'}
    return gera_eventoovr(session, params=params, user_name=user_name)
