import sys
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models.laudo import Base, SAT, Empresa, get_empresa, get_empresas, \
    get_empresas_nome

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)


class LaudoTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.session = session

    def create_sat(self, numero, datapedido):
        sat = self.session.query(SAT).filter(SAT.numeroSAT == numero).one_or_none()
        if sat:
            return sat
        sat = SAT()
        sat.numeroSAT = numero
        sat.dataPedido = datapedido
        self.session.add(sat)
        self.session.commit()
        sat = self.session.query(SAT).filter(SAT.numeroSAT == numero).one_or_none()
        return sat

    def test_SAT(self):
        datapedido = datetime(2020, 1, 1)
        sat = self.create_sat(1, datapedido)
        assert sat.get_numero() == '0817800/00001/2020'


class EmpresaTestCase(unittest.TestCase):
    """Empresa lê a navi_cnpj (só leitura).

    Os testes semeiam pelo Core, que não passa pelo flush.
    """

    CADASTRO = [
        # A mesma raiz, fora de ordem: a matriz (0001) é a menor
        ('11222333000281', 'ALFA COMERCIO LTDA'),
        ('11222333000100', 'ALFA COMERCIO LTDA'),
        ('11222333000362', 'ALFA COMERCIO LTDA'),
        ('44555666000177', 'ALFA TRANSPORTES SA'),
        ('77888999000144', 'BETA IMPORTADORA LTDA'),
    ]

    def setUp(self) -> None:
        self.session = session
        self.session.execute(Empresa.__table__.delete())
        self.session.execute(Empresa.__table__.insert(),
                             [{'cnpj': cnpj, 'nome_empresarial_pj': nome}
                              for cnpj, nome in self.CADASTRO])
        self.session.commit()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.execute(Empresa.__table__.delete())
        self.session.commit()

    def test_tabela_e_colunas(self):
        assert Empresa.__tablename__ == 'navi_cnpj'
        colunas = [coluna.name for coluna in Empresa.__table__.columns]
        assert colunas == ['cnpj', 'nome_empresarial_pj']
        empresa = self.session.query(Empresa).filter(Empresa.cnpj == '77888999000144').one()
        assert empresa.nome == 'BETA IMPORTADORA LTDA'
        assert empresa.dump() == {'cnpj': '77888999000144', 'nome': 'BETA IMPORTADORA LTDA'}

    def test_so_leitura_inclusao(self):
        empresa = Empresa()
        empresa.cnpj = '99999999000199'
        empresa.nome = 'NOVA'
        self.session.add(empresa)
        with self.assertRaises(RuntimeError):
            self.session.commit()
        self.session.rollback()
        assert self.session.query(Empresa).filter(Empresa.cnpj == '99999999000199').count() == 0

    def test_so_leitura_alteracao_e_exclusao(self):
        empresa = self.session.query(Empresa).filter(Empresa.cnpj == '77888999000144').one()
        empresa.nome = 'OUTRO NOME'
        with self.assertRaises(RuntimeError):
            self.session.commit()
        self.session.rollback()
        empresa = self.session.query(Empresa).filter(Empresa.cnpj == '77888999000144').one()
        self.session.delete(empresa)
        with self.assertRaises(RuntimeError):
            self.session.commit()
        self.session.rollback()
        assert self.session.query(Empresa).filter(Empresa.cnpj == '77888999000144').one().nome == \
            'BETA IMPORTADORA LTDA'

    def test_get_empresa_exato(self):
        assert get_empresa(self.session, '11222333000362').cnpj == '11222333000362'

    def test_get_empresa_pela_raiz_traz_a_matriz(self):
        assert get_empresa(self.session, '11222333').cnpj == '11222333000100'
        # CNPJ completo fora do cadastro, com raiz conhecida
        assert get_empresa(self.session, '11222333000999').cnpj == '11222333000100'

    def test_get_empresa_cpf_e_desconhecido(self):
        # A raiz do CPF é a de uma empresa do cadastro: não pode achar
        assert get_empresa(self.session, '11222333444') is None
        assert get_empresa(self.session, '55555555000155') is None
        with self.assertRaises(ValueError):
            get_empresa(self.session, '1122')

    def test_get_empresas_na_ordem_do_cnpj(self):
        empresas = get_empresas(self.session, '11222333000362')
        assert [empresa.cnpj for empresa in empresas] == \
            ['11222333000100', '11222333000281', '11222333000362']
        assert [empresa.cnpj for empresa in get_empresas(self.session, '11222333', limit=2)] == \
            ['11222333000100', '11222333000281']
        assert get_empresas(self.session, '55555555') == []

    def test_get_empresas_nome_uma_por_raiz(self):
        empresas = get_empresas_nome(self.session, 'ALFA')
        assert [(empresa.cnpj, empresa.nome) for empresa in empresas] == \
            [('11222333000100', 'ALFA COMERCIO LTDA'), ('44555666000177', 'ALFA TRANSPORTES SA')]
        assert [empresa.cnpj for empresa in get_empresas_nome(self.session, 'ALFA', limit=1)] == \
            ['11222333000100']
        assert get_empresas_nome(self.session, 'GAMA') == []
        with self.assertRaises(ValueError):
            get_empresas_nome(self.session, 'AL')
