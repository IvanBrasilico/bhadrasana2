"""Validação de campos e tabela de rejeição da API Recintos (apirecintos_registros_rejeitados).

Cobre os casos reais que motivaram a tabela:
- número de contêiner com 12 caracteres (recinto 7961304): coluna de identidade, evento rejeitado;
- placa de semirreboque com 19 caracteres (recinto 6913201): coluna auxiliar, campo anulado e
  evento mantido;
- placa de semirreboque com М cirílico (recinto 8931404): charset latin1, campo normalizado e
  evento mantido;
- contêiner válido com espaço no meio, em pesagem (recinto 6913201): limpo no mapeamento e
  gravado, sem rejeição.
Antes, todos geravam erro MySQL (1406 ou 1366) e rollback do lote inteiro. A rede genérica de
tamanho (TestTamanhoGenerico) cobre as demais colunas de texto de todos os eventos.
"""
import json
import sys
from datetime import datetime

import pandas as pd
import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '.')

from bhadrasana.models import Base  # noqa: E402
from bhadrasana.models.apirecintos import (  # noqa: E402
    ACAO_CAMPO_ANULADO, ACAO_CAMPO_NORMALIZADO, ACAO_EVENTO_REJEITADO, AcessoVeiculo,
    EmbarqueDesembarque, InspecaoNaoInvasiva, PesagemVeiculo, RegistroRejeitado,
    limpa_numero_conteiner, persiste_df, persiste_rejeitados, processa_json,
    valida_numero_conteiner, valida_placa)

CLASSES_EVENTO = [AcessoVeiculo, PesagemVeiculo, EmbarqueDesembarque, InspecaoNaoInvasiva]

CHAVE_INSPECAO = ['numeroConteiner', 'dataHoraOcorrencia']
CHAVE_PESAGEM = ['placa', 'dataHoraOcorrencia']
CHAVE_ACESSO = ['placa', 'operacao', 'tipoOperacao', 'dataHoraOcorrencia']
CHAVE_EMBARQUE = ['numeroConteiner', 'dataHoraOcorrencia']
CONTEINER_VALIDO = 'CAAU2235240'
CONTEINER_12_CARACTERES = 'CAAUU2235240'  # caso real do recinto 7961304 (erro MySQL 1406)
CONTEINER_COM_ESPACO = 'UETU 5244953'  # caso real do recinto 6913201, em pesagem (erro 1406)
PLACA_VALIDA = '5767UDC'
PLACA_SEMIRREBOQUE_LIXO = '5767UDCSEMIRREBOQUE'  # caso real do recinto 6913201 (erro MySQL 1406)
PLACA_SEMIRREBOQUE_CIRILICA = 'МIO3H52'  # caso real do recinto 8931404 (erro MySQL 1366)


def evento_inspecao(numero_conteiner, data_hora_ocorrencia='2026-09-29T15:13:18'):
    """Evento tipo 25 no formato que chega em processa_json (após limpa_json_apirecintos)."""
    return {
        'dadosTransmissao': {'tipoEvento': 25, 'dataHoraTransmissao': '2026-09-29T15:26:59'},
        'jsonOriginal': {
            'codigoRecinto': '7961304',
            'tipoOperacao': 'I',
            'contingencia': True,
            'dataHoraOcorrencia': data_hora_ocorrencia,
            'vazio': False,
            'listaConteineresUld': [{'numeroConteiner': numero_conteiner,
                                     'ocrNumero': True, 'tipo': '22G1'}],
        },
    }


