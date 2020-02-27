from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Table, Numeric
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata

marcasencontradas_table = Table('ovr_marcasencontradas', metadata,
                                Column('rvf_id', BigInteger(),
                                       ForeignKey('ovr_verificacoesfisicas.id')),
                                Column('marca_id', BigInteger(),
                                       ForeignKey('ovr_marcas.id'))
                                )

infracoesencontradas_table = Table('ovr_infracoesencontradas', metadata,
                                   Column('rvf_id', BigInteger(),
                                          ForeignKey('ovr_verificacoesfisicas.id')),
                                   Column('infracao_id', BigInteger(),
                                          ForeignKey('ovr_infracoes.id'))
                                   )


class RVF(Base):
    __tablename__ = 'ovr_verificacoesfisicas'
    id = Column(BigInteger(), primary_key=True)
    ovr_id = Column(BigInteger(), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    numeroDI = Column(VARCHAR(10), index=True)
    numeroDUE = Column(VARCHAR(10), index=True)
    descricao = Column(VARCHAR(40), index=True)
    peso = Column(Numeric(10, 2), index=True)
    volume = Column(Numeric(10, 2), index=True)
    marcasencontradas = relationship('Marca',
                                     secondary=marcasencontradas_table)
    infracoesencontradas = relationship('Infracao',
                                        secondary=infracoesencontradas_table)
    datahora = Column(TIMESTAMP, index=True)
    username = Column(VARCHAR(14), index=True)
    create_date = Column(TIMESTAMP, index=True,
                         server_default=func.current_timestamp())
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())


class Marca(Base):
    __tablename__ = 'ovr_marcas'
    id = Column(BigInteger(), primary_key=True)
    nome = Column(VARCHAR(50), index=True)


class Infracao(Base):
    __tablename__ = 'ovr_infracoes'
    id = Column(BigInteger(), primary_key=True)
    nome = Column(VARCHAR(50), index=True)


if __name__ == '__main__':
    import sys

    sys.path.insert(0, '.')
    sys.path.insert(0, '../ajna_docs/commons')
    sys.path.insert(0, '../virasana')
    from bhadrasana.main import engine, session

    metadata.drop_all(engine,
                      [
                          metadata.tables['ovr_marcasencontradas'],
                          metadata.tables['ovr_marcas'],
                          metadata.tables['ovr_infracoesencontradas'],
                          metadata.tables['ovr_infracoes'],
                          metadata.tables['ovr_verificacoesfisicas']
                      ])
    metadata.create_all(engine,
                        [
                            metadata.tables['ovr_marcasencontradas'],
                            metadata.tables['ovr_marcas'],
                            metadata.tables['ovr_infracoesencontradas'],
                            metadata.tables['ovr_infracoes'],
                            metadata.tables['ovr_verificacoesfisicas']
                        ])

    for nome in ('Falsa declaração de conteúdo',
                 'Interposição',
                 'Contrafação',
                 'Quantidade divergente',
                 'Fraude de valor',
                 'Mercadoria não declarada',
                 'Contrabando - produto proibido',
                 'Drogas',
                 'Armas',
                 'Cigarros'):
        infracao = Infracao()
        infracao.nome = nome
        session.add(infracao)
    session.commit()
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
