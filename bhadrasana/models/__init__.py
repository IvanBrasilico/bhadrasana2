import datetime

from sqlalchemy import Column, func, VARCHAR
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

from ajna_commons.flask.log import logger

Base = declarative_base()


class ENaoAutorizado(Exception):
    def __init__(self):
        Exception.__init__(self, 'Usuário não autorizado.')


class ESomenteMesmoUsuario(Exception):
    def __init__(self):
        Exception.__init__(self, 'Somente o Usuário que cadastra pode editar.')


class BaseRastreavel(Base):
    __abstract__ = True
    user_name = Column(VARCHAR(14), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user_name is None and kwargs.get('user_name'):
            self.user_name = kwargs['user_name']


def handle_datahora(params):
    data = params.get('adata', '')
    hora = params.get('ahora', '')
    try:
        if isinstance(data, str):
            data = datetime.datetime.strptime(data, '%Y-%m-%d')
    except Exception as err:
        data = datetime.date.today()
        logger.error('handle_datahora: %s' % err)
    try:
        if isinstance(hora, str):
            hora = datetime.datetime.strptime(hora, '%H:%M').time()
    except Exception as err:
        hora = datetime.datetime.now().time()
        logger.error('handle_datahora: %s' % err)
    return datetime.datetime.combine(data, hora)


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