def evento_pesagem(placa, placa_semirreboque, data_hora_ocorrencia='2026-10-01T16:01:12',
                   numero_conteiner=None):
    """Evento tipo 3 (PesagemVeiculo), com os valores do caso real do recinto 6913201."""
    return {
        'dadosTransmissao': {'tipoEvento': 3, 'dataHoraTransmissao': '2026-10-01T13:01:18'},
        'jsonOriginal': {
            'codigoRecinto': '6913201',
            'tipoOperacao': 'I',
            'contingencia': False,
            'dataHoraOcorrencia': data_hora_ocorrencia,
            'pesoBrutoBalanca': 42780.0,
            'pesoBrutoManifesto': 0.0,
            'taraConjunto': 13630.0,
            'capturaAutoPeso': False,
            'placa': placa,
            'listaConteineresUld': [{'numeroConteiner': numero_conteiner}] if numero_conteiner
            else [],
            'listaSemirreboque': [{'placa': placa_semirreboque, 'tara': 8000.0}],
        },
    }


def evento_acesso(placa_semirreboque, nome_motorista='ROBERT GABRIEL COFFANI CRESPO',
                  numero_conteiner='KOCU4207306', operacao='C', tipo_operacao='I'):
    """Evento tipo 1 (AcessoVeiculo), com os valores do caso real do recinto 8931404."""
    return {
        'dadosTransmissao': {'tipoEvento': 1, 'dataHoraTransmissao': '2026-10-05T01:14:53'},
        'jsonOriginal': {
            'codigoRecinto': '8931404',
            'tipoOperacao': tipo_operacao,
            'contingencia': False,
            'dataHoraOcorrencia': '2026-10-05T01:11:54',
            'operacao': operacao,
            'direcao': 'S',
            'placa': 'GIA6H99',
            'ocrPlaca': True,
            'cnpjTransportador': '08011564000131',
            'motorista': {'cpf': '45886730842', 'nome': nome_motorista},
            'listaConteineresUld': [{'numeroConteiner': numero_conteiner,
                                     'ocrNumero': True, 'tipo': '45G1'}],
            'listaSemirreboque': [{'placa': placa_semirreboque, 'ocrPlaca': True}],
            'listaDeclaracaoAduaneira': [{'tipo': 'DUIMP', 'numeroDeclaracao': '26BR00018703179'}],
            'listaManifestos': [{'listaConhecimentos': [{'tipo': 'CE_MERCANTE',
                                                         'numero': '152605302165469'}]}],
        },
    }


def evento_embarque(numero_conteiner, viagem='123456789'):
    """Evento tipo 4 (EmbarqueDesembarque). numero_conteiner None simula carga solta."""
    return {
        'dadosTransmissao': {'tipoEvento': 4, 'dataHoraTransmissao': '2026-10-08T10:05:00'},
        'jsonOriginal': {
            'codigoRecinto': '8931356',
            'tipoOperacao': 'I',
            'contingencia': False,
            'dataHoraOcorrencia': '2026-10-08T10:00:00',
            'viagem': viagem,
            'escala': '26000123456',
            'embarqueDesembarque': 'D',
            'pesoBrutoBalanca': 21000.0,
            'numeroConteiner': numero_conteiner,
            'tipoConteiner': '45G1',
        },
    }


def lote(*eventos):
    return json.dumps(list(eventos))


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine, [classe.__table__ for classe in CLASSES_EVENTO] +
                             [RegistroRejeitado.__table__])
    sessao = sessionmaker(bind=engine)()
    yield sessao
    sessao.close()


class TestValidaNumeroConteiner:

    @pytest.mark.parametrize('numero', [CONTEINER_VALIDO, 'MSKU1234567', None, ''])
    def test_aceita_valido_ou_ausente(self, numero):
        assert valida_numero_conteiner(numero) is None

    def test_tamanho_excedido(self):
        motivo, detalhe = valida_numero_conteiner(CONTEINER_12_CARACTERES)
        assert motivo == 'TAMANHO_EXCEDIDO'
        assert '12' in detalhe

    @pytest.mark.parametrize('numero', ['CAAU223524', 'caau2235240', 'CAA12235240',
                                        'CAAU223524A', '12345678901', 'CAAU 235240',
                                        'МSKU1234567',  # М cirílico: não é ASCII
                                        'CAAU٢235240'])  # dígito árabe: não é [0-9]
    def test_formato_invalido(self, numero):
        motivo, _ = valida_numero_conteiner(numero)
        assert motivo == 'FORMATO_INVALIDO'


