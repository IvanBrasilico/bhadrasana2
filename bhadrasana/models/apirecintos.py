import json
import os
import sys
import zipfile
from typing import Type, Tuple, Union

import numpy as np
import pandas as pd
from dateutil import parser
from sqlalchemy import BigInteger, Column, DateTime, Boolean, String, UniqueConstraint, Numeric

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


def get_listaNfe(o_kwargs: dict) -> Union[str, None]:
    """
    Pega objeto listaNfe e faz "listão" separado por ,

       Returns: listaChaveNfe separado por vírgula
    """
    listaNfe = o_kwargs.get('listaNfe')
    if listaNfe and isinstance(listaNfe, list) and \
            len(listaNfe) > 0:
        # print(listaNfe)
        Nfes = []
        for row in listaNfe:
            chave = row.get('chaveNfe')
            if chave:
                Nfes.append(chave)
        return ', '.join(Nfes)


def numeric_c(texto):
    return ''.join([c for c in texto if c.isnumeric()])

def alfanumeric_c(texto):
    return ''.join([c for c in texto if c.isalnum()])

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
    tipoConteiner = Column(String(4), index=True)
    vazioConteiner = Column(Boolean(), index=True)
    listaSemirreboque = Column(String(1))  # Placeholder
    placaSemirreboque = Column(String(7), index=True)
    ocrPlacaSemirreboque = Column(Boolean(), index=True)
    vazioSemirreboque = Column(Boolean(), index=True)
    listaDeclaracaoAduaneira = Column(String(1))  # Placeholder
    tipoDeclaracao = Column(String(3))
    numeroDeclaracao = Column(String(15), index=True)
    listaManifestos = Column(String(1))  # Placeholder
    tipoConhecimento = Column(String(15))
    numeroConhecimento = Column(String(15), index=True)
    listaNfe = Column(String(200), index=True)

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.operacao = kwargs.get('operacao')
        self.direcao = kwargs.get('direcao')
        placa = kwargs.get('placa')
        if placa:
            self.placa = alfanumeric_c(placa)
        self.ocrPlaca = kwargs.get('ocrPlaca')
        cnpjTransportador = kwargs.get('cnpjTransportador')
        if cnpjTransportador:
            self.cnpjTransportador = ''.join([c for c in cnpjTransportador if c.isnumeric()])
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
        self.listaNfe = get_listaNfe(kwargs)

    def get_tipoDeclaracao(self):
        if self.tipoDeclaracao:
            return self.tipoDeclaracao
        return 'Declaração'

    def get_tipoConhecimento(self):
        if self.tipoConhecimento:
            return self.tipoConhecimento
        return 'Declaração'

    def is_duplicate(self, session):
        return session.query(AcessoVeiculo).filter(AcessoVeiculo.placa == self.placa). \
                   filter(AcessoVeiculo.operacao == self.operacao). \
                   filter(AcessoVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia).one_or_none() is not None


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
    listaSemirreboque = Column(String(1))  # Placeholder
    placaSemirreboque = Column(String(7), index=True)
    taraSemirreboque = Column(Numeric(7, 2))

    def _mapeia(self, *args, **kwargs):
        super()._mapeia(**kwargs)
        self.pesoBrutoBalanca = kwargs.get('pesoBrutoBalanca')
        self.pesoBrutoManifesto = kwargs.get('pesoBrutoManifesto')
        self.capturaAutoPeso = kwargs.get('capturaAutoPeso', False)
        placa = kwargs.get('placa')
        if placa:
            self.placa = alfanumeric_c(placa)
        # self.ocrPlaca == kwargs.get('ocrPlaca')
        self.numeroConteiner, _, _, _ = get_listaConteineresUld(kwargs)
        placaSemirreboque, _, _, self.taraSemirreboque = get_listaSemirreboque(kwargs)
        if placaSemirreboque:
            self.placaSemirreboque = alfanumeric_c(placaSemirreboque)

    def is_duplicate(self, session):
        return session.query(PesagemVeiculo).filter(PesagemVeiculo.placa == self.placa). \
                   filter(PesagemVeiculo.dataHoraOcorrencia == self.dataHoraOcorrencia).one_or_none() is not None


