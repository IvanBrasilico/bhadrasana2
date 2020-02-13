from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Integer, ForeignKey
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata


# Tabelas auxiliares / log


class FMA(Base):
    __tablename__ = 'fma_fmas'
    id = Column(BigInteger(), primary_key=True)
    numero = Column(VARCHAR(10), index=True)
    ano = Column(VARCHAR(4), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    recinto = Column(VARCHAR(50), index=True)
    observacoes = Column(VARCHAR(200), index=True)
    datahora = Column(TIMESTAMP, index=True)
    fase = Column(Integer(), index=True)
    status = Column(Integer(), index=True)
    user_name = Column(VARCHAR(50), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())
    historico = relationship("HistoricoFMA", back_populates="fma")


class HistoricoFMA(Base):
    __tablename__ = 'fma_historico'
    id = Column(BigInteger(), primary_key=True)
    fma_id = Column(BigInteger(), ForeignKey('fma_fmas.id'))
    fma = relationship("FMA", back_populates="historico")
    fase = Column(Integer(), index=True, default=0)
    status = Column(Integer(), index=True, default=0)
    user_name = Column(VARCHAR(50), index=True)
    motivo = Column(VARCHAR(50), index=True)
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
                            metadata.tables['fma_fmas'],
                            metadata.tables['fma_historico'],
                        ])
