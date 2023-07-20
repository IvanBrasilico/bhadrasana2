import json
import sys
from typing import Type

import numpy as np
import pandas as pd
from dateutil import parser
from sqlalchemy import BigInteger, Column, DateTime, Boolean, String, UniqueConstraint, exists, Numeric

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from ajna_commons.flask.log import logger
from bhadrasana.models import Base, BaseRastreavel, BaseDumpable

metadata = Base.metadata


def converte_datetime(str_datetime: str):
    try:
        return parser.isoparse(str_datetime).replace(tzinfo=None)
    except:
        return None


class EventoAPIBase(BaseRastreavel, BaseDumpable):
    __abstract__ = True
    id = Column(BigInteger(), primary_key=True)
    codigoRecinto = Column(String(7), index=True)
    dataHoraTransmissao = Column(DateTime(), index=True)
    dataHoraOcorrencia = Column(DateTime(), index=True)
    tipoOperacao = Column(String(1), index=True)  # I - Inclusão, R - Retificação
    contingencia = Column(Boolean(), index=True)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k in self.get_campos():
            setattr(self, k, kwargs.get(k))


class AcessoVeiculo(EventoAPIBase):
    __tablename__ = 'apirecintos_acessosveiculo'
    __table_args__ = (UniqueConstraint('placa', 'operacao', 'dataHoraOcorrencia'),
                      )
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

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.operacao = kwargs.get('operacao')
        self.direcao = kwargs.get('direcao')
        self.placa = kwargs.get('placa')
        self.ocrPlaca = kwargs.get('ocrPlaca')
        cnpjTransportador = kwargs.get('cnpjTransportador')
        self.cnpjTransportador = ''.join([c for c in cnpjTransportador if c.isnumeric()])
        motorista = kwargs.get('motorista')
        if motorista and isinstance(motorista, dict):
            cpf = motorista.get('cpf')
            self.cpfMotorista = ''.join([c for c in cpf if c.isnumeric()])
            self.nomeMotorista = motorista.get('nome')
        listaConteineresUld = kwargs.get('listaConteineresUld')
        if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
            self.numeroConteiner = listaConteineresUld[0]['numeroConteiner']
            self.ocrNumero = listaConteineresUld[0]['ocrNumero']

    def is_duplicate(self, session):
        return session.query(exists().where(
            AcessoVeiculo.placa == self.placa and
            AcessoVeiculo.operacao == self.operacao and
            AcessoVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia)).scalar()


class PesagemVeiculo(EventoAPIBase):
    __tablename__ = 'apirecintos_pesagensveiculo'
    __table_args__ = (UniqueConstraint('placa', 'dataHoraOcorrencia'),)
    pesoBrutoBalanca = Column(Numeric(7, 2), index=True)
    pesoBrutoManifesto = Column(Numeric(7, 2))
    taraConjunto = Column(Numeric(7, 2))
    capturaAutoPeso = Column(Boolean(), index=True)
    placa = Column(String(7), index=True)
    listaConteineresUld = Column(String(1))  # Placeholder
    numeroConteiner = Column(String(11), index=True)

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.pesoBrutoBalanca = kwargs.get('pesoBrutoBalanca')
        self.pesoBrutoManifesto = kwargs.get('pesoBrutoManifesto')
        self.capturaAutoPeso = kwargs.get('capturaAutoPeso')
        self.placa = kwargs.get('placa')
        # self.ocrPlaca == kwargs.get('ocrPlaca']
        listaConteineresUld = kwargs.get('listaConteineresUld')
        if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
            self.numeroConteiner = listaConteineresUld[0]['numeroConteiner']
            # self.ocrNumero == kwargs.get('listaConteineresUld[0]['ocrNumero']

    def is_duplicate(self, session):
        return session.query(exists().where(
            PesagemVeiculo.placa == self.placa and
            PesagemVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia)).scalar()


