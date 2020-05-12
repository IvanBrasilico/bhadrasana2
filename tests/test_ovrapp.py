import sys
import unittest

# from flask_testing import TestCase
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
from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags

from test_base import BaseTestCase

SECRET = 'teste'


def create_tables(engine, session):
    metadata.create_all(engine)
    create_tiposevento(session)
    create_tiposprocesso(session)
    create_flags(session)
    mercante.metadata.create_all(engine, [
        mercante.metadata.tables['itensresumo']
    ])


def drop_tables(engine):
    metadata.drop_all(engine)
    mercante.metadata.drop_all(engine, [
        mercante.metadata.tables['itensresumo']
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

configure_app(app, session, mongodb)
risco_app(app)
rvf_app(app)
ovr_app(app)


class OVRAppTestCase(BaseTestCase):

    def setUp(self) -> None:
        create_tables(engine, session)
        super().setUp(session)
        self.app = app.test_client()

    def tearDown(self) -> None:
        drop_tables(engine)

    def get_token(self, text):
        token_start = text.find('name="csrf_token" value="')
        text_from_start = text[token_start + 25:]
        token_end = text_from_start.find('/>')
        token_text = text_from_start[:token_end - 1]
        return token_text

    def login(self):
        rv = self.app.get('/login')
        assert rv.data is not None
        token_text = self.get_token(str(rv.data))
        rv = self.app.post('/login', data={'csrf_token': token_text,
                                           'username': 'ivan',
                                           'senha': 'ivan'},
                           follow_redirects=True)

    def test_home(self):
        rv = self.app.get('/')
        assert rv.status_code == 302

    def test_ovr_1(self):
        self.login()
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
        self.login()
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


if __name__ == '__main__':
    unittest.main()
