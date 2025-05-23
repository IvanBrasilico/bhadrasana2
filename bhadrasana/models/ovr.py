import sys

from bson import ObjectId
from gridfs import GridFS

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../ajna_api')
sys.path.insert(0, '../virasana')
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Integer, \
    ForeignKey, Numeric, CHAR, Table, create_engine, Text, event, Boolean
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship, sessionmaker

from bhadrasana.models import Base, BaseRastreavel, BaseDumpable, myEnum

metadata = Base.metadata


class EventoEspecial(Enum):
    Responsavel = 1
    RVF = 2
    TG = 3
    Autuacao = 4
    AuditorResponsavel = 5
    MudancaSetor = 6
    InspecaoNaoInvasiva = 7
    EncerramentoComResultado = 8
    EncerramentoSemResultado = 9


tipoStatusOVREspecial = [
    ('Atribuição de responsável', EventoEspecial.Responsavel.value, 1),
    ('RVF incluída', EventoEspecial.RVF.value, 1),
    ('TG incluído', EventoEspecial.TG.value, 1),
    ('Emissão de Auto de Infração', EventoEspecial.Autuacao.value, 3),
    ('Definição de Auditor Responsável', EventoEspecial.AuditorResponsavel.value, 1),
    ('Atribuição para outro Setor', EventoEspecial.MudancaSetor.value, 0),
    ('Inspeção não invasiva', EventoEspecial.InspecaoNaoInvasiva.value, 1),
    ('Encerramento com resultado', EventoEspecial.EncerramentoComResultado.value, 3),
    ('Encerramento sem resultado', EventoEspecial.EncerramentoSemResultado.value, 4),
]

tipoStatusOVR = [
    'Aguardando distribuicão',
    'Em verificação física',
    'Aguardando Medida Judicial',
    'Aguardando Providência de Outro Setor',
    'Aguardando Laudo Técnico',
    'Aguardando Laudo de Marcas',
    'Aguardando Saneamento',
    'Recebimento de Saneamento',
    'Intimação/Notificação',
    'Intimação Não Respondida',
    'Retificação do Termo de Guarda',
    'Arquivamento',
]

tipoOperacao = [
    'Mercadoria Abandonada',
    'Repressão mediante análise de risco na importação',
    'Repressão mediante análise de risco na exportação',
    'Pesquisa e seleção na importação',
    'Pesquisa e seleção na exportação',
    'Demanda externa',
    'Registro de operação de outros países',
    'Vigilância',
    'Registro de operação de outros órgãos'
]

faseOVR = [
    'Iniciada',
    'Ativa',
    'Suspensa',
    'Concluída',
    'Arquivada'
]

classOVR = [
    'text-warning',
    'text-primary',
    'text-danger',
    'text-success',
    'text-secondary',
]

tipoProcesso = [
    'Perdimento',
    'Crédito',
    'Sanção',
    'RFFP',
    'Dossiê',
    'Radar'
]

unidadeMedida = [
    'UN',
    'KG',
    ' '
]


class TipoResultado(Enum):
    Apreensao = 1
    Perdimento = 2
    Credito = 3
    Sancao = 4
    DARF = 5
    MultaRFB = 6
    MultaOutroOrgao = 7


class FonteDocx(Enum):
    Ficha = 1
    RVF = 2
    Marcas = 3
    TG_Ficha = 4


class Assistente(Enum):
    Marcas = 1


class Enumerado(myEnum):

    @classmethod
    def faseOVR(cls, id=None):
        return cls.get_tipo(faseOVR, id)

    @classmethod
    def classOVR(cls, id=None):
        return cls.get_tipo(classOVR, id)

    @classmethod
    def tipoOperacao(cls, id=None):
        return cls.get_tipo(tipoOperacao, id)

    @classmethod
    def tipoProcesso(cls, id=None):
        return cls.get_tipo(tipoProcesso, id)

    @classmethod
    def unidadeMedida(cls, id=None):
        return cls.get_tipo(unidadeMedida, id)

    @classmethod
    def index_unidadeMedida(cls, sigla):
        return unidadeMedida.index(sigla)


