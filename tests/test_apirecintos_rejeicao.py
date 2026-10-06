"""Validação de campos e tabela de rejeição da API Recintos (apirecintos_registros_rejeitados).

Cobre os casos reais que motivaram a tabela:
- número de contêiner com 12 caracteres (recinto 7961304): coluna de identidade, evento rejeitado;
- placa de semirreboque com 19 caracteres (recinto 6913201): coluna auxiliar, campo anulado e
  evento mantido.
Antes, os dois geravam erro MySQL 1406 e rollback do lote inteiro.
"""
import json
import sys
from datetime import datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '.')

from bhadrasana.models import Base  # noqa: E402
from bhadrasana.models.apirecintos import (  # noqa: E402
    ACAO_CAMPO_ANULADO, ACAO_EVENTO_REJEITADO, InspecaoNaoInvasiva, PesagemVeiculo,
    RegistroRejeitado, persiste_df, persiste_rejeitados, processa_json, valida_numero_conteiner,
    valida_placa)

CHAVE_INSPECAO = ['numeroConteiner', 'dataHoraOcorrencia']
CHAVE_PESAGEM = ['placa', 'dataHoraOcorrencia']
CONTEINER_VALIDO = 'CAAU2235240'
CONTEINER_12_CARACTERES = 'CAAUU2235240'  # caso real do recinto 7961304 (erro MySQL 1406)
PLACA_VALIDA = '5767UDC'
PLACA_SEMIRREBOQUE_LIXO = '5767UDCSEMIRREBOQUE'  # caso real do recinto 6913201 (erro MySQL 1406)


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


def evento_pesagem(placa, placa_semirreboque, data_hora_ocorrencia='2026-10-01T16:01:12'):
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
            'listaSemirreboque': [{'placa': placa_semirreboque, 'tara': 8000.0}],
        },
    }


def lote(*eventos):
    return json.dumps(list(eventos))


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine, [InspecaoNaoInvasiva.__table__, PesagemVeiculo.__table__,
                                      RegistroRejeitado.__table__])
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
                                        'CAAU223524A', '12345678901', 'CAAU 235240'])
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

    def test_formato_invalido(self):
        motivo, _ = valida_placa('ABC-123')
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
