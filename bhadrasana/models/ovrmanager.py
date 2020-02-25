from datetime import timedelta

from sqlalchemy import and_

from ajna_commons.flask.log import logger
from bhadrasana.models import handle_datahora
from bhadrasana.models.ovr import OVR, EventoOVR, TipoEventoOVR, ProcessoOVR, \
    TipoProcessoOVR, ItemTG, Recinto, Usuario, TGOVR


def get_usuarios(session, user_name: str = None):
    usuarios = session.query(Usuario).all()
    usuarios_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(usuarios_list, key=lambda x: x[1])


def get_recintos(session):
    recintos = session.query(Recinto).all()
    recintos_list = [(recinto.id, recinto.nome) for recinto in recintos]
    return sorted(recintos_list, key=lambda x: x[1])


def get_tipos_evento(session):
    tiposeventos = session.query(TipoEventoOVR).all()
    return [(tipo.id, tipo.nome) for tipo in tiposeventos]


def get_tipos_processo(session):
    tiposprocesso = session.query(TipoProcessoOVR).all()
    return [(tipo.id, tipo.descricao) for tipo in tiposprocesso]


def cadastra_ovr(session, params: dict) -> OVR:
    ovr = get_ovr(session, params.get('id'))
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
    return session.query(OVR).filter(OVR.id == id).one_or_none()


def get_ovr_filtro(session, pfiltro):
    filtro = and_()
    if pfiltro.get('datainicio'):
        filtro = and_(OVR.datahora >= pfiltro.get('datainicio'), filtro)
    datafim = pfiltro.get('datafim')
    if datafim:
        datafim = datafim + timedelta(days=1)
        filtro = and_(OVR.datahora <= datafim, filtro)
    if pfiltro.get('numeroCEmercante'):
        filtro = and_(OVR.numeroCEmercante.ilike(pfiltro.get('numeroCEmercante')),
                      filtro)
    if pfiltro.get('numero'):
        filtro = and_(OVR.numero.ilike(pfiltro.get('numero')), filtro)
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
                            responsavel: str,
                            id_tipo_evento_atribuicao=16
                            ) -> OVR:
    """Atualiza campo responsável na OVR. Gera evento correspondente.

    :param session: Conexão com banco SQLAlchemy
    :param ovr_id: ID da OVR a atribuir responsável
    :param responsavel: CPF do novo responsável
    :return: OVR modificado
    """
    try:
        ovr = get_ovr(session, ovr_id)
        # TODO: Ver como mapear id_tipoevento de forma melhor
        params = {'tipoevento_id': id_tipo_evento_atribuicao,
                  'motivo': responsavel,  # Novo Responsável
                  'user_name': ovr.responsavel_cpf,  # Responsável anterior
                  'ovr_id': ovr.id
                  }
        evento = gera_eventoovr(session, params, commit=False)
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


def cadastra_tgovr(session, params) -> TGOVR:
    tgovr = get_tgovr(session, params.get('id'))
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


def gera_objeto(instance: object, session, params):
    for key, value in params.items():
        if value is not None and value != 'None':
            setattr(instance, key, value)
    try:
        session.add(instance)
        session.commit()
    except Exception as err:
        session.rollback()
        logger.error('Erro gera_objeto %s: %s' %
                     (instance.__class__.__name__, str(err)))
        logger.error(instance.__dict__)
        raise err
    return instance


def delete_objeto(session, classname, id):
    try:
        klass = globals()[classname]
        instance = session.query(klass).filter(klass.id == id).one_or_none()
        if instance is None:
            return False
        session.delete(instance)
        session.commit()
    except Exception as err:
        session.rollback()
        logger.error(str(err), exc_info=True)
        return False
    return True