flags_table = Table('ovr_flags_ovr', metadata,
                    Column('rvf_id', BigInteger(),
                           ForeignKey('ovr_ovrs.id')),
                    Column('flag_id', BigInteger(),
                           ForeignKey('ovr_flags.id')),
                    )


class OVR(BaseRastreavel, BaseDumpable):
    __tablename__ = 'ovr_ovrs'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    numero = Column(VARCHAR(10), index=True)
    # Ano para facilitar chave única FMA
    ano = Column(VARCHAR(4), index=True)
    tipooperacao = Column(Integer(), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    numerodeclaracao = Column(VARCHAR(20), index=True)  # DUE
    observacoes = Column(VARCHAR(1000), index=True)
    datahora = Column(TIMESTAMP, index=True)
    dataentrada = Column(DateTime, index=True)
    fase = Column(Integer(), index=True, default=0)
    tipoevento_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                           ForeignKey('ovr_tiposevento.id'),
                           default=1)
    tipoevento = relationship('TipoEventoOVR')
    recinto_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                        ForeignKey('ovr_recintos.id'))
    recinto = relationship('Recinto')
    setor_id = Column(CHAR(15),
                      ForeignKey('ovr_setores.id'))
    setor = relationship('Setor')
    responsavel_cpf = Column(VARCHAR(15), ForeignKey('ovr_usuarios.cpf'))
    responsavel = relationship('Usuario')
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())
    historico = relationship('EventoOVR', back_populates='ovr')
    processos = relationship('ProcessoOVR', back_populates='ovr')
    resultados = relationship('ResultadoOVR', back_populates='ovr')
    tgs = relationship('TGOVR', back_populates='ovr')
    flags = relationship('Flag', secondary=flags_table)
    cnpj_fiscalizado = Column(VARCHAR(15), index=True)
    cpfauditorresponsavel = Column(VARCHAR(15))

    def get_ano(self):
        if self.datahora is not None and isinstance(self.datahora, datetime):
            return self.datahora.year
        return self.ano

    def get_numero(self):
        # Formatação de número definida apenas para FMA
        if self.tipooperacao == 0:
            try:
                return '{:05d}'.format(int(self.numero))
            except (ValueError, TypeError):
                pass
        if self.numero is None:
            return ''
        return self.numero

    def get_fase(self):
        return Enumerado.faseOVR(self.fase)

    def get_class(self):
        return Enumerado.classOVR(self.fase)

    def get_tipooperacao(self):
        return Enumerado.tipoOperacao(self.tipooperacao)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fase = 0

    def dump(self, exclude=None, explode=True):
        dumped = super().dump(exclude)
        if explode:
            dumped['tipooperacao_descricao'] = self.get_tipooperacao()
            dumped['fase_descricao'] = self.get_fase()
            dumped['ano'] = self.get_ano()
            if self.responsavel:
                dumped['responsavel'] = self.responsavel.nome
            if self.setor:
                dumped['setor'] = self.setor.nome
            if self.recinto:
                dumped['recinto'] = self.recinto.nome
                # dumped['cnpj_recinto'] = self.recinto.cnpj
            dumped['numero'] = self.get_numero()
            dumped['flags'] = [flag.nome for flag in self.flags]
            dumped['historico'] = [evento.dump() for evento in self.historico]
            dumped['processos'] = [processo.dump() for processo in self.processos]
            dumped['tgs'] = [tg.dump() for tg in self.tgs]
            dumped['datahora'] = datetime.strftime(self.datahora, '%d-%m-%Y %H:%M:%S')
        return dumped


class Flag(Base):
    __tablename__ = 'ovr_flags'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(100), index=True)

    def __str__(self):
        return '{}'.format(self.nome)


