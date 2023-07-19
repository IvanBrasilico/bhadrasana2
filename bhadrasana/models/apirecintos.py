import json
import sys
from typing import Type

import pandas as pd
from dateutil import parser
from sqlalchemy import BigInteger, Column, DateTime, Boolean, String, UniqueConstraint, exists

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from ajna_commons.flask.log import logger
from bhadrasana.models import Base, BaseRastreavel, BaseDumpable

metadata = Base.metadata


def converte_datetime(str_datetime: str):
    return parser.isoparse(str_datetime).replace(tzinfo=None)


class AcessoVeiculo(BaseRastreavel, BaseDumpable):
    __tablename__ = 'apirecintos_acessosveiculo'
    __table_args__ = (UniqueConstraint('placa', 'operacao', 'dataHoraOcorrencia'),
                      )
    id = Column(BigInteger(), primary_key=True)
    codigoRecinto = Column(String(7), index=True)
    dataHoraOcorrencia = Column(DateTime(), index=True)
    operacao = Column(String(1), index=True)  # G - A*g*endamento, C - A*c*esso
    direcao = Column(String(1), index=True)  # E - Entrada, S - Saída
    placa = Column(String(7), index=True)
    ocrPlaca = Column(Boolean(), index=True)
    cnpjTransportador = Column(String(15), index=True)
    motorista = Column(Boolean())  # Placeholder
    motorista_cpf = Column(String(11), index=True)
    motorista_nome = Column(String(50), index=True)
    listaConteineresUld = Column(Boolean())  # Placeholder
    numeroConteiner = Column(String(11), index=True)
    ocrNumero = Column(Boolean(), index=True)

    def _init(self, codigoRecinto, operacao, direcao, dataHoraOcorrencia, placa, ocrPlaca,
              cnpjTransportador, motorista, listaConteineresUld):
        self.codigoRecinto = codigoRecinto
        self.operacao = operacao
        self.direcao = direcao
        self.dataHoraOcorrencia = converte_datetime(dataHoraOcorrencia)
        self.placa = placa
        self.ocrPlaca = ocrPlaca
        self.cnpjTransportador = ''.join([c for c in cnpjTransportador if c.isnumeric()])
        if motorista and isinstance(motorista, dict):
            self.motorista_cpf = ''.join([c for c in motorista['cpf'] if c.isnumeric()])
            self.motorista_nome = motorista['nome']
        if listaConteineresUld and isinstance(listaConteineresUld, list) and len(listaConteineresUld) > 0:
            self.numeroConteiner = listaConteineresUld[0]['numeroConteiner']
            self.ocrNumero = listaConteineresUld[0]['ocrNumero']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        evento_filtrado = {k: v for k, v in kwargs.items() if k in self.get_campos()}
        self._init(**evento_filtrado)

    def isduplicate(self, session):
        return session.query(exists().where(
            AcessoVeiculo.placa == self.placa and
            AcessoVeiculo.operacao == self.operacao and
            AcessoVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia)).scalar()


def le_json(caminho_json: str, classeevento: Type[BaseDumpable], chave_unica: list) -> pd.DataFrame:
    with open(caminho_json) as json_in:
        texto = json_in.readlines()
    json_raw = json.loads(''.join(texto))
    eventos = []
    for evento_json in json_raw:
        json_original = evento_json['jsonOriginal']
        instancia = classeevento(**json_original)
        eventos.append(instancia.dump())
    df_eventos = pd.DataFrame(eventos)
    df_eventos = df_eventos.drop_duplicates(subset=chave_unica)
    logger.info(f'Recuperados {len(json_raw)} eventos. Mantidos {len(df_eventos)} '
                f'após remoção de duplicatas de chave primária.')
    if classeevento == AcessoVeiculo:
        df_eventos = df_eventos[df_eventos['operacao'] == 'C']
    logger.info(f'Mantidos {len(df_eventos)} após filtragem de Eventos de A*c*esso (Operação=C).')
    return df_eventos


def persiste_df(df_eventos: pd.DataFrame, classeevento: Type[BaseDumpable]):
    cont_sucesso = 0
    ind = 0
    for ind, evento_dict in enumerate(df_eventos.to_dict('records'), 1):
        evento = classeevento(**evento_dict)
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
        metadata.drop_all(engine, [metadata.tables['apirecintos_acessosveiculo'], ])
        metadata.create_all(engine, [metadata.tables['apirecintos_acessosveiculo'], ])
        df_eventos = le_json(r'C:\Users\25052288840\Downloads\api_recintos\DPW_ev1_20230727\json.txt',
                             AcessoVeiculo, ['placa', 'operacao', 'dataHoraOcorrencia'])
        persiste_df(df_eventos, AcessoVeiculo)
