from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
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

tipoProcesso = [
    'Perdimento',
    'Crédito',
    'Sanção',
    'RFFP',
    'Dossiê'
]

unidadeMedida = [
    'UN',
    'KG'
]


class Enumerado:

    @classmethod
    def get_tipo(cls, listatipo: list, id: int = None):
        if (id is not None) and isinstance(id, int):
            return listatipo[id]
        else:
            return [(id, item) for id, item in enumerate(listatipo)]

    @classmethod
    def faseOVR(cls, id=None):
        return cls.get_tipo(faseOVR, id)

    @classmethod
    def tipoOperacao(cls, id=None):
        return cls.get_tipo(tipoOperacao, id)

    @classmethod
    def tipoProcesso(cls, id=None):
        return cls.get_tipo(tipoProcesso, id)

    @classmethod
    def unidadeMedida(cls, id=None):
        return cls.get_tipo(unidadeMedida, id)


class OVR(Base):
    __tablename__ = 'ovr_ovrs'
    id = Column(BigInteger(), primary_key=True)
    numero = Column(VARCHAR(10), index=True)
    tipooperacao = Column(Integer(), index=True)
    ano = Column(VARCHAR(4), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    recinto = Column(VARCHAR(50), index=True)
    observacoes = Column(VARCHAR(200), index=True)
    datahora = Column(TIMESTAMP, index=True)
    fase = Column(Integer(), index=True)
    tipoevento_id = Column(BigInteger(), ForeignKey('ovr_tiposevento.id'))
    tipoevento = relationship("TipoEventoOVR")
    responsavel = Column(VARCHAR(14), index=True)
    user_name = Column(VARCHAR(14), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())
    historico = relationship("EventoOVR", back_populates="ovr")
    processos = relationship("ProcessoOVR", back_populates="ovr")
    itenstg = relationship("ItemTG", back_populates="ovr")

    def get_fase(self):
        return Enumerado.faseOVR(self.fase)

    def get_tipooperacao(self):
        return Enumerado.tipoOperacao(self.tipooperacao)


class TipoEventoOVR(Base):
    __tablename__ = 'ovr_tiposevento'
    id = Column(BigInteger(), primary_key=True)
    nome = Column(VARCHAR(50), index=True)
    descricao = Column(VARCHAR(100), index=True)
    fase = Column(Integer(), index=True, default=0)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class TipoProcessoOVR(Base):
    __tablename__ = 'ovr_tiposprocesso'
    id = Column(BigInteger(), primary_key=True)
    descricao = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class EventoOVR(Base):
    __tablename__ = 'ovr_eventos'
    id = Column(BigInteger(), primary_key=True)
    ovr_id = Column(BigInteger(), ForeignKey('ovr_ovrs.id'))
    ovr = relationship("OVR", back_populates="historico")
    tipoevento_id = Column(BigInteger(), ForeignKey('ovr_tiposevento.id'))
    tipoevento = relationship("TipoEventoOVR")
    fase = Column(Integer(), index=True, default=0)
    user_name = Column(VARCHAR(50), index=True)
    motivo = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class ProcessoOVR(Base):
    __tablename__ = 'ovr_processos'
    id = Column(BigInteger(), primary_key=True)
    ovr_id = Column(BigInteger(), ForeignKey('ovr_ovrs.id'))
    ovr = relationship("OVR", back_populates="processos")
    tipoprocesso_id = Column(Integer(), ForeignKey('ovr_tiposprocesso.id'))
    tipoprocesso = relationship("TipoProcessoOVR")
    numero = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())


class Marca(Base):
    __tablename__ = 'ovr_marcas'
    id = Column(BigInteger(), primary_key=True)
    nome = Column(VARCHAR(50), index=True)


class ItemTG(Base):
    __tablename__ = 'ovr_itenstg'
    id = Column(BigInteger(), primary_key=True)
    ovr_id = Column(BigInteger(), ForeignKey('ovr_ovrs.id'))
    ovr = relationship("OVR", back_populates="itenstg")
    descricao = Column(VARCHAR(200), index=True, nullable=False)
    qtde = Column(Numeric())
    unidadedemedida = Column(Integer(), index=True)
    valor = Column(Numeric())
    ncm = Column(VARCHAR(8), index=True)
    marca_id = Column(BigInteger(), ForeignKey('ovr_marcas.id'))
    marca = relationship(Marca)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())

    def get_unidadedemedida(self):
        return Enumerado.unidadeMedida(self.unidadedemedida)


if __name__ == '__main__':
    import sys

    sys.path.insert(0, '.')
    sys.path.insert(0, '../ajna_docs/commons')
    sys.path.insert(0, '../virasana')
    from bhadrasana.main import engine

    metadata.create_all(engine,
                        [
                            # metadata.tables['ovr_ovrs'],
                            # metadata.tables['ovr_tiposevento'],
                            # metadata.tables['ovr_tiposprocesso'],
                            # metadata.tables['ovr_eventos'],
                            # metadata.tables['ovr_processos'],
                            metadata.tables['ovr_itenstg'],

                        ])