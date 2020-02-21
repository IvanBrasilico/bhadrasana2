from datetime import timedelta

from ajna_commons.flask.log import logger
from bhadrasana.models import handle_datahora
from bhadrasana.models.ovr import OVR, EventoOVR, TipoEventoOVR, ProcessoOVR, \
    TipoProcessoOVR, ItemTG, Recinto, Usuario
from sqlalchemy import and_


def get_usuarios(session, user_name: str=None):
    usuarios = session.query(Usuario).all()
    recintos_list = [(usuario.cpf, usuario.nome) for usuario in usuarios]
    return sorted(recintos_list, key=lambda x: x[1])


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


def cadastra_ovr(session, params):
    ovr = get_ovr(session, params.get('id'))
    for key, value in params.items():
        if value and value != 'None':
            print(key, value)
            setattr(ovr, key, value)
    ovr.datahora = handle_datahora(params)
    try:
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
        print(ovr)
    return ovr


def get_ovr(session, id: int = None):
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
    if pfiltro.get('fase'):
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


def atribui_responsavel_ovr(session, params):
    try:
        ovr = get_ovr(session, params.get('ovr_id'))
        evento = EventoOVR()
        evento.tipoevento_id = 16
        evento.motivo = ovr.responsavel_cpf # Responsável anterior
        evento.ovr_id = ovr.id
        ovr.responsavel_cpf = params.get('responsavel')
        evento.user_name = ovr.responsavel_cpf
        session.add(evento)
        session.add(ovr)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return ovr


def gera_eventoovr(session, params):
    evento = EventoOVR()
    for key, value in params.items():
        print(key, value)
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
        session.commit()
    except Exception as err:
        session.rollback()
        raise err

    return evento


def gera_processoovr(session, params):
    return gera_objeto(ProcessoOVR(),
                       session, params)


def cadastra_itemtg(session, params):
    item_tg = get_itemtg(session, params.get('id'))
    return gera_objeto(item_tg,
                       session, params)


def lista_itemtg(session, ovr_id):
    try:
        ovr_id = int(ovr_id)
    except (ValueError, TypeError):
        return None
    return session.query(ItemTG).filter(ItemTG.ovr_id == ovr_id).all()


def get_itemtg(session, id: int = None):
    if id is None or id == 'None':
        itemtg = ItemTG()
        print('Criando ItemTG zerado...')
        return itemtg
    return session.query(ItemTG).filter(ItemTG.id == id).one_or_none()


def gera_objeto(object, session, params):
    for key, value in params.items():
        if value and value != 'None':
            setattr(object, key, value)
    try:
        session.add(object)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
    return object


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