class TipoEventoOVR(BaseDumpable):
    __tablename__ = 'ovr_tiposevento'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(50), index=True)
    descricao = Column(VARCHAR(100), index=True)
    fase = Column(Integer(), index=True, default=0)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())
    eventoespecial = Column(Integer(), index=True)
    ordem = Column(Integer())

    def __str__(self):
        return '{} - {}'.format(self.id, self.nome)

    @property
    def descricao_fase(self):
        return Enumerado.faseOVR(self.fase)


class RoteiroOperacaoOVR(Base):
    """Classe para confecção de roteiros/checklists por tipo de operação."""
    __tablename__ = 'ovr_roteiros'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    tipooperacao = Column(Integer(), index=True, default=0)
    tipoevento_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                           ForeignKey('ovr_tiposevento.id'))
    tipoevento = relationship('TipoEventoOVR')
    descricao = Column(VARCHAR(500), index=True)
    ordem = Column(Integer(), index=True)
    quem = Column(VARCHAR(10), index=True)

    @property
    def descricao_tipooperacao(self):
        return Enumerado.tipoOperacao(self.tipooperacao)


class Recinto(Base):
    __tablename__ = 'ovr_recintos'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(50), index=True)
    descricao = Column(VARCHAR(100), index=True)
    cod_dte = Column(Integer())
    cnpj = Column(VARCHAR(15), index=True)
    cod_siscomex = Column(VARCHAR(20), index=True)
    cod_unidade = Column(VARCHAR(20), index=True)
    cod_carga = Column(VARCHAR(20), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())

    def __repr__(self):
        codigo = self.cod_siscomex if self.cod_siscomex else self.cod_dte
        return f'{self.nome} ({codigo}) CNPJ {self.cnpj}'


class TipoProcessoOVR(Base):
    __tablename__ = 'ovr_tiposprocesso'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    descricao = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class EventoOVR(BaseRastreavel, BaseDumpable):
    __tablename__ = 'ovr_eventos'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    ovr_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_ovrs.id'))
    ovr = relationship('OVR', back_populates='historico')
    tipoevento_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                           ForeignKey('ovr_tiposevento.id'))
    tipoevento = relationship('TipoEventoOVR')
    fase = Column(Integer(), index=True, default=0)
    motivo = Column(VARCHAR(200), index=True)
    anexo_filename = Column(VARCHAR(100), index=True)  # ID no Mongo
    excluido = Column(Boolean, index=True)
    meramente_informativo = Column(Boolean, index=False)

    def get_detalhes(self):
        return self.motivo.split('|')[0]

    def get_motivos(self):
        return ''.join(self.motivo.split('|')[1:] )


    @property
    def descricao_fase(self):
        return Enumerado.faseOVR(self.fase)

    def dump(self, exclude=None, explode=True):
        dumped = super().dump(exclude)
        if explode:
            if self.tipoevento:
                dumped['tipoevento_descricao'] = self.tipoevento.nome
            if self.fase:
                dumped['fase_descricao'] = self.descricao_fase
        return dumped


class ProcessoOVR(BaseRastreavel, BaseDumpable):
    __tablename__ = 'ovr_processos'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    ovr_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_ovrs.id'))
    ovr = relationship('OVR', back_populates='processos')
    tipoprocesso_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                             ForeignKey('ovr_tiposprocesso.id'))
    tipoprocesso = relationship('TipoProcessoOVR')
    numero = Column(VARCHAR(50), index=True)
    numerolimpo = Column(VARCHAR(50), index=True)

    def atualiza_numerolimpo(self, numero):
        self.numerolimpo = ''.join([s for s in numero if s.isnumeric()])

    def dump(self, exclude=None, explode=True):
        dumped = super().dump(exclude)
        if explode:
            dumped['tipoprocesso'] = self.tipoprocesso.descricao
        return dumped


@event.listens_for(ProcessoOVR.numero, 'set', retval=True)
def atualiza_numerolimpo(target, value, oldvalue, initiator):
    target.atualiza_numerolimpo(value)
    return value


class Marca(BaseDumpable):
    __tablename__ = 'ovr_marcas'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    nome = Column(VARCHAR(50), index=True)

    def __str__(self):
        return '{}'.format(self.nome)