class InspecaoNaoInvasiva(EventoAPIBase):
    __tablename__ = 'apirecintos_inspecoesnaoinvasivas'
    __table_args__ = (UniqueConstraint('numeroConteiner', 'dataHoraOcorrencia'),)
    vazio = Column(Boolean(), index=True)
    placa = Column(String(7), index=True)
    listaConteineresUld = Column(String(1))  # Placeholder
    tipoConteiner = Column(String(4), index=True)
    numeroConteiner = Column(String(11), index=True)
    ocrNumero = Column(Boolean(), index=True)
    listaSemirreboque = Column(String(1))  # Placeholder
    placaSemirreboque = Column(String(7), index=True)
    ocrPlacaSemirreboque = Column(Boolean(), index=True)

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

    def is_duplicate(self, session):
        return session.query(InspecaoNaoInvasiva). \
                   filter(InspecaoNaoInvasiva.numeroConteiner == self.numeroConteiner). \
                   filter(InspecaoNaoInvasiva.dataHoraOcorrencia == self.dataHoraOcorrencia).\
                   one_or_none() is not None


def le_json(caminho_json: str, classeevento: Type[BaseDumpable], chave_unica: list) -> pd.DataFrame:
    with open(caminho_json) as json_in:
        texto = ''.join(json_in.readlines())
    return processa_json(texto, classeevento, chave_unica)


def processa_json(texto: str, classeevento: Type[BaseDumpable], chave_unica: list) -> pd.DataFrame:
    """ Lê Eventos do Arquivo um a um, tratar e retorna em um dataframe com o dump dos Eventos

    Faz também os tratamentos:
      eliminar linhas duplicadas de acordo com a chave passada
      tratar nan
      filtrar de acordo com regras de negócio


    Args:
        texto: RAW do arquivo JSON recebido
        classeevento: Classe do Evento (ver classes SQLALchemy do arquivo models/apirecintos.py)
        chave_unica: lista de campos que compõem a chave única do Evento

    Returns:

    """
    json_raw = json.loads(''.join(texto))
    eventos = []
    for evento_json in json_raw:
        instancia = classeevento()
        instancia.processa_json(evento_json)
        if (instancia.placa is None) and ('placa' in chave_unica):
            continue
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


def persiste_df(df_eventos: pd.DataFrame, classeevento: Type[BaseDumpable], session):
    """Percorre dataframe, instanciando Eventos e adicionando à sessão, finalizando com commit no banco"""
    cont_sucesso = 0
    ind = 0
    for ind, evento_dict in enumerate(df_eventos.to_dict('records'), 1):
        evento = classeevento(**evento_dict)
        # print(evento.dump())
        if evento.is_duplicate(session):
            continue
        session.add(evento)
        cont_sucesso += 1
    try:
        session.commit()
    except Exception as err:
        session.rollback()
        logger.error(err, exc_info=True)
    logger.info(f'{ind} Eventos lidos, {cont_sucesso} inseridos')


if __name__ == '__main__':  # pragma: no-cover
    confirma = 'S'
    # input('Revisar o código... Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        from ajna_commons.flask.conf import SQL_URI
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
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
                           '25': InspecaoNaoInvasiva}
                indices = {AcessoVeiculo: ['placa', 'operacao', 'dataHoraOcorrencia'],
                           PesagemVeiculo: ['placa', 'dataHoraOcorrencia'],
                           InspecaoNaoInvasiva: ['numeroConteiner', 'dataHoraOcorrencia']}
                classe = classes[tipoevento]
                indice = indices[classe]
                print(classe, indice)
                json_texto = zip_file.read('json.txt').decode()
                df_eventos = processa_json(json_texto, classe, indice)
                persiste_df(df_eventos, classe, session)
        # Sair por segurança. Comentar linha abaixo para funcionar
        sys.exit(0)
        '''
        metadata.drop_all(engine, [metadata.tables['apirecintos_acessosveiculo'],
                                   metadata.tables['apirecintos_pesagensveiculo'],
                                   metadata.tables['apirecintos_inspecoesnaoinvasivas'], ])
        metadata.create_all(engine, [metadata.tables['apirecintos_acessosveiculo'],
                                     metadata.tables['apirecintos_pesagensveiculo'],
                                     metadata.tables['apirecintos_inspecoesnaoinvasivas'], ])
        '''
