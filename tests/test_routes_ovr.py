import sys

from bs4 import BeautifulSoup

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')

import virasana.integracao.mercante.mercantealchemy as mercante
from ajnaapi.recintosapi import models as recintosapi_models
from bhadrasana.models.rvf import create_infracoes

sys.path.append('.')

from tests.app_creator import app, engine, session
from bhadrasana.models import Setor, Usuario, PerfilUsuario, get_perfisusuario
from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags, create_marcas

from .test_base import BaseTestCase

SECRET = 'teste'

"""
Divisão:    Divisão Teste
Chefe:      geraldo senha geraldo

Equipe:     Equipe A
Chefe:      marcelo senha marcelo
Membros:    usuario1 senha usuario1
            usuario2 senha usuario2
            
Equipe:     Equipe B
Chefe:      kanoo senha kanoo
Membros:    usuario3 senha usuario3
            usuario4 senha usuario4
            
"""


def create_setores(session):
    setores = [(40, 'Divisão Teste', None),
               (50, 'Equipe A', 40),
               (60, 'Equipe B', 40)]
    for linha in setores:
        setor = Setor()
        setor.id = linha[0]
        setor.nome = linha[1]
        setor.pai_id = linha[2]
        session.add(setor)
    session.commit()


def create_perfis(session):
    perfis = [(1, 'geraldo', 2),  # Supervisor
              (2, 'marcelo', 2),  # Supervisor
              (3, 'kanoo', 2)]    # Supervisor

    for linha in perfis:
        perfil = PerfilUsuario()
        perfil.id = linha[0]
        perfil.cpf = linha[1]
        perfil.perfil = linha[2]
    session.commit()


def create_usuarios(session):
    usuarios = [('carlos', 'carlos', 40),
                ('erika', 'erika', 50),
                ('usuarioA1', 'usuarioA1', 50),
                ('usuarioA2', 'usuarioA2', 50),
                ('kanoo', 'kanoo', 60),
                ('usuarioB3', 'usuarioB3', 60),
                ('usuarioB4', 'usuarioB4', 60)
                ]
    for linha in usuarios:
        usuario = Usuario()
        usuario.cpf = linha[0]
        usuario.nome = linha[0]
        usuario.setor_id = linha[2]
        # usuario.perfis = linha[3]
        session.add(usuario)
    session.commit()


create_setores(session)
create_perfis(session)
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

    def recupera_perfil(self):
        perfis = get_perfisusuario(self.session, 'erika')

    def test_a01(self):
        # Erika cria uma ficha limpa
        # Atribui responsabilidade para usuarioA1 da sua equipe
        # Verifica fichas do seu setor
        self.login('erika', 'erika')
        recinto = self.create_recinto('Wonderland')
        self.session.refresh(recinto)
        params = {'tipooperacao': 'Mercadoria Abandonada',
                  'numeroCEmercante': 'CE-123456789',
                  'cnjp_fiscalizado': '12345678',
                  'recinto_id': recinto.id,
                  'adata': '2021-01-01',
                  'ahora': '13:15'}
        ovr = self.create_OVR(params, 'erika')
        self.session.refresh(ovr)
        ficha = self.app.get('/ovr?id=%s' % ovr.id)
        # with open('saida_tests.html', 'w') as fileout:
        #     fileout.write(str(rv.data))
        assert ficha.status_code == 200
        assert ovr.tipooperacao == 'Mercadoria Abandonada'
        assert b'CE-123456789' in ficha.data
        assert ovr.fase == 0  # Iniciada
        assert ovr.tipoevento_id == 1  # Aguardando distribuição
        assert ovr.user_name == 'erika'
        assert ovr.cpfauditorresponsavel is None
        assert ovr.setor_id == '50'  # Equipe 01 - Setor do Adriano
        assert ovr.responsavel is None
        ficha = self.app.get('/ovr?id=%s' % ovr.id)
        text = str(ficha.data)
        responsavelovr_pos = text.find('action="responsavelovr"')
        responsavelovr_text = text[responsavelovr_pos:]
        token_text = self.get_token(responsavelovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': ovr.id,
                   'responsavel': 'usuarioA1'}
        ficha = self.app.post('/responsavelovr', data=payload, follow_redirects=True)
        assert b'usuarioA1' in ficha.data
        assert ovr.fase == 1  # Ativa
        assert ovr.tipoevento_id == 13  # Atribuição de responsável
        assert ovr.tipoevento.nome == 'Atribuição de responsável'
        assert ovr.user_name == 'erika'
        assert ovr.cpfauditorresponsavel is None
        assert ovr.setor_id == '50'  # Equipe 01 - Setor do Adriano
        assert ovr.responsavel.nome == 'usuarioA1'
        soup = BeautifulSoup(ficha.data, features='lxml')
        table = soup.find('table', {'id': 'table_eventos'})
        rows = [str(row) for row in table.findAll("tr")]
        assert len(rows) == 2
        ficha_setores = self.app.get('/ovrs_meus_setores')
        with open('saida_tests.html', 'w') as fileout:
            fileout.write(str(ficha_setores.data))
        assert ficha_setores.status_code == 200
        soup = BeautifulSoup(ficha_setores.data, features='lxml')
        table = soup.find('table', {'id': 'minhas_ovrs_table'})
        rows = [str(row) for row in table.findAll("tr")]
        assert len(rows) == 2

