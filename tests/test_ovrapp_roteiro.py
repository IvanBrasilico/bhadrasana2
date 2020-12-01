import sys

sys.path.append('.')
sys.path.insert(0, '../ajna_api')
import unittest
from datetime import datetime, timedelta

import mongomock
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import virasana.integracao.mercante.mercantealchemy as mercante
from ajnaapi.recintosapi import models as recintosapi_models
from bhadrasana.models.ovrmanager import get_ovr
from bhadrasana.models.rvf import create_infracoes
from bhadrasana.routes.admin import admin_app
from bhadrasana.routes.ovr import ovr_app
from bhadrasana.routes.ovr2 import ovr2_app
from bhadrasana.routes.risco import risco_app
from bhadrasana.routes.rvf import rvf_app

sys.path.append('.')

import ajna_commons.flask.login as login_ajna
from ajna_commons.flask.user import DBUser
from bhadrasana.views import app
from bhadrasana.models import Setor, Usuario
from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags, create_marcas, OVR

from .test_base import BaseTestCase

SECRET = 'teste'

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
    app.config['mongodb'] = mongodb['test']
    app.config['mongo_risco'] = mongodb['risco']
    return app


engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
from mongomock.gridfs import enable_gridfs_integration

enable_gridfs_integration()
mongodb = mongomock.MongoClient()