class RepresentanteMarca(BaseDumpable):
    __tablename__ = 'ovr_representantes_marcas'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    cnpj = Column(VARCHAR(15), index=True)
    nome = Column(VARCHAR(200), index=True)
    endereco = Column(VARCHAR(200), index=True)
    cep = Column(VARCHAR(10), index=True)
    telefone = Column(VARCHAR(20), index=True)
    email = Column(VARCHAR(100), index=True)
    representacoes = relationship('Representacao', back_populates='representante')

    def __str__(self):
        return '{} - {}'.format(self.nome, self.cnpj)


class Representacao(Base):
    __tablename__ = 'ovr_representacoes'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    marca_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                      ForeignKey('ovr_marcas.id'))
    marca = relationship('Marca')
    representante_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                              ForeignKey('ovr_representantes_marcas.id'))
    representante = relationship('RepresentanteMarca', back_populates='representacoes')
    inicio = Column(TIMESTAMP, index=True)
    fim = Column(DateTime, index=True)

    def __str__(self):
        representante_nome = 'Nenhum'
        if self.representante_id and self.representante:
            representante_nome = self.representante.nome

        return 'Marca: {} - Representante: {} - Inicio: {} - Fim: {}'.format(
            self.marca.nome, representante_nome, self.inicio, self.fim)


class TipoMercadoria(Base):
    __tablename__ = 'ovr_tiposmercadoria'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(50), index=True)


marcas_table = Table('ovr_tgvor_marcas', metadata,
                     Column('tg_id', BigInteger().with_variant(Integer, 'sqlite'),
                            ForeignKey('ovr_tgovr.id')),
                     Column('marca_id', BigInteger().with_variant(Integer, 'sqlite'),
                            ForeignKey('ovr_marcas.id'))
                     )


class TGOVR(BaseRastreavel, BaseDumpable):
    __tablename__ = 'ovr_tgovr'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    ovr_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_ovrs.id'))
    ovr = relationship('OVR', back_populates='tgs')
    # Número do contêiner ou de lote
    numerolote = Column(VARCHAR(20), index=True, nullable=False)
    descricao = Column(VARCHAR(500), index=True, nullable=False)
    unidadedemedida = Column(Integer(), index=True)
    qtde = Column(Numeric(10, 2))
    valor = Column(Numeric(12, 2))
    marcas = relationship('Marca',
                          secondary=marcas_table)
    tipomercadoria_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                               ForeignKey('ovr_tiposmercadoria.id'))
    tipomercadoria = relationship('TipoMercadoria')
    itenstg = relationship('ItemTG', back_populates='tg')
    numerotg = Column(VARCHAR(50), index=True)
    afrfb = Column(VARCHAR(20), index=True)
    identificacao = Column(VARCHAR(50), index=True)
    observacoes = Column(VARCHAR(500), index=True)

    @property
    def get_unidadedemedida(self):
        return Enumerado.unidadeMedida(self.unidadedemedida)

    @property
    def numerotg_alnum(self):
        return ''.join(s for s in self.numerotg if s.isalnum())

    def dump(self, exclude=None, explode=True):
        dumped = super().dump(exclude)
        dumped['qtde'] = str(dumped['qtde'])
        dumped['valor'] = str(dumped['valor'])
        if self.tipomercadoria:
            dumped['tipomercadoria_descricao'] = self.tipomercadoria.nome
        return dumped


