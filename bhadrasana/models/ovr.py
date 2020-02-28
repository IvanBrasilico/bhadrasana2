from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Integer, \
    ForeignKey, Numeric, CHAR, Table
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship

from ajna_commons.flask.log import logger
from bhadrasana.models import Base, BaseRastreavel

metadata = Base.metadata

tipoStatusOVR = [
    'Aguardando distribuicão',
    'Em verificação física',
    'Aguardando Medida Judicial',
    'Aguardando Providência de Outro Setor',
    'Aguardando Laudo Técnico',
    'Aguardando Laudo de Marcas'
    'Aguardando Saneamento',
    'Recebimento de Saneamento',
    'Intimação/Notificação',
    'Intimação Não Respondida',
    'Retificação do Termo de Guarda'
    'Conclusão',
    'Arquivamento',
    'Atribuição de responsável'
]

tipoOperacao = [
    'Mercadoria Abandonada',
    'Análise de risco',
    'Operação',
    'Denúncia',
    'Demanda interna',
    'Demanda externa'
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
                logger.warning('Item %s não encontrado em %s' % (id, listatipo))
                return None
        else:
            return [(id, item) for id, item in enumerate(listatipo, 1)]

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


class OVR(BaseRastreavel):
    __tablename__ = 'ovr_ovrs'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    numero = Column(VARCHAR(10), index=True)
    tipooperacao = Column(Integer(), index=True)
    ano = Column(VARCHAR(4), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    recinto = Column(VARCHAR(50), index=True)
    observacoes = Column(VARCHAR(200), index=True)
    datahora = Column(TIMESTAMP, index=True)
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

    def get_fase(self):
        return Enumerado.faseOVR(self.fase)

    def get_class(self):
        return Enumerado.classOVR(self.fase)

    def get_tipooperacao(self):
        return Enumerado.tipoOperacao(self.tipooperacao)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fase = 0


class TipoEventoOVR(Base):
    __tablename__ = 'ovr_tiposevento'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    nome = Column(VARCHAR(50), index=True)
    descricao = Column(VARCHAR(100), index=True)
    fase = Column(Integer(), index=True, default=0)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


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


class EventoOVR(Base):
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
    user_name = Column(VARCHAR(50), index=True)
    motivo = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class ProcessoOVR(Base):
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

mercadorias_table = Table('ovr_tgvor_mercadorias', metadata,
                          Column('tg_id', BigInteger().with_variant(Integer, 'sqlite'),
                                 ForeignKey('ovr_tgovr.id')),
                          Column('tipomercadoria_id',
                                 BigInteger().with_variant(Integer, 'sqlite'),
                                 ForeignKey('ovr_tiposmercadoria.id'))
                          )


class TGOVR(Base):
    __tablename__ = 'ovr_tgovr'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    ovr_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_ovrs.id'))
    ovr = relationship('OVR', back_populates='tgs')
    # Número do contêiner ou de lote
    numerolote = Column(VARCHAR(20), index=True, nullable=False)
    descricao = Column(VARCHAR(200), index=True, nullable=False)
    unidadedemedida = Column(Integer(), index=True)
    qtde = Column(Numeric(10, 4))
    valor = Column(Numeric(10, 4))
    marcas = relationship('Marca',
                          secondary=marcas_table)
    mercadorias = relationship('TipoMercadoria',
                               secondary=mercadorias_table)
    itenstg = relationship('ItemTG', back_populates='tg')
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())

    def get_unidadedemedida(self):
        return Enumerado.unidadeMedida(self.unidadedemedida)


class ItemTG(Base):
    __tablename__ = 'ovr_itenstg'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    tg_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                   ForeignKey('ovr_tgovr.id'))
    tg = relationship('TGOVR', back_populates='itenstg')
    numero = Column(Integer, index=True)
    descricao = Column(VARCHAR(200), index=True, nullable=False)
    qtde = Column(Numeric(10, 4))
    unidadedemedida = Column(Integer(), index=True)
    valor = Column(Numeric(10, 4))
    ncm = Column(VARCHAR(8), index=True)
    marca_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                      ForeignKey('ovr_marcas.id'))
    marca = relationship(Marca)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())

    def get_unidadedemedida(self):
        return Enumerado.unidadeMedida(self.unidadedemedida)


if __name__ == '__main__':  # pragma: no-cover
    confirma = input('Revisar o código... '
                     'Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        import sys

        sys.path.insert(0, '.')
        sys.path.insert(0, '../ajna_docs/commons')
        sys.path.insert(0, '../virasana')
        from bhadrasana.main import engine

        metadata.drop_all(engine)
        metadata.create_all(engine)

        metadata.drop_all(engine,
                          [
                              # metadata.tables['ovr_ovrs'],
                              # metadata.tables['ovr_tiposevento'],
                              # metadata.tables['ovr_tiposprocesso'],
                              # metadata.tables['ovr_eventos'],
                              # metadata.tables['ovr_processos'],
                              # metadata.tables['ovr_tgovr'],
                              # metadata.tables['ovr_itenstg'],
                              # metadata.tables['ovr_setores'],
                              # metadata.tables['ovr_usuarios'],
                              # metadata.tables['ovr_tiposmercadoria'],
                          ])

        metadata.create_all(engine,
                            [
                                #  metadata.tables['ovr_ovrs'],
                                #  metadata.tables['ovr_tiposevento'],
                                #  metadata.tables['ovr_tiposprocesso'],
                                #  metadata.tables['ovr_eventos'],
                                #  metadata.tables['ovr_processos'],
                                #  metadata.tables['ovr_tiposmercadoria'],
                                #  metadata.tables['ovr_tgovr'],
                                #  metadata.tables['ovr_itenstg'],
                                #  metadata.tables['ovr_setores'],
                                #  metadata.tables['ovr_usuarios'],
                                #  metadata.tables['ovr_recintos'],
                            ])
        """
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
        """

        """
        fases = [0, 1, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 4, 1]
        for nome, fase in enumerate(tipoStatusOVR, fases):
            evento = TipoEventoOVR()
            evento.nome = nome
            evento.fase = fase
            session.add(evento)
        session.commit()
        """
