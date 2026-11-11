"""Tela Pesquisa Empresa (consulta_empresa) com a Empresa lida da navi_cnpj.

Pelo nome: uma linha por raiz de CNPJ. Pelo CNPJ: os estabelecimentos da raiz, cada um com as
Fichas dele (navi-dados/PLANO_EMPRESA_NAVI_CNPJ.md, decisão D2).
"""
import sys

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')

from bs4 import BeautifulSoup

from bhadrasana.models.laudo import Empresa
from tests.app_creator import app, session, recria_banco
from .test_base import BaseTestCase

CADASTRO = [
    ('11222333000281', 'ALFA COMERCIO LTDA'),
    ('11222333000100', 'ALFA COMERCIO LTDA'),
    ('11222333000362', 'ALFA COMERCIO LTDA'),
    ('44555666000177', 'ALFA TRANSPORTES SA'),
]


class PesquisaEmpresaTestCase(BaseTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        recria_banco()
        session.execute(Empresa.__table__.insert(),
                        [{'cnpj': cnpj, 'nome_empresarial_pj': nome} for cnpj, nome in CADASTRO])
        session.commit()

    def setUp(self) -> None:
        super().setUp(session)
        self.app = app.test_client()
        self.login('ivan', 'ivan')

    def get_token(self, text):
        token_start = text.find('name="csrf_token" value="')
        text_from_start = text[token_start + 25:]
        token_end = text_from_start.find('/>')
        return text_from_start[:token_end - 1]

    def login(self, username, senha):
        rv = self.app.get('/login')
        token_text = self.get_token(str(rv.data))
        self.app.post('/login', data={'csrf_token': token_text,
                                      'username': username,
                                      'senha': senha},
                      follow_redirects=True)

    def pesquisa(self, cnpj='', nome=''):
        rv = self.app.get('/consulta_empresa')
        token_text = self.get_token(str(rv.data))
        rv = self.app.post('/consulta_empresa', data={'csrf_token': token_text,
                                                      'cnpj': cnpj, 'nome': nome})
        assert rv.status_code == 200
        # Nenhuma consulta da tela falhou (o erro vira aviso na página)
        assert 'Erro! Detalhes no log' not in rv.data.decode()
        soup = BeautifulSoup(rv.data, features='lxml')
        linhas = soup.find('table', {'id': 'empresas_table'}).find('tbody').find_all('tr')
        return [[' '.join(td.get_text().split()) for td in linha.find_all('td')] for linha in linhas]

    def cria_ficha(self, cnpj):
        recinto = self.create_recinto('Recinto Pesquisa Empresa')
        self.create_OVR({'cnpj_fiscalizado': cnpj, 'recinto_id': recinto.id,
                         'adata': '2026-01-10', 'ahora': '10:00'}, 'ivan')

    def test_pelo_cnpj_lista_as_filiais_com_as_fichas_de_cada_uma(self):
        self.cria_ficha('11222333000281')
        self.cria_ficha('11222333000281')
        self.cria_ficha('11222333000362')
        linhas = self.pesquisa(cnpj='11222333000362')
        assert linhas == [['11222333000100', 'ALFA COMERCIO LTDA'],
                          ['11222333000281 (2)', 'ALFA COMERCIO LTDA'],
                          ['11222333000362 (1)', 'ALFA COMERCIO LTDA']]
        # Só a raiz: a mesma lista
        assert [linha[0] for linha in self.pesquisa(cnpj='11222333')] == \
            ['11222333000100', '11222333000281 (2)', '11222333000362 (1)']

    def test_pelo_cnpj_fora_do_cadastro(self):
        # Uma linha sem CNPJ e sem nome, como antes da navi_cnpj
        assert self.pesquisa(cnpj='55555555000155') == [['', '']]

    def test_pelo_nome_uma_linha_por_raiz(self):
        linhas = self.pesquisa(nome='ALFA')
        assert [linha[1] for linha in linhas] == ['ALFA COMERCIO LTDA', 'ALFA TRANSPORTES SA']
        assert linhas[0][0].startswith('11222333000100')
        assert linhas[1][0] == '44555666000177'
