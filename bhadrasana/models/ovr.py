from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Integer, ForeignKey
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata


# Tabelas auxiliares / log


class OVR(Base):
    __tablename__ = 'ovr_ovrs'
    id = Column(BigInteger(), primary_key=True)
    numero = Column(VARCHAR(10), index=True)
    ano = Column(VARCHAR(4), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    recinto = Column(VARCHAR(50), index=True)
    observacoes = Column(VARCHAR(200), index=True)
    datahora = Column(TIMESTAMP, index=True)
    fase = Column(Integer(), index=True)
    responsavel = Column(VARCHAR(14), index=True)
    user_name = Column(VARCHAR(14), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())
    historico = relationship("EventoOVR", back_populates="ovr")
    processos = relationship("ProcessoOVR", back_populates="ovr")


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


if __name__ == '__main__':
    import sys

    sys.path.insert(0, '.')
    sys.path.insert(0, '../ajna_docs/commons')
    sys.path.insert(0, '../virasana')
    from bhadrasana.main import engine

    metadata.create_all(engine,
                        [
                            metadata.tables['ovr_ovrs'],
                            # metadata.tables['ovr_tiposevento'],
                            metadata.tables['ovr_tiposprocesso'],
                            metadata.tables['ovr_eventos'],
                            metadata.tables['ovr_processos'],

                        ])
