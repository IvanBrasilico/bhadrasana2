import sys
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Integer, \
    ForeignKey, Numeric, CHAR, Table, create_engine, Text
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship, sessionmaker

sys.path.insert(0, '.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from bhadrasana.models import Base, BaseRastreavel

metadata = Base.metadata


class EventoEspecial(Enum):
    Responsavel = 1
    RVF = 2
    TG = 3
    Autuação = 4


tipoStatusOVREspecial = [
    ('Atribuição de responsável', EventoEspecial.Responsavel.value, 1),
    ('RVF incluída', EventoEspecial.RVF.value, 1),
    ('TG incluído', EventoEspecial.TG.value, 1),
    ('Emissão de Auto de Infração', EventoEspecial.Autuação.value, 4)
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
    'Análise de risco na importação',
    'Operação / análise de risco na exportação',
    'Denúncia na importação',
    'Denúncia na exportação',
    'Demanda externa',
    'Registro de operação de outros órgãos/países'
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
    'KG'
]


class Enumerado:

    @classmethod
    def get_tipo(cls, listatipo: list, id: int = None):
        if (id is not None) and isinstance(id, int):
            try:
                return listatipo[id]
            except IndexError:
                print('Item %s não encontrado em %s' % (id, listatipo))
                return None
        else:
            return [(id, item) for id, item in enumerate(listatipo, 0)]

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


class OVR(BaseRastreavel):
    __tablename__ = 'ovr_ovrs'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    numero = Column(VARCHAR(10), index=True)
    tipooperacao = Column(Integer(), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    numerodeclaracao = Column(VARCHAR(20), index=True)
    observacoes = Column(VARCHAR(500), index=True)
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
    tgs = relationship('TGOVR', back_populates='ovr')
    flags = relationship('Flag', secondary=flags_table)

    def get_ano(self):
        if self.datahora is not None and isinstance(self.datahora, datetime):
            return self.datahora.year
        return ''

    def get_fase(self):
        return Enumerado.faseOVR(self.fase)

    def get_class(self):
        return Enumerado.classOVR(self.fase)

    def get_tipooperacao(self):
        return Enumerado.tipoOperacao(self.tipooperacao)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fase = 0


class Flag(Base):
    __tablename__ = 'ovr_flags'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(100), index=True)


class TipoEventoOVR(Base):
    __tablename__ = 'ovr_tiposevento'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(50), index=True)
    descricao = Column(VARCHAR(100), index=True)
    fase = Column(Integer(), index=True, default=0)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())
    eventoespecial = Column(Integer(), index=True)


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


class Recinto(Base):
    __tablename__ = 'ovr_recintos'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(50), index=True)
    descricao = Column(VARCHAR(100), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class TipoProcessoOVR(Base):
    __tablename__ = 'ovr_tiposprocesso'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    descricao = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class EventoOVR(BaseRastreavel):
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
    motivo = Column(VARCHAR(50), index=True)
    anexo_filename = Column(VARCHAR(100), index=True)  # ID no Mongo


class ProcessoOVR(BaseRastreavel):
    __tablename__ = 'ovr_processos'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    ovr_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_ovrs.id'))
    ovr = relationship('OVR', back_populates='processos')
    tipoprocesso_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                             ForeignKey('ovr_tiposprocesso.id'))
    tipoprocesso = relationship('TipoProcessoOVR')
    numero = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class Marca(Base):
    __tablename__ = 'ovr_marcas'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    nome = Column(VARCHAR(50), index=True)


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


class TGOVR(BaseRastreavel):
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
    valor = Column(Numeric(10, 2))
    marcas = relationship('Marca',
                          secondary=marcas_table)
    tipomercadoria_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                               ForeignKey('ovr_tiposmercadoria.id'))
    tipomercadoria = relationship('TipoMercadoria')
    itenstg = relationship('ItemTG', back_populates='tg')
    numerotg = Column(VARCHAR(20), index=True)
    afrfb = Column(VARCHAR(20), index=True)
    identificacao = Column(VARCHAR(50), index=True)
    observacoes = Column(VARCHAR(500), index=True)

    def get_unidadedemedida(self):
        return Enumerado.unidadeMedida(self.unidadedemedida)


class ItemTG(BaseRastreavel):
    __tablename__ = 'ovr_itenstg'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    tg_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                   ForeignKey('ovr_tgovr.id'), nullable=False)
    tg = relationship('TGOVR', back_populates='itenstg')
    numero = Column(Integer, index=True, nullable=False)
    descricao = Column(VARCHAR(500), index=True, nullable=False)
    qtde = Column(Numeric(10, 2))
    unidadedemedida = Column(Integer(), index=True)
    valor = Column(Numeric(10, 2), index=True)
    ncm = Column(VARCHAR(8), index=True)
    marca_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                      ForeignKey('ovr_marcas.id'))
    marca = relationship(Marca)

    def get_unidadedemedida(self):
        return Enumerado.unidadeMedida(self.unidadedemedida)


class Relatorio(Base):
    __tablename__ = 'ovr_relatorios'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(200), index=True, nullable=False)
    sql = Column(Text())


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
    """Cria testes para classe TipoProcesso"""
    for nome in ('Dossiê',
                 'Auto de infração',
                 'RFPFP'):
        flag = Flag()
        flag.nome = nome
        session.add(flag)
    session.commit()


def create_tiposevento(session):
    """Cria dados da tabela básica de Eventos"""
    fases = [0, 1, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 4]
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
        # sys.exit(0)
        # metadata.drop_all(engine)
        metadata.create_all(engine,
                            [
                                metadata.tables['ovr_roteiros']
                                # metadata.tables['ovr_flags'],
                                # metadata.tables['ovr_flags_ovr'],
                            ])
        metadata.drop_all(engine,
                          [
                              # metadata.tables['ovr_tgvor_marcas'],
                              # metadata.tables['ovr_itenstg'],
                              # metadata.tables['ovr_eventos'],
                              # metadata.tables['ovr_processos'],
                              # metadata.tables['ovr_tgovr'],
                          ])
        # metadata.create_all(engine)
        # create_tiposevento(session)
        # create_marcas(session)
        # create_tipomercadoria(session)
        # create_flags(session)
        # create_tiposprocesso(session)
