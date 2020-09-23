from collections import OrderedDict
from datetime import timedelta, datetime
from enum import Enum
from typing import List, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import and_, text, or_, func
from sqlalchemy.orm import Session

from ajna_commons.flask.log import logger
from bhadrasana.models import Usuario, Setor, EBloqueado
from bhadrasana.models import handle_datahora, ESomenteMesmoUsuario, gera_objeto, \
    get_usuario_logado
from bhadrasana.models.ovr import OVR, EventoOVR, TipoEventoOVR, ProcessoOVR, \
    TipoProcessoOVR, ItemTG, Recinto, TGOVR, Marca, Enumerado, TipoMercadoria, \
    EventoEspecial, Flag, Relatorio, RoteiroOperacaoOVR, flags_table, VisualizacaoOVR, \
    OKRObjective, OKRResultMeta, OKRResult
from bhadrasana.models.rvf import Infracao, infracoesencontradas_table, RVF
from bhadrasana.models.virasana_manager import get_conhecimento
from virasana.integracao.mercante.mercantealchemy import Item


def get_recintos(session) -> List[Tuple[int, str]]:
    recintos = session.query(Recinto).all()
    recintos_list = [(recinto.id, recinto.nome) for recinto in recintos]
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
        rows = df_eventos_especiais.values.tolist()

    result.append(names)
    result.extend(rows)
    return result


def cadastra_ovr(session, params: dict, user_name: str) -> OVR:
    usuario = get_usuario_logado(session, user_name)
    ovr = get_ovr(session, params.get('id'))
    if ovr.user_name and ovr.user_name != usuario.cpf \
            and ovr.responsavel_cpf != usuario.cpf:
        raise ESomenteMesmoUsuario()
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
        ovr.status = 1
        return ovr
    ovr = session.query(OVR).filter(OVR.id == ovr_id).one_or_none()
    if ovr is None:
        return get_ovr(session)
    return ovr


def get_ovr_responsavel(session, user_name: str) -> List[OVR]:
    return session.query(OVR).filter(OVR.responsavel_cpf == user_name).all()


def get_ovr_criadaspor(session, user_name: str) -> List[OVR]:
    return session.query(OVR).filter(OVR.user_name == user_name).all()


def get_ovr_filtro(session,
                   pfiltro: dict = None,
                   user_name: str = None) -> List[OVR]:
    filtro = and_()
    tables = []
    if user_name:
        ids_setores = [setor.id for setor in get_setores_cpf(session, user_name)]
        filtro = and_(OVR.setor_id.in_(ids_setores))
    if pfiltro and isinstance(pfiltro, dict):
        if pfiltro.get('datainicio'):
            filtro = and_(OVR.datahora >= pfiltro.get('datainicio'), filtro)
        datafim = pfiltro.get('datafim')
        if datafim:
            datafim = datafim + timedelta(days=1)
            filtro = and_(OVR.datahora <= datafim, filtro)
        if pfiltro.get('numeroCEmercante'):
            filtro = and_(OVR.numeroCEmercante.like(
                pfiltro.get('numeroCEmercante') + '%'),
                filtro)
        if pfiltro.get('cnpj_fiscalizado'):
            filtro = and_(OVR.cnpj_fiscalizado.like(
                pfiltro.get('cnpj_fiscalizado')[:8] + '%'),
                filtro)
        if pfiltro.get('numero'):
            filtro = and_(OVR.numero.like(pfiltro.get('numero') + '%'), filtro)
        if pfiltro.get('numerodeclaracao'):
            filtro = and_(OVR.numerodeclaracao.like(
                pfiltro.get('numerodeclaracao') + '%'), filtro)
        if pfiltro.get('tipooperacao') and pfiltro.get('tipooperacao') != 'None':
            filtro = and_(OVR.tipooperacao == int(pfiltro.get('tipooperacao')), filtro)
        if pfiltro.get('fase') and pfiltro.get('fase') != 'None':
            filtro = and_(OVR.fase == int(pfiltro.get('fase')), filtro)
        if pfiltro.get('tipoevento_id') and pfiltro.get('tipoevento_id') != 'None':
            filtro = and_(OVR.tipoevento_id == int(pfiltro.get('tipoevento_id')), filtro)
        if pfiltro.get('responsavel') and pfiltro.get('responsavel') != 'None':
            filtro = and_(OVR.responsavel_cpf == pfiltro.get('responsavel'), filtro)
        if pfiltro.get('recinto_id') and pfiltro.get('recinto_id') != 'None':
            filtro = and_(OVR.recinto_id == int(pfiltro.get('recinto_id')), filtro)
        if pfiltro.get('flag_id') and pfiltro.get('flag_id') != 'None':
            filtro = and_(Flag.id == int(pfiltro.get('flag_id')), filtro)
            tables.extend([flags_table, Flag])
        # TODO: E se selecionar flags e infracoes????
        if pfiltro.get('infracao_id') and pfiltro.get('infracao_id') != 'None':
            filtro = and_(Infracao.id == int(pfiltro.get('infracao_id')), filtro)
            tables.extend([RVF, infracoesencontradas_table, Infracao])
        setor_id = pfiltro.get('setor_id')
        if setor_id and setor_id != 'None':
            setores = get_setores_filhos_recursivo_id(session, setor_id)
            ids_setores = [setor_id, *[setor.id for setor in setores]]
            filtro = and_(OVR.setor_id.in_(ids_setores), filtro)
    logger.info('get_ovr_filtro - pfiltro' + str(pfiltro))
    logger.info('get_ovr_filtro - filtro' + str(filtro))
    q = session.query(OVR)
    if len(tables) > 0:
        for table in tables:
            q = q.join(table)
        # ovrs = q.filter(filtro).limit(100).all()
    logger.info('get_ovr_filtro - query' + str(q))
    ovrs = q.filter(filtro).limit(200).all()
    return [ovr for ovr in ovrs]