class TestValidaPlaca:

    @pytest.mark.parametrize('placa', ['ABC1234', 'ABC1D23',  # Brasil antiga e Mercosul
                                       'AB123CD', 'ABCD123',  # Argentina, Paraguai
                                       None, ''])
    def test_aceita_valida_ou_ausente(self, placa):
        assert valida_placa(placa) is None

    def test_tamanho_excedido(self):
        motivo, detalhe = valida_placa(PLACA_SEMIRREBOQUE_LIXO)
        assert motivo == 'TAMANHO_EXCEDIDO'
        assert '19' in detalhe

    @pytest.mark.parametrize('placa', ['ABC-123', PLACA_SEMIRREBOQUE_CIRILICA])
    def test_formato_invalido_estrito_a_ascii(self, placa):
        motivo, _ = valida_placa(placa)
        assert motivo == 'FORMATO_INVALIDO'


class TestColunaIdentidadeRejeitaEvento:

    def test_separa_rejeitado_e_mantem_validos(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES),
                 evento_inspecao(CONTEINER_VALIDO, '2026-09-29T16:00:00')),
            InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert list(df_eventos['numeroConteiner']) == [CONTEINER_VALIDO]
        assert len(rejeitados) == 1
        rejeitado = rejeitados[0]
        assert rejeitado.nomeTabela == 'apirecintos_inspecoesnaoinvasivas'
        assert rejeitado.nomeColuna == 'numeroConteiner'
        assert rejeitado.valorColuna == CONTEINER_12_CARACTERES
        assert rejeitado.motivo == 'TAMANHO_EXCEDIDO'
        assert rejeitado.detalhe.endswith(ACAO_EVENTO_REJEITADO)
        assert rejeitado.tipoEvento == '25'
        assert rejeitado.codigoRecinto == '7961304'
        assert rejeitado.tipoOperacao == 'I'
        assert rejeitado.dataHoraOcorrencia == datetime(2026, 9, 29, 15, 13, 18)
        assert rejeitado.dataHoraTransmissao == datetime(2026, 9, 29, 15, 26, 59)

    def test_lote_so_com_rejeitados_nao_quebra(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES)), InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert df_eventos.empty
        assert len(rejeitados) == 1

    def test_lote_sem_problemas_nao_gera_rejeicao(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_VALIDO)), InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert len(df_eventos) == 1
        assert rejeitados == []

    def test_placa_principal_da_pesagem_e_identidade(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_pesagem(PLACA_SEMIRREBOQUE_LIXO, 'ABC1234')),
            PesagemVeiculo, CHAVE_PESAGEM)
        assert df_eventos.empty
        assert len(rejeitados) == 1
        assert rejeitados[0].nomeColuna == 'placa'
        assert rejeitados[0].detalhe.endswith(ACAO_EVENTO_REJEITADO)


