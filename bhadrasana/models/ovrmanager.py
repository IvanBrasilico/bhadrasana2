import datetime

from ajna_commons.flask.log import logger
from bhadrasana.models.ovr import OVR, EventoOVR, TipoEventoOVR, ProcessoOVR, TipoProcessoOVR
from sqlalchemy import and_

tipoStatusOVR = [
    'Aguardando distribuicão',
    'Em verificação física',
    'Aguardando Medida Judicial',
    'Aguardando Providência de Outro Setor',
    'Aguardando Laudo Técnico',
    'Aguardando Laudo de Marcas'
    'Aguardando Saneamento',
    'Recebimento de Saneamento',
    'Intimação/Notificação',
    'Intimação Não Respondida',
    'Retificação do Termo de Guarda'
]

faseOVR = [
    'Iniciada',
    'Ativa',
    'Suspensa',
    'Concluída',
    'Arquivada'
]

tipoProcesso = [
    'Perdimento',
    'Crédito',
    'Sanção',
    'RFFP',
    'Dossiê'
]


class Enumerado:

    @classmethod
    def get_tipo(cls, listatipo: list, id: int = None):
        if id:
            return listatipo[id]
        else:
            return [(id, item) for id, item in enumerate(listatipo)]

    @classmethod
    def faseOVR(cls, id=None):
        return cls.get_tipo(faseOVR, id)

    @classmethod
    def tipoProcesso(cls, id=None):
        return cls.get_tipo(tipoProcesso, id)


def get_tipos_evento(session):
    tiposeventos = session.query(TipoEventoOVR).all()
    return [(tipo.id, tipo.nome) for tipo in tiposeventos]

def get_tipos_processo(session):
    tiposprocesso = session.query(TipoProcessoOVR).all()
    return [(tipo.id, tipo.descricao) for tipo in tiposprocesso]


def cadastra_ovr(session, params):
    ovr = get_ovr(session, params.get('id'))
    for key, value in params.items():
        setattr(ovr, key, value)
    data = params.get('adata', '')
    hora = params.get('ahora', '')
    try:
        if isinstance(data, str):
            data = datetime.strptime(data, '%Y-%m-%d')
    except:
        data = datetime.date.today()
    try:
        if isinstance(hora, str):
            hora = datetime.strptime(data, '%H:%M')
    except:
        hora = datetime.datetime.now().time()
    ovr.datahora = datetime.datetime.combine(data, hora)
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
    if pfiltro.get('datafim'):
        filtro = and_(OVR.datahora <= pfiltro.get('datafim'), filtro)
    if pfiltro.get('numeroCEmercante'):
        filtro = and_(OVR.numeroCEmercante.ilike(pfiltro.get('numeroCEmercante')),
                      filtro)
    if pfiltro.get('numero'):
        filtro = and_(OVR.numero.ilike(pfiltro.get('numero')), filtro)
    if pfiltro.get('status') and pfiltro.get('status') != 'None':
        filtro = and_(OVR.status == int(pfiltro.get('status')), filtro)
    if pfiltro.get('fase'):
        filtro = and_(OVR.fase == int(pfiltro.get('fase')), filtro)
    ovrs = session.query(OVR).filter(filtro).all()
    logger.info(str(pfiltro))
    logger.info(str(filtro))
    return [ovr for ovr in ovrs]


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


def gera_objeto(object, session, params):
    for key, value in params.items():
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
