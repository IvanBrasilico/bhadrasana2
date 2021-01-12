import sys

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')

import virasana.integracao.mercante.mercantealchemy as mercante
from ajnaapi.recintosapi import models as recintosapi_models
from bhadrasana.models.rvf import create_infracoes

sys.path.append('.')

from tests.app_creator import app, engine, session
from bhadrasana.models import Setor, Usuario
from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags, create_marcas

from .test_base import BaseTestCase

SECRET = 'teste'

"""
Divisão:    Divisão 01
Chefe:      tiberio senha tiberio

Equipe:     Equipe 01
Chefe:      adriano senha adriano
Membros:    usuario1 senha usuario1
            usuario2 senha usuario2
            
Equipe:     Equipe 02
Chefe:      kanoo senha kanoo
Membros:    usuario3 senha usuario3
            usuario4 senha usuario4
            
"""


def create_setores(session):
    setores = [(40, 'Divisão 01', None),
               (50, 'Equipe 01', 40),
               (60, 'Equipe 02', 40)]
    for linha in setores:
        setor = Setor()
        setor.id = linha[0]
        setor.nome = linha[1]
        setor.pai_id = linha[2]
        session.add(setor)
    session.commit()


def create_usuarios(session):
    usuarios = [('tiberio', 'tiberio', 40),
                ('adriano', 'adriano', 50),
                ('usuario1', 'usuario1', 50),
                ('usuario2', 'usuario2', 50),
                ('kanoo', 'kanoo', 60),
                ('usuario3', 'usuario3', 60),
                ('usuario4', 'usuario4', 60)
                ]
    for linha in usuarios:
        usuario = Usuario()
        usuario.cpf = linha[0]
        usuario.nome = linha[0]
        usuario.setor_id = linha[2]
        session.add(usuario)
    session.commit()

create_setores(session)
create_usuarios(session)

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
        # print('>>>>>>>>>>>>>>', rv, rv.data, rv.status_code)
        # with open('saida_login.html', 'w') as fileout:
        #     fileout.write(str(rv.data))

    def test_home(self):
        rv = self.app.get('/')
        assert rv.status_code == 302

    def test_ovr_1(self):
        self.login('adriano', 'adriano')
        recinto = self.create_recinto('Teste OVR')
        # usuario = self.create_usuario('123', 'user1')
        self.session.refresh(recinto)
        params = {'numeroCEmercante': 'CE Teste',
                  'recinto_id': recinto.id,
                  'adata': '2020-01-01',
                  'ahora': '13:13'}
        ovr = self.create_OVR(params, 'adriano')
        self.session.refresh(ovr)
        rv = self.app.get('/ovr?id=%s' % ovr.id)
        # with open('saida_ovr1.html', 'w') as fileout:
        #     fileout.write(str(rv.data))
        assert b'CE Teste' in rv.data
        assert rv.status_code == 200