class TestColunaAuxiliarAnulaCampo:

    def test_anula_campo_e_mantem_evento(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_pesagem(PLACA_VALIDA, PLACA_SEMIRREBOQUE_LIXO)),
            PesagemVeiculo, CHAVE_PESAGEM)
        assert len(df_eventos) == 1
        assert df_eventos.iloc[0]['placa'] == PLACA_VALIDA
        assert pd.isna(df_eventos.iloc[0]['placaSemirreboque'])
        assert len(rejeitados) == 1
        rejeitado = rejeitados[0]
        assert rejeitado.nomeTabela == 'apirecintos_pesagensveiculo'
        assert rejeitado.nomeColuna == 'placaSemirreboque'
        assert rejeitado.valorColuna == PLACA_SEMIRREBOQUE_LIXO
        assert rejeitado.motivo == 'TAMANHO_EXCEDIDO'
        assert rejeitado.detalhe.endswith(ACAO_CAMPO_ANULADO)
        assert rejeitado.tipoEvento == '3'
        assert rejeitado.codigoRecinto == '6913201'
        assert rejeitado.dataHoraOcorrencia == datetime(2026, 10, 1, 16, 1, 12)

    def test_persiste_evento_sem_o_campo(self, session):
        df_eventos, rejeitados = processa_json(
            lote(evento_pesagem(PLACA_VALIDA, PLACA_SEMIRREBOQUE_LIXO)),
            PesagemVeiculo, CHAVE_PESAGEM)
        assert persiste_rejeitados(rejeitados, session) == 1
        persiste_df(df_eventos, PesagemVeiculo, session)
        pesagem = session.query(PesagemVeiculo).one()
        assert pesagem.placa == PLACA_VALIDA
        assert pesagem.placaSemirreboque is None
        assert float(pesagem.pesoBrutoBalanca) == 42780.0
        assert session.query(RegistroRejeitado).count() == 1

    def test_identidade_e_auxiliar_invalidos_no_mesmo_evento(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_pesagem(PLACA_SEMIRREBOQUE_LIXO, PLACA_SEMIRREBOQUE_LIXO)),
            PesagemVeiculo, CHAVE_PESAGEM)
        assert df_eventos.empty
        assert sorted(r.nomeColuna for r in rejeitados) == ['placa', 'placaSemirreboque']

    def test_placa_da_inspecao_e_auxiliar(self):
        evento = evento_inspecao(CONTEINER_VALIDO)
        evento['jsonOriginal']['placa'] = PLACA_SEMIRREBOQUE_LIXO
        df_eventos, rejeitados = processa_json(lote(evento), InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert list(df_eventos['numeroConteiner']) == [CONTEINER_VALIDO]
        assert pd.isna(df_eventos.iloc[0]['placa'])
        assert [r.nomeColuna for r in rejeitados] == ['placa']
        assert rejeitados[0].detalhe.endswith(ACAO_CAMPO_ANULADO)


class TestNormalizacaoCharset:
    """Normalização genérica de todas as colunas de texto (EventoAPIBase.normaliza_textos)."""

    def test_homoglifo_corrigido_e_evento_mantido(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso(PLACA_SEMIRREBOQUE_CIRILICA)), AcessoVeiculo, CHAVE_ACESSO)
        assert len(df_eventos) == 1
        assert df_eventos.iloc[0]['placaSemirreboque'] == 'MIO3H52'
        assert len(rejeitados) == 1
        rejeitado = rejeitados[0]
        assert rejeitado.nomeTabela == 'apirecintos_acessosveiculo'
        assert rejeitado.nomeColuna == 'placaSemirreboque'
        assert rejeitado.motivo == 'ENCODING_INVALIDO'
        # Evidência em ASCII: a própria tabela de rejeição é latin1
        assert rejeitado.valorColuna == '\\u041cIO3H52'
        assert rejeitado.detalhe == '\\u041c -> M. ' + ACAO_CAMPO_NORMALIZADO
        assert rejeitado.tipoEvento == '1'
        assert rejeitado.codigoRecinto == '8931404'

    def test_persiste_placa_corrigida(self, session):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso(PLACA_SEMIRREBOQUE_CIRILICA)), AcessoVeiculo, CHAVE_ACESSO)
        assert persiste_rejeitados(rejeitados, session) == 1
        persiste_df(df_eventos, AcessoVeiculo, session)
        acesso = session.query(AcessoVeiculo).one()
        assert acesso.placaSemirreboque == 'MIO3H52'
        assert acesso.placa == 'GIA6H99'
        assert acesso.numeroConteiner == 'KOCU4207306'

    def test_homoglifo_em_coluna_de_identidade_corrigido_antes_do_validador(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao('КOCU4207306')),  # К cirílico
            InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert list(df_eventos['numeroConteiner']) == ['KOCU4207306']
        assert [r.motivo for r in rejeitados] == ['ENCODING_INVALIDO']

    def test_sem_equivalente_em_identidade_rejeita_evento(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao('汉OCU4207306')),  # ideograma: vira '?' e o validador barra
            InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert df_eventos.empty
        assert [r.motivo for r in rejeitados] == ['ENCODING_INVALIDO', 'FORMATO_INVALIDO']
        assert rejeitados[1].valorColuna == '?OCU4207306'
        assert rejeitados[1].detalhe.endswith(ACAO_EVENTO_REJEITADO)

    def test_nome_em_outro_alfabeto_vira_marca_e_evento_mantido(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso('ABC1234', nome_motorista='汉字 SILVA')),
            AcessoVeiculo, CHAVE_ACESSO)
        assert df_eventos.iloc[0]['nomeMotorista'] == '?? SILVA'
        assert [r.nomeColuna for r in rejeitados] == ['nomeMotorista']
        assert rejeitados[0].valorColuna == '\\u6c49\\u5b57 SILVA'

    def test_acento_do_portugues_nao_e_tocado(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso('ABC1234', nome_motorista='JOSÉ ANTÔNIO ASSUNÇÃO')),
            AcessoVeiculo, CHAVE_ACESSO)
        assert df_eventos.iloc[0]['nomeMotorista'] == 'JOSÉ ANTÔNIO ASSUNÇÃO'
        assert rejeitados == []