create_tables(engine, session)
configure_app(app, session, mongodb)
risco_app(app)
rvf_app(app)
ovr_app(app)
ovr2_app(app)
admin_app(app, session)

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

    def get_consulta_container(self, numero, datainicio, datafim):
        rv = self.app.get('/consulta_container')
        assert rv.data is not None
        # print(rv.data)
        token_text = self.get_token(str(rv.data))
        # print(token_text)
        payload = {'csrf_token': token_text, 'numerolote': numero,
                   'datainicio': datetime.strftime(datainicio, '%Y-%m-%d'),
                   'datafim': datetime.strftime(datafim, '%Y-%m-%d')}
        rv = self.app.post('/consulta_container', data=payload)
        # print(rv.data)
        # print(rv.status_code)
        return str(rv.data), rv.status_code

    def test_consulta_conteiner(self):
        datainicio = datetime(2020, 1, 1, 0, 0)
        ovr1, ovr2 = self.create_OVRs_test_ovrs_container(datainicio)
        datafim = datetime(2020, 7, 3, 0, 0)
        self.login('ivan', 'ivan')
        text, status_code = self.get_consulta_container('A1', datainicio, datafim)
        assert status_code == 200
        assert '1234' in text
        text, status_code = self.get_consulta_container('A2', datainicio, datafim)
        assert status_code == 200
        assert '1234' in text
        text, status_code = self.get_consulta_container('A3', datainicio, datafim)
        assert status_code == 200
        assert '12345' in text
        # Case insensitive
        text, status_code = self.get_consulta_container('a3', datainicio, datafim)
        assert status_code == 200
        assert '12345' in text
        text, status_code = self.get_consulta_container('A4', datainicio, datafim)
        assert status_code == 200
        assert '1234' not in text

    def get_consulta_container_text(self, numero):
        payload = {'numerolote': numero}
        rv = self.app.post('/consulta_conteiner_text', data=payload)
        return str(rv.data), rv.status_code

    def test_consulta_conteiner_text(self):
        datainicio = datetime.today() - timedelta(days=1)
        ovr1, ovr2 = self.create_OVRs_test_ovrs_container(datainicio)
        ovr1.datahora = datainicio
        ovr2.datahora = datainicio
        self.session.add(ovr1)
        self.session.add(ovr2)
        self.session.commit()
        self.login('ivan', 'ivan')
        text, status_code = self.get_consulta_container_text('A1')
        assert status_code == 200
        assert '1234' in text
        text, status_code = self.get_consulta_container_text('A2')
        assert status_code == 200
        assert '1234' in text
        text, status_code = self.get_consulta_container_text('A3')
        assert status_code == 200
        assert '12345' in text
        text, status_code = self.get_consulta_container_text('A4')
        assert status_code == 200
        assert '1234' not in text

    def test_visualizacoes(self):
        ce1 = mercante.Conhecimento()
        ce1.numeroCEmercante = '1234'
        item1 = mercante.Item()
        item1.numeroCEmercante = '1234'
        item1.codigoConteiner = 'ABCD'
        ovr = OVR()
        ovr.numeroCEmercante = '1234'
        ovr.responsavel_cpf = 'ivan'
        self.session.add(ce1)
        self.session.add(item1)
        self.session.add(ovr)
        self.session.commit()
        self.login('ivan', 'ivan')
        # Testar as várias visualizações.
        # Por enquanto vai testar apenas se não dá erro e se retorna títulos dos campos.
        # Depois precisa alimentar uma base de testes e testar retorno quanto a conteúdo
        rv = self.app.get('/minhas_ovrs')
        token_text = self.get_token(str(rv.data))
        payload = {'csrf_token': token_text,
                   'tipoexibicao': 1}
        rv = self.app.post('/minhas_ovrs', data=payload, follow_redirects=True)
        assert rv.status_code == 200
        print(rv.data)
        assert b'Alertas' in rv.data
        payload['tipoexibicao'] = 2
        rv = self.app.post('/minhas_ovrs', data=payload, follow_redirects=True)
        assert rv.status_code == 200
        assert b'Declara' in rv.data
        payload['tipoexibicao'] = 3
        rv = self.app.post('/minhas_ovrs', data=payload, follow_redirects=True)
        assert rv.status_code == 200
        assert b'Infra' in rv.data
        payload['tipoexibicao'] = 4
        rv = self.app.post('/minhas_ovrs', data=payload, follow_redirects=True)
        assert rv.status_code == 200
        assert b'CNPJ/Nome' in rv.data

    def create_CE_containeres_teste(self):
        """Sherlock Holmes, da Equipe 221B Baker Street, seleciona os CEs-Mercante
        152005079623267 e 152005080025807 para verificação"""
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
        """1. Criar ficha para CE 152005079623267"""
        recinto = self.create_recinto('Londres')
        self.session.refresh(recinto)
        self.recinto_id = recinto.id
        self.login('holmes', 'holmes')
        rv = self.app.get('/ovr')
        token_text = self.get_token(str(rv.data))
        # payload = {'csrf_token': token_text,
        #            'numeroCEmercante': '152005079623267',
        #            'recinto_id': self.recinto_id,
        #            'adata': '1859-05-22',
        #            'ahora': '22:21'}
        # alterei a data de criação da Ficha para não quebrar a pesquisa de fichas no meu setor
        # pois a busca padrão são fichas dentro do mesmo mês
        adata = datetime.strftime(datetime.today(), "%Y-%m-%d")
        payload = {'csrf_token': token_text,
                   'numeroCEmercante': '152005079623267',
                   'recinto_id': self.recinto_id,
                   'adata': adata,
                   'ahora': '22:21'}
        rv = self.app.post('/ovr', data=payload, follow_redirects=True)
        assert b'152005079623267' in rv.data
        assert rv.status_code == 200

    def test_a1b_cria_flag_FichaCE(self):
        """Pesquisar ficha para CE 152005079623267 e criar Flag"""
        self.login('holmes', 'holmes')
        rv = self.app.get('/pesquisa_ovr')
        token_text = self.get_token(str(rv.data))
        payload = {'csrf_token': token_text,
                   'numeroCEmercante': '152005079623267',
                   'tipooperacao': 'None',
                   'fase': 'None',
                   'recinto_id': 'None',
                   'tipoevento_id': 'None',
                   'flag_id': 'None',
                   'infracao_id': 'None'}
        rv = self.app.post('/pesquisa_ovr', data=payload, follow_redirects=True)
        assert rv.status_code == 200
        assert b'152005079623267' in rv.data
        soup = BeautifulSoup(rv.data, features='lxml')
        table = soup.find('table', {'id': 'pesquisa_ovr_table'})
        rows = [str(row) for row in table.findAll("tr")]
        # print(rows)
        assert len(rows) == 2
        assert '152005079623267' in ''.join(rows)
        table_text = ''.join(rows)
        ovr_id_pos = table_text.find('"ovr?id=')
        ovr_id = table_text[ovr_id_pos + 8: ovr_id_pos + 9]
        # incluir flags
        rv = self.app.get('inclui_flag_ovr?ovr_id=%s&flag_nome=Perecível' % ovr_id)
        assert rv.status_code == 201
        assert b'Perec' in rv.data
        flag_id = rv.json[0]['id']
        rv = self.app.get('ovr?id=%s' % ovr_id)
        soup = BeautifulSoup(rv.data, features='lxml')
        text_div_flags = soup.find('div', {'id': 'div_flags_ovr'}).text
        assert 'Perecível' in text_div_flags
        rv = self.app.get('exclui_flag_ovr?ovr_id=%s&flag_id=%s' % (ovr_id, flag_id))
        assert rv.status_code == 201
        assert b'Perec' not in rv.data
        assert len(rv.json) == 0
        rv = self.app.get('ovr?id=%s' % ovr_id)
        soup = BeautifulSoup(rv.data, features='lxml')
        text_div_flags = soup.find('div', {'id': 'div_flags_ovr'}).text
        assert 'Perecível' not in text_div_flags

    def test_a2_atribuir_responsabilidade_watson(self):
        """2. Atribuir responsabilidade para Watson"""
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
        """3. Entrar na programação/lista de contêineres e imagens e programar verificação física de um dos contêineres"""
        self.create_CE_containeres_teste()
        self.login('holmes', 'holmes')
        rv = self.app.get('/programa_rvf_ajna?ovr_id=%s' % 1)
        assert b'container=1' in rv.data
        assert b'container=2' in rv.data
        rv = self.app.get('/programa_rvf_ajna?ovr_id=%s&container=%s' % (1, 1),
                          follow_redirects=True)
        print(str(rv.data))
        assert b'container=1' not in rv.data
        assert 'n. 1' in str(rv.data)
        assert b'container=1' not in rv.data

    def test_b1_consulta_fichas(self):
        """Watson entra no Sistema
            1. Consulta suas fichas
        """
        self.login('watson', 'watson')
        rv = self.app.get('/minhas_ovrs')  # Fichas a mim atribuídas
        print(str(rv.data))
        assert rv.status_code == 200
        assert b'152005079623267' in rv.data
        # Agora vamos assegurar que Watson não vê a Ficha em ovrs_criador
        rv = self.app.get('/ovrs_criador')  # Fichas criadas por mim
        assert rv.status_code == 200
        assert b'152005079623267' not in rv.data
        # A ficha deve aparecer nas fichas do Setor
        rv = self.app.get('/ovrs_meus_setores')  # Fichas dos meus Setores
        print("....", str(rv.data))
        assert rv.status_code == 200
        assert b'152005079623267' in rv.data

        # Agora vamos assegurar que Holmes, como já distribuiu a OVR para Watson,
        # não a vê mais em minhas_ovrs (mas vê em ovrs_criador E em ovrs_meus_setores)
        self.login('holmes', 'holmes')
        rv = self.app.get('/minhas_ovrs')
        assert rv.status_code == 200
        assert b'152005079623267' not in rv.data
        rv = self.app.get('/ovrs_criador')
        assert rv.status_code == 200
        assert b'152005079623267' in rv.data
        rv = self.app.get('/ovrs_meus_setores')
        assert rv.status_code == 200
        print(rv.data)
        # FIXME: Teste falhando, mas OK na interface???
        assert b'152005079623267' in rv.data

    def test_b2_agendamento_verificacao_fisica(self):
        """2 - Evento de agendamento de verificação física"""
        self.login('watson', 'watson')
        rv = self.app.get('/ovr?id=%s' % 1)
        text = str(rv.data)
        movimentaovr_pos = text.find('action="eventoovr"')
        movimentaovr_text = text[movimentaovr_pos:]
        token_text = self.get_token(movimentaovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': 1,
                   'tipoevento_id': 2,
                   'motivo': 'Teste b2',
                   'user_name': 'watson'}
        rv = self.app.post('/eventoovr', data=payload, follow_redirects=True)
        soup = BeautifulSoup(rv.data, features='lxml')
        table = soup.find('table', {'id': 'table_eventos'})
        rows = [str(row) for row in table.findAll("tr")]
        assert len(rows) == 3
        assert 'verificação física' in ''.join(rows)
        # Teste desfazer e refazer
        """
        rv = self.app.get('/ovr?id=%s' % 1)
        text = str(rv.data)
        desfaz_pos = text.find('action="desfazer')
        desfaz_text = text[desfaz_pos:]
        token_text = self.get_token(desfaz_text)
        payload = {'csrf_token': token_text, 'ovr_id': 1}
        rv = self.app.post('/desfazer_ultimo_eventoovr', data=payload, follow_redirects=True)
        app.logger.info(rv.status_code)
        app.logger.info(rv.data)
        soup = BeautifulSoup(rv.data, features='lxml')
        table = soup.find('table', {'id': 'table_eventos'})
        rows = [str(row) for row in table.findAll("tr")]
        assert len(rows) == 2
        rv = self.app.get('/ovr?id=%s' % 1)
        text = str(rv.data)
        movimentaovr_pos = text.find('action="eventoovr"')
        movimentaovr_text = text[movimentaovr_pos:]
        token_text = self.get_token(movimentaovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': 1,
                   'tipoevento_id': 2,
                   'motivo': 'Teste b2',
                   'user_name': 'watson'}
        rv = self.app.post('/eventoovr', data=payload, follow_redirects=True)
        soup = BeautifulSoup(rv.data, features='lxml')
        table = soup.find('table', {'id': 'table_eventos'})
        rows = [str(row) for row in table.findAll("tr")]
        assert len(rows) == 3
        """

    def test_b3_informar_RVF_carregar_fotos(self):
        """3 - Informa RVF carregando fotos"""
        self.login('watson', 'watson')
        rv = self.app.get('lista_rvfovr?ovr_id=%s' % 1)
        soup = BeautifulSoup(rv.data, features='lxml')
        table = soup.find('table', {'id': 'table_lista_rvfovr'})
        rows = [str(row) for row in table.findAll("tr")]
        # print(rows)
        assert len(rows) == 2  # Tem uma rvf já programada no passo anterior
        table_text = ''.join(rows)
        rvf_id_pos = table_text.find('"rvf?id=')
        rvf_id = table_text[rvf_id_pos + 8: rvf_id_pos + 9]
        # print(rvf_id)
        rv = self.app.get('rvf?id=%s' % rvf_id)
        assert b'name="id" value="1' in rv.data
        text = str(rv.data)
        token_text = self.get_token(text)
        payload = {'csrf_token': token_text,
                   'id': rvf_id,
                   'numeroCEmercante': '152005079623267',
                   'numerolote': 'abcd1234567',
                   'descricao': 'Teste b3',
                   'peso': 13.17,
                   'volume': 12.45,
                   'adata': '2020-01-01',
                   'ahora': '01:01',
                   'ovr_id': 1,
                   'user_name': 'watson'}
        rv = self.app.post('/rvf', data=payload, follow_redirects=True)
        assert rv.status_code == 200
        texto = str(rv.data)
        for key, value in payload.items():
            if key != 'csrf_token':
                # print(f">>>>>>>>>>>>>>> value: {str(value)} texto: {texto}")
                assert str(value) in texto
        # Lacres
        rv = self.app.get('inclui_lacre_verificado?rvf_id=%s&lacre_numero=B3A' % rvf_id)
        assert rv.status_code == 201
        rv = self.app.get('inclui_lacre_verificado?rvf_id=%s&lacre_numero=B3B' % rvf_id)
        assert rv.status_code == 201
        assert b'B3A' in rv.data
        assert b'B3B' in rv.data
        rv_json = rv.json
        # print(rv_json)
        lacre_id = rv_json[1]['id']
        rv = self.app.get('exclui_lacre_verificado?rvf_id=%s&lacre_id=%s'
                          % (rvf_id, lacre_id))
        assert rv.status_code == 201
        assert b'B3A' in rv.data
        assert b'B3B' not in rv.data
        # Infrações
        rv = self.app.get('inclui_infracao_encontrada?rvf_id=%s&infracao_nome=Armas' % rvf_id)
        assert rv.status_code == 201
        assert 'Armas' in str(rv.data)
        infracao_id = rv.json[0]['id']
        rv = self.app.get('inclui_infracao_encontrada?rvf_id=%s&infracao_nome=Contrafação' % rvf_id)
        assert rv.status_code == 201
        assert 'Contrafação' in str(rv.json)
        # Marcas
        rv = self.app.get('inclui_marca_encontrada?rvf_id=%s&marca_nome=Adidas' % rvf_id)
        assert rv.status_code == 201
        assert b'Adidas' in rv.data
        marca_id = rv.json[0]['id']
        # Imagens

        # Testar tela RVF com as inclusões
        rv = self.app.get('rvf?id=%s' % rvf_id)
        assert b'B3A' in rv.data
        assert b'B3B' not in rv.data
        soup = BeautifulSoup(rv.data, features='lxml')
        text_div_marcas = soup.find('div', {'id': 'div_marcas_encontradas'}).text
        assert 'Adidas' in text_div_marcas
        text_div_infracoes = soup.find('div', {'id': 'div_infracoes_encontradas'}).text
        assert 'Armas' in text_div_infracoes
        # Excluir infracoes e marcas
        rv = self.app.get('exclui_infracao_encontrada?rvf_id=%s&infracao_id=%s'
                          % (rvf_id, infracao_id))
        assert rv.status_code == 201
        print('*******', rv.data)
        rv = self.app.get('exclui_marca_encontrada?rvf_id=%s&marca_id=%s'
                          % (rvf_id, marca_id))
        assert rv.status_code == 201
        print('*******', rv.data)
        # Testar tela RVF com as exclusões
        rv = self.app.get('rvf?id=%s' % rvf_id)
        soup = BeautifulSoup(rv.data, features='lxml')
        assert b'B3A' in rv.data
        assert b'B3B' not in rv.data
        text_div_armas = soup.find('div', {'id': 'div_marcas_encontradas'}).text
        assert 'Adidas' not in text_div_armas
        text_div_infracoes = soup.find('div', {'id': 'div_infracoes_encontradas'}).text
        assert 'Armas' not in text_div_infracoes
        assert 'Contra' in text_div_infracoes

    def test_b4_Devolver_para_Holmes(self):
        """4 - Devolve para Holmes"""
        self.login('watson', 'watson')
        rv = self.app.get('/ovr?id=%s' % 1)
        text = str(rv.data)
        responsavelovr_pos = text.find('action="responsavelovr"')
        responsavelovr_text = text[responsavelovr_pos:]
        token_text = self.get_token(responsavelovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': 1,
                   'responsavel': 'holmes'}
        rv = self.app.post('/responsavelovr', data=payload, follow_redirects=True)
        assert b'holmes' in rv.data

    def test_c1_Consultar_Fichas_Modificadas(self):
        """Holmes consulta suas fichas, vê mudanças na verificação física
        e que possivelmente há uma contrafação, distribui
        para Irene Adler para tratar."""
        self.login('holmes', 'holmes')
        rv = self.app.get('/minhas_ovrs')
        assert rv.status_code == 200
        assert b'152005079623267' in rv.data
        soup = BeautifulSoup(rv.data, features='lxml')
        table_text = str(soup.find('table', {'id': 'minhas_ovrs_table'}).extract())
        # print(table_text)
        assert 'class="warning' in table_text
        ovr_id_pos = table_text.find('"ovr?id=')
        ovr_id = table_text[ovr_id_pos + 8: ovr_id_pos + 9]
        # print('*********', ovr_id)
        rv = self.app.get('/ovr?id=%s' % ovr_id)
        soup = BeautifulSoup(rv.data, features='lxml')
        btn_text = str(soup.find('button', {'id': 'btn_rvf'}).extract())
        assert 'Verificações físicas (1)' in btn_text
        rv = self.app.get('lista_rvfovr?ovr_id=%s' % 1)
        soup = BeautifulSoup(rv.data, features='lxml')
        table = soup.find('table', {'id': 'table_lista_rvfovr'})
        rows = [str(row) for row in table.findAll("tr")]
        table_text = str(soup.find('table', {'id': 'table_lista_rvfovr'}).extract())
        # print(rows)
        assert len(rows) == 2  # Tem uma rvf já programada no passo anterior
        rvf_id_pos = table_text.find('"rvf?id=')
        rvf_id = table_text[rvf_id_pos + 8: rvf_id_pos + 9]
        # print('***********', rvf_id)
        rv = self.app.get('rvf?id=%s' % rvf_id)
        soup = BeautifulSoup(rv.data, features='lxml')
        text_div_infracoes = soup.find('div', {'id': 'div_infracoes_encontradas'}).text
        assert 'Contra' in text_div_infracoes
        rv = self.app.get('/ovr?id=%s' % ovr_id)
        text = str(rv.data)
        # print(text)
        responsavelovr_pos = text.find('action="responsavelovr"')
        responsavelovr_text = text[responsavelovr_pos:]
        token_text = self.get_token(responsavelovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': 1,
                   'responsavel': 'adler',
                   'motivo': 'Solicitar Laudo das marcas encontradas!!'}
        rv = self.app.post('/responsavelovr', data=payload, follow_redirects=True)
        ovr = get_ovr(session, 1)
        assert ovr.responsavel_cpf == 'adler'
        movimentaovr_pos = text.find('action="eventoovr"')
        movimentaovr_text = text[movimentaovr_pos:]
        token_text = self.get_token(movimentaovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': 1,
                   'tipoevento_id': 2,
                   'motivo': 'Solicitar Laudo das marcas encontradas!!',
                   'user_name': 'adler'}
        rv = self.app.post('/eventoovr', data=payload, follow_redirects=True)
        assert b'ESomenteUsuarioResponsavel' in rv.data
        self.login('adler', 'adler')
        rv = self.app.post('/eventoovr', data=payload, follow_redirects=True)
        # with open('testc1.html', 'w') as html_out:
        #     html_out.write(rv.data.decode('utf8'))
        assert b'adler' in rv.data
        soup = BeautifulSoup(rv.data, features='lxml')
        text_span_responsavel = soup.find('span', {'id': 'responsavel_nome'}).text
        assert 'adler' in text_span_responsavel
        assert b'Solicitar Laudo' in rv.data


if __name__ == '__main__':
    unittest.main()
