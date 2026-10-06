import json
import os
import re
import sys
import zipfile
from typing import List, Optional, Type, Tuple, Union

import numpy as np
import pandas as pd
from dateutil import parser
from dotenv import load_dotenv
from sqlalchemy import BigInteger, Column, DateTime, Boolean, Integer, String, UniqueConstraint, \
    Numeric
from sqlalchemy.exc import IntegrityError

load_dotenv()

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from ajna_commons.flask.log import logger
from bhadrasana.models import Base, BaseRastreavel, BaseDumpable

metadata = Base.metadata


def converte_datetime(str_datetime: str):
    try:
        return parser.isoparse(str_datetime).replace(tzinfo=None, microsecond=0)
    except:
        return None


class EventoAPIBase(BaseRastreavel, BaseDumpable):
    __abstract__ = True
    # with_variant: BIGINT no MySQL (inalterado); INTEGER no SQLite dos testes (autoincremento)
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    codigoRecinto = Column(String(7), index=True)
    dataHoraTransmissao = Column(DateTime(), index=True)
    dataHoraOcorrencia = Column(DateTime(), index=True)
    tipoOperacao = Column(String(1), index=True)  # I - Inclusão, R - Retificação
    contingencia = Column(Boolean(), index=True)

    # Regras de validação por coluna: {nomeColuna: validador}. O validador recebe o valor já
    # mapeado e retorna None se válido, ou (motivo, detalhe) se o evento deve ser rejeitado
    # (ver RegistroRejeitado). Subclasses sobrescrevem para declarar suas regras.
    # ATENÇÃO: o nome precisa conter '_' para não ser tratado como coluna por get_campos().
    _validadores = {}

    def valida_campos(self) -> List[Tuple[str, object, str, str]]:
        """Aplica _validadores aos campos já mapeados.

        Returns: lista de (nomeColuna, valor, motivo, detalhe). Vazia se o evento é válido.
        """
        rejeicoes = []
        for nome_coluna, validador in self._validadores.items():
            valor = getattr(self, nome_coluna, None)
            resultado = validador(valor)
            if resultado:
                motivo, detalhe = resultado
                rejeicoes.append((nome_coluna, valor, motivo, detalhe))
        return rejeicoes

    def _mapeia(self, *args, **kwargs):
        self.codigoRecinto = kwargs.get('codigoRecinto')
        self.tipoOperacao = kwargs.get('tipoOperacao')
        self.dataHoraTransmissao = converte_datetime(kwargs.get('dataHoraTransmissao'))
        self.dataHoraOcorrencia = converte_datetime(kwargs.get('dataHoraOcorrencia'))
        self.contingencia = kwargs.get('contingencia')

    def processa_json(self, json_dict):
        json_original = json_dict['jsonOriginal']
        evento_filtrado = {k: v for k, v in json_original.items() if k in self.get_campos()}
        evento_filtrado['dataHoraTransmissao'] = json_dict['dadosTransmissao']['dataHoraTransmissao']
        for k in self.get_campos():
            if evento_filtrado.get(k) is None:
                evento_filtrado[k] = None
        self._mapeia(**evento_filtrado)
        logger.info(self.__class__.__name__)
        logger.info(self)
        logger.info(evento_filtrado)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k in self.get_campos():
            val = kwargs.get(k)
            # Limpeza global de NaN: impede que valores inválidos do Pandas cheguem ao MySQL
            if isinstance(val, float) and np.isnan(val):
                val = None
            setattr(self, k, val)

def get_listaConteineresUld(o_kwargs: dict) -> Union[Tuple[str, bool, str, bool], Tuple[None, bool, None, bool]]:
    """
    "estoura" objeto listaConteineresUld

       Returns: numeroConteiner, ocrNumero, tipo, vazio
    """
    listaConteineresUld = o_kwargs.get('listaConteineresUld')
    if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
        return listaConteineresUld[0].get('numeroConteiner'), \
            listaConteineresUld[0].get('ocrNumero', False), \
            listaConteineresUld[0].get('tipo'), \
            listaConteineresUld[0].get('vazio', False)
    return None, False, None, False


def get_listaSemirreboque(o_kwargs: dict) -> Union[Tuple[str, bool, bool, float], Tuple[None, bool, bool, None]]:
    """
    "estoura" objeto listaSemirreboque

       Returns: placa, ocrPlaca, vazio, tara
    """
    listaSemirreboque = o_kwargs.get('listaSemirreboque')
    if listaSemirreboque and isinstance(listaSemirreboque, list) and len(listaSemirreboque) > 0:
        return listaSemirreboque[0].get('placa'), \
            listaSemirreboque[0].get('ocrPlaca', False), \
            listaSemirreboque[0].get('vazio', False), \
            listaSemirreboque[0].get('tara')
    return None, False, False, None


