import datetime

from bhadrasana.models.fma import FMA, HistoricoFMA
from sqlalchemy import and_

tipoStatusFMA = [
    'Aguardando distribuicão',
    'Afixação de Edital de Abandono',
    'Aguardando Medida Judicial',
    'Aguardando Providência de Outro Setor',
    'Devolução de FMA',
    'Devolução de RMA',
    'Intimação/Notificação',
    'Intimação Não Respondida',
    'Intimação Respondida',
    'Laudo/Labor Atendido',
    'Liberação para Distribuição',
    'Montagem de Processo',
    'Preparação para Intimar/Notificar',
    'Retificação do TG Digitado',
    'Solic. Laudo Técnico/Labor'
]

faseOVR = [
    'Iniciada',
    'Ativa',
    'Suspensa',
    'Arquivada'
]


class Enumerado:
    @classmethod
    def tipoStatusFMA(cls, id=None):
        if id:
            return tipoStatusFMA[id]
        else:
            return [(id, item) for id, item in enumerate(tipoStatusFMA)]

    @classmethod
    def faseOVR(cls, id=None):
        if id:
            return faseOVR[id]
        else:
            return [(id, item) for id, item in enumerate(faseOVR)]


def cadastra_fma(session, params):
    fma = get_fma(session, params.get('id'))
    for key, value in params.items():
        setattr(fma, key, value)
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
    fma.datahora = datetime.datetime.combine(data, hora)
    try:
        session.add(fma)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err
        print(fma)

    return fma


def get_fma(session, id: int = None):
    if id is None:
        fma = FMA()
        fma.status = 1
        return fma
    return session.query(FMA).filter(FMA.id == id).one_or_none()


def get_fma_filtro(session, pfiltro):
    filtro = and_()
    if pfiltro.get('datainicio'):
        filtro = and_(FMA.datahora >= pfiltro.get('datainicio'))
    if pfiltro.get('datafim'):
        filtro = and_(FMA.datahora <= pfiltro.get('datafim'))
    if pfiltro.get('numeroCEmercante'):
        filtro = and_(FMA.numeroCEmercante.ilike(pfiltro.get('numeroCEmercante')),
                      filtro)
    if pfiltro.get('numero'):
        filtro = and_(FMA.numero.ilike(pfiltro.get('numero')), filtro)
    # if pfiltro.get('status'):
    #    filtro = and_(FMA.status == pfiltro.get('status'), filtro)
    fmas = session.query(FMA).filter(filtro).all()
    return [fma for fma in fmas]


def fase_status(status_id):
    """Retorna fase correspondente ao status"""
    if status_id in (2, 3, 14):
        return 2 # Suspensa
    return 1 # Ativa



def movimenta_fma(session, params):
    historicofma = HistoricoFMA()
    for key, value in params.items():
        setattr(historicofma, key, value)
    historicofma.fase = fase_status(historicofma.status)
    try:
        fma = get_fma(session, historicofma.fma_id)
        fma.status = historicofma.status
        fma.fase = historicofma.fase
        session.add(fma)
        session.add(historicofma)
        session.commit()
    except Exception as err:
        session.rollback()
        raise err

    return historicofma
