from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Table
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata

# Tabelas auxiliares / log


marcasencontradas_table = Table('marcasencontradas', metadata,
                                Column('rvf_id', BigInteger(), ForeignKey('verificacoesfisicas.id')),
                                Column('marca_id', BigInteger(), ForeignKey('marcas.id'))
                                )


class RVF(Base):
    __tablename__ = 'verificacoesfisicas'
    id = Column(BigInteger(), primary_key=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    numeroDI = Column(VARCHAR(10), index=True)
    numeroDUE = Column(VARCHAR(10), index=True)
    descricao = Column(VARCHAR(40), index=True)
    marcasencontradas = relationship("Marca",
                                     secondary=marcasencontradas_table)
    datahora = Column(TIMESTAMP, index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())


class Marca(Base):
    __tablename__ = 'marcas'
    id = Column(BigInteger(), primary_key=True)
    nome = Column(VARCHAR(50), index=True)


if __name__ == '__main__':
    import sys

    sys.path.insert(0, '.')
    sys.path.insert(0, '../ajna_docs/commons')
    sys.path.insert(0, '../virasana')
    from bhadrasana.main import engine

    metadata.create_all(engine,
                        [
                            metadata.tables['marcasencontradas'],
                            metadata.tables['marcas'],
                            metadata.tables['verificacoesfisicas']
                        ])
