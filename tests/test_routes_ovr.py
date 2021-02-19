import sys
from datetime import date

from virasana.integracao.mercante import mercantealchemy

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')

from tests.app_creator import app, session, drop_tables, engine
from bhadrasana.models import Setor, Usuario, PerfilUsuario, get_perfisusuario
from bs4 import BeautifulSoup
from bhadrasana.models.laudo import Empresa
from .test_base import BaseTestCase

SECRET = 'teste'

"""
Divisão:    Divisão Teste
Chefe:      carlos senha carlos

Equipe:     Equipe A
Chefe:      erika senha erika
Membros:    usuarioA1 senha usuarioA1
            usuarioA2 senha usuarioA2
            
Equipe:     Equipe B
Chefe:      kanoo senha kanoo
Membros:    usuarioB3 senha usuarioB3
            usuarioB4 senha usuarioB4
            
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
    perfis = [(1, 'carlos', 2),  # Supervisor
              (2, 'erika', 2),  # Supervisor
              (3, 'kanoo', 2)]  # Supervisor

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
        usuario.nome = linha[1]
        usuario.setor_id = linha[2]
        # usuario.perfis = linha[3]
        session.add(usuario)
    session.commit()


def create_empresas(session):
    empresas = [(1, '04175124000169', 'Empresa de teste')]
    for linha in empresas:
        empresa = Empresa()
        empresa.id = linha[0]
        empresa.cnpj = linha[1]
        empresa.nome = linha[2]
        session.add(empresa)
    session.commit()


create_setores(session)
create_perfis(session)
create_usuarios(session)
create_empresas(session)


class OVRAppTestCase(BaseTestCase):

    def render_page(self, content):
        with open('saida_tests.html', 'w') as fileout:
            fileout.write(content)

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
        return self.app.post('/login', data={'csrf_token': token_text,
                                           'username': username,
                                           'senha': senha},
                           follow_redirects=True)
        # with open('saida_login.html', 'w') as fileout:
        #     fileout.write(str(rv.data))

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def recupera_perfil(self):
        perfis = get_perfisusuario(self.session, 'erika')

    def test_a01(self):
        # Erika cria uma ficha limpa
        # Atribui responsabilidade para usuarioA1 da sua equipe
        # Verifica fichas do seu setor
        login = self.login('erika', 'erika')
        assert b'erika' in login.data
        recinto = self.create_recinto('Wonderland')
        self.session.refresh(recinto)
        params = {'tipooperacao': 'Mercadoria Abandonada',
                  'numeroCEmercante': 'CE-123456789AAB',
                  'cnpj_fiscalizado': '04175124000169',
                  'numerodeclaracao': '111222333444',
                  'recinto_id': recinto.id,
                  'adata': '2021-01-01',
                  'ahora': '13:15'}
        ovr1 = self.create_OVR(params, 'erika')
        self.session.refresh(ovr1)
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        assert ficha.status_code == 200
        assert ovr1.tipooperacao == 'Mercadoria Abandonada'
        assert b'CE-123456789AAB' in ficha.data
        assert ovr1.fase == 0  # Iniciada
        assert ovr1.tipoevento_id == 1  # Aguardando distribuição
        assert ovr1.user_name == 'erika'
        assert ovr1.cpfauditorresponsavel is None
        assert ovr1.setor_id == '50'  # Equipe 01 - Setor da Érika
        assert ovr1.responsavel is None
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        text = str(ficha.data)
        # self.render_page(text)
        responsavelovr_pos = text.find('action="responsavelovr"')
        responsavelovr_text = text[responsavelovr_pos:]
        token_text = self.get_token(responsavelovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': ovr1.id,
                   'responsavel': 'usuarioA1'}
        ficha = self.app.post('/responsavelovr', data=payload, follow_redirects=True)
        assert b'usuarioA1' in ficha.data
        assert ovr1.fase == 1  # Ativa
        assert ovr1.tipoevento_id == 13  # Atribuição de responsável
        assert ovr1.tipoevento.nome == 'Atribuição de responsável'
        assert ovr1.user_name == 'erika'
        assert ovr1.cpfauditorresponsavel is None
        assert ovr1.setor_id == '50'  # Equipe 01 - Setor da Érika
        assert ovr1.responsavel.nome == 'usuarioA1'
        soup = BeautifulSoup(ficha.data, features='lxml')
        table = soup.find('table', {'id': 'table_eventos'})
        rows = [str(row) for row in table.findAll("tr")]
        assert len(rows) == 2
        # ficha_setores = self.app.get('/ovrs_meus_setores')
        # assert ficha_setores.status_code == 200
        # soup = BeautifulSoup(ficha_setores.data, features='lxml')
        # self.render_page(str(soup))
        # table = soup.find('table', {'id': 'minhas_ovrs_table'})
        # # self.render_page(str(soup))
        # rows = [str(row) for row in table.findAll("tr")]
        # assert len(rows) == 2

        # usuarioA1 cria nova ficha com o mesmo CNPJ, Número declaração e CE
        self.login('usuarioA1', 'usuarioA1')
        params = {'tipooperacao': 'Mercadoria Abandonada',
                  'numeroCEmercante': 'CE-123456789AAB',
                  'cnpj_fiscalizado': '04175124000169',
                  'numerodeclaracao': '111222333444',
                  'recinto_id': recinto.id,
                  'adata': '2021-01-14',
                  'ahora': '09:40'}
        ovr2 = self.create_OVR(params, 'usuarioA1')
        self.session.refresh(ovr2)
        ficha = self.app.get('/ovr?id=%s' % ovr2.id)
        soup = BeautifulSoup(ficha.data, features='lxml')
        # self.render_page(str(soup))
        assert 'Atenção!!! CE-Mercante já possui Fichas:' in str(soup)
        assert 'Atenção!!! DUE já possui Fichas:' in str(soup)
        assert 'Empresa (mostrando 6 meses, utilize pesquisa empresa para ver mais)' in str(soup)
        session.delete(ovr1)
        session.delete(ovr2)
        self.logout()

    def test_a02(self):
        # usuarioB3 cria uma ficha limpa
        # Define usuarioB4 como auditor responsável para ficha
        self.login('usuarioB3', 'usuarioB3')
        params = {'tipooperacao': 'Análise de risco na importação',
                  'numeroCEmercante': '987654321AABBCC',
                  'recinto_id': 2,
                  'setor_id': '2',
                  'numerodeclaracao': '1010101010',
                  'adata': '2020-01-15',
                  'ahora': '09:15',
                  'dataentrada': date(year=2021, month=6, day=20)}
        ovr1 = self.create_OVR(params, 'usuarioB3')
        self.session.refresh(ovr1)
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        # self.render_page(str(ficha.data))
        assert ficha.status_code == 200
        text = str(ficha.data)
        token_text = self.get_token(text)
        payload = {'csrf_token': token_text,
                   'ovr_id': ovr1.id,
                   'responsavel': 'usuarioB4'
                   }
        ficha = self.app.post('/auditorresponsavelovr', data=payload, follow_redirects=True)
        # self.render_page(str(ficha.data))
        assert ficha.status_code == 200
        assert ovr1.cpfauditorresponsavel == 'usuarioB4'
        session.delete(ovr1)
        self.logout()

    def test_a03(self):
        # Carlos cria uma ficha limpa
        # Atribui responsabilidade para usuarioB4 da Equipe B
        # usuarioB4 arquiva a ficha
        self.login('carlos', 'carlos')
        params = {'tipooperacao': 'Mercadoria Abandonada',
                  'adata': '2021-01-01',
                  'ahora': '13:15'}
        ovr1 = self.create_OVR(params, 'carlos')
        self.session.refresh(ovr1)
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        assert ficha.status_code == 200
        assert ovr1.fase == 0  # Iniciada
        assert ovr1.tipoevento_id == 1  # Aguardando distribuição
        assert ovr1.user_name == 'carlos'
        assert ovr1.responsavel is None
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        text = str(ficha.data)
        # self.render_page(text)
        responsavelovr_pos = text.find('action="responsavelovr"')
        responsavelovr_text = text[responsavelovr_pos:]
        token_text = self.get_token(responsavelovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': ovr1.id,
                   'responsavel': 'usuarioB4'}
        ficha = self.app.post('/responsavelovr', data=payload, follow_redirects=True)
        assert b'usuarioB4' in ficha.data
        assert ovr1.fase == 1  # Ativa
        assert ovr1.tipoevento_id == 13  # Atribuição de responsável
        assert ovr1.tipoevento.nome == 'Atribuição de responsável'
        assert ovr1.user_name == 'carlos'
        assert ovr1.responsavel.nome == 'usuarioB4'

        # Usuário B4 arquiva a ficha
        self.login('usuarioB4', 'usuarioB4')
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        text = str(ficha.data)
        token_text = self.get_token(responsavelovr_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': ovr1.id,
                   'tipoevento_id': '12'}
        ficha = self.app.post('/eventoovr', data=payload, follow_redirects=True)
        self.render_page(str(ficha.data))
        assert ovr1.fase == 4  # Arquivada
        assert ovr1.tipoevento_id == 12  # Arquivamento
        assert ovr1.tipoevento.nome == 'Arquivamento'
        assert ovr1.responsavel.nome == 'usuarioB4'
        session.delete(ovr1)
        self.logout()

    def test_a04(self):
        # Carlos consulta uma ficha
        self.login('carlos', 'carlos')
        ficha = self.app.get('/ovr/id=1')
        assert ficha.status_code == 200
        self.logout()

    # def test_a05(self):
    #     # Usuário não encontrado ao acessar Pesquisa OVR
    #     login = self.login('usuarioNone', 'usuarioNone')
    #     assert b'usuarioNone' in login.data
    #     fichas = self.app.get('/pesquisa_ovr')
    #     assert fichas.status_code == 200

    def test_a06_encerrar_ficha(self):
        # Kanoo cria ficha limpa e tenta encerrar sem atribuir responsável
        self.login('kanoo', 'kanoo')
        params = {'tipooperacao': 'Mercadoria Abandonada',
                  'recinto_id': 1}
        ovr1 = self.create_OVR(params, 'kanoo')
        self.session.refresh(ovr1)
        assert ovr1.id is not None
        assert ovr1.responsavel is None
        assert ovr1.fase == 0
        encerramento_ovr = self.app.get('/encerramento_ovr?ovr_id=%s' % ovr1.id)
        assert encerramento_ovr.status_code == 200
        text = str(encerramento_ovr.data)
        self.render_page(text)
        encerrar_ficha = text.find('action="encerrar_ficha"')
        encerrar_ficha_text = text[encerrar_ficha:]
        token_text = self.get_token(encerrar_ficha_text)
        payload = {'csrf_token': token_text,
                   'ovr_id': ovr1.id}
        ficha_encerrada = self.app.post('/encerrar_ficha', data=payload, follow_redirects=True)
        # self.render_page(str(ficha_encerrada.data))
        self.logout()


    def test_z01(self):
        # Kanoo cria uma ficha limpa
        # Retona erro
        self.login('kanoo', 'kanoo')
        params = {'tipooperacao': 'Mercadoria Abandonada',
                  'numeroCEmercante': '1222333444555AB',
                  'recinto_id': 1,
                  'numerodeclaracao': '111222333444',
                  'adata': '2021-01-14',
                  'ahora': '11:25'}
        ovr1 = self.create_OVR(params, 'kanoo')
        self.session.refresh(ovr1)
        mercantealchemy.metadata.drop_all(engine, [
            mercantealchemy.metadata.tables['conhecimentosresumo']
        ])
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        # self.render_page(str(ficha.data))
        assert ficha.status_code == 200
        self.logout()

    def test_z02(self):
        # Carlos cria uma ficha limpa
        # Retona outro erro
        self.login('carlos', 'carlos')
        params = {'tipooperacao': 'Mercadoria Abandonada',
                  'adata': '2021-01-25',
                  'ahora': '09:25'}
        ovr1 = self.create_OVR(params, 'carlos')
        self.session.refresh(ovr1)
        drop_tables(engine)
        ficha = self.app.get('/ovr?id=%s' % ovr1.id)
        # self.render_page(str(ficha.data))
        assert ficha.status_code == 200
        inclui_flag = self.app.get('/inclui_flag_ovr')
        assert inclui_flag.status_code == 500
        exclui_flag = self.app.get('/exclui_flag_ovr')
        assert exclui_flag.status_code == 500
        self.logout()
