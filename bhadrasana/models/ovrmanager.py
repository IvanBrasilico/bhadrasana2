from datetime import timedelta, datetime
from typing import List, Tuple

import pandas as pd
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from ajna_commons.flask.log import logger
from bhadrasana.models import Usuario, Setor, EBloqueado
from bhadrasana.models import handle_datahora, ESomenteMesmoUsuario, gera_objeto, \
    get_usuario_logado
from bhadrasana.models.ovr import OVR, EventoOVR, TipoEventoOVR, ProcessoOVR, \
    TipoProcessoOVR, ItemTG, Recinto, TGOVR, Marca, Enumerado, TipoMercadoria, \
    EventoEspecial, Flag, Relatorio


def get_recintos(session) -> List[Tuple[int, str]]:
    recintos = session.query(Recinto).all()
    recintos_list = [(recinto.id, recinto.nome) for recinto in recintos]
    return sorted(recintos_list, key=lambda x: x[1])


def get_tipos_evento(session) -> List[Tuple[int, str]]:
    tiposeventos = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.eventoespecial.is_(None)).order_by(
        TipoEventoOVR.nome
    ).all()
    print(tiposeventos)
    return [(tipo.id, tipo.nome) for tipo in tiposeventos]


def get_tipos_processo(session):
    tiposprocesso = session.query(TipoProcessoOVR).all()
    return [(tipo.id, tipo.descricao) for tipo in tiposprocesso]


def get_relatorios(session):
    relatorios = session.query(Relatorio).order_by(Relatorio.nome).all()
    return [(relatorio.id, relatorio.nome) for relatorio in relatorios]


def get_relatorio(session, relatorio_id: int):
    return session.query(Relatorio).filter(Relatorio.id == relatorio_id).one_or_none()


def executa_relatorio(session, user_name: str, relatorio: Relatorio,
                      data_inicial: datetime, data_final: datetime,
                      filtrar_setor=False):
    params = {'datainicio': data_inicial, 'datafim': data_final}
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
    if ovr.user_name and ovr.user_name != user_name:
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


def get_ovr_responsavel(session, user_name: str):
    return session.query(OVR).filter(OVR.responsavel_cpf == user_name).all()


def get_ovr_filtro(session, user_name: str, pfiltro: dict = None, filtrar_setor=True):
    filtro = and_()
    if filtrar_setor:
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
            filtro = and_(OVR.numeroCEmercante.ilike(
                pfiltro.get('numeroCEmercante') + '%'),
                filtro)
        if pfiltro.get('numero'):
            filtro = and_(OVR.numero.ilike(pfiltro.get('numero') + '%'), filtro)
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
        if pfiltro.get('numero') and pfiltro.get('numero') != 'None':
            filtro = and_(OVR.numero == int(pfiltro.get('numero')), filtro)

    ovrs = session.query(OVR).filter(filtro).all()
    logger.info(str(pfiltro))
    logger.info(str(filtro))
    return [ovr for ovr in ovrs]


def get_flags(session):
    flags = session.query(Flag).all()
    return [flag for flag in flags]


def get_flags_choice(session):
    flags = session.query(Flag).all()
    return [(flag.id, flag.nome) for flag in flags]


def inclui_flag_ovr(session, ovr_id, flag_nome):
    flag = session.query(Flag).filter(
        Flag.nome == flag_nome).one_or_none()
    if flag:
        return gerencia_flag_ovr(session, ovr_id,
                                 flag.id,
                                 inclui=True)
    return None


def exclui_flag_ovr(session, ovr_id, flag_id):
    return gerencia_flag_ovr(session, ovr_id, flag_id, inclui=False)


def gerencia_flag_ovr(session, ovr_id, flag_id, inclui=True):
    ovr = session.query(OVR).filter(OVR.id == ovr_id).one_or_none()
    if ovr:
        flag = session.query(Flag).filter(
            Flag.id == flag_id).one_or_none()
        if flag:
            if inclui:
                ovr.flags.append(flag)
            else:
                ovr.flags.remove(flag)
            session.commit()
            return ovr.flags
    return None


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
            TipoEventoOVR.eventoespecial == EventoEspecial.Autuação.value).first()
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


def gera_eventoovr(session, params: dict, commit=True) -> EventoOVR:
    evento = EventoOVR()
    for key, value in params.items():
        setattr(evento, key, value)
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


def gera_processoovr(session, params) -> ProcessoOVR:
    return gera_objeto(ProcessoOVR(),
                       session, params)


def cadastra_tgovr(session, params, user_name: str) -> TGOVR:
    usuario = get_usuario_logado(session, user_name)
    tgovr = get_tgovr(session, params.get('id'))
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


def lista_tgovr(session, ovr_id):
    try:
        ovr_id = int(ovr_id)
    except (ValueError, TypeError):
        return None
    return session.query(TGOVR).filter(TGOVR.ovr_id == ovr_id).all()


def get_tgovr(session, tg_id: int = None):
    if tg_id is None or tg_id == 'None':
        tgovr = TGOVR()
        print('Criando TGOVR zerado...')
        return tgovr
    return session.query(TGOVR).filter(TGOVR.id == tg_id).one_or_none()


