"""Importação de itens do TG pela planilha exportada do SECTA (formato padrão desde 24/11/2026).

A planilha de teste é gerada na hora, com dados fictícios, no layout da exportação: uma aba
"Sheet0", cabeçalho na linha 1 e as colunas de COLUNAS_SECTA.
"""
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.models.ovr import metadata, TGOVR, ItemTG
from bhadrasana.models.ovrmanager import (AVISO_DOLAR_SEM_TAXA, alerta_unidades_desconhecidas,
                                          importa_planilha_tg, indice_unidade_medida,
                                          normaliza_ncm, texto_ou_nulo)

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)

COLUNAS_SECTA = ['Linha', 'Termo', 'Taxa de Câmbio', 'Id da Mercadoria', 'Tipo de Produto', 'NCM',
                 'Marca da Mercadoria', 'Modelo da Mercadoria', 'Observações da Mercadoria',
                 'Unidade de Medida da Mercadoria', 'Quantidade da Mercadoria', 'Valor Item',
                 'Valor do Veículo', 'II', 'IPI', 'PISPASEP', 'COFINS', 'ICMS', 'IpiEsp',
                 'PisPasepEsp', 'CofinsEsp', 'Cide']


def linha_secta(linha, ncm, descricao, qtde=10, valor=2.0, unidade='UN', taxa=5.0,
                tipo='*[OUTROS (DEMAIS TIPOS)]', marca=' ', modelo=' '):
    return [linha, '123456/2026', taxa, 90000000 + linha, tipo, ncm,
            marca, modelo, descricao, unidade, qtde, valor, '', 18, 15, 2.1, 9.65, 18,
            0, 0, 0, 0]


def grava_planilha_secta(caminho, linhas):
    pd.DataFrame(linhas, columns=COLUNAS_SECTA).to_excel(caminho, index=False,
                                                         sheet_name='Sheet0')


COLUNAS_FMA = ['Nº Item', 'Não preencher', 'NCM', 'Não preencher', 'Não preencher',
               'DESCRIÇÃO MARCA MODELO COMPOSIÇÃO Nº SÉRIE ', 'Unidade de Medida', 'QTDE',
               'Preço USD']


def grava_planilha_fma(caminho, linhas):
    """Aba "3-UPLOAD SECTA" da planilha de FMA: preço em dólar, sem taxa de câmbio."""
    enchimento = [['-', '-', '-', ' ', ' ', '-', '-', '-', '-']] * 3
    pd.DataFrame(linhas + enchimento).to_excel(caminho, index=False, header=COLUNAS_FMA,
                                               sheet_name='3-UPLOAD SECTA')


COLUNAS_SAFIRA = ['Código NCM', 'Unid. Medida', 'Modelo', 'Descrição', 'Valor Unitário',
                  'Quantidade', 'Marca']


def grava_planilha_safira(caminho, linhas):
    """Layout antigo (Safira): descrição, marca e modelo em colunas próprias, valor em reais."""
    pd.DataFrame(linhas, columns=COLUNAS_SAFIRA).to_excel(caminho, index=False)


class TextoOuNuloTestCase(unittest.TestCase):

    def test_em_branco_vira_nulo(self):
        for valor in (None, '', ' ', '   '):
            self.assertIsNone(texto_ou_nulo(valor), repr(valor))

    def test_tira_espacos_das_pontas_e_aceita_numero(self):
        self.assertEqual(texto_ou_nulo('  MODELO X '), 'MODELO X')
        self.assertEqual(texto_ou_nulo(5523), '5523')

    def test_corta_no_tamanho_da_coluna(self):
        self.assertEqual(len(texto_ou_nulo('A' * 300)), 200)
        self.assertEqual(texto_ou_nulo('ABCDEF', tamanho=3), 'ABC')


class NormalizaNCMTestCase(unittest.TestCase):

    def test_numero_que_perdeu_o_zero_a_esquerda(self):
        self.assertEqual(normaliza_ncm(9012100), '09012100')
        self.assertEqual(normaliza_ncm(1012100), '01012100')
        self.assertEqual(normaliza_ncm(np.int64(9012100)), '09012100')

    def test_float_inteiro_nao_ganha_digito(self):
        self.assertEqual(normaliza_ncm(9012100.0), '09012100')
        self.assertEqual(normaliza_ncm(70139900.0), '70139900')
        self.assertEqual(normaliza_ncm(np.float64(9012100.0)), '09012100')

    def test_ncm_completo_fica_igual(self):
        self.assertEqual(normaliza_ncm(70139900), '70139900')
        self.assertEqual(normaliza_ncm('70139900'), '70139900')
        self.assertEqual(normaliza_ncm('7013.99.00'), '70139900')
        self.assertEqual(normaliza_ncm('0901.21.00'), '09012100')

    def test_texto_de_sete_digitos_ganha_o_zero(self):
        self.assertEqual(normaliza_ncm('9012100'), '09012100')

    def test_niveis_parciais(self):
        self.assertEqual(normaliza_ncm('7013'), '7013')
        self.assertEqual(normaliza_ncm('090121'), '090121')
        self.assertEqual(normaliza_ncm(901), '0901')
        self.assertEqual(normaliza_ncm(90121), '090121')

    def test_mais_de_oito_digitos_e_cortado(self):
        self.assertEqual(normaliza_ncm('701399001234'), '70139900')
        self.assertEqual(normaliza_ncm('123456789'), '12345678')