def get_listaDeclaracaoAduaneira(o_kwargs: dict) -> Union[Tuple[str, str], Tuple[None, None]]:
    """
    "estoura" objeto listaDeclaracaoAduaneira

       Returns: tipo, numeroDeclaracao
    """
    listaDeclaracaoAduaneira = o_kwargs.get('listaDeclaracaoAduaneira')
    if listaDeclaracaoAduaneira and isinstance(listaDeclaracaoAduaneira, list) and \
            len(listaDeclaracaoAduaneira) > 0:
        return listaDeclaracaoAduaneira[0].get('tipo'), \
            listaDeclaracaoAduaneira[0].get('numeroDeclaracao')
    return None, None


def get_listaManifestos(o_kwargs: dict) -> Union[Tuple[str, str], Tuple[None, None]]:
    """
    "estoura" objeto listaManifestos

       Returns: tipo, numero (listaConhecimentos)
    """
    listaManifestos = o_kwargs.get('listaManifestos')
    if listaManifestos and isinstance(listaManifestos, list) and \
            len(listaManifestos) > 0:
        listaConhecimentos = listaManifestos[0].get('listaConhecimentos')
        if listaConhecimentos and isinstance(listaConhecimentos, list) and \
                len(listaConhecimentos) > 0:
            return listaConhecimentos[0].get('tipo'), \
                listaConhecimentos[0].get('numero')
    return None, None


def get_listaNfe(o_kwargs: dict, limite: int = None) -> Union[str, None]:
    """
    Pega objeto listaNfe e faz "listão" separado por ,

       Returns: listaChaveNfe separado por vírgula
    """
    listaNfe = o_kwargs.get('listaNfe')
    Nfes = []
    if listaNfe and isinstance(listaNfe, list) and \
            len(listaNfe) > 0:
        # print(listaNfe)
        for row in listaNfe:
            chave = row.get('chaveNfe')
            if chave:
                Nfes.append(chave)
    resultado = ', '.join(Nfes)
    if limite and resultado and len(resultado) > limite:
        return resultado[:limite]
    return resultado

def get_listaPortoDescarregamento(o_kwargs: dict) -> Union[str, None]:
    """
    "estoura" objeto get_listaPortoDescarregamento retornando apenas o '0'

       Returns: porto (get_listaPortoDescarregamento)
    """
    listaConteineresUld = o_kwargs.get('listaConteineresUld')
    if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
        listaPortoDescarregamento = listaConteineresUld[0].get('listaPortoDescarregamento')
        if listaPortoDescarregamento and isinstance(listaPortoDescarregamento, list) and \
                len(listaPortoDescarregamento) > 0:
            return listaPortoDescarregamento[0].get('porto')
    return None

def get_listaPaisDestinoFinalCarga(o_kwargs: dict) -> Union[str, None]:
    """
    "estoura" objeto get_listaPaisDestinoFinalCarga retornando apenas o '0'

       Returns: pais (get_listaPaisDestinoFinalCarga)
    """
    listaConteineresUld = o_kwargs.get('listaConteineresUld')
    if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
        listaPaisDestinoFinalCarga = listaConteineresUld[0].get('listaPaisDestinoFinalCarga')
        if listaPaisDestinoFinalCarga and isinstance(listaPaisDestinoFinalCarga, list) and \
                len(listaPaisDestinoFinalCarga) > 0:
            return listaPaisDestinoFinalCarga[0].get('pais')
    return None


def get_listaNavio(o_kwargs: dict) -> Union[Tuple[str, str], Tuple[None, None]]:
    """
    "estoura" objeto listaNavio

       Returns: imo, nome (listaNavio)
    """
    listaConteineresUld = o_kwargs.get('listaConteineresUld')
    if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
        listaNavio = listaConteineresUld[0].get('listaNavio')
        if listaNavio and isinstance(listaNavio, list) and \
                len(listaNavio) > 0:
            return listaNavio[0].get('imo'), listaNavio[0].get('nome')
    return None, None


def numeric_c(texto):
    return ''.join([c for c in texto if c.isnumeric()])


def alfanumeric_c(texto):
    return ''.join([c for c in texto if c.isalnum()])