class InspecaoNaoInvasiva(EventoAPIBase):
    __tablename__ = 'apirecintos_inspecoesnaoinvasivas'
    __table_args__ = (UniqueConstraint('numeroConteiner', 'dataHoraOcorrencia'),)
    vazio = Column(Boolean(), index=True)
    placa = Column(String(7), index=True)
    listaConteineresUld = Column(String(1))  # Placeholder
    tipoConteiner = Column(String(4), index=True)
    numeroConteiner = Column(String(11), index=True)
    ocrNumero = Column(Boolean(), index=True)

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.vazio = kwargs.get('vazio')
        self.placa = kwargs.get('placa')
        listaConteineresUld = kwargs.get('listaConteineresUld')
        if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
            self.tipoConteiner = listaConteineresUld[0]['tipo']
            self.numeroConteiner = listaConteineresUld[0]['numeroConteiner']
            self.ocrNumero = listaConteineresUld[0]['ocrNumero']

    def is_duplicate(self, session):
        return session.query(exists().where(
            PesagemVeiculo.placa == self.placa and
            PesagemVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia)).scalar()


def le_json(caminho_json: str, classeevento: Type[BaseDumpable], chave_unica: list) -> pd.DataFrame:
    with open(caminho_json) as json_in:
        texto = json_in.readlines()
    json_raw = json.loads(''.join(texto))
    eventos = []
    for evento_json in json_raw:
        instancia = classeevento()
        instancia.processa_json(evento_json)
        eventos.append(instancia.dump())
    df_eventos = pd.DataFrame(eventos)
    df_eventos = df_eventos.drop_duplicates(subset=chave_unica)
    df_eventos = df_eventos.replace({np.nan: ''})
    logger.info(f'Recuperados {len(json_raw)} eventos. Mantidos {len(df_eventos)} '
                f'após remoção de duplicatas de chave primária.')
    if classeevento == AcessoVeiculo:
        df_eventos = df_eventos[df_eventos['operacao'] == 'C']
        logger.info(f'Mantidos {len(df_eventos)} eventos após filtragem de Eventos de A*c*esso (Operação=C).')
    return df_eventos


def persiste_df(df_eventos: pd.DataFrame, classeevento: Type[BaseDumpable]):
    cont_sucesso = 0
    ind = 0
    for ind, evento_dict in enumerate(df_eventos.to_dict('records'), 1):
        evento = classeevento(**evento_dict)
        # print(evento.dump())
        session.add(evento)
        session.flush()
        cont_sucesso += 1
    try:
        session.commit()
        logger.info(f'{ind} Eventos lidos, {cont_sucesso} inseridos')
    except Exception as err:
        session.rollback()
        logger.error(err, exc_info=True)


if __name__ == '__main__':  # pragma: no-cover
    confirma = input('Revisar o código... '
                     'Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        from ajna_commons.flask.conf import SQL_URI
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        # Sair por segurança. Comentar linha abaixo para funcionar
        # sys.exit(0)
        metadata.drop_all(engine, [metadata.tables['apirecintos_acessosveiculo'],
                                   metadata.tables['apirecintos_pesagensveiculo'],
                                   metadata.tables['apirecintos_inspecoesnaoinvasivas'], ])
        metadata.create_all(engine, [metadata.tables['apirecintos_acessosveiculo'],
                                     metadata.tables['apirecintos_pesagensveiculo'],
                                     metadata.tables['apirecintos_inspecoesnaoinvasivas'], ])
        df_eventos = le_json(r'C:\Users\25052288840\Downloads\api_recintos\DPW_ev1_20230727\json.txt',
                             AcessoVeiculo, ['placa', 'operacao', 'dataHoraOcorrencia'])
        persiste_df(df_eventos, AcessoVeiculo)
        df_eventos = le_json(r'C:\Users\25052288840\Downloads\api_recintos\DPW_ev2_20230727\json.txt',
                             PesagemVeiculo, ['placa', 'dataHoraOcorrencia'])
        persiste_df(df_eventos, PesagemVeiculo)
        df_eventos = le_json(r'C:\Users\25052288840\Downloads\api_recintos\DPW_ev3_20230727\json.txt',
                             InspecaoNaoInvasiva, ['numeroConteiner', 'dataHoraOcorrencia'])
        persiste_df(df_eventos, InspecaoNaoInvasiva)
