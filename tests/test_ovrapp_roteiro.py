import sys
import unittest

import mongomock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import virasana.integracao.mercante.mercantealchemy as mercante
from bhadrasana.routes.ovr import ovr_app
from bhadrasana.routes.risco import risco_app
from bhadrasana.routes.rvf import rvf_app

sys.path.append('.')

import ajna_commons.flask.login as login_ajna
from ajna_commons.flask.user import DBUser
from bhadrasana.views import app
from bhadrasana.models import Setor, Usuario
from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags

from test_base import BaseTestCase

SECRET = 'teste'


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
    mercante.metadata.create_all(engine, [
        mercante.metadata.tables['itensresumo'],
        mercante.metadata.tables['ncmitemresumo'],
        mercante.metadata.tables['conhecimentosresumo']
    ])


def drop_tables(engine):
    metadata.drop_all(engine)
    mercante.metadata.drop_all(engine, [
        mercante.metadata.tables['itensresumo'],
        mercante.metadata.tables['ncmitemresumo'],
        mercante.metadata.tables['conhecimentosresumo']
    ])


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
    app.config['mongodb'] = mongodb
    return app

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
mongodb = mongomock.MongoClient()

try:
    create_tables(engine, session)
    configure_app(app, session, mongodb)
    risco_app(app)
    rvf_app(app)
    ovr_app(app)
except:
    pass

try:
    create_setores(session)
except Exception as err:
    print(err)
    session.rollback()
try:
    create_usuarios(session)
except Exception as err:
    print(err)
    session.rollback()


class OVRAppTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)
        self.app = app.test_client()

    def get_token(self, text):
        token_start = text.find('name="csrf_token" value="')
        text_from_start = text[token_start + 25:]
        token_end = text_from_start.find('/>')
        token_text = text_from_start[:token_end - 1]
        return token_text

    def login(self, username, senha):
        rv = self.app.get('/login')
        assert rv.data is not None
        token_text = self.get_token(str(rv.data))
        rv = self.app.post('/login', data={'csrf_token': token_text,
                                           'username': username,
                                           'senha': senha},
                           follow_redirects=True)

    def test_home(self):
        rv = self.app.get('/')
        assert rv.status_code == 302

    def test_ovr_1(self):
        self.login('ivan', 'ivan')
        recinto = self.create_recinto('Teste OVR')
        usuario = self.create_usuario('123', 'user1')
        self.session.refresh(recinto)
        params = {'numeroCEmercante': 'CE Teste',
                  'recinto_id': recinto.id,
                  'adata': '2020-01-01',
                  'ahora': '13:13'}
        ovr = self.create_OVR(params, '123')
        self.session.refresh(ovr)
        rv = self.app.get('/ovr?id=%s' % ovr.id)
        assert b'CE Teste' in rv.data
        assert rv.status_code == 200

    def get_consulta_container(self, numero):
        rv = self.app.get('/consulta_container')
        assert rv.data is not None
        # print(rv.data)
        token_text = self.get_token(str(rv.data))
        # print(token_text)
        payload = {'csrf_token': token_text, 'numerolote': numero}
        rv = self.app.post('/consulta_container', data=payload)
        # print(rv.data)
        # print(rv.status_code)
        return str(rv.data), rv.status_code

    def test_consulta_conteiner(self):
        ovr1, ovr2 = self.create_OVRs_test_ovrs_container()
        self.login('ivan', 'ivan')
        text, status_code = self.get_consulta_container('1')
        assert status_code == 200
        assert '1234' in text
        text, status_code = self.get_consulta_container('2')
        assert status_code == 200
        assert '1234' in text
        text, status_code = self.get_consulta_container('3')
        assert status_code == 200
        assert '12345' in text
        text, status_code = self.get_consulta_container('4')
        assert status_code == 200
        assert '1234' not in text


    def create_CE_containeres_teste(self):
        ce1 = mercante.Conhecimento()
        ce1.numeroCEmercante = '152005079623267'
        item1 = mercante.Item()
        item1.numeroCEmercante = '152005079623267'
        item1.codigoConteiner = '1'
        item2 = mercante.Item()
        item2.numeroCEmercante = '152005079623267'
        item2.codigoConteiner = '2'
        self.session.add(ce1)
        self.session.add(item1)
        self.session.add(item2)
        self.session.commit()


    def test_a1_criaFichaCE(self):
        recinto = self.create_recinto('Londres')
        self.session.refresh(recinto)
        self.recinto_id = recinto.id
        self.login('holmes', 'holmes')
        rv = self.app.get('/ovr')
        token_text = self.get_token(str(rv.data))
        payload = {'csrf_token': token_text,
                   'numeroCEmercante': '152005079623267',
                   'recinto_id': self.recinto_id,
                   'adata': '1859-05-22',
                   'ahora': '22:21'}
        rv = self.app.post('/ovr', data=payload, follow_redirects=True)
        assert b'152005079623267' in rv.data
        assert rv.status_code == 200

    def test_a2_atribuir_responsabilidade_watson(self):
        self.login('holmes', 'holmes')
        rv = self.app.get('/ovr?id=%s' % 1)
        text = str(rv.data)
        responsavelovr_pos = text.find('action="responsavelovr"')
        responsavelovr_text = text[responsavelovr_pos:]
        token_text = self.get_token(responsavelovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': 1,
                   'responsavel': 'watson'}
        rv = self.app.post('/responsavelovr', data=payload, follow_redirects=True)
        assert b'watson' in rv.data

    def test_a3_programa_container(self):
        self.create_CE_containeres_teste()
        self.login('holmes', 'holmes')
        rv = self.app.get('/ovr?id=%s' % 1)
        text = str(rv.data)


if __name__ == '__main__':
    unittest.main()
