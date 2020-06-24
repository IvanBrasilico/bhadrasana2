import datetime

from sqlalchemy import Column, func, VARCHAR, CHAR, ForeignKey, Integer
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session, sessionmaker

from ajna_commons.flask.conf import SQL_URI
from ajna_commons.flask.log import logger

engine = create_engine(SQL_URI, pool_recycle=600)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class BaseDumpable(Base):
    __abstract__ = True

    def dump(self, exclude=None):
        dump = dict([(k, v) for k, v in vars(self).items() if not k.startswith('_')])
        if exclude:
            for key in exclude:
                if dump.get(key):
                    dump.pop(key)
        return dump


class ENaoAutorizado(Exception):
    def __init__(self, msg='Usuário não autorizado.'):
        Exception.__init__(self, msg)


class ESomenteMesmoUsuario(Exception):
    def __init__(self):
        Exception.__init__(self, 'Somente o Usuário que cadastra pode editar.')


class EBloqueado(Exception):
    def __init__(self):
        Exception.__init__(self, 'Bloqueado para edição.'
                                 'Status/fase não permite alteração.')


perfilAcesso = (
    'Consulta',
    'Operador',
    'Supervisor',
    'Cadastrador'
)


class myEnum:

    @classmethod
    def get_tipo(cls, listatipo: list, id: int = None):
        if (id is not None) and isinstance(id, int):
            try:
                return listatipo[id]
            except IndexError:
                raise IndexError('Item %s não encontrado em %s' % (id, listatipo))
        else:
            return [(id, item) for id, item in enumerate(listatipo, 0)]

    @classmethod
    def get_id(cls, listatipo: list, descricao: str):
        try:
            # logger.info('****' + str(listatipo.index(descricao)))
            return listatipo.index(descricao)
        except ValueError:
            raise ValueError('Item %s não encontrado em %s' % (id, listatipo))


class Enumerado(myEnum):

    @classmethod
    def perfilAcesso(cls, id: int = None):
        return cls.get_tipo(perfilAcesso, id)

    @classmethod
    def perfilAcesso_id(cls, descricao: str):
        return cls.get_id(perfilAcesso, descricao)


class BaseRastreavel(Base):
    __abstract__ = True
    user_name = Column(VARCHAR(14), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user_name is None and kwargs.get('user_name'):
            self.user_name = kwargs['user_name']


class Setor(Base):
    __tablename__ = 'ovr_setores'
    id = Column(CHAR(15), primary_key=True)
    nome = Column(CHAR(50), index=True)
    pai_id = Column(CHAR(15), ForeignKey('ovr_setores.id'))
    pai = relationship('Setor')

    def __str__(self):
        return '{} - {}'.format(self.id, self.nome)


class Usuario(Base):
    __tablename__ = 'ovr_usuarios'
    cpf = Column(CHAR(15), primary_key=True)
    nome = Column(CHAR(50), index=True)
    telegram = Column(CHAR(50), index=True)
    setor_id = Column(CHAR(15), ForeignKey('ovr_setores.id'))
    setor = relationship('Setor')
    perfis = relationship('PerfilUsuario', back_populates='usuario')

    def __str__(self):
        return '{} - {}'.format(self.cpf, self.nome)


class PerfilUsuario(Base):
    __tablename__ = 'ovr_perfis_usuarios'
    id = Column(Integer().with_variant(Integer, 'sqlite'), primary_key=True)
    cpf = Column(CHAR(15), ForeignKey('ovr_usuarios.cpf'))
    usuario = relationship('Usuario')
    perfil = Column(Integer(), index=True, default=0)

    @property
    def perfil_descricao(self):
        return Enumerado.get_tipo(perfilAcesso, self.perfil)

    def __str__(self):
        return '{} - {}'.format(self.cpf, self.perfil_descricao)


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
        hora = datetime.datetime.strptime(hora, '%H:%M').time()
    except Exception as err:
        hora = datetime.datetime.now().time()
        logger.error('handle_datahora: %s' % err)
    return datetime.datetime.combine(data, hora)


def get_usuario_logado(session, user_name: str) -> Usuario:
    if user_name is None:
        raise KeyError('Usuário não foi informado!')
    usuario = session.query(Usuario).filter(
        Usuario.cpf == user_name).one_or_none()
    if not usuario:
        raise ENaoAutorizado('Usuário %s inválido ou não informado.' % user_name +
                             'Somente Usuários habilitados podem acessar.')
    return usuario


def get_usuario_telegram(session, telegram: str) -> Usuario:
    return session.query(Usuario).filter(
        Usuario.telegram == telegram).one_or_none()


def get_usuario(session, user_name: str) -> Usuario:
    return session.query(Usuario).filter(
        Usuario.cpf == user_name).one_or_none()


def get_perfisusuario(session, cpf: str) -> list:
    return session.query(PerfilUsuario).filter(
        PerfilUsuario.cpf == cpf).all()


def usuario_tem_perfil(session, cpf: str, perfil: int) -> PerfilUsuario:
    operfil = session.query(PerfilUsuario).filter(
        PerfilUsuario.cpf == cpf).filter(
        PerfilUsuario.perfil == perfil).one_or_none()
    # logger.info('***********' + cpf + ' ' + str(perfil))
    return operfil is not None


def gera_objeto(instance: object, session, params):
    # get_usuario_logado(session, params)
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


if __name__ == '__main__':
    import sys

    sys.path.append('.')
    sys.path.append('../ajna_docs/commons')
    sys.path.append('../virasana')
    from ajna_commons.flask.conf import SQL_URI

    engine = create_engine(SQL_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    # Sair por segurança. Comentar linha abaixo para funcionar
    # sys.exit(0)
    # Base.metadata.drop_all(engine, [
    # metadata.tables['ovr_perfisusuarios'], ])
    Base.metadata.create_all(engine, [
        Base.metadata.tables['ovr_perfis_usuarios']
    ])