class TestLimpaNumeroConteiner:

    @pytest.mark.parametrize('entrada, esperado', [
        (CONTEINER_COM_ESPACO, 'UETU5244953'),
        ('uetu-524495.3', 'UETU5244953'),
        (' UETU5244953 ', 'UETU5244953'),
        ('UETU5244953', 'UETU5244953'),
        (None, None), ('', None), (' - ', None),
        (123, 123),  # não é texto: quem reprova é o validador
        ('\u041cSKU 1234567', '\u041cSKU1234567'),  # homóglifo preservado para normaliza_textos
    ])
    def test_limpa(self, entrada, esperado):
        assert limpa_numero_conteiner(entrada) == esperado


class TestNumeroConteinerEmTodasAsTabelas:
    """A mesma limpeza e a mesma regra de formato valem para os quatro eventos."""

    def test_pesagem_com_espaco_e_limpa_e_gravada(self, session):
        df_eventos, rejeitados = processa_json(
            lote(evento_pesagem('SVZ1I18', 'ELO4D21', '2026-10-08T16:45:04',
                                numero_conteiner=CONTEINER_COM_ESPACO)),
            PesagemVeiculo, CHAVE_PESAGEM)
        assert rejeitados == []  # limpar separador não é rejeição
        persiste_df(df_eventos, PesagemVeiculo, session)
        pesagem = session.query(PesagemVeiculo).one()
        assert pesagem.numeroConteiner == 'UETU5244953'
        assert pesagem.placa == 'SVZ1I18'
        assert pesagem.placaSemirreboque == 'ELO4D21'

    def test_pesagem_conteiner_invalido_anula_campo(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_pesagem(PLACA_VALIDA, 'ELO4D21',
                                numero_conteiner=CONTEINER_12_CARACTERES)),
            PesagemVeiculo, CHAVE_PESAGEM)
        assert len(df_eventos) == 1
        assert pd.isna(df_eventos.iloc[0]['numeroConteiner'])
        assert [(r.nomeColuna, r.motivo, r.valorColuna) for r in rejeitados] == [
            ('numeroConteiner', 'TAMANHO_EXCEDIDO', CONTEINER_12_CARACTERES)]
        assert rejeitados[0].detalhe.endswith(ACAO_CAMPO_ANULADO)

    def test_acesso_conteiner_invalido_anula_campo(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso('ABC1234', numero_conteiner='KOCU42073')),
            AcessoVeiculo, CHAVE_ACESSO)
        assert len(df_eventos) == 1
        assert pd.isna(df_eventos.iloc[0]['numeroConteiner'])
        assert [(r.nomeColuna, r.motivo) for r in rejeitados] == [
            ('numeroConteiner', 'FORMATO_INVALIDO')]
        assert rejeitados[0].detalhe.endswith(ACAO_CAMPO_ANULADO)

    def test_acesso_minusculo_com_separadores_e_limpo(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso('ABC1234', numero_conteiner='kocu-420730.6')),
            AcessoVeiculo, CHAVE_ACESSO)
        assert df_eventos.iloc[0]['numeroConteiner'] == 'KOCU4207306'
        assert rejeitados == []

    def test_embarque_conteiner_invalido_rejeita_evento(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_embarque(CONTEINER_12_CARACTERES)), EmbarqueDesembarque, CHAVE_EMBARQUE)
        assert df_eventos.empty
        assert [(r.nomeTabela, r.nomeColuna, r.motivo) for r in rejeitados] == [
            ('apirecintos_embarquedesembarque', 'numeroConteiner', 'TAMANHO_EXCEDIDO')]
        assert rejeitados[0].detalhe.endswith(ACAO_EVENTO_REJEITADO)

    def test_embarque_com_espaco_e_limpo(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_embarque(CONTEINER_COM_ESPACO)), EmbarqueDesembarque, CHAVE_EMBARQUE)
        assert list(df_eventos['numeroConteiner']) == ['UETU5244953']
        assert rejeitados == []

    def test_embarque_carga_solta_sem_conteiner_e_aceito(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_embarque(None)), EmbarqueDesembarque, CHAVE_EMBARQUE)
        assert len(df_eventos) == 1
        assert rejeitados == []

    def test_inspecao_com_espaco_e_limpa(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_COM_ESPACO)), InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert list(df_eventos['numeroConteiner']) == ['UETU5244953']
        assert rejeitados == []