class UnidadeMedidaTestCase(unittest.TestCase):

    def test_unidades_conhecidas_em_varias_grafias(self):
        for texto in ('UN', 'un', ' Un ', 'UN.', 'UNIDADE', 'unidades', 'UND', 'Unid.'):
            self.assertEqual(indice_unidade_medida(texto), 0, texto)
        for texto in ('KG', 'kg', 'Kg.', 'QUILO', 'quilograma', 'Quilogramas', 'KGS'):
            self.assertEqual(indice_unidade_medida(texto), 1, texto)

    def test_unidades_desconhecidas(self):
        for texto in ('PAR', 'DUZIA', 'L', 'M2', '', '   ', None, 5):
            self.assertIsNone(indice_unidade_medida(texto), repr(texto))

    def test_aviso_lista_unidades_e_linhas(self):
        aviso = alerta_unidades_desconhecidas({'PAR': [3, 5], 'DUZIA': [4]})
        self.assertIn('gravada como UN', aviso)
        self.assertIn('"PAR" (linhas 3, 5)', aviso)
        self.assertIn('"DUZIA" (linha 4)', aviso)
        self.assertIn('O sistema só conhece UN e KG.', aviso)

    def test_aviso_resume_muitas_linhas_e_escapa_html(self):
        aviso = alerta_unidades_desconhecidas({'<b>CX</b>': list(range(2, 12))})
        self.assertIn('(linhas 2, 3, 4, 5, 6 e mais 5)', aviso)
        self.assertIn('&lt;b&gt;CX&lt;/b&gt;', aviso)
        self.assertNotIn('<b>', aviso)