def cadastra_itemtg(session, params):
    item_tg = get_itemtg(session, params.get('id'))
    return gera_objeto(item_tg,
                       session, params)


def lista_itemtg(session, tg_id):
    try:
        tg_id = int(tg_id)
    except (ValueError, TypeError):
        return []
    return session.query(ItemTG).filter(ItemTG.tg_id == tg_id).all()


def get_itemtg(session, itemid: int = None):
    if itemid is None or itemid == 'None':
        itemtg = ItemTG()
        print('Criando ItemTG zerado...')
        return itemtg
    return session.query(ItemTG).filter(ItemTG.id == itemid).one_or_none()


def get_itemtg_numero(session, tg: TGOVR, numero: int) -> ItemTG:
    """Retorna ItemTG do TG e numero passados. Se não existir, retorna ItemTG vazio."""
    itemtg = session.query(ItemTG).filter(ItemTG.tg_id == tg.id).filter(
        ItemTG.ncm == numero).one_or_none()
    if itemtg is None:
        itemtg = ItemTG()
    return itemtg


# TODO: mover Setores e Usuários daqui e do models/ovr para módulos específicos
def get_usuarios(session):
    usuarios = session.query(Usuario).all()
    usuarios_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(usuarios_list, key=lambda x: x[1])

def get_afrfb(session):
    #TODO: Filtrar Usuários do Setor/ Unidade / AFRFB ???
    return get_usuarios(session)


def usuario_index(usuarios: list, pcpf: str) -> int:
    """Percorre a lista e retorna o índice do cpf ou -1

    :param usuarios: lista [cpf, nome] conforme get_usuarios
    :param pcpf: cpf do usuário atual / a pesquisar
    """
    index = -1
    pcpf = pcpf.strip()
    for ind, tuple in enumerate(usuarios):
        if pcpf == tuple[0].strip():
            index = ind
            break
    return index


def get_setores_filhos(session, setor: Setor) -> list:
    return session.query(Setor).filter(Setor.pai_id == setor.id).all()


def get_setores_filhos_recursivo(session, setor: Setor) -> list:
    setores_total = []
    setores_filhos = get_setores_filhos(session, setor)
    print([setor.nome for setor in setores_filhos])
    setores_total.extend(setores_filhos)
    for setor in setores_filhos:
        setores_filhos = get_setores_filhos_recursivo(session, setor)
        setores_total.extend(setores_filhos)

    return setores_total


def get_setores(session) -> list:
    setores = session.query(Setor).all()
    setores_list = [(setor.id, setor.nome) for setor in setores]
    return sorted(setores_list, key=lambda x: x[1])


def get_setores_usuario(session, usuario: Usuario) -> list:
    setores = [usuario.setor]
    setores_filhos = get_setores_filhos_recursivo(session, usuario.setor)
    setores.extend(setores_filhos)
    return setores
    # setores_list = [(setor.id, setor.nome) for setor in setores]
    # return sorted(setores_list, key=lambda x: x[1])


def get_setores_cpf(session, cpf_usuario: str) -> list:
    usuario = session.query(Usuario).filter(Usuario.cpf == cpf_usuario).one_or_none()
    print(usuario, type(usuario))
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


def get_tiposmercadoria_choice(session):
    tipos = session.query(TipoMercadoria).all()
    return [(tipo.id, tipo.nome) for tipo in tipos]


def importa_planilha(session, tg: TGOVR, afile):
    if '.csv' in afile.filename:
        df = pd.read_csv(afile, sep=';',
                         header=1, encoding='windows-1252')
    elif '.xls' in afile.filename:
        df = pd.read_excel(afile)
    elif '.ods' in afile.filename:
        df = pd.read_excel(afile, engine='ods')
    else:
        raise Exception('Extensão de arquivo desconhecida! Conheço .csv, .ods e .xls')
    print(df.head())
    try:
        for index, row in df.iterrows():
            itemtg = get_itemtg_numero(session, tg, row['numero'])
            itemtg.tg_id = tg.id
            itemtg.descricao = row['descricao']
            itemtg.qtde = row['qtde']
            itemtg.unidadedemedida = Enumerado.index_unidadeMedida(row['unidadedemedida'])
            ncm = row.get['ncm']
            if ncm:
                itemtg.ncm = ncm
            valor = row.get['valor']
            if valor:
                itemtg.valor = valor
            session.add(itemtg)
        session.commit()
    except KeyError as err:
        raise KeyError('Campo não encontrado. Campos obrigatórios na planilha são '
                       'numero, descricao, qtde e unidademedida. Opcionais ncm e valor.'
                       'Erro: %s' % str(err))


def exporta_planilhaovr(session: Session, user_name: str, filename: str):
    """
    Gera tabelão de OVRs (Tabela Gerencial EQODI) com pivot table

    :param session: Conexão SQLAlchemy ao Banco de Dados
    :param user_name: Nome do Usuário
    :param filename: Nome do arquivo a gerar com caminho completo
    """
    # FIXME: Bandit está erroneamente identificando como sql injection abaixo.
    # Ignorando...
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
