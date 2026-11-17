"""Testes do dashboard das Operações (/operacoes_dashboard): o filtro pelo período de abertura da Ficha (`OVR.datahora`,
09/11/2026). O padrão continua "Sem filtro".

17/11/2026: atalho de ano, total do resumo com cada Ficha uma vez e as Fichas repetidas, a categoria "Fichas sem
operação informada" (resultado registrado no período), os fiscalizados com nome da navi_cnpj e a descrição e as NCMs
dos CEs na tela da Operação."""
import re
import sys
import unittest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')

import virasana.integracao.mercante.mercantealchemy as mercante  # noqa: E402
from bhadrasana.models import laudo  # noqa: E402
from bhadrasana.models import operacoes_dashboard as od  # noqa: E402
from bhadrasana.models.laudo import Empresa  # noqa: E402
from bhadrasana.models.ovr import Flag, OVR, ResultadoOVR, TipoResultado, metadata  # noqa: E402
from bhadrasana.models.rvf import RVF  # noqa: E402 - a Ficha referencia a RVF (o mapper precisa dela)
from bhadrasana.routes.operacoes_dashboard import ano_inteiro, anos_do_atalho, dashboard_app, \
    descreve_periodo  # noqa: E402

INICIO_FEV, FIM_FEV = date(2026, 2, 1), date(2026, 2, 15)
ANO_2026 = date(2026, 1, 1), date(2026, 12, 31)
CE1, CE2, CE3 = '152605000000001', '152605000000002', '152605000000003'


def cria_tabelas():
    """A sessão SQLite com as tabelas do Fichas, a navi_cnpj e as do Mercante usadas pelo dashboard."""
    engine = create_engine('sqlite://')
    metadata.create_all(engine)
    laudo.metadata.create_all(engine, [laudo.metadata.tables['navi_cnpj']])
    mercante.metadata.create_all(engine, [mercante.metadata.tables['conhecimentosresumo'],
                                          mercante.metadata.tables['ncmitemresumo']])
    return sessionmaker(bind=engine)()


def monta_banco():
    """'Operação Teste' com quatro Fichas (a 2ª no último segundo de 15/02, a 3ª no primeiro de 16/02) e duas Fichas
    pendentes (fora de operação, ainda abertas) com outra flag."""
    session = cria_tabelas()
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
        resumo = {linha['flag_id']: linha
                  for linha in od.monta_resumo_operacoes(self.session, INICIO_FEV, FIM_FEV)['linhas']}
        self.assertEqual(resumo[self.operacao.id]['total_ovrs'], 1)
        self.assertEqual(resumo[self.operacao.id]['percentual_conclusao'], 100)    # a única do período, concluída
        self.assertEqual(resumo[-1]['total_ovrs'], 1)
        sem_filtro = {linha['flag_id']: linha for linha in od.monta_resumo_operacoes(self.session)['linhas']}
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


def nova_ficha(session, datahora, fase=0, flags=(), cnpj=None, ce=None):
    ficha = OVR()
    ficha.datahora, ficha.fase, ficha.cnpj_fiscalizado, ficha.numeroCEmercante = datahora, fase, cnpj, ce
    ficha.flags = list(flags)
    session.add(ficha)
    session.commit()
    return ficha


def novo_resultado(session, ficha, registrado_em, valor, tipo=TipoResultado.Credito):
    # o __init__ de BaseRastreavel descarta os argumentos nomeados: campo a campo
    resultado = ResultadoOVR()
    resultado.ovr_id, resultado.create_date = ficha.id, registrado_em
    resultado.tipo_resultado, resultado.valor = tipo.value, Decimal(valor)
    session.add(resultado)
    session.commit()


def nova_rvf(session, ficha, conteiner, ce=None, descricao='Encontrado na verificação'):
    rvf = RVF()
    rvf.ovr_id, rvf.numerolote, rvf.numeroCEmercante, rvf.descricao = ficha.id, conteiner, ce, descricao
    session.add(rvf)
    session.commit()
    return rvf


