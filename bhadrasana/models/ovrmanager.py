from datetime import timedelta

import pandas as pd
from ajna_commons.flask.log import logger
from bhadrasana.models import Usuario, Setor, EBloqueado
from bhadrasana.models import handle_datahora, ESomenteMesmoUsuario, gera_objeto, \
    get_usuario_logado
from bhadrasana.models.ovr import OVR, EventoOVR, TipoEventoOVR, ProcessoOVR, \
    TipoProcessoOVR, ItemTG, Recinto, TGOVR, Marca, Enumerado, TipoMercadoria, EventoEspecial
from sqlalchemy import and_
from sqlalchemy.orm import Session


def get_recintos(session):
    recintos = session.query(Recinto).all()
    recintos_list = [(recinto.id, recinto.nome) for recinto in recintos]
    return sorted(recintos_list, key=lambda x: x[1])


def get_tipos_evento(session):
    tiposeventos = session.query(TipoEventoOVR).filter(
        TipoEventoOVR.eventoespecial == None).order_by(
        TipoEventoOVR.nome
    ).all()
    return [(tipo.id, tipo.nome) for tipo in tiposeventos]


def get_tipos_processo(session):
    tiposprocesso = session.query(TipoProcessoOVR).all()
    return [(tipo.id, tipo.descricao) for tipo in tiposprocesso]


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


def get_ovr(session, id: int = None) -> OVR:
    if id is None:
        ovr = OVR()
        ovr.status = 1
        return ovr
    ovr = session.query(OVR).filter(OVR.id == id).one_or_none()
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

    ovrs = session.query(OVR).filter(filtro).all()
    logger.info(str(pfiltro))
    logger.info(str(filtro))
    return [ovr for ovr in ovrs]


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
        evento_params = {'tipoevento_id': tipoevento.id,
                  'motivo': responsavel,  # Novo Responsável
                  'user_name': ovr.responsavel_cpf,  # Responsável anterior
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


def get_tgovr(session, id: int = None):
    if id is None or id == 'None':
        tgovr = TGOVR()
        print('Criando TGOVR zerado...')
        return tgovr
    return session.query(TGOVR).filter(TGOVR.id == id).one_or_none()


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


def get_itemtg(session, id: int = None):
    if id is None or id == 'None':
        itemtg = ItemTG()
        print('Criando ItemTG zerado...')
        return itemtg
    return session.query(ItemTG).filter(ItemTG.id == id).one_or_none()


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
    sql_processos = 'SELECT o.id, tipoprocesso_id, p.numero FROM ovr_ovrs o inner join ovr_processos p on o.id = p.ovr_id'
    sql_ovrs = 'SELECT * FROM ovr_ovrs'
    processsos = pd.read_sql(sql_processos, session.get_bind())
    processsos = processsos.pivot(index='id', columns='tipoprocesso_id', values='numero')
    processsos = processsos.fillna('').reset_index()
    ovrs = pd.read_sql(sql_ovrs, session.get_bind())
    df = pd.merge(ovrs, processsos, how='inner', on='id')
    df.to_csv(filename)