class ItemTG(BaseRastreavel, BaseDumpable):
    __tablename__ = 'ovr_itenstg'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    tg_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                   ForeignKey('ovr_tgovr.id'), nullable=False)
    tg = relationship('TGOVR', back_populates='itenstg')
    numero = Column(Integer, index=True, nullable=False)
    descricao = Column(VARCHAR(500), index=True, nullable=False)
    contramarca = Column(VARCHAR(200), index=True)
    modelo = Column(VARCHAR(200), index=True)
    qtde = Column(Numeric(10, 2))
    unidadedemedida = Column(Integer(), index=True)
    valor = Column(Numeric(10, 2), index=True)
    ncm = Column(VARCHAR(8), index=True)
    marca_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                      ForeignKey('ovr_marcas.id'))
    marca = relationship(Marca)

    @property
    def get_unidadedemedida(self):
        return Enumerado.unidadeMedida(self.unidadedemedida)

    @property
    def hscode(self):
        return self.ncm[:6]

    def importa_str_float(self, ovalor: str):
        ovalor = ''.join([c for c in ovalor if c in '0123456789.'])
        return float(ovalor)

    def set_qtde_str(self, strqtde: str):
        self.qtde = self.importa_str_float(strqtde)

    def set_valor_str(self, strvalor: str):
        self.valor = self.importa_str_float(strvalor)

    def format_float(self, ofloat):
        if ofloat is None:
            return '0.00'
        return '{:,.2f}'.format(ofloat). \
            replace('.', '-').replace(',', '.').replace('-', ',')

    @property
    def qtde_str(self) -> str:
        if self.qtde is None:
            return '0.00'
        return '{:,.2fd}'.format(self.qtde)

    @property
    def valor_str(self) -> str:
        if self.valor is None:
            return '0.00'
        return '{:0,.2f}'.format(self.valor). \
            replace('.', '-').replace(',', '.').replace('-', ',')

    def dump(self, exclude=None, explode=True):
        dumped = super().dump(exclude)
        dumped['qtde'] = self.format_float(self.qtde)
        dumped['valor'] = self.format_float(self.valor)
        if self.marca:
            dumped['marca_descricao'] = self.marca.nome
        dumped['unidadedemedida'] = self.get_unidadedemedida
        return dumped


class Relatorio(Base):
    __tablename__ = 'ovr_relatorios'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(200), index=True, nullable=False)
    sql = Column(Text())


class OKRResult(Base):
    __tablename__ = 'ovr_results'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(200), index=True, nullable=False)
    sql = Column(Text())


class OKRResultMeta(Base):
    __tablename__ = 'ovr_okrs'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    objective_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                          ForeignKey('ovr_objectives.id'), nullable=False)
    objective = relationship('OKRObjective', back_populates='key_results')
    result_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                       ForeignKey('ovr_results.id'), nullable=False)
    result = relationship('OKRResult')
    ameta = Column(Integer)
    resultados: list = []


class OKRObjective(Base):
    __tablename__ = 'ovr_objectives'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(200), index=True, nullable=False)
    setor_id = Column(CHAR(15))
    inicio = Column(DateTime())
    fim = Column(DateTime())
    key_results = relationship(OKRResultMeta)

    def data_format(self, data):
        return datetime.strftime(data, '%d/%m/%Y')

    @property
    def get_inicio(self):
        if self.inicio is None:
            return ''
        return self.data_format(self.inicio)

    @property
    def get_fim(self):
        if self.fim is None:
            return ''
        return self.data_format(self.fim)

    @property
    def inicio_date(self):
        if self.inicio is None:
            return ''
        return datetime.strftime(self.inicio, '%Y-%m-%d')

    @property
    def fim_date(self):
        if self.fim is None:
            return ''
        return datetime.strftime(self.fim, '%Y-%m-%d')


class VisualizacaoOVR(BaseRastreavel):
    """Classe para registrar ultima visualizacao de um usuario."""
    __tablename__ = 'ovr_visualizacoes'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    ovr_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_ovrs.id'))
    ovr = relationship('OVR')


class ResultadoOVR(BaseRastreavel):
    """Classe para registrar resultado (multa/auto) de uma OVR."""
    __tablename__ = 'ovr_resultados'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    ovr_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_ovrs.id'))
    ovr = relationship('OVR')
    cpf_auditor = Column(VARCHAR(11))
    tipo_resultado = Column(Integer(), default=1)
    valor = Column(Numeric(12, 2))

    @property
    def get_tipo_resultado(self):
        return TipoResultado(self.tipo_resultado).name