def get_ovr_container(session, numerolote: str,
                      datainicio: datetime = None,
                      datafim: datetime = None,
                      lista_numeroDUEs=[]) -> Tuple[List[str], List[OVR]]:
    filtro_data = and_()
    if datainicio:
        filtro_data = and_(OVR.datahora >= datainicio, filtro_data)
    if datafim:
        datafim = datafim + timedelta(days=1)
        filtro_data = and_(OVR.datahora <= datafim, filtro_data)
    # Lista CEs
    filtro_data_ces = and_()
    if datainicio:
        filtro_data_ces = and_(Item.dataAtualizacao >= datainicio, filtro_data_ces)
    if datafim:
        datafim = datafim + timedelta(days=1)
        filtro_data_ces = and_(Item.dataAtualizacao <= datafim, filtro_data_ces)
    filtro = and_(filtro_data, Item.codigoConteiner.like(numerolote.strip()))
    itens = session.query(Item).filter(filtro).all()
    listaCE = [item.numeroCEmercante for item in itens]
    # Filtra OVRs
    filtro = and_(filtro_data,
                  or_(
                      OVR.numeroCEmercante.in_(listaCE),
                      OVR.numerodeclaracao.in_(lista_numeroDUEs)
                  ))
    ovrs = session.query(OVR).filter(filtro).all()
    return listaCE, [ovr for ovr in ovrs]


def get_ovr_empresa(session, cnpj: str,
                    datainicio: datetime = None,
                    datafim: datetime = None) -> List[OVR]:
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos.')
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


def get_flags(session) -> List[Flag]:
    flags = session.query(Flag).all()
    return [flag for flag in flags]


def get_flags_choice(session) -> List[Tuple[int, str]]:
    flags = session.query(Flag).all()
    return [(flag.id, flag.nome) for flag in flags]


def inclui_flag_ovr(session, ovr_id, flag_nome) -> List[Flag]:
    flag = session.query(Flag).filter(
        Flag.nome == flag_nome).one_or_none()
    # logger.info(flag, flag_nome)
    if flag:
        return gerencia_flag_ovr(session, ovr_id,
                                 flag.id,
                                 inclui=True)
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
                            responsavel: str) -> OVR:
    """Atualiza campo responsável na OVR. Gera evento correspondente.

    :param session: Conexão com banco SQLAlchemy
    :param ovr_id: ID da OVR a atribuir responsável
    :param responsavel: CPF do novo responsável
    :return: OVR modificado
    """
    try:
        ovr = get_ovr(session, ovr_id)
        tipoevento = session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == EventoEspecial.Responsavel.value).first()
        if ovr.responsavel_cpf is None:
            responsavel_anterior = 'Nenhum'
        else:
            responsavel_anterior = ovr.responsavel_cpf
        evento_params = {'tipoevento_id': tipoevento.id,
                         'motivo': 'Anterior: ' + responsavel_anterior,
                         'user_name': responsavel,  # Novo Responsável
                         'ovr_id': ovr.id
                         }
        evento = gera_eventoovr(session, evento_params, commit=False)
        ovr.responsavel_cpf = responsavel  # Novo responsavel
        session.add(evento)
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return ovr


