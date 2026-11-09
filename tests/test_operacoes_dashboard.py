"""Testes do dashboard das Operações (/operacoes_dashboard): o filtro pelo período de abertura da Ficha (`OVR.datahora`,
09/11/2026). O padrão continua "Sem filtro"."""
import sys
import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')

from bhadrasana.models import operacoes_dashboard as od  # noqa: E402
from bhadrasana.models.ovr import Flag, OVR, metadata  # noqa: E402
from bhadrasana.models.rvf import RVF  # noqa: E402,F401 - a Ficha referencia a RVF (o mapper precisa dela)
from bhadrasana.routes.operacoes_dashboard import dashboard_app, descreve_periodo  # noqa: E402

INICIO_FEV, FIM_FEV = date(2026, 2, 1), date(2026, 2, 15)


def monta_banco():
    """'Operação Teste' com quatro Fichas (a 2ª no último segundo de 15/02, a 3ª no primeiro de 16/02) e duas Fichas
    pendentes (fora de operação, ainda abertas) com outra flag."""
    engine = create_engine('sqlite://')
    metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    operacao, outra = Flag(), Flag()
    operacao.nome, outra.nome = 'Operação Teste', 'Outra'
    session.add_all([operacao, outra])
    session.commit()
    for datahora, flag, fase in ((datetime(2026, 1, 10, 8), operacao, 0),
                                 (datetime(2026, 2, 15, 23, 59, 59), operacao, 3),
                                 (datetime(2026, 2, 16), operacao, 0), (datetime(2026, 3, 1, 12), operacao, 4),
                                 (datetime(2026, 2, 1), outra, 0), (datetime(2026, 4, 1), outra, 1)):
        ficha = OVR()
        ficha.datahora, ficha.fase = datahora, fase
        ficha.flags = [flag]
        session.add(ficha)
    session.commit()
    return session, operacao