class ModeloDocx(BaseRastreavel):
    __tablename__ = 'ovr_docx'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    filename = Column(VARCHAR(200), index=True)
    _id = Column(VARCHAR(100), index=True)  # ID no Mongo
    fonte_docx_id = Column(Integer())

    def get_documento(self, db):
        fs = GridFS(db)
        return fs.get(ObjectId(self._id))


class TiposEventoAssistente(Base):
    """Classe para filtrar tipos de evento por tipo de assistente."""
    __tablename__ = 'ovr_tiposeventoassistente'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    assistente = Column(Integer(), index=True, default=0)
    tipoevento_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                           ForeignKey('ovr_tiposevento.id'))
    tipoevento = relationship('TipoEventoOVR')

    @property
    def descricao_assistente(self):
        return Assistente(self.tipooperacao)


def create_marcas(session):
    """Cria testes para classe Marcas"""
    for nome in ('Adidas',
                 'Burberry',
                 'Tag Hauer',
                 'Nike',
                 'Apple',
                 'Disney'):
        marca = Marca()
        marca.nome = nome
        session.add(marca)
    session.commit()


def create_tiposprocesso(session):
    """Cria testes para classe TipoProcesso"""
    for descricao in ('Dossiê',
                      'Auto de infração',
                      'RFPFP'):
        tipo = TipoProcessoOVR()
        tipo.descricao = descricao
        session.add(tipo)
    session.commit()


def create_flags(session):
    """Cria testes para classe Flag (alertas)"""
    for nome in ('Perecível',
                 'Alto valor agregado',
                 'Importação proibida'):
        flag = Flag()
        flag.nome = nome
        session.add(flag)
    session.commit()


def create_tiposevento(session):
    """Cria dados da tabela básica de Eventos"""
    fases = [0, 1, 2, 2, 2, 2, 2, 1, 2, 1, 2, 4]
    for nome, fase in zip(tipoStatusOVR, fases):
        evento = TipoEventoOVR()
        evento.nome = nome
        evento.fase = fase
        session.add(evento)
    for nome, especial, fase in tipoStatusOVREspecial:
        evento = TipoEventoOVR()
        evento.nome = nome
        evento.fase = fase
        evento.eventoespecial = especial
        session.add(evento)
    session.commit()


def create_tipomercadoria(session):
    """Cria dados da tabela básica de TipoMercadoria"""
    tiposmercadoria = ['Alimentos',
                       'Automotivo',
                       'Bagagem',
                       'Brinquedos',
                       'Eletro-eletrônico',
                       'Livro',
                       'Informática',
                       'Máquinas',
                       'Papel',
                       'Têxtil',
                       'Químico',
                       'Ferramenta',
                       'Obras de metal',
                       'Obras de borracha',
                       'Obras de vidro',
                       'Obras de plástico',
                       'Bebidas',
                       'Medicamento',
                       'Sem valor comercial',
                       'Container vazio']
    for nome in tiposmercadoria:
        tipomercadoria = TipoMercadoria()
        tipomercadoria.nome = nome
        session.add(tipomercadoria)
    session.commit()


if __name__ == '__main__':  # pragma: no-cover
    confirma = input('Revisar o código... '
                     'Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        import sys

        sys.path.append('.')
        sys.path.append('../ajna_docs/commons')
        sys.path.append('../virasana')
        from ajna_commons.flask.conf import SQL_URI

        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        # Sair por segurança. Comentar linha abaixo para funcionar
        # metadata.drop_all(engine)
        # sys.exit(0)
        metadata.create_all(engine,
                            [
                                metadata.tables['ovr_resultados'],
                            ])
        sys.exit(0)
        metadata.drop_all(engine,
                          [
                              metadata.tables['ovr_resultados'],
                          ])
        processos = []  # session.query(ProcessoOVR).all()
        for processo in processos:
            # print(processo)
            processo.set_numero(processo.numero)
            session.add(processo)
            # print(processo.numero, processo.numerolimpo)
        session.commit()
        metadata.create_all(engine)
        create_tiposevento(session)
        create_marcas(session)
        create_tipomercadoria(session)
        create_flags(session)
        create_tiposprocesso(session)