class TestTamanhoGenerico:
    """Rede genérica contra o erro 1406 em qualquer coluna (EventoAPIBase._valida_tamanhos)."""

    def test_coluna_auxiliar_sem_regra_e_anulada(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_embarque(CONTEINER_VALIDO, viagem='1234567890AB')),
            EmbarqueDesembarque, CHAVE_EMBARQUE)
        assert len(df_eventos) == 1
        assert pd.isna(df_eventos.iloc[0]['viagem'])
        assert df_eventos.iloc[0]['numeroConteiner'] == CONTEINER_VALIDO
        rejeitado, = rejeitados
        assert rejeitado.nomeColuna == 'viagem'
        assert rejeitado.valorColuna == '1234567890AB'
        assert rejeitado.motivo == 'TAMANHO_EXCEDIDO'
        assert rejeitado.detalhe == 'Esperado até 9 caracteres, recebido 12. ' + ACAO_CAMPO_ANULADO

    def test_coluna_da_chave_unica_rejeita_evento(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso('ABC1234', tipo_operacao='XX')), AcessoVeiculo, CHAVE_ACESSO)
        assert df_eventos.empty
        rejeitado, = rejeitados
        assert rejeitado.nomeColuna == 'tipoOperacao'
        assert rejeitado.motivo == 'TAMANHO_EXCEDIDO'
        assert rejeitado.detalhe.endswith(ACAO_EVENTO_REJEITADO)

    def test_colunas_da_chave_unica_vem_da_tabela(self):
        assert PesagemVeiculo._colunas_chave_unica() == {
            'placa', 'dataHoraOcorrencia', 'dataHoraTransmissao'}
        assert InspecaoNaoInvasiva._colunas_chave_unica() == {
            'numeroConteiner', 'dataHoraOcorrencia'}

    @pytest.mark.parametrize('classe', CLASSES_EVENTO)
    def test_nenhum_texto_sai_maior_que_a_coluna(self, classe):
        """Vale para toda coluna de texto de todo evento, inclusive as criadas no futuro."""
        chave_unica = classe._colunas_chave_unica()
        colunas = [coluna for coluna in classe.__table__.columns
                   if isinstance(coluna.type, String) and coluna.name not in chave_unica]
        evento = classe()
        for coluna in colunas:
            setattr(evento, coluna.name, 'X' * (coluna.type.length + 1))
        rejeicoes = evento.valida_campos()
        assert not any(rejeicao.rejeita_evento for rejeicao in rejeicoes)
        assert {rejeicao.nomeColuna for rejeicao in rejeicoes} == {c.name for c in colunas}
        assert all(getattr(evento, coluna.name) is None for coluna in colunas)

    @pytest.mark.parametrize('classe', CLASSES_EVENTO)
    def test_estouro_em_qualquer_coluna_da_chave_unica_rejeita_evento(self, classe):
        for nome in classe._colunas_chave_unica():
            coluna = classe.__table__.columns[nome]
            if not isinstance(coluna.type, String):
                continue
            evento = classe()
            setattr(evento, nome, 'X' * (coluna.type.length + 1))
            assert [rejeicao.rejeita_evento for rejeicao in evento.valida_campos()] == [True]

    def test_valor_no_limite_da_coluna_nao_e_tocado(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_embarque(CONTEINER_VALIDO, viagem='123456789')),
            EmbarqueDesembarque, CHAVE_EMBARQUE)
        assert df_eventos.iloc[0]['viagem'] == '123456789'
        assert rejeitados == []

    def test_agendamento_nao_e_validado_nem_registrado(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_acesso(PLACA_SEMIRREBOQUE_LIXO, operacao='G')),
            AcessoVeiculo, CHAVE_ACESSO)
        assert df_eventos.empty
        assert rejeitados == []


