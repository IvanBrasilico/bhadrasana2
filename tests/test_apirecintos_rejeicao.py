"""Validação de campos e tabela de rejeição da API Recintos (apirecintos_registros_rejeitados).

Cobre o caso real que motivou a tabela: número de contêiner com 12 caracteres enviado por um
recinto, que gerava erro MySQL 1406 e fazia rollback do lote inteiro.
"""
import json
import sys
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '.')

from bhadrasana.models import Base  # noqa: E402
from bhadrasana.models.apirecintos import (  # noqa: E402
    InspecaoNaoInvasiva, RegistroRejeitado, persiste_df, persiste_rejeitados, processa_json,
    valida_numero_conteiner)

CHAVE_UNICA = ['numeroConteiner', 'dataHoraOcorrencia']
CONTEINER_VALIDO = 'CAAU2235240'
CONTEINER_12_CARACTERES = 'CAAUU2235240'  # caso real do recinto 7961304 (erro MySQL 1406)


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


def lote(*eventos):
    return json.dumps(list(eventos))


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine, [InspecaoNaoInvasiva.__table__, RegistroRejeitado.__table__])
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


class TestProcessaJsonRejeicao:

    def test_separa_rejeitado_e_mantem_validos(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES),
                 evento_inspecao(CONTEINER_VALIDO, '2026-09-29T16:00:00')),
            InspecaoNaoInvasiva, CHAVE_UNICA)
        assert list(df_eventos['numeroConteiner']) == [CONTEINER_VALIDO]
        assert len(rejeitados) == 1
        rejeitado = rejeitados[0]
        assert rejeitado.nomeTabela == 'apirecintos_inspecoesnaoinvasivas'
        assert rejeitado.nomeColuna == 'numeroConteiner'
        assert rejeitado.valorColuna == CONTEINER_12_CARACTERES
        assert rejeitado.motivo == 'TAMANHO_EXCEDIDO'
        assert rejeitado.tipoEvento == '25'
        assert rejeitado.codigoRecinto == '7961304'
        assert rejeitado.tipoOperacao == 'I'
        assert rejeitado.dataHoraOcorrencia == datetime(2026, 9, 29, 15, 13, 18)
        assert rejeitado.dataHoraTransmissao == datetime(2026, 9, 29, 15, 26, 59)

    def test_lote_so_com_rejeitados_nao_quebra(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES)), InspecaoNaoInvasiva, CHAVE_UNICA)
        assert df_eventos.empty
        assert len(rejeitados) == 1

    def test_lote_sem_problemas_nao_gera_rejeicao(self):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_VALIDO)), InspecaoNaoInvasiva, CHAVE_UNICA)
        assert len(df_eventos) == 1
        assert rejeitados == []


class TestPersisteRejeitados:

    def test_grava_rejeitados_e_eventos_validos(self, session):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES),
                 evento_inspecao(CONTEINER_VALIDO, '2026-09-29T16:00:00')),
            InspecaoNaoInvasiva, CHAVE_UNICA)
        assert persiste_rejeitados(rejeitados, session) == 1
        persiste_df(df_eventos, InspecaoNaoInvasiva, session)
        assert session.query(RegistroRejeitado).count() == 1
        gravados = session.query(InspecaoNaoInvasiva).all()
        assert [e.numeroConteiner for e in gravados] == [CONTEINER_VALIDO]

    def test_reenvio_nao_duplica_rejeicao(self, session):
        for _ in range(2):
            _, rejeitados = processa_json(
                lote(evento_inspecao(CONTEINER_12_CARACTERES)), InspecaoNaoInvasiva, CHAVE_UNICA)
            persiste_rejeitados(rejeitados, session)
        assert session.query(RegistroRejeitado).count() == 1

    def test_evento_repetido_no_mesmo_lote_gera_uma_rejeicao(self, session):
        _, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES),
                 evento_inspecao(CONTEINER_12_CARACTERES)),
            InspecaoNaoInvasiva, CHAVE_UNICA)
        assert len(rejeitados) == 2
        assert persiste_rejeitados(rejeitados, session) == 1

    def test_lote_so_com_rejeitados_persiste_sem_erro(self, session):
        df_eventos, rejeitados = processa_json(
            lote(evento_inspecao(CONTEINER_12_CARACTERES)), InspecaoNaoInvasiva, CHAVE_UNICA)
        persiste_rejeitados(rejeitados, session)
        persiste_df(df_eventos, InspecaoNaoInvasiva, session)  # DataFrame vazio não pode quebrar
        assert session.query(InspecaoNaoInvasiva).count() == 0

    def test_lista_vazia_retorna_zero(self, session):
        assert persiste_rejeitados([], session) == 0

    def test_valor_longo_e_truncado(self):
        rejeitado = RegistroRejeitado('tabela', 'coluna', 'MOTIVO', valorColuna='X' * 300)
        assert len(rejeitado.valorColuna) == 255
