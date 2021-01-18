import sys
import mongomock
from ajnaapi.recintosapi import models as recintosapi_models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bhadrasana.models import Setor, Usuario
from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags, create_marcas
from bhadrasana.models.rvf import create_infracoes
from bhadrasana.routes.admin import admin_app
from bhadrasana.routes.ovr import ovr_app
from bhadrasana.routes.ovr2 import ovr2_app
from bhadrasana.routes.risco import risco_app
from bhadrasana.routes.rvf import rvf_app
from bhadrasana.views import app
from ajna_commons.flask.user import DBUser
import ajna_commons.flask.login as login_ajna
import virasana.integracao.mercante.mercantealchemy as mercante
import bhadrasana.models.laudo as laudo
from mongomock.gridfs import enable_gridfs_integration

sys.path.append('.')

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
enable_gridfs_integration()
mongodb = mongomock.MongoClient()

SECRET = 'teste'


def configure_app(app, sqlsession, mongodb):
    """Configurações gerais e de Banco de Dados da Aplicação."""
    app.config['DEBUG'] = False
    app.secret_key = SECRET
    app.config['SECRET_KEY'] = SECRET
    app.config['SESSION_TYPE'] = 'filesystem'
    login_ajna.configure(app)
    # Aceitar qualquer login
    DBUser.dbsession = None
    app.config['dbsession'] = sqlsession
    app.config['mongodb'] = mongodb['test']
    app.config['mongo_risco'] = mongodb['risco']
    return app


"""
Divisão:    God Save the Queen
Chefe:      mycroft senha m5
Equipe:     221B Baker Street
Chefe:      holmes senha sherlock
Membros:    watson senha dr
            adler senha irene
Equipe: Scotland Yard
Chefe:         lestrade senha inspetor
Membros:       macdonald senha inspetor
"""


def create_setores(session):
    setores = [(1, 'God Save the Queen', None),
               (2, '221b', 1),
               (3, 'SY', 1)]
    for linha in setores:
        setor = Setor()
        setor.id = linha[0]
        setor.nome = linha[1]
        setor.pai_id = linha[2]
        session.add(setor)
    session.commit()


def create_usuarios(session):
    usuarios = [('mycroft', 'm5', 1),
                ('holmes', 'sherlock', 2),
                ('watson', 'dr', 2),
                ('adler', 'irene', 2),
                ('lestrade', 'inspetor', 3),
                ('macdonald', 'inspetor', 3),
                ('ivan', 'ivan', 3)
                ]
    for linha in usuarios:
        usuario = Usuario()
        usuario.cpf = linha[0]
        usuario.nome = linha[0]
        usuario.setor_id = linha[2]
        session.add(usuario)
    session.commit()


def create_tables(engine, session):
    drop_tables(engine)
    metadata.create_all(engine)
    create_tiposevento(session)
    create_tiposprocesso(session)
    create_flags(session)
    create_marcas(session)
    create_infracoes(session)
    mercante.metadata.create_all(engine, [
        mercante.metadata.tables['itensresumo'],
        mercante.metadata.tables['ncmitemresumo'],
        mercante.metadata.tables['conhecimentosresumo']
    ])
    recintosapi_models.Base.metadata.create_all(engine)
    laudo.metadata.create_all(engine, [
        laudo.metadata.tables['laudo_empresas'],
    ])


def drop_tables(engine):
    metadata.drop_all(engine)
    mercante.metadata.drop_all(engine, [
        mercante.metadata.tables['itensresumo'],
        mercante.metadata.tables['ncmitemresumo'],
        mercante.metadata.tables['conhecimentosresumo']
    ])


create_tables(engine, session)
create_setores(session)
create_usuarios(session)
configure_app(app, session, mongodb)
risco_app(app)
rvf_app(app)
ovr_app(app)
ovr2_app(app)
admin_app(app, session)