class TestPersisteRejeitados:

    def test_grava_rejeitados_e_eventos_validos(self, session):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES),
                 evento_inspecao(CONTEINER_VALIDO, '2026-09-29T16:00:00')),
            InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert persiste_rejeitados(rejeitados, session) == 1
        persiste_df(df_eventos, InspecaoNaoInvasiva, session)
        assert session.query(RegistroRejeitado).count() == 1
        gravados = session.query(InspecaoNaoInvasiva).all()
        assert [e.numeroConteiner for e in gravados] == [CONTEINER_VALIDO]

    def test_reenvio_nao_duplica_rejeicao(self, session):
        for _ in range(2):
            _, rejeitados = processa_json(
                lote(evento_inspecao(CONTEINER_12_CARACTERES)), InspecaoNaoInvasiva,
                CHAVE_INSPECAO)
            persiste_rejeitados(rejeitados, session)
        assert session.query(RegistroRejeitado).count() == 1

    def test_evento_repetido_no_mesmo_lote_gera_uma_rejeicao(self, session):
        _, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES),
                 evento_inspecao(CONTEINER_12_CARACTERES)),
            InspecaoNaoInvasiva, CHAVE_INSPECAO)
        assert len(rejeitados) == 2
        assert persiste_rejeitados(rejeitados, session) == 1

    def test_lote_so_com_rejeitados_persiste_sem_erro(self, session):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES)), InspecaoNaoInvasiva, CHAVE_INSPECAO)
        persiste_rejeitados(rejeitados, session)
        persiste_df(df_eventos, InspecaoNaoInvasiva, session)  # DataFrame vazio não pode quebrar
        assert session.query(InspecaoNaoInvasiva).count() == 0

    def test_lista_vazia_retorna_zero(self, session):
        assert persiste_rejeitados([], session) == 0

    def test_valor_longo_e_truncado(self):
        rejeitado = RegistroRejeitado('tabela', 'coluna', 'MOTIVO', valorColuna='X' * 300)
        assert len(rejeitado.valorColuna) == 255

    def test_valor_fora_do_charset_e_escapado(self):
        rejeitado = RegistroRejeitado('tabela', 'coluna', 'MOTIVO',
                                      valorColuna=PLACA_SEMIRREBOQUE_CIRILICA, detalhe='汉')
        assert rejeitado.valorColuna == '\\u041cIO3H52'
        assert rejeitado.detalhe == '\\u6c49'
