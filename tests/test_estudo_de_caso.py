"""Testes do pacote de estudos de caso (bhadrasana/estudo_de_caso, 23/11/2026).

Banco SQLite em memória com as tabelas do Fichas, a navi_cnpj e as do Mercante; os dois Mongo (imagens de escaneamento
e fotos do Fichas) simulados com mongomock. Casos fictícios: a Operação Alfa (duas Fichas; a principal com CE, RVF,
12 fotos, uma delas fora do GridFS, TG e resultados), a Operação Beta (aberta em 2025) e uma Ficha de valor maior só
com outra flag, que não é Operação.
"""
import io
import json
import sys
import tempfile
import unittest
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest import mock

import mongomock
from bson import ObjectId
from gridfs import GridFS
from mongomock.gridfs import enable_gridfs_integration
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')

import virasana.integracao.mercante.mercantealchemy as mercante  # noqa: E402
from bhadrasana.estudo_de_caso import pacote  # noqa: E402
from bhadrasana.models import laudo  # noqa: E402
from bhadrasana.models.laudo import Empresa  # noqa: E402
from bhadrasana.models.ovr import Flag, ItemTG, Marca, OVR, Recinto, ResultadoOVR, TGOVR, TipoResultado, \
    metadata  # noqa: E402
from bhadrasana.models.rvf import ApreensaoRVF, ImagemRVF, Infracao, RVF, TipoApreensao  # noqa: E402

enable_gridfs_integration()
CE1 = '152605262642500'
CONTEINER = 'FBLU0242500'
CNPJ = '11222333000181'
RVF_EM = datetime(2026, 8, 5, 10, 0)


def jpeg(largura, altura, cor=(120, 80, 40), exif=None) -> bytes:
    saida = io.BytesIO()
    imagem = Image.new('RGB', (largura, altura), cor)
    if exif:
        imagem.save(saida, 'JPEG', exif=exif)
    else:
        imagem.save(saida, 'JPEG')
    return saida.getvalue()


def cria_tabelas():
    engine = create_engine('sqlite://')
    metadata.create_all(engine)
    laudo.metadata.create_all(engine, [laudo.metadata.tables['navi_cnpj']])
    mercante.metadata.create_all(engine, [mercante.metadata.tables[nome] for nome in (
        'conhecimentosresumo', 'itensresumo', 'ncmitemresumo', 'manifestosresumo')])
    return sessionmaker(bind=engine)()


def nova_ficha(session, datahora, flags, valor_tg=None, ce=None, cnpj=None, fase=3):
    ficha = OVR()
    ficha.datahora, ficha.fase, ficha.tipooperacao = datahora, fase, 1
    ficha.numeroCEmercante, ficha.cnpj_fiscalizado = ce, cnpj
    ficha.flags = list(flags)
    session.add(ficha)
    session.commit()
    if valor_tg:
        tg = TGOVR()
        tg.ovr_id, tg.numerolote, tg.descricao = ficha.id, CONTEINER, 'Guarda-chuvas'
        tg.valor, tg.qtde, tg.unidadedemedida, tg.numerotg = Decimal(valor_tg), Decimal('9720'), 0, 'TG 1/2026'
        session.add(tg)
        session.commit()
    return ficha