def informa_lavratura_auto(session, ovr_id: int,
                           responsavel: str) -> OVR:
    """Atualiza campo responsável na OVR. Gera evento correspondente.

    :param session: Conexão com banco SQLAlchemy
    :param ovr_id: ID da OVR a atribuir responsável
    :param responsavel: CPF do novo responsável
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
                         'user_name': responsavel,  # Novo Responsável
                         'ovr_id': ovr.id
                         }
        evento = gera_eventoovr(session, evento_params, commit=False)
        ovr.responsavel_cpf = responsavel  # Novo responsavel
        session.add(evento)
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return ovr


def gera_eventoovr(session, params: dict, commit=True, user_name=None) -> EventoOVR:
    evento = EventoOVR()
    for key, value in params.items():
        setattr(evento, key, value)
    if user_name:
        evento.user_name = user_name
    tipoevento = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.id == int(evento.tipoevento_id)
    ).one()
    evento.fase = tipoevento.fase
    try:
        ovr = get_ovr(session, evento.ovr_id)
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


def desfaz_ultimo_eventoovr(session, ovr_id: int) -> EventoOVR:
    evento_anterior = None
    ovr = get_ovr(session, ovr_id)
    ultimo_evento = ovr.historico[len(ovr.historico) - 1]
    if ultimo_evento.tipoevento.eventoespecial is not None:
        raise Exception('Este Evento não pode ser desfeito!!')
    if len(ovr.historico) > 1:
        evento_anterior = ovr.historico[len(ovr.historico) - 2]
    try:
        session.delete(ultimo_evento)
        if evento_anterior:
            ovr.fase = evento_anterior.fase
            ovr.tipoevento_id = evento_anterior.tipoevento_id
        else:
            ovr.fase = 0
            ovr.tipoevento_id = None
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err


def gera_processoovr(session, params) -> ProcessoOVR:
    return gera_objeto(ProcessoOVR(),
                       session, params)


def cadastra_tgovr(session, params, user_name: str) -> TGOVR:
    usuario = get_usuario_logado(session, user_name)
    tgovr = get_tgovr(session, params.get('id'))
    if tgovr.ovr_id is not None:
        ovr = get_ovr(session, tgovr.ovr_id)
    else:
        ovr = get_ovr(session, params.get('ovr_id'))
    if ovr and ovr.fase > 2:
        raise EBloqueado()
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
        evento = gera_eventoovr(session, evento_params, commit=False)
        session.add(evento)
    return gera_objeto(tgovr,
                       session, params)


def lista_tgovr(session, ovr_id) -> List[TGOVR]:
    try:
        ovr_id = int(ovr_id)
    except (ValueError, TypeError):
        return []
    return session.query(TGOVR).filter(TGOVR.ovr_id == ovr_id).all()


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
    print(total_qtde, total_valor)
    session.add(tg)
    session.commit()


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

def get_usuarios_setores(session, setores) -> List[Tuple[str, str]]:
    usuarios = session.query(Usuario).filter(Usuario.setor_id.in_(setores)).all()
    usuarios_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(usuarios_list, key=lambda x: x[1])


def get_afrfb(session) -> Usuario:
    # TODO: Filtrar Usuários do Setor/ Unidade / AFRFB ???
    return get_usuarios(session)


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


def get_setores(session) -> List[Tuple[str, str]]:
    setores = session.query(Setor).all()
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
    ('descricao', ['Descrição', 'TIPO']),
    ('ncm', ['Código NCM', 'NCM']),
    ('contramarca', ['Marca', 'MARCA']),
    ('modelo', ['Modelo', 'MODELO']),
    ('unidadedemedida', ['Unid. Medida', 'UNIDADE']),
    ('procedencia', ['País Procedência', '*****']),  # Não utilizado ainda
    ('origem', ['País Origem', '***']),  # Não utilizado ainda
    ('moeda', ['Moeda', '****']),  # Não utilizado ainda
    ('qtde', ['Quantidade', 'QUANTIDADE']),
    ('valor', ['Valor Unitário', 'VALOR']),
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


def muda_chaves(original: dict) -> dict:
    new_dict = {}
    print(original)
    for key, alternative_keys in de_para.items():
        for alternative_key in alternative_keys:
            if original.get(alternative_key):
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
    elif '.xls' in lfilename:
        df = pd.read_excel(afile)
    elif '.ods' in lfilename:
        df = pd.read_excel(afile, engine='odf')
    else:
        raise Exception('Extensão de arquivo desconhecida! Conheço .csv, .ods e .xls')
    # print(df.head())
    df = df.replace({np.nan: None})
    alertas = dict()
    try:
        for index, original_row in df.iterrows():
            row = muda_chaves(original_row)
            if row.get('descricao') is None:
                logger.info('Abortando linha {} da planilha {}'
                            'devido descrição vazia'.format(index, lfilename))
                continue
            numero = row.get('numero')
            if numero:
                itemtg = get_itemtg_numero(session, tg, numero)
            else:
                itemtg = get_itemtg_descricao_qtde_modelo(
                    session, tg,
                    row['descricao'], row['qtde'], row.get('modelo'))
                itemtg.numero = index
            itemtg.tg_id = tg.id
            itemtg.descricao = row['descricao']
            itemtg.qtde = row['qtde']
            itemtg.unidadedemedida = Enumerado.index_unidadeMedida(row['unidadedemedida'])
            itemtg.modelo = row.get('modelo')
            itemtg.contramarca = row.get('marca')
            ncm = row.get('ncm')
            if ncm:
                itemtg.ncm = ncm
            else:
                if alertas.get('ncm') is None:
                    alertas['ncm'] = 'Campo ncm ({}) não encontrado.'. \
                        format(de_para.get('ncm'))
            valor = row.get('valor')
            if valor:
                itemtg.valor = valor
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
            medicao = result_proxy.scalar()
            print(medicao, type(medicao))
            key_result.resultado = medicao
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