def valida_peso(peso, limite=99999999.99):
    """Valida se o peso recebido é numérico e está dentro do limite do banco de dados.
    Evita erro 1264 (Out of range value) no MySQL.
    """
    if peso is not None:
        try:
            peso_float = float(peso)
            if peso_float > limite:
                logger.warning(f"Peso absurdo detectado e anulado (acima de {limite}): {peso}")
                return None
            return peso
        except (ValueError, TypeError):
            return None
    return None


REGEX_NUMERO_CONTEINER = re.compile(r'^[A-Z]{4}\d{7}$')


def valida_numero_conteiner(numero) -> Optional[Tuple[str, str]]:
    """Valida o formato do número de contêiner: 4 letras maiúsculas + 7 dígitos (11 caracteres).

    Valor ausente (None ou vazio) é aceito, mantendo o comportamento anterior do sistema.
    Evita o erro 1406 (Data too long) do MySQL e impede que valores inválidos entrem na
    chave única das tabelas de eventos.

    Returns: None se válido, ou (motivo, detalhe) para registro em RegistroRejeitado
    """
    if numero is None or numero == '':
        return None
    if not isinstance(numero, str):
        return 'FORMATO_INVALIDO', f'Esperado texto, recebido {type(numero).__name__}'
    if REGEX_NUMERO_CONTEINER.match(numero):
        return None
    if len(numero) > 11:
        return 'TAMANHO_EXCEDIDO', \
            f'Esperado 11 caracteres (4 letras + 7 dígitos), recebido {len(numero)}'
    return 'FORMATO_INVALIDO', 'Esperado 4 letras maiúsculas seguidas de 7 dígitos'


def _trunca(valor, tamanho: int) -> Optional[str]:
    """Converte para texto e trunca. Garante que o registro de rejeição nunca estoure coluna."""
    if valor is None:
        return None
    return str(valor)[:tamanho]