def monta_banco_completo():
    """Duas Operações e Fichas fora delas, com resultados, fiscalizados, RVFs e CEs (casos-limite fictícios).

    - Operação A: f1 (concluída, crédito de 1.000, CE1, duas RVFs), f2 (também na Operação B), f3 (filial fora da
      navi_cnpj: o nome vem da raiz), f4 (CPF; RVF com o CE1, sem CE na Ficha), f5 (sem fiscalizado; CE3 fora do
      Mercante).
    - Fora de Operação: p1 (aberta em 2026, ainda aberta, resultado em 2026: pendente E sem operação), p2 (aberta em
      2025, resultado em 2026), p3 (aberta em 2026, resultado em 2025), p4 (concluída sem resultado).
    """
    session = cria_tabelas()
    operacao_a, operacao_b = Flag(), Flag()
    operacao_a.nome, operacao_b.nome = 'Operação A', 'Operação B'
    session.add_all([operacao_a, operacao_b])
    session.commit()
    session.execute(Empresa.__table__.insert(), [
        {'cnpj': '11222333000181', 'nome_empresarial_pj': 'IMPORTADORA UM LTDA'},
        {'cnpj': '44555666000107', 'nome_empresarial_pj': 'COMERCIAL DOIS SA'},
    ])
    session.add(mercante.Conhecimento(numeroCEmercante=CE1, descricao='SAPATOS ESPORTIVOS'))
    session.add(mercante.Conhecimento(numeroCEmercante=CE2, descricao='BOLSAS'))
    for conteiner, ncm in (('MSCU1234567', '64041100'), ('MSCU1234567', '64029990'),
                           ('TGHU7654321', '42029200')):
        session.add(mercante.NCMItem(numeroCEMercante=CE1, codigoConteiner=conteiner, identificacaoNCM=ncm))
    session.commit()
    f = {
        'f1': nova_ficha(session, datetime(2026, 3, 1), 3, [operacao_a], '11222333000181', CE1),
        'f2': nova_ficha(session, datetime(2026, 3, 2), 0, [operacao_a, operacao_b], '11222333000181', CE2),
        'f3': nova_ficha(session, datetime(2026, 3, 3), 0, [operacao_a], '44555666000299'),
        'f4': nova_ficha(session, datetime(2026, 3, 4), 0, [operacao_a], '12345678909'),
        'f5': nova_ficha(session, datetime(2026, 3, 5), 0, [operacao_a], None, CE3),
        'p1': nova_ficha(session, datetime(2026, 3, 5), 0),
        'p2': nova_ficha(session, datetime(2025, 12, 20), 3),
        'p3': nova_ficha(session, datetime(2026, 2, 1), 3),
        'p4': nova_ficha(session, datetime(2026, 4, 1), 3),
    }
    novo_resultado(session, f['f1'], datetime(2026, 3, 10), '1000.00')
    novo_resultado(session, f['p1'], datetime(2026, 3, 20), '500.00')
    novo_resultado(session, f['p2'], datetime(2026, 1, 15), '200.00')
    novo_resultado(session, f['p3'], datetime(2025, 12, 31, 23, 59, 59), '300.00')
    nova_rvf(session, f['f1'], 'MSCU1234567')
    nova_rvf(session, f['f1'], 'XXXU0000000')     # contêiner sem NCM no CE: todas as do CE
    nova_rvf(session, f['f4'], 'TGHU7654321', ce=CE1)
    return session, operacao_a, operacao_b, f


class TestAtalhoDeAno(unittest.TestCase):

    def test_ano_atual_e_os_cinco_anteriores(self):
        self.assertEqual(anos_do_atalho(date(2026, 11, 17)),
                         [(2026, 'Ano atual (2026)'), (2025, '2025'), (2024, '2024'), (2023, '2023'),
                          (2022, '2022'), (2021, '2021')])

    def test_ano_inteiro_so_de_01_01_a_31_12(self):
        self.assertEqual(ano_inteiro(*ANO_2026), 2026)
        self.assertIsNone(ano_inteiro(date(2026, 1, 1), date(2026, 12, 30)))
        self.assertIsNone(ano_inteiro(date(2025, 1, 1), date(2026, 12, 31)))
        self.assertIsNone(ano_inteiro(date(2026, 1, 1), None))
        self.assertIsNone(ano_inteiro(None, None))