class TestFiltroDeAbertura(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.session, cls.operacao = monta_banco()

    def total(self, flag_id, inicio=None, fim=None):
        return od.monta_dashboard_operacao(self.session, flag_id, inicio, fim)['total_ovrs']

    def test_sem_filtro_e_o_padrao(self):
        self.assertEqual(self.total(self.operacao.id), 4)
        self.assertEqual(self.total(-1), 2)

    def test_periodo_com_os_dois_dias_inteiros(self):
        # 15/02 às 23:59:59 entra; 16/02 à 00:00 não
        self.assertEqual(self.total(self.operacao.id, INICIO_FEV, FIM_FEV), 1)
        self.assertEqual(self.total(self.operacao.id, date(2026, 2, 16), date(2026, 2, 16)), 1)

    def test_so_um_lado_do_periodo(self):
        self.assertEqual(self.total(self.operacao.id, inicio=date(2026, 2, 16)), 2)
        self.assertEqual(self.total(self.operacao.id, fim=date(2026, 1, 31)), 1)

    def test_pendentes_tambem_filtradas(self):
        self.assertEqual(self.total(-1, date(2026, 3, 15), date(2026, 4, 30)), 1)
        self.assertEqual(self.total(-1, INICIO_FEV, FIM_FEV), 1)

    def test_resumo_das_operacoes_com_o_periodo(self):
        resumo = {linha['flag_id']: linha for linha in od.monta_resumo_operacoes(self.session, INICIO_FEV, FIM_FEV)}
        self.assertEqual(resumo[self.operacao.id]['total_ovrs'], 1)
        self.assertEqual(resumo[self.operacao.id]['percentual_conclusao'], 100)    # a única do período, concluída
        self.assertEqual(resumo[-1]['total_ovrs'], 1)
        sem_filtro = {linha['flag_id']: linha for linha in od.monta_resumo_operacoes(self.session)}
        self.assertEqual(sem_filtro[self.operacao.id]['total_ovrs'], 4)

    def test_pendentes_sao_as_abertas_fora_de_qualquer_operacao(self):
        """09/11/2026: a Ficha sem flag entra; a de uma Operação com outra flag não (o filtro antigo, na
        junção com as flags, errava os dois casos)."""
        session, operacao = monta_banco()
        outra = session.query(Flag).filter(Flag.nome == 'Outra').one()
        fichas = {}
        for nome, datahora, flags, fase in (('sem flag', datetime(2026, 5, 1), [], 0),
                                            ('operação e outra', datetime(2026, 5, 2), [operacao, outra], 0),
                                            ('sem flag concluída', datetime(2026, 5, 3), [], 3)):
            ficha = OVR()
            ficha.datahora, ficha.fase = datahora, fase
            ficha.flags = flags
            session.add(ficha)
            fichas[nome] = ficha
        session.commit()
        pendentes = {ficha.id for ficha in od.listar_ovrs_com_pendencias(session)}
        self.assertIn(fichas['sem flag'].id, pendentes)
        self.assertNotIn(fichas['operação e outra'].id, pendentes)
        self.assertNotIn(fichas['sem flag concluída'].id, pendentes)
        self.assertEqual(len(pendentes), 3)          # as 2 abertas com 'Outra' da base e a sem flag
        self.assertEqual(od.monta_dashboard_operacao(session, operacao.id)['total_ovrs'], 5)

    def test_descricao_do_periodo(self):
        self.assertEqual(descreve_periodo(None, None), 'Sem filtro')
        self.assertEqual(descreve_periodo(INICIO_FEV, FIM_FEV), 'de 01/02/2026 a 15/02/2026')
        self.assertEqual(descreve_periodo(INICIO_FEV, None), 'a partir de 01/02/2026')
        self.assertEqual(descreve_periodo(None, FIM_FEV), 'até 15/02/2026')


class TestTela(unittest.TestCase):
    """A tela na app de teste do Fichas, com o banco deste teste."""

    @classmethod
    def setUpClass(cls):
        from tests.app_creator import app
        if 'dashboard_operacoes' not in app.view_functions:
            dashboard_app(app)
        cls.app = app
        cls.session, cls.operacao = monta_banco()
        cls.sessao_antes = app.config.get('dbsession')
        app.config['dbsession'] = cls.session
        cls.cliente = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.app.config['dbsession'] = cls.sessao_antes

    def html(self, **params):
        resposta = self.cliente.get('/operacoes_dashboard', query_string=params)
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_data(as_text=True)

    def test_sem_filtro_por_padrao(self):
        html = self.html()
        self.assertIn('<b>Sem filtro</b>', html)
        self.assertIn('name="abertura_inicio" id="abertura_inicio" value=""', html)
        self.assertIn(f'href="/operacoes_dashboard?flag_id={self.operacao.id}"', html)

    def test_periodo_no_resumo_e_nos_links(self):
        html = self.html(abertura_inicio='2026-02-01', abertura_fim='2026-02-15')
        self.assertIn('<b>de 01/02/2026 a 15/02/2026</b>', html)
        self.assertIn('value="2026-02-01"', html)
        self.assertIn(f'flag_id={self.operacao.id}&amp;abertura_inicio=2026-02-01&amp;abertura_fim=2026-02-15', html)

    def test_operacao_com_periodo_invertido_e_data_invalida(self):
        html = self.html(flag_id=self.operacao.id, abertura_inicio='2026-02-15', abertura_fim='2026-02-01')
        self.assertIn('<b>de 01/02/2026 a 15/02/2026</b>', html)     # trocadas
        self.assertIn('Total Fichas: 1', html)
        self.assertIn(f'href="/operacoes_dashboard?flag_id={self.operacao.id}"', html)    # o "Sem filtro" da operação
        html = self.html(flag_id=self.operacao.id, abertura_inicio='15/02/2026')
        self.assertIn('<b>Sem filtro</b>', html)
        self.assertIn('Total Fichas: 4', html)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