class ControleExtracaoRecintos(Base):
    __tablename__ = 'apirecintos_controle_extracao'
    __table_args__ = (UniqueConstraint('codigoRecinto', 'tipoEvento'),)
    
    id = Column(BigInteger(), primary_key=True)
    codigoRecinto = Column(String(7), index=True)
    tipoEvento = Column(String(2), index=True)
    ultimaDataPesquisada = Column(DateTime())

    def __init__(self, codigoRecinto, tipoEvento, ultimaDataPesquisada, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.codigoRecinto = codigoRecinto
        self.tipoEvento = tipoEvento
        self.ultimaDataPesquisada = ultimaDataPesquisada


class RegistroRejeitado(BaseRastreavel):
    """Evento da API Recintos recusado na validação por dado mal formado.

    Uma linha por coluna rejeitada. Guarda o necessário para localizar o evento na origem
    (tabela de destino, recinto, datas) e o campo/valor que violou a regra. O evento NÃO é
    gravado na tabela de destino. Ver EventoAPIBase._validadores e processa_json.
    """
    __tablename__ = 'apirecintos_registros_rejeitados'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nomeTabela = Column(String(64), index=True, nullable=False)
    tipoEvento = Column(String(2))
    codigoRecinto = Column(String(7), index=True)
    dataHoraTransmissao = Column(DateTime(), index=True)
    dataHoraOcorrencia = Column(DateTime(), index=True)
    tipoOperacao = Column(String(1))
    nomeColuna = Column(String(64), index=True, nullable=False)
    valorColuna = Column(String(255))
    motivo = Column(String(30), index=True, nullable=False)
    detalhe = Column(String(255))

    def __init__(self, nomeTabela: str, nomeColuna: str, motivo: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nomeTabela = _trunca(nomeTabela, 64)
        self.nomeColuna = _trunca(nomeColuna, 64)
        self.motivo = _trunca(motivo, 30)
        self.tipoEvento = _trunca(kwargs.get('tipoEvento'), 2)
        self.codigoRecinto = _trunca(kwargs.get('codigoRecinto'), 7)
        self.dataHoraTransmissao = kwargs.get('dataHoraTransmissao')
        self.dataHoraOcorrencia = kwargs.get('dataHoraOcorrencia')
        self.tipoOperacao = _trunca(kwargs.get('tipoOperacao'), 1)
        self.valorColuna = _trunca(kwargs.get('valorColuna'), 255)
        self.detalhe = _trunca(kwargs.get('detalhe'), 255)

    @classmethod
    def from_evento(cls, evento: EventoAPIBase, tipoEvento, nomeColuna: str, valor,
                    motivo: str, detalhe: str) -> 'RegistroRejeitado':
        """Monta a rejeição a partir de um evento já mapeado (ver EventoAPIBase.valida_campos)."""
        return cls(evento.__tablename__, nomeColuna, motivo,
                   tipoEvento=tipoEvento,
                   codigoRecinto=evento.codigoRecinto,
                   dataHoraTransmissao=evento.dataHoraTransmissao,
                   dataHoraOcorrencia=evento.dataHoraOcorrencia,
                   tipoOperacao=evento.tipoOperacao,
                   valorColuna=valor,
                   detalhe=detalhe)

    def chave(self) -> tuple:
        """Chave natural: evita gravar a mesma rejeição em reenvios da mesma janela pelo ETL."""
        return (self.nomeTabela, self.nomeColuna, self.codigoRecinto,
                self.dataHoraOcorrencia, self.valorColuna)

    def is_duplicate(self, session) -> bool:
        return session.query(RegistroRejeitado). \
            filter(RegistroRejeitado.nomeTabela == self.nomeTabela). \
            filter(RegistroRejeitado.nomeColuna == self.nomeColuna). \
            filter(RegistroRejeitado.codigoRecinto == self.codigoRecinto). \
            filter(RegistroRejeitado.dataHoraOcorrencia == self.dataHoraOcorrencia). \
            filter(RegistroRejeitado.valorColuna == self.valorColuna). \
            first() is not None


class AcessoVeiculo(EventoAPIBase):
    __tablename__ = 'apirecintos_acessosveiculo'
    __table_args__ = (UniqueConstraint('placa', 'operacao', 'tipoOperacao', 'dataHoraOcorrencia', 'dataHoraRegistro'),
                      )
    dataHoraRegistro = Column(DateTime(), index=True)
    operacao = Column(String(1), index=True)  # G - A*g*endamento, C - A*c*esso
    direcao = Column(String(1), index=True)  # E - Entrada, S - Saída
    placa = Column(String(7), index=True)
    ocrPlaca = Column(Boolean(), index=True)
    cnpjTransportador = Column(String(15), index=True)
    motorista = Column(String(1))  # Placeholder
    cpfMotorista = Column(String(11), index=True)
    nomeMotorista = Column(String(50), index=True)
    listaConteineresUld = Column(String(1))  # Placeholder
    numeroConteiner = Column(String(11), index=True)
    ocrNumero = Column(Boolean(), index=True)
    tipoConteiner = Column(String(4), index=True)
    vazioConteiner = Column(Boolean(), index=True)
    listaSemirreboque = Column(String(1))  # Placeholder
    placaSemirreboque = Column(String(7), index=True)
    ocrPlacaSemirreboque = Column(Boolean(), index=True)
    vazioSemirreboque = Column(Boolean(), index=True)
    listaDeclaracaoAduaneira = Column(String(1))  # Placeholder
    tipoDeclaracao = Column(String(20))
    numeroDeclaracao = Column(String(15), index=True)
    listaManifestos = Column(String(1))  # Placeholder
    tipoConhecimento = Column(String(20))
    numeroConhecimento = Column(String(15), index=True)
    listaNfe = Column(String(690), index=True)
    #Inclusão de novos campos do AcessoVeiculo
    listaPortoDescarregamento = Column(String(1))  # Placeholder
    listaPaisDestinoFinalCarga = Column(String(1))  # Placeholder
    listaNavio = Column(String(1))  # Placeholder
    portoDescarregamento = Column(String(5))
    paisDestinoFinalCarga = Column(String(2))
    navio = Column(String(10))

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.operacao = kwargs.get('operacao')
        self.direcao = kwargs.get('direcao')

        placa_raw = kwargs.get('placa')
        if placa_raw:
            # Limpa caracteres especiais
            placa_clean = alfanumeric_c(placa_raw)

            # CORREÇÃO CRÍTICA: Trunca para 7 caracteres
            # Isso garante que o Python busque no banco exatamente o que o MySQL consegue armazenar.
            # Resolve o erro 1062 causado por placas duplas/concatenadas.
            self.placa = placa_clean[:7]

        self.ocrPlaca = kwargs.get('ocrPlaca')
        cnpjTransportador = kwargs.get('cnpjTransportador')
        if cnpjTransportador:
            self.cnpjTransportador = ''.join([c for c in cnpjTransportador if c not in '.-/'])
        motorista = kwargs.get('motorista')
        if motorista and isinstance(motorista, dict):
            cpf = motorista.get('cpf')
            if cpf:
                self.cpfMotorista = ''.join([c for c in cpf if c.isnumeric()])
            self.nomeMotorista = motorista.get('nome')
        self.numeroConteiner, self.ocrNumero, self.tipoConteiner, self.vazioConteiner = \
            get_listaConteineresUld(kwargs)
        placaSemirreboque, self.ocrPlacaSemirreboque, self.vazioSemirreboque, _ = \
            get_listaSemirreboque(kwargs)
        if placaSemirreboque:
            self.placaSemirreboque = alfanumeric_c(placaSemirreboque)
        self.tipoDeclaracao, self.numeroDeclaracao = get_listaDeclaracaoAduaneira(kwargs)
        self.tipoConhecimento, self.numeroConhecimento = get_listaManifestos(kwargs)
        if self.numeroConhecimento:
            self.numeroConhecimento = self.numeroConhecimento.strip()[:15]
        
        # Utiliza a truncagem centralizada na função utilitária
        self.listaNfe = get_listaNfe(kwargs, limite=690)
        self.portoDescarregamento = get_listaPortoDescarregamento(kwargs)
        self.paisDestinoFinalCarga = get_listaPaisDestinoFinalCarga(kwargs)
        self.navio, _ = get_listaNavio(kwargs)

    def get_tipoDeclaracao(self):
        if self.tipoDeclaracao:
            return self.tipoDeclaracao
        return 'Declaração'

    def get_tipoConhecimento(self):
        if self.tipoConhecimento:
            return self.tipoConhecimento
        return 'Conhecimento'

    def is_duplicate(self, session):
        return session.query(AcessoVeiculo). \
            filter(AcessoVeiculo.placa == self.placa). \
            filter(AcessoVeiculo.operacao == self.operacao). \
            filter(AcessoVeiculo.tipoOperacao == self.tipoOperacao). \
            filter(AcessoVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia). \
            filter(AcessoVeiculo.dataHoraRegistro == self.dataHoraRegistro). \
            one_or_none() is not None

    def to_sivana(self) -> dict:
        info = f'Contêiner:{self.numeroConteiner} - ' + \
               f'Motorista: {self.cpfMotorista} - ' + \
               f'CE: {self.numeroConhecimento}'
        dict_sivana = {
            'placa': self.placa,
            'ponto': self.codigoRecinto,
            'sentido': self.direcao,
            'dataHora': self.dataHoraOcorrencia.strftime('%Y-%m-%dT%H:%M:%S'),
            'info': info
        }
        return dict_sivana


class EmbarqueDesembarque(EventoAPIBase):
    __tablename__ = 'apirecintos_embarquedesembarque'
    __table_args__ = (UniqueConstraint('numeroConteiner', 'dataHoraOcorrencia'),
                      )

    viagem = Column(String(9), index=True)
    pesoBrutoManifesto = Column(Numeric(7, 2))
    escala = Column(String(11))
    embarqueDesembarque = Column(String(1))  # E - Embarque D - Desembarque
    cargaSolta = Column(String(5), index=True)
    pesoBrutoBalanca = Column(Numeric(7, 2))
    numeroConteiner = Column(String(11), index=True)
    taraConteiner = Column(Numeric(7, 2))
    tipoConteiner = Column(String(4), index=True)
    listaManifestos = Column(String(1))  # Placeholder
    tipoConhecimento = Column(String(20))
    numeroConhecimento = Column(String(15), index=True)
    listaDeclaracaoAduaneira = Column(String(1))  # Placeholder
    listaNfe = Column(String(690), index=True)

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.viagem = kwargs.get('viagem')
        self.pesoBrutoManifesto = valida_peso(kwargs.get('pesoBrutoManifesto'), 99999999.99)
        self.escala = kwargs.get('escala')
        self.embarqueDesembarque = kwargs.get('embarqueDesembarque')
        self.cargaSolta = kwargs.get('cargaSolta')
        self.pesoBrutoBalanca = valida_peso(kwargs.get('pesoBrutoBalanca'), 99999.99)
        numeroConteiner = kwargs.get('numeroConteiner')
        if numeroConteiner:
            self.numeroConteiner = ''.join([c for c in numeroConteiner if c.isalnum()])
        self.taraConteiner = valida_peso(kwargs.get('taraConteiner'), 99999.99)
        self.tipoConteiner = kwargs.get('tipoConteiner')
        self.tipoDeclaracao, self.numeroDeclaracao = get_listaDeclaracaoAduaneira(kwargs)
        self.tipoConhecimento, self.numeroConhecimento = get_listaManifestos(kwargs)
        self.listaNfe = get_listaNfe(kwargs, limite=690)

    def is_duplicate(self, session):
        return session.query(EmbarqueDesembarque). \
            filter(EmbarqueDesembarque.numeroConteiner == self.numeroConteiner). \
            filter(EmbarqueDesembarque.dataHoraOcorrencia == self.dataHoraOcorrencia). \
            one_or_none() is not None


class PesagemVeiculo(EventoAPIBase):
    __tablename__ = 'apirecintos_pesagensveiculo'
    __table_args__ = (UniqueConstraint('placa', 'dataHoraOcorrencia', 'dataHoraTransmissao'),)
    dataHoraTransmissao = Column(DateTime(), index=True)
    pesoBrutoBalanca = Column(Numeric(7, 2), index=True)
    pesoBrutoManifesto = Column(Numeric(7, 2))
    taraConjunto = Column(Numeric(7, 2))
    capturaAutoPeso = Column(Boolean(), index=True)
    placa = Column(String(7), index=True)
    listaConteineresUld = Column(String(1))  # Placeholder
    numeroConteiner = Column(String(11), index=True)
    listaSemirreboque = Column(String(1))  # Placeholder
    placaSemirreboque = Column(String(7), index=True)
    taraSemirreboque = Column(Numeric(7, 2))

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.pesoBrutoBalanca = valida_peso(kwargs.get('pesoBrutoBalanca'), 99999.99)
        self.pesoBrutoManifesto = valida_peso(kwargs.get('pesoBrutoManifesto'), 99999999.99)
        self.taraConjunto = valida_peso(kwargs.get('taraConjunto'), 99999.99)
        self.capturaAutoPeso = kwargs.get('capturaAutoPeso', False)
        placa = kwargs.get('placa')
        if placa:
            self.placa = alfanumeric_c(placa)
        # self.ocrPlaca == kwargs.get('ocrPlaca')
        self.numeroConteiner, _, _, _ = get_listaConteineresUld(kwargs)
        placaSemirreboque, _, _, taraSemirreboque_raw = get_listaSemirreboque(kwargs)
        self.taraSemirreboque = valida_peso(taraSemirreboque_raw, 99999.99)

        if placaSemirreboque:
            self.placaSemirreboque = alfanumeric_c(placaSemirreboque)

    def is_duplicate(self, session):
        return session.query(PesagemVeiculo).filter(
            PesagemVeiculo.placa == self.placa,
            PesagemVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia,
            PesagemVeiculo.dataHoraTransmissao == self.dataHoraTransmissao
        ).one_or_none() is not None


class InspecaoNaoInvasiva(EventoAPIBase):
    __tablename__ = 'apirecintos_inspecoesnaoinvasivas'
    __table_args__ = (UniqueConstraint('numeroConteiner', 'dataHoraOcorrencia'),)
    _validadores = {'numeroConteiner': valida_numero_conteiner}
    vazio = Column(Boolean(), index=True)
    placa = Column(String(7), index=True)
    listaConteineresUld = Column(String(1))  # Placeholder
    tipoConteiner = Column(String(4), index=True)
    numeroConteiner = Column(String(11), index=True)
    ocrNumero = Column(Boolean(), index=True)
    listaSemirreboque = Column(String(1))  # Placeholder
    placaSemirreboque = Column(String(7), index=True)
    ocrPlacaSemirreboque = Column(Boolean(), index=True)
    listaManifestos = Column(String(1))  # Placeholder
    tipoConhecimento = Column(String(20))
    numeroConhecimento = Column(String(15), index=True)

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.vazio = kwargs.get('vazio', False)
        if not isinstance(self.vazio, bool):
            self.vazio = False
        placa = kwargs.get('placa')
        if placa:
            self.placa = alfanumeric_c(placa)
        self.numeroConteiner, self.ocrNumero, self.tipoConteiner, _ = get_listaConteineresUld(kwargs)
        placaSemirreboque, self.ocrPlacaSemirreboque, _, _ = get_listaSemirreboque(kwargs)
        if placaSemirreboque:
            self.placaSemirreboque = alfanumeric_c(placaSemirreboque)
        self.tipoConhecimento, self.numeroConhecimento = get_listaManifestos(kwargs)

    def is_duplicate(self, session):
        return session.query(InspecaoNaoInvasiva). \
            filter(InspecaoNaoInvasiva.numeroConteiner == self.numeroConteiner). \
            filter(InspecaoNaoInvasiva.dataHoraOcorrencia == self.dataHoraOcorrencia). \
            one_or_none() is not None


def le_json(caminho_json: str, classeevento: Type[BaseDumpable],
            chave_unica: list) -> Tuple[pd.DataFrame, List[RegistroRejeitado]]:
    with open(caminho_json) as json_in:
        texto = ''.join(json_in.readlines())
    return processa_json(texto, classeevento, chave_unica)


def processa_json(texto: str, classeevento: Type[BaseDumpable],
                  chave_unica: list) -> Tuple[pd.DataFrame, List[RegistroRejeitado]]:
    """ Lê Eventos do Arquivo um a um, tratar e retorna em um dataframe com o dump dos Eventos

    Faz também os tratamentos:
      separar eventos com dados mal formados (ver EventoAPIBase._validadores) em RegistroRejeitado
      eliminar linhas duplicadas de acordo com a chave passada
      tratar nan
      filtrar de acordo com regras de negócio


    Args:
        texto: RAW do arquivo JSON recebido
        classeevento: Classe do Evento (ver classes SQLALchemy do arquivo models/apirecintos.py)
        chave_unica: lista de campos que compõem a chave única do Evento

    Returns:
        (df_eventos, rejeitados): dataframe com os eventos válidos (vazio se nenhum) e
        lista de RegistroRejeitado a persistir com persiste_rejeitados

    """
    json_raw = json.loads(''.join(texto))
    eventos = []
    rejeitados = []
    for evento_json in json_raw:
        #print(evento_json, type(evento_json))
        instancia = classeevento()
        instancia.processa_json(evento_json)
        if ('placa' in chave_unica) and (instancia.placa is None):
            continue
        rejeicoes = instancia.valida_campos()
        if rejeicoes:
            tipo_evento = evento_json.get('dadosTransmissao', {}).get('tipoEvento')
            for nome_coluna, valor, motivo, detalhe in rejeicoes:
                rejeitados.append(RegistroRejeitado.from_evento(
                    instancia, tipo_evento, nome_coluna, valor, motivo, detalhe))
            continue
        instancia_dump = instancia.dump()
        instancia_dump.pop('id', None)
        eventos.append(instancia_dump)
    if rejeitados:
        logger.warning(f'{len(rejeitados)} eventos rejeitados na validação de campos '
                       f'(ver {RegistroRejeitado.__tablename__}).')
    if not eventos:
        logger.info(f'Recuperados {len(json_raw)} eventos. Nenhum evento válido para persistir.')
        return pd.DataFrame(), rejeitados
    df_eventos = pd.DataFrame(eventos)
    df_eventos['dataHoraOcorrencia'] = pd.to_datetime(df_eventos['dataHoraOcorrencia'])
    # print(df_eventos[df_eventos['placa']== 'DPC9J28'].sort_values('placa'))
    df_eventos = df_eventos.drop_duplicates(subset=chave_unica)
    # Substitui NaNs por None (NULL no SQL), evitando o erro de "nan" no MySQL
    df_eventos = df_eventos.where(pd.notnull(df_eventos), None)
    # print(df_eventos[df_eventos['placa']== 'DPC9J28'].sort_values('placa'))
    logger.info(f'Recuperados {len(json_raw)} eventos. Mantidos {len(df_eventos)} '
                f'após remoção de duplicatas de chave primária.')
    if classeevento == AcessoVeiculo:
        df_eventos = df_eventos[df_eventos['operacao'] == 'C']
        logger.info(f'Mantidos {len(df_eventos)} eventos após filtragem de Eventos de A*c*esso (Operação=C).')
    return df_eventos, rejeitados



def fix_strdoida(s: str) -> str:
    if not isinstance(s, str):
        return s
    # Tenta reverter UTF‑8 interpretado como latin1/Windows‑1252
    for enc in ("latin1", "cp1252"):
        try:
            return s.encode(enc).decode("utf-8")
        except Exception:
            continue
    return s

def corrige_campos(evento, classeevento: Type[BaseDumpable]):
    if classeevento == AcessoVeiculo:
        try:
            logger.error(f'*******Forçando a barra para ver se entrou aqui***** "{evento.nomeMotorista}"')
            # Corrige mojibake (ex.: MENDONÃ‡A -> MENDONÇA)
            evento.nomeMotorista = fix_strdoida(evento.nomeMotorista or '')
        except Exception:
            logger.error(f'persiste_df: Nome motorita "{evento.nomeMotorista}" não pôde ser lido!!!')
            evento.nomeMotorista = ''
        logger.error(f'*******Forçando a barra para ver como saiu aqui***** "{evento.nomeMotorista}"')

def persiste_df(df_eventos: pd.DataFrame, classeevento: Type[BaseDumpable], session):
    """Percorre dataframe, instanciando Eventos e adicionando à sessão, finalizando com commit no banco"""
    cont_sucesso = 0
    ind = 0
    try:
        for ind, evento_dict in enumerate(df_eventos.to_dict('records'), 1):
            evento = classeevento(**evento_dict)
            # print(evento.dump())
            if evento.is_duplicate(session):
                continue
            corrige_campos(evento, classeevento)
            session.add(evento)
            cont_sucesso += 1
        session.commit()
    except IntegrityError as err:
        # Erros de integridade (inclui chave duplicada 1062)
        session.rollback()
        logger.error(f'persiste_df IntegrityError: {err}')
        # Se for erro de chave duplicada (MySQL 1062), tratamos como "ok, já estava inserido"
        orig = getattr(err, "orig", None)
        args = getattr(orig, "args", [])
        code = args[0] if args and len(args) > 0 else None
        if code == 1062:
            logger.info("persiste_df: chave duplicada (1062) detectada; ignorando e seguindo como idempotente.")
            # Não relançamos: o endpoint devolve sucesso e o consumidor não quebra
            return
        # Outros erros de integridade continuam sendo críticos
        raise
    except Exception as err:
        session.rollback()
        logger.error(f'persiste_df: {err}')
        raise err
    logger.info(f'{ind} Eventos lidos, {cont_sucesso} inseridos')


def persiste_rejeitados(rejeitados: List[RegistroRejeitado], session) -> int:
    """Grava os registros rejeitados na validação (ver processa_json), em commit próprio.

    Nunca propaga exceção: um problema ao gravar a rejeição não pode derrubar a ingestão dos
    eventos válidos. Reenvios da mesma janela pelo ETL não geram linhas repetidas.

    Returns: quantidade de registros efetivamente gravados
    """
    if not rejeitados:
        return 0
    cont_gravados = 0
    chaves_lote = set()
    try:
        for rejeitado in rejeitados:
            chave = rejeitado.chave()
            if chave in chaves_lote or rejeitado.is_duplicate(session):
                continue
            chaves_lote.add(chave)
            session.add(rejeitado)
            cont_gravados += 1
        session.commit()
    except Exception as err:
        session.rollback()
        logger.error(f'persiste_rejeitados: {err}', exc_info=True)
        return 0
    logger.warning(f'{len(rejeitados)} registros rejeitados, {cont_gravados} gravados '
                   f'em {RegistroRejeitado.__tablename__}')
    return cont_gravados


if __name__ == '__main__':  # pragma: no-cover
    confirma = 'S'
    # input('Revisar o código... Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        from ajna_commons.flask.conf import SQL_URI
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine, autoflush=False)
        session = Session()



        # Sair por segurança. Comentar linha abaixo para funcionar
        sys.exit(0)

        caminho = 'C:\\Users\\25052288840\\Downloads\\api_recintos\\'
        arquivos = os.listdir(caminho)

        for arquivo in arquivos:
            if '.zip' in arquivo:
                print(arquivo)
                zip_file = zipfile.ZipFile(caminho + arquivo, 'r')
                tipoevento = zip_file.read('tipoEvento.txt').decode()
                print(tipoevento)
                classes = {'1': AcessoVeiculo,
                           '3': PesagemVeiculo,
                           '4': EmbarqueDesembarque,
                           '25': InspecaoNaoInvasiva}
                indices = {AcessoVeiculo: ['placa', 'operacao', 'tipoOperacao', 'dataHoraOcorrencia'],
                           PesagemVeiculo: ['placa', 'dataHoraOcorrencia'],
                           EmbarqueDesembarque: ['numeroConteiner', 'dataHoraOcorrencia'],
                           InspecaoNaoInvasiva: ['numeroConteiner', 'dataHoraOcorrencia']}
                classe = classes[tipoevento]
                indice = indices[classe]
                logger.info(f'Classe: {classe}, Chave única: {indice}')
                json_texto = zip_file.read('json.txt').decode()
                df_eventos, rejeitados = processa_json(json_texto, classe, indice)
                persiste_rejeitados(rejeitados, session)
                try:
                    persiste_df(df_eventos, classe, session)
                except Exception as err:
                    logger.info(err)
        # Sair por segurança. Comentar linha abaixo para funcionar
        sys.exit(0)

        '''
        metadata.drop_all(engine, [metadata.tables['apirecintos_acessosveiculo'],
                                   metadata.tables['apirecintos_pesagensveiculo'],
                                   [metadata.tables['apirecintos_embarquedesembarque']])
                                   metadata.tables['apirecintos_inspecoesnaoinvasivas'], ])
        metadata.create_all(engine, [metadata.tables['apirecintos_acessosveiculo'],
                                     metadata.tables['apirecintos_pesagensveiculo'],
                                     [metadata.tables['apirecintos_embarquedesembarque']])
                                     metadata.tables['apirecintos_inspecoesnaoinvasivas'], ])
        '''