class ImportaPlanilhaSectaTestCase(unittest.TestCase):

    def setUp(self):
        self.tg = TGOVR()
        self.tg.numerolote = 'TESTE'
        self.tg.descricao = 'TG de teste'
        session.add(self.tg)
        session.commit()
        self.pasta = tempfile.mkdtemp()
        self.planilha = os.path.join(self.pasta, 'exportacao_secta.xlsx')

    def tearDown(self):
        # A importação não fecha a planilha; no Windows o arquivo fica travado.
        shutil.rmtree(self.pasta, ignore_errors=True)

    def itens(self):
        consulta = session.query(ItemTG).filter(ItemTG.tg_id == self.tg.id)
        return consulta.order_by(ItemTG.numero).all()

    def test_ncm_dos_capitulos_01_a_09_recupera_o_zero(self):
        grava_planilha_secta(self.planilha, [
            linha_secta(1, 9012100, 'CAFÉ TORRADO EM GRÃO, MARCA FICTÍCIA'),
            linha_secta(2, 1012100, 'CAVALO REPRODUTOR DE RAÇA PURA'),
            linha_secta(3, 70139900, 'TRAVESSA DE VIDRO, MARCA FICTÍCIA'),
        ])
        importa_planilha_tg(session, self.tg, self.planilha)
        itens = self.itens()
        self.assertEqual(len(itens), 3)
        self.assertEqual([item.ncm for item in itens], ['09012100', '01012100', '70139900'])

    def test_campos_do_item_e_conversao_pela_taxa_de_cambio(self):
        grava_planilha_secta(self.planilha, [
            linha_secta(1, 70139900, 'TRAVESSA DE VIDRO, MARCA FICTÍCIA',
                        qtde=138, valor=3.49, unidade='UN', taxa=5.584),
            linha_secta(2, 70133700, 'COPO DE VIDRO, MARCA FICTÍCIA',
                        qtde=12.5, valor=2.0, unidade='KG', taxa=5.584),
        ])
        importa_planilha_tg(session, self.tg, self.planilha)
        primeiro, segundo = self.itens()
        self.assertEqual(primeiro.descricao, 'TRAVESSA DE VIDRO, MARCA FICTÍCIA')
        self.assertEqual(primeiro.qtde, Decimal('138'))
        self.assertEqual(primeiro.valor, Decimal('19.49'))  # 3,49 x 5,584
        self.assertEqual(primeiro.get_unidadedemedida, 'UN')
        self.assertEqual(segundo.qtde, Decimal('12.5'))
        self.assertEqual(segundo.valor, Decimal('11.17'))  # 2,00 x 5,584
        self.assertEqual(segundo.get_unidadedemedida, 'KG')

    def test_marca_e_modelo_preenchidos_sao_gravados(self):
        grava_planilha_secta(self.planilha, [
            linha_secta(1, 91021100, 'CAIXA EM AÇO', tipo='RELÓGIO DE PULSO',
                        marca='MARCA FICTÍCIA', modelo='MODELO X'),
        ])
        importa_planilha_tg(session, self.tg, self.planilha)
        (item,) = self.itens()
        self.assertEqual(item.contramarca, 'MARCA FICTÍCIA')
        self.assertEqual(item.modelo, 'MODELO X')
        # a descrição continua composta por tipo, marca, modelo e observações
        self.assertEqual(item.descricao,
                         'RELÓGIO DE PULSO MARCA FICTÍCIA MODELO X CAIXA EM AÇO')

    def test_marca_e_modelo_em_branco_ficam_nulos(self):
        grava_planilha_secta(self.planilha, [
            linha_secta(1, 70139900, 'TRAVESSA DE VIDRO FICTÍCIA'),  # um espaço em cada
            linha_secta(2, 70139900, 'COPO DE VIDRO FICTÍCIO', marca='', modelo=''),
            linha_secta(3, 70139900, 'JARRA DE VIDRO FICTÍCIA', marca=' MARCA ', modelo=' M1 '),
        ])
        importa_planilha_tg(session, self.tg, self.planilha)
        self.assertEqual([(item.contramarca, item.modelo) for item in self.itens()],
                         [(None, None), (None, None), ('MARCA', 'M1')])

    def test_layout_antigo_grava_marca_e_modelo_e_reimportar_nao_duplica(self):
        grava_planilha_safira(self.planilha, [
            [38249090, 'UN', 'MODELO Y ', 'POLIUREIA FICTÍCIA', 500.0, 2, 'MARCA FICTÍCIA'],
            [38249090, 'KG', None, 'RESINA FICTÍCIA', 10.0, 5, None],
        ])
        importa_planilha_tg(session, self.tg, self.planilha)
        importa_planilha_tg(session, self.tg, self.planilha)
        itens = self.itens()
        self.assertEqual([(item.descricao, item.contramarca, item.modelo) for item in itens],
                         [('POLIUREIA FICTÍCIA', 'MARCA FICTÍCIA', 'MODELO Y'),
                          ('RESINA FICTÍCIA', None, None)])

    def test_sucesso_no_formato_padrao_nao_gera_aviso(self):
        grava_planilha_secta(self.planilha, [
            linha_secta(1, 70139900, 'TRAVESSA DE VIDRO FICTÍCIA'),
        ])
        self.assertEqual(importa_planilha_tg(session, self.tg, self.planilha), '')

    def test_falta_de_coluna_que_muda_o_resultado_avisa(self):
        linhas = pd.DataFrame([linha_secta(1, 70139900, 'TRAVESSA DE VIDRO FICTÍCIA')],
                              columns=COLUNAS_SECTA)
        linhas.drop(columns=['NCM']).to_excel(self.planilha, index=False, sheet_name='Sheet0')
        aviso = importa_planilha_tg(session, self.tg, self.planilha)
        self.assertEqual(aviso, 'Campo ncm(Código NCM, NCM) não encontrado.')
        self.assertEqual(len(self.itens()), 1)

    def test_planilha_de_fma_em_dolar_sem_taxa_de_cambio_avisa(self):
        grava_planilha_fma(self.planilha, [
            [1, '*[OUTROS (DEMAIS TIPOS)]', 85013210, None, ' ', 'MOTOR FICTÍCIO', 'UN', 1, 500],
        ])
        aviso = importa_planilha_tg(session, self.tg, self.planilha)
        self.assertEqual(aviso, AVISO_DOLAR_SEM_TAXA)
        (item,) = self.itens()
        self.assertEqual(item.valor, Decimal('500'))  # gravado em dólar, sem conversão

    def test_unidade_desconhecida_grava_un_e_avisa(self):
        grava_planilha_secta(self.planilha, [
            linha_secta(1, 70139900, 'ITEM EM UNIDADE', unidade='UN'),
            linha_secta(2, 64039990, 'SAPATO FICTÍCIO', unidade='PAR'),
            linha_secta(3, 70139900, 'ITEM EM DÚZIA', unidade='DUZIA'),
            linha_secta(4, 64039990, 'OUTRO SAPATO FICTÍCIO', unidade='par'),
            linha_secta(5, 9012100, 'CAFÉ FICTÍCIO', unidade='Quilograma'),
        ])
        aviso = importa_planilha_tg(session, self.tg, self.planilha)
        itens = self.itens()
        self.assertEqual(len(itens), 5)
        self.assertEqual([item.get_unidadedemedida for item in itens],
                         ['UN', 'UN', 'UN', 'UN', 'KG'])
        self.assertTrue(aviso.startswith('Unidade de medida não reconhecida'), aviso)
        self.assertIn('"PAR" (linha 3)', aviso)
        self.assertIn('"par" (linha 5)', aviso)
        self.assertIn('"DUZIA" (linha 4)', aviso)

    def test_sem_aviso_de_unidade_quando_todas_sao_conhecidas(self):
        grava_planilha_secta(self.planilha, [
            linha_secta(1, 70139900, 'ITEM EM UNIDADE', unidade='UN.'),
            linha_secta(2, 9012100, 'CAFÉ FICTÍCIO', unidade='kg'),
        ])
        aviso = importa_planilha_tg(session, self.tg, self.planilha)
        self.assertNotIn('Unidade de medida', aviso)
        self.assertEqual([item.get_unidadedemedida for item in self.itens()], ['UN', 'KG'])


if __name__ == '__main__':
    unittest.main()