def monta_banco():
    session = cria_tabelas()
    recinto = Recinto()
    recinto.nome = 'BTP'
    alfa, beta, outra = Flag(), Flag(), Flag()
    alfa.nome, beta.nome, outra.nome = 'Operação Alfa', 'Operação Beta', 'Outra flag'
    marca, infracao = Marca(), Infracao()
    marca.nome, infracao.nome = 'MARCA X', 'Contrafação'
    session.add_all([recinto, alfa, beta, outra, marca, infracao])
    session.execute(Empresa.__table__.insert(), [{'cnpj': CNPJ, 'nome_empresarial_pj': 'ALFA IMPORTADORA LTDA'}])
    session.add(mercante.Conhecimento(
        numeroCEmercante=CE1, consignatario=CNPJ, embarcador='YIWU SHIPPER CO., LIMITED  ROOM 1002, YIWU, CHINA',
        portoOrigemCarga='CNNGB', portoDestFinal='BRSSZ', numConhecimento='OBO2607066', tipoBLConhecimento='12',
        manifestoCE='1326501468860', dataEmissao='2026-07-20', cubagem='68.000', descricao='UMBRELLA',
        tipoTrafego='5', valorFrete='6150.00', codigoMoedaFrete='220', modalidadeFrete='HH',
        codigoRecolhimentoFrete='P'))
    session.add(mercante.Manifesto(numero='1326501468860', portoCarregamento='CNNGB', portoDescarregamento='BRSSZ'))
    session.add(mercante.Item(numeroCEmercante=CE1, numeroSequencialItemCarga='1', codigoConteiner=CONTEINER,
                              isoCode='45G1', lacre='YMAW487720', pesoBruto='20494.650', tara='3900'))
    for seq, ncm, descricao, volumes in (('1', '66019100', 'UMBRELLA', '900'), ('2', '42029200', 'BAGS', '31'),
                                         ('3', '42029200', 'BAGS', '31')):
        session.add(mercante.NCMItem(numeroCEMercante=CE1, numeroSequencialItemCarga=seq, codigoConteiner=CONTEINER,
                                     identificacaoNCM=ncm, descritivo=descricao, qtdeVolumes=volumes))
    session.commit()
    fichas = {
        'principal': nova_ficha(session, datetime(2026, 8, 1), [alfa], '500000.00', CE1, CNPJ),
        'menor': nova_ficha(session, datetime(2026, 8, 2), [alfa], '100.00'),
        'beta': nova_ficha(session, datetime(2025, 3, 1), [beta], '200.00'),
        'fora': nova_ficha(session, datetime(2026, 5, 1), [outra], '9999999.00'),
    }
    principal = fichas['principal']
    principal.recinto_id = recinto.id
    item = ItemTG()
    item.tg_id, item.numero, item.descricao, item.qtde, item.valor = principal.tgs[0].id, 1, 'Guarda-chuva', 9720, 1
    item.marca_id, item.ncm = marca.id, '66019100'
    session.add(item)
    for tipo, valor in ((TipoResultado.Perdimento, '500000.00'), (TipoResultado.Credito, '1000.00')):
        resultado = ResultadoOVR()
        resultado.ovr_id, resultado.tipo_resultado, resultado.valor = principal.id, tipo.value, Decimal(valor)
        resultado.create_date = datetime(2026, 9, 1)
        session.add(resultado)
    rvf = RVF()
    rvf.ovr_id, rvf.numerolote, rvf.numeroCEmercante, rvf.datahora = principal.id, CONTEINER, CE1, RVF_EM
    rvf.descricao, rvf.peso = 'Encontrados guarda-chuvas com a MARCA X, sem autorização do titular.', Decimal('21000')
    rvf.infracoesencontradas = [infracao]
    rvf.marcasencontradas = [marca]
    session.add(rvf)
    session.commit()
    tipo = TipoApreensao()
    tipo.descricao = 'Cocaína'
    session.add(tipo)
    session.commit()
    apreensao = ApreensaoRVF()
    apreensao.rvf_id, apreensao.tipo_id, apreensao.peso = rvf.id, tipo.id, Decimal('35.5')
    session.add(apreensao)
    # sem flag (fora das Operações): sem RVF, só com o CE; e com RVF de um contêiner sem escaneamento
    fichas['sem_rvf'] = nova_ficha(session, datetime(2026, 7, 28), [], ce=CE1, cnpj=CNPJ)
    fichas['sem_escaneamento'] = nova_ficha(session, datetime(2026, 8, 1), [])
    outra_rvf = RVF()
    outra_rvf.ovr_id, outra_rvf.numerolote, outra_rvf.datahora = fichas['sem_escaneamento'].id, \
        'TGHU7654321', RVF_EM
    session.add(outra_rvf)
    session.commit()
    return session, fichas, rvf, (alfa, beta, outra)


class EstudoDeCasoTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.session, cls.fichas, cls.rvf, cls.flags = monta_banco()
        cliente = mongomock.MongoClient()
        cls.mongodb, cls.mongo_risco = cliente['test'], cliente['risco']
        escaneamentos = GridFS(cls.mongodb)
        for quando, largura in ((datetime(2026, 7, 30, 14), 3000), (datetime(2026, 8, 20), 1000),
                                (datetime(2025, 1, 10), 1000)):
            escaneamentos.put(jpeg(largura, 1000, (90, 90, 90)), filename=f'{CONTEINER}.jpg', metadata={
                'numeroinformado': CONTEINER, 'dataescaneamento': quando, 'contentType': 'image/jpeg'})
        fotos = GridFS(cls.mongo_risco)
        for ordem in range(1, 13):
            imagem = ImagemRVF()
            imagem.rvf_id, imagem.ordem = cls.rvf.id, ordem
            imagem.descricao = f'Foto {ordem}'
            # a 12ª aponta para um arquivo que não está no GridFS
            imagem.imagem = str(ObjectId()) if ordem == 12 else str(fotos.put(jpeg(1600, 1200), filename='f.jpg'))
            cls.session.add(imagem)
        cls.session.commit()
        cls.pasta = tempfile.TemporaryDirectory()
        cls.referencias = Path(cls.pasta.name) / 'referencias'
        cls.referencias.mkdir()
        for nome, conteudo in (('portos.json', {'CNNGB': 'Ningbo', 'BRSSZ': 'Santos'}),
                               ('paises.json', {'CN': 'China', 'BR': 'Brasil'}),
                               ('ncm.json', {'capitulos': {'66': 'Guarda-chuvas'},
                                             'posicoes': {'6601': 'Guarda-chuvas e sombrinhas'}})):
            (cls.referencias / nome).write_text(json.dumps(conteudo), encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.pasta.cleanup()

    @classmethod
    def gera(cls, **parametros) -> tuple:
        destino = Path(cls.pasta.name) / f'pacote_{len(list(Path(cls.pasta.name).glob("*.zip")))}.zip'
        indice = pacote.gera_pacote(cls.session, cls.mongodb, cls.mongo_risco, destino,
                                    referencias=cls.referencias, agora=datetime(2026, 11, 23, 9, 30), **parametros)
        return indice, zipfile.ZipFile(destino)

    @staticmethod
    def dados_do_caso(arquivo_zip, pasta) -> dict:
        return json.loads(arquivo_zip.read(f'{pasta}/dados.json').decode('utf-8'))


class TestFicha(EstudoDeCasoTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.indice, cls.zip = cls.gera(ficha_id=cls.fichas['principal'].id)
        cls.pasta_caso = f"caso_01_ficha_{cls.fichas['principal'].id}"
        cls.dados = cls.dados_do_caso(cls.zip, cls.pasta_caso)

    @classmethod
    def tearDownClass(cls):
        cls.zip.close()
        super().tearDownClass()

    def test_arquivos_do_pacote(self):
        nomes = set(self.zip.namelist())
        self.assertTrue({'SKILL.md', 'indice.json', f'{self.pasta_caso}/dados.json', f'{self.pasta_caso}/resumo.md',
                         f'{self.pasta_caso}/escaneamento_{CONTEINER}.jpg'} <= nomes)
        fotos = sorted(nome for nome in nomes if '/fotos/' in nome)
        self.assertEqual(fotos, [f'{self.pasta_caso}/fotos/foto_{n:02d}.jpg' for n in range(1, 11)])
        self.assertEqual(self.indice['origem'], {'modo': 'ficha', 'ficha': self.fichas['principal'].id})
        self.assertEqual(self.indice['gerado_em'], '23/11/2026 09:30')

    def test_slide_de_abertura(self):
        campos = dict(self.dados['slide_abertura']['campos'])
        self.assertEqual(campos['Importador (consignatário)'], 'ALFA IMPORTADORA LTDA')
        self.assertEqual(campos['CNPJ'], '11.222.333/0001-81')
        self.assertEqual(campos['Conhecimento (BL)'], 'OBO2607066 (HBL)')
        self.assertEqual(campos['CE-Mercante'], CE1)
        self.assertEqual(campos['Porto de origem'], 'CNNGB – Ningbo, China')
        self.assertEqual(campos['Data de emissão do BL'], '20/07/2026')
        self.assertEqual(campos['Peso bruto declarado'], '20.494,650 kg')
        self.assertEqual(campos['Cubagem'], '68,000 m³')
        self.assertEqual(campos['Volumes'], '962')
        self.assertEqual(campos['Frete'], 'USD 6.150,00')
        self.assertEqual(campos['Modalidade do frete'], 'HH – House to House')
        self.assertEqual(campos['Recinto'], 'BTP')
        self.assertNotIn('Notificado', campos)           # vazio: fica de fora
        self.assertNotIn('Fiscalizado na Ficha', campos)  # é o próprio consignatário
        mercadorias = self.dados['slide_abertura']['mercadorias']
        self.assertEqual([(m['ncm'], m['descricao'], m['volumes']) for m in mercadorias],
                         [('6601.91.00', 'UMBRELLA', '900'), ('4202.92.00', 'BAGS', '62')])   # BAGS somados
        self.assertEqual(mercadorias[0]['posicao'], 'Guarda-chuvas e sombrinhas')

    def test_escaneamento_mais_recente_antes_da_rvf(self):
        imagem, = self.dados['slide_escaneamento']['imagens']
        self.assertEqual((imagem['data'], imagem['dias_da_referencia']), ('30/07/2026 14:00', -6))
        self.assertEqual(imagem['escaneamentos_do_conteiner'], 3)
        conteudo = Image.open(io.BytesIO(self.zip.read(f'{self.pasta_caso}/escaneamento_{CONTEINER}.jpg')))
        self.assertEqual(conteudo.size, (2400, 800))        # 3000 px: reduzido

    def test_fotos_em_miniatura_e_aviso_da_que_falta(self):
        fotos = self.dados['slide_resultado']['fotos']
        self.assertEqual([foto['legenda'] for foto in fotos][:6], [f'Foto {n}' for n in range(1, 7)])
        self.assertEqual(self.dados['slide_resultado']['fotos_na_ficha'], 11)
        self.assertNotIn('Foto 12', [foto['legenda'] for foto in fotos])
        miniatura = Image.open(io.BytesIO(self.zip.read(f'{self.pasta_caso}/fotos/foto_01.jpg')))
        self.assertEqual(miniatura.size, (800, 600))
        self.assertTrue(any('não estão no GridFS' in aviso for aviso in self.dados['avisos']))

    def test_slide_de_resultado(self):
        resultado = self.dados['slide_resultado']
        self.assertEqual(resultado['destaques'], [
            ['Valor das mercadorias retidas (TG)', 'R$ 500.000,00'],
            ['Perdimento', 'R$ 500.000,00'],
            ['Multas e créditos', 'R$ 1.000,00'],
            ['Quantidade retida', '9.720 UN'],
            ['Apreensão – Cocaína', '35,50 kg'],
        ])
        self.assertEqual(resultado['infracoes'], ['Contrafação'])
        self.assertEqual(resultado['marcas'], ['MARCA X'])
        self.assertIn('sem autorização do titular', resultado['descricao_rvf'])
        self.assertEqual(self.dados['titulo_sugerido'], 'Estudo de caso 1 – ALFA')
        self.assertEqual(self.dados['fatos']['diferenca_peso_rvf_declarado_pct'], 2.5)
        self.assertEqual(self.dados['fatos']['posicoes_ncm_declaradas'], 2)

    def test_resumo_e_skill(self):
        resumo = self.zip.read(f'{self.pasta_caso}/resumo.md').decode('utf-8')
        self.assertIn('| CNPJ | 11.222.333/0001-81 |', resumo)
        self.assertIn('Contêiner FBLU0242500 – escaneado em 30/07/2026', resumo)
        skill = self.zip.read('SKILL.md').decode('utf-8')
        self.assertTrue(skill.startswith('---\nname: estudos-de-caso-fichas\n'))
        # tudo o que a skill manda ler existe no dados.json
        for bloco, campos in (('slide_abertura', ('titulo', 'campos', 'mercadorias', 'mercadorias_total')),
                              ('slide_escaneamento', ('titulo', 'imagens', 'sem_imagem')),
                              ('slide_resultado', ('titulo', 'destaques', 'infracoes', 'marcas', 'mercadorias_retidas',
                                                   'descricao_rvf', 'fotos'))):
            for campo in campos:
                self.assertIn(campo, self.dados[bloco])
                self.assertIn(campo, skill)
        for campo in ('legenda_sugerida', 'regra', 'dias_da_referencia', 'referencia', 'escaneamentos_do_conteiner'):
            self.assertIn(campo, self.dados['slide_escaneamento']['imagens'][0])
        for campo in ('titulo_sugerido', 'operacao', 'fatos', 'avisos', 'ficha', 'conhecimento', 'rvfs', 'tgs'):
            self.assertIn(campo, self.dados)

    def test_ficha_inexistente_ou_ficha_e_ano(self):
        with self.assertRaisesRegex(ValueError, 'Ficha 999999 não encontrada'):
            self.gera(ficha_id=999999)
        with self.assertRaisesRegex(ValueError, 'não os dois'):
            self.gera(ficha_id=1, ano=2026)


class TestOperacoes(EstudoDeCasoTestCase):

    def test_maiores_operacoes_so_flags_de_operacao(self):
        alfa, beta, _ = self.flags
        self.assertEqual([op.nome for op, _ in pacote.maiores_operacoes(self.session)],
                         ['Operação Alfa', 'Operação Beta'])
        self.assertEqual([op.nome for op, _ in pacote.maiores_operacoes(self.session, quantidade=1)],
                         ['Operação Alfa'])
        self.assertEqual([op.nome for op, _ in pacote.maiores_operacoes(self.session, *pacote.periodo_do_ano(2025))],
                         ['Operação Beta'])
        self.assertEqual(pacote.maiores_operacoes(self.session, *pacote.periodo_do_ano(2024)), [])

    def test_pacote_das_operacoes(self):
        indice, arquivo_zip = self.gera(quantidade=2)
        self.addCleanup(arquivo_zip.close)
        self.assertEqual(indice['origem']['periodo_de_abertura'], 'Sem filtro')
        self.assertEqual([caso['operacao'] for caso in indice['casos']], ['Operação Alfa', 'Operação Beta'])
        self.assertEqual(indice['casos'][0]['ficha'], self.fichas['principal'].id)   # a de maior valor
        dados = self.dados_do_caso(arquivo_zip, indice['casos'][0]['pasta'])
        self.assertEqual(dados['titulo_sugerido'], 'Estudo de caso 1 – Alfa')
        operacao = dados['operacao']
        self.assertEqual((operacao['fichas'], operacao['valor_total']), (2, 'R$ 501.100,00'))
        self.assertEqual(operacao['fiscalizados'][0], {'documento': '11.222.333/0001-81',
                                                       'nome': 'ALFA IMPORTADORA LTDA', 'fichas': 1})
        self.assertEqual([ficha['id'] for ficha in operacao['outras_fichas']], [self.fichas['menor'].id])
        self.assertIn(['Operação', 'Operação Alfa'], dados['slide_abertura']['campos'])
        # a Ficha da Beta não tem CE nem RVF: sai, com os avisos
        beta = self.dados_do_caso(arquivo_zip, indice['casos'][1]['pasta'])
        self.assertEqual(beta['slide_escaneamento']['imagens'], [])
        self.assertEqual(len(beta['avisos']), 2)

    def test_ano_sem_operacao_com_valor(self):
        with self.assertRaisesRegex(ValueError, 'de 01/01/2024 a 31/12/2024'):
            self.gera(ano=2024)


class TestCasosDeBorda(EstudoDeCasoTestCase):

    def caso(self, chave, **parametros) -> dict:
        indice, arquivo_zip = self.gera(ficha_id=self.fichas[chave].id, **parametros)
        self.addCleanup(arquivo_zip.close)
        return self.dados_do_caso(arquivo_zip, indice['casos'][0]['pasta'])

    def test_sem_rvf_usa_os_conteineres_do_ce_e_a_data_da_ficha(self):
        dados = self.caso('sem_rvf')
        imagem, = dados['slide_escaneamento']['imagens']
        self.assertEqual(imagem['referencia'], 'data de abertura da Ficha: 28/07/2026 00:00')
        self.assertEqual(imagem['dias_da_referencia'], 2)       # nenhum antes: o primeiro depois
        self.assertIn('depois', imagem['regra'])
        self.assertEqual(dados['slide_resultado']['fotos'], [])
        self.assertTrue(any('não tem RVF' in aviso for aviso in dados['avisos']))

    def test_conteiner_sem_escaneamento_no_prazo(self):
        dados = self.caso('sem_escaneamento')
        self.assertEqual(dados['slide_escaneamento'], {
            'titulo': 'Estudo de caso 1 – escaneamento', 'imagens': [], 'sem_imagem': ['TGHU7654321']})
        self.assertTrue(any('TGHU7654321: nenhum escaneamento' in aviso for aviso in dados['avisos']))

    def test_erro_de_leitura_no_mongo_nao_derruba_o_caso(self):
        with mock.patch.object(pacote, 'get_imagens_container', side_effect=RuntimeError('fora do ar')), \
                mock.patch.object(pacote, 'reduz_imagem', side_effect=OSError('corrompida')):
            dados = self.caso('principal')
        self.assertEqual((dados['slide_escaneamento']['imagens'], dados['slide_resultado']['fotos']), ([], []))
        self.assertIn(f'Contêiner {CONTEINER}: erro ao buscar o escaneamento (RuntimeError).', dados['avisos'])
        self.assertEqual(sum('não foi possível ler (OSError)' in aviso for aviso in dados['avisos']), 10)
        self.assertEqual(dict(dados['slide_abertura']['campos'])['CE-Mercante'], CE1)   # os dados saem


class TestRegras(unittest.TestCase):

    def registros(self, *datas):
        return [{'_id': n, 'metadata': {'dataescaneamento': data}} for n, data in enumerate(datas)]

    def test_escaneamento_antes_depois_e_fora_da_janela(self):
        registros = self.registros(datetime(2026, 7, 1), datetime(2026, 8, 5, 18), datetime(2026, 8, 12))
        escolha = pacote.escolhe_escaneamento(registros, RVF_EM)
        self.assertEqual((escolha['registro']['_id'], escolha['dias']), (1, 0))   # no mesmo dia, depois da hora
        escolha = pacote.escolhe_escaneamento(self.registros(datetime(2026, 8, 12)), RVF_EM)
        self.assertEqual(escolha['dias'], 7)
        self.assertIn('depois', escolha['regra'])
        self.assertIsNone(pacote.escolhe_escaneamento(self.registros(datetime(2026, 3, 1), datetime(2026, 9, 1)),
                                                      RVF_EM))
        self.assertIsNone(pacote.escolhe_escaneamento(self.registros(None), RVF_EM))
        escolha = pacote.escolhe_escaneamento(registros, None)
        self.assertEqual(escolha['registro']['_id'], 2)                            # sem referência: a mais recente

    def test_amostra_reprodutivel(self):
        self.assertEqual(pacote.amostra(range(5), 10), [0, 1, 2, 3, 4])
        escolhidos = pacote.amostra(range(30), 10, em_ordem=6, semente=42)
        self.assertEqual(escolhidos[:6], [0, 1, 2, 3, 4, 5])
        self.assertEqual(len(escolhidos), 10)
        self.assertEqual(escolhidos, sorted(escolhidos))                           # na ordem da RVF
        self.assertEqual(escolhidos, pacote.amostra(range(30), 10, em_ordem=6, semente=42))
        self.assertEqual(pacote.amostra(range(30), 3, em_ordem=6), [0, 1, 2])

    def test_miniatura_gira_pela_orientacao_exif(self):
        exif = Image.Exif()
        exif[0x0112] = 6                                                          # girar 90°
        conteudo = pacote.reduz_imagem(jpeg(1600, 800, exif=exif.tobytes()), 800)
        self.assertEqual(Image.open(io.BytesIO(conteudo)).size, (400, 800))
        pequeno = jpeg(300, 200)
        self.assertIs(pacote.reduz_imagem(pequeno, 2400, so_se_maior=True), pequeno)

    def test_formatacao(self):
        self.assertEqual(pacote.br_moeda(Decimal('5397750')), 'R$ 5.397.750,00')
        self.assertEqual(pacote.br_moeda(None), 'R$ 0,00')
        self.assertEqual(pacote.br_inteiro_ou_decimal(Decimal('12.5')), '12,50')
        self.assertEqual(pacote.formata_documento('12345678909'), '123.456.789-09')
        self.assertEqual(pacote.formata_documento('ABC'), 'ABC')
        self.assertEqual(pacote.numero_do_texto('1.234,56'), Decimal('1234.56'))
        self.assertIsNone(pacote.numero_do_texto('n/d'))
        self.assertEqual(pacote.data_do_texto('20072026'), '20/07/2026')
        self.assertEqual(pacote.data_do_texto('jul/26'), 'jul/26')
        self.assertEqual(pacote.nome_curto('HGS COMEX LTDA'), 'HGS')
        self.assertEqual(pacote.nome_curto('JB COMERCIO'), 'JB COMERCIO')
        self.assertEqual(pacote.rotulo(lambda codigo: ['A'][codigo], 7), '7')
        self.assertEqual(pacote.nome_do_pacote(ano=2026, hoje=date(2026, 11, 23)),
                         'estudos_de_caso_operacoes_2026_20261123.zip')

    def test_portos_sem_as_tabelas_do_navi_i(self):
        referencias = pacote.Referencias(None)
        self.assertFalse(referencias.disponivel)
        self.assertEqual(referencias.porto('CNNGB'), 'CNNGB')
        self.assertEqual(referencias.posicao_ncm('66019100'), '')

    def test_base_sem_as_colunas_do_frete(self):
        """Base em que o M2 do Mercante não chegou: o CE sai sem o frete."""
        session = mock.Mock()
        with mock.patch.object(pacote, '_consulta_conhecimento',
                               side_effect=[OperationalError('SELECT', {}, Exception('Unknown column')), 'CE']):
            self.assertEqual(pacote.carrega_conhecimento(session, CE1), 'CE')
        session.rollback.assert_called_once()


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
