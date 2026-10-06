"""Normalização de charset e homóglifos dos eventos da API Recintos (apirecintos_normalizacao).

Caso real: recinto 8931404 enviou placaSemirreboque 'МIO3H52' com М cirílico (U+041C), que a
tabela latin1 recusou com erro MySQL 1366, derrubando o lote inteiro.
"""
import sys

import pytest

sys.path.insert(0, '.')

from bhadrasana.models import apirecintos_normalizacao as normalizacao  # noqa: E402
from bhadrasana.models.apirecintos_normalizacao import (  # noqa: E402
    HOMOGLIFOS, descreve_substituicoes, escapa_nao_representaveis, normaliza_texto)

M_CIRILICO = 'М'


class TestTabelaHomoglifos:

    def test_chaves_estao_fora_do_charset(self):
        """Invariante que sustenta o caminho rápido de normaliza_texto."""
        for caractere in HOMOGLIFOS:
            with pytest.raises(UnicodeEncodeError):
                caractere.encode('cp1252')

    def test_valores_sao_letras_ou_hifen_ascii(self):
        """Letra nunca vira dígito: O cirílico fica O, nunca 0."""
        for novo in HOMOGLIFOS.values():
            assert novo.isascii()
            assert novo.isalpha() or novo == '-'


class TestNormalizaTexto:

    @pytest.mark.parametrize('texto', ['MIO3H52', 'JOSÉ DA SILVA', 'Nº 1ª', 'µ', 'ÆØÅ ñ ç €',
                                       '', None])
    def test_nao_toca_no_que_e_representavel(self, texto):
        assert normaliza_texto(texto) == (texto, [])

    def test_homoglifo_cirilico(self):
        assert normaliza_texto(M_CIRILICO + 'IO3H52') == ('MIO3H52', [(M_CIRILICO, 'M')])

    def test_homoglifo_grego(self):
        assert normaliza_texto('ΑBC1234')[0] == 'ABC1234'

    def test_largura_total_via_nfkc(self):
        assert normaliza_texto('ＭＩＯ')[0] == 'MIO'

    def test_acento_fora_do_charset_via_nfkd(self):
        assert normaliza_texto('MUSTAFA ŞAHİN')[0] == 'MUSTAFA SAHIN'

    def test_invisivel_removido(self):
        assert normaliza_texto('ABC​1234') == ('ABC1234', [('​', '')])

    def test_sem_equivalente_vira_substituto(self):
        texto, substituicoes = normaliza_texto('汉字')
        assert texto == '??'
        assert substituicoes == [('汉', '?'), ('字', '?')]

    def test_hifen_unicode(self):
        assert normaliza_texto('ABC‐1234')[0] == 'ABC-1234'

    def test_pares_repetidos_listados_uma_vez(self):
        assert normaliza_texto('ООО') == ('OOO', [('О', 'O')])

    @pytest.mark.parametrize('texto', [M_CIRILICO + 'IO3H52', 'JOSÉ 汉', 'A​B',
                                       'Ｍ', 'Ş', 'ÆØÅ ñ ç €', 'Łódź'])
    def test_saida_sempre_representavel_e_idempotente(self, texto):
        novo, _ = normaliza_texto(texto)
        novo.encode('cp1252')
        assert normaliza_texto(novo) == (novo, [])

    def test_charset_none_mantem_homoglifos_ligados(self, monkeypatch):
        monkeypatch.setattr(normalizacao, 'CHARSET_BANCO', None)
        assert normaliza_texto(M_CIRILICO + 'IO3H52') == ('MIO3H52', [(M_CIRILICO, 'M')])
        assert normaliza_texto('汉') == ('汉', [])


class TestEvidencia:

    def test_escapa_so_o_que_nao_e_representavel(self):
        assert escapa_nao_representaveis(M_CIRILICO + 'IO3H52') == '\\u041cIO3H52'
        assert escapa_nao_representaveis('JOSÉ') == 'JOSÉ'
        assert escapa_nao_representaveis(None) is None

    def test_descreve_substituicoes_em_ascii(self):
        descricao = descreve_substituicoes([(M_CIRILICO, 'M'), ('​', ''), ('汉', '?')])
        assert descricao == '\\u041c -> M; \\u200b removido; \\u6c49 -> ?'
        descricao.encode('ascii')