class TestSemOperacaoETotais(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.session, cls.operacao_a, cls.operacao_b, cls.f = monta_banco_completo()

    def ids(self, fichas):
        return {ficha.id for ficha in fichas}

    def test_categoria_so_com_periodo(self):
        self.assertNotIn(od.ID_SEM_OPERACAO, [op.id for op in od.listar_operacoes(self.session)])
        self.assertIn(od.ID_SEM_OPERACAO,
                      [op.id for op in od.listar_operacoes(self.session, com_sem_operacao=True)])
        self.assertEqual(od.listar_fichas_sem_operacao(self.session), [])

    def test_sem_operacao_pela_data_do_resultado(self):
        """Entra a Ficha fora de Operação com resultado registrado no período, qualquer que seja a abertura ou a
        fase; não entram a de Operação com resultado, a com resultado fora do período nem a sem resultado."""
        self.assertEqual(self.ids(od.listar_fichas_sem_operacao(self.session, *ANO_2026)),
                         {self.f['p1'].id, self.f['p2'].id})
        self.assertEqual(self.ids(od.listar_fichas_sem_operacao(self.session, date(2025, 12, 31), date(2025, 12, 31))),
                         {self.f['p3'].id})     # registrado no último segundo do dia
        self.assertEqual(self.ids(od.listar_fichas_sem_operacao(self.session, inicio=date(2026, 3, 11))),
                         {self.f['p1'].id})

    def test_total_conta_cada_ficha_uma_vez_e_lista_as_repetidas(self):
        resumo = od.monta_resumo_operacoes(self.session, *ANO_2026)
        linhas = {linha['flag_id']: linha for linha in resumo['linhas']}
        self.assertEqual([linha['flag_id'] for linha in resumo['linhas']][:2], [od.ID_PENDENTES, od.ID_SEM_OPERACAO])
        self.assertEqual(linhas[od.ID_PENDENTES]['total_ovrs'], 1)            # p1
        self.assertEqual(linhas[od.ID_SEM_OPERACAO]['total_ovrs'], 2)         # p1 e p2
        self.assertEqual(linhas[self.operacao_a.id]['total_ovrs'], 5)
        self.assertEqual(linhas[self.operacao_b.id]['total_ovrs'], 1)         # f2
        self.assertEqual(sum(linha['total_ovrs'] for linha in resumo['linhas']), 9)
        totais = resumo['totais']
        self.assertEqual(totais['total_ovrs'], 7)                             # f1 a f5, p1 e p2
        self.assertEqual(totais['percentual_conclusao'], 28)                  # f1 e p2: 2 de 7
        self.assertEqual(totais['total_multas'], Decimal('1700.00'))          # e não 2.200 (p1 em duas linhas)
        self.assertEqual(totais['total_ces'], 3)
        self.assertEqual(totais['total_rvfs'], 3)
        self.assertEqual(totais['total_containers'], 3)
        repetidas = {ficha['id']: ficha['linhas'] for ficha in resumo['repetidas']}
        self.assertEqual(repetidas, {
            self.f['f2'].id: ['Operação A', 'Operação B'],
            self.f['p1'].id: ['Fichas pendentes**', 'Fichas sem operação informada***'],
        })

    def test_sem_periodo_nao_tem_a_categoria(self):
        resumo = od.monta_resumo_operacoes(self.session)
        self.assertNotIn(od.ID_SEM_OPERACAO, [linha['flag_id'] for linha in resumo['linhas']])
        self.assertEqual([ficha['id'] for ficha in resumo['repetidas']], [self.f['f2'].id])

    def test_fiscalizados_com_nome_da_navi_cnpj(self):
        dados = od.monta_detalhe_operacao(self.session, self.operacao_a.id, *ANO_2026)
        self.assertEqual(dados['fiscalizados'], [
            {'cnpj': '11222333000181', 'nome': 'IMPORTADORA UM LTDA', 'qtd_fichas': 2},
            {'cnpj': '12345678909', 'nome': '', 'qtd_fichas': 1},                 # CPF: sem nome
            {'cnpj': '44555666000299', 'nome': 'COMERCIAL DOIS SA', 'qtd_fichas': 1},   # pela raiz
            {'cnpj': '', 'nome': '', 'qtd_fichas': 1},                            # não informado, por último
        ])
        nomes = {ovr['id']: ovr['fiscalizado_nome'] for ovr in dados['ovrs']}
        self.assertEqual(nomes[self.f['f3'].id], 'COMERCIAL DOIS SA')
        self.assertNotIn('fiscalizados', od.monta_dashboard_operacao(self.session, self.operacao_a.id))

    def test_descricao_e_ncms_dos_ces(self):
        dados = od.monta_detalhe_operacao(self.session, self.operacao_a.id, *ANO_2026)
        rvfs = {rvf['numerolote']: rvf for rvf in dados['rvfs']}
        self.assertEqual(rvfs['MSCU1234567']['ce'], CE1)                      # o CE da Ficha
        self.assertEqual(rvfs['MSCU1234567']['ce_descricao'], 'SAPATOS ESPORTIVOS')
        self.assertEqual(rvfs['MSCU1234567']['ce_ncms']['todas'], ['64029990', '64041100'])   # as do contêiner
        self.assertEqual(rvfs['XXXU0000000']['ce_ncms']['todas'], ['42029200', '64029990', '64041100'])
        self.assertEqual(rvfs['TGHU7654321']['ce_ncms']['todas'], ['42029200'])   # o CE da RVF (f4 não tem)
        conhecimentos = {ce['ce']: ce for ce in dados['conhecimentos']}
        self.assertEqual(list(conhecimentos), [CE1, CE2, CE3])
        self.assertEqual(conhecimentos[CE1]['fichas'], sorted([self.f['f1'].id, self.f['f4'].id]))
        self.assertEqual(conhecimentos[CE1]['ncms']['todas'], ['42029200', '64029990', '64041100'])
        self.assertEqual((conhecimentos[CE2]['descricao'], conhecimentos[CE2]['ncms']['todas']), ('BOLSAS', []))
        self.assertFalse(conhecimentos[CE3]['no_mercante'])

    def test_ncms_exibidas_tem_limite(self):
        ncms = od.lista_ncms(str(84000000 + n) for n in range(od.MAXIMO_NCMS + 3))
        self.assertEqual((len(ncms['exibidas']), len(ncms['todas']), ncms['restantes']), (od.MAXIMO_NCMS,
                                                                                          od.MAXIMO_NCMS + 3, 3))


class TestTelaCompleta(unittest.TestCase):
    """A tela com o atalho de ano, o rodapé, a categoria sem operação e o detalhe (fiscalizados e CEs)."""

    @classmethod
    def setUpClass(cls):
        from tests.app_creator import app
        if 'dashboard_operacoes' not in app.view_functions:
            dashboard_app(app)
        cls.app = app
        cls.session, cls.operacao_a, cls.operacao_b, cls.f = monta_banco_completo()
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

    def test_atalho_de_ano(self):
        html = self.html()
        self.assertIn(f'Ano atual ({date.today().year})', html)
        self.assertNotIn('<option value="2025" selected>', html)
        html = self.html(abertura_inicio='2025-01-01', abertura_fim='2025-12-31')
        self.assertIn('<option value="2025" selected>2025</option>', html)

    def test_rodape_e_repetidas_no_resumo(self):
        html = self.html(abertura_inicio='2026-01-01', abertura_fim='2026-12-31')
        self.assertIn('<tfoot>', html)
        self.assertIn('id="total_resumo"', html)
        self.assertIn('Fichas sem operação informada***', html)
        self.assertIn('Fichas em mais de uma linha do resumo (2)', html)
        self.assertIn('R$ 1.700,00', html)
        self.assertIn(f'flag_id={od.ID_SEM_OPERACAO}&amp;abertura_inicio=2026-01-01', html)

    def test_sem_periodo_sem_a_categoria(self):
        html = self.html()
        self.assertNotIn('Fichas sem operação informada***</option>', html)
        self.assertNotIn(f'value="{od.ID_SEM_OPERACAO}"', html)

    def test_categoria_sem_operacao_ou_flag_desconhecida_sem_periodo_mostram_o_resumo(self):
        for flag_id in (od.ID_SEM_OPERACAO, 9999):
            html = self.html(flag_id=flag_id)
            self.assertIn('Resumo das operações', html)

    def test_detalhe_da_categoria_sem_operacao(self):
        html = self.html(flag_id=od.ID_SEM_OPERACAO, abertura_inicio='2026-01-01', abertura_fim='2026-12-31')
        self.assertIn('Total Fichas: 2', html)
        # o "Sem filtro" volta ao resumo: a categoria não existe sem período
        self.assertEqual(re.search(r'href="([^"]*)"\s+id="sem_filtro"', html).group(1), '/operacoes_dashboard')

    def test_detalhe_com_fiscalizados_e_ces(self):
        html = self.html(flag_id=self.operacao_a.id)
        self.assertIn('<h2>Fiscalizados</h2>', html)
        self.assertIn('11.222.333/0001-81', html)
        self.assertIn('IMPORTADORA UM LTDA', html)
        self.assertIn('<th>Fiscalizado</th>', html)
        self.assertIn('SAPATOS ESPORTIVOS', html)
        self.assertIn('64029990, 64041100', html)
        self.assertIn('CE não encontrado no Mercante', html)
        self.assertIn(f'href="/ovr?id={self.f["f4"].id}"', html)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
