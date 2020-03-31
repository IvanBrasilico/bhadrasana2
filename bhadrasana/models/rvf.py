import sys

from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Table, \
    Numeric, Integer, create_engine
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship, sessionmaker

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from bhadrasana.models import Base, BaseRastreavel

from bhadrasana.models.ovr import Marca

# Base = declarative_base()

metadata = Base.metadata

marcasencontradas_table = Table('ovr_marcasencontradas', metadata,
                                Column('rvf_id', BigInteger(),
                                       ForeignKey('ovr_verificacoesfisicas.id')),
                                Column('marca_id', BigInteger(),
                                       ForeignKey('ovr_marcas.id')),
                                )

infracoesencontradas_table = Table('ovr_infracoesencontradas', metadata,
                                   Column('rvf_id', BigInteger(),
                                          ForeignKey('ovr_verificacoesfisicas.id')),
                                   Column('infracao_id', BigInteger(),
                                          ForeignKey('ovr_infracoes.id')),
                                   )


class RVF(BaseRastreavel):
    __tablename__ = 'ovr_verificacoesfisicas'
    id = Column(BigInteger(), primary_key=True)
    ovr_id = Column(BigInteger(), index=True)
    numeroCEmercante = Column(VARCHAR(15), index=True)
    numeroDI = Column(VARCHAR(10), index=True)
    numeroDUE = Column(VARCHAR(10), index=True)
    numerolote = Column(VARCHAR(20), index=True)
    descricao = Column(VARCHAR(40), index=True)
    peso = Column(Numeric(10, 2), index=True)
    volume = Column(Numeric(10, 2), index=True)
    marcasencontradas = relationship('Marca',
                                     secondary=marcasencontradas_table)
    infracoesencontradas = relationship('Infracao',
                                        secondary=infracoesencontradas_table)
    datahora = Column(TIMESTAMP, index=True)
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())


class ImagemRVF(Base):
    __tablename__ = 'ovr_imagensrvf'
    id = Column(BigInteger(), primary_key=True)
    rvf_id = Column(BigInteger(), index=True)
    imagem = Column(VARCHAR(100))  # _id da imagem no GrifFS
    descricao = Column(VARCHAR(40), index=True)
    tg_id = Column(BigInteger(), index=True)
    itemtg_id = Column(BigInteger(), index=True)
    marca_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                      ForeignKey('ovr_marcas.id'))
    marca = relationship(Marca)


class Infracao(Base):
    __tablename__ = 'ovr_infracoes'
    id = Column(BigInteger(), primary_key=True)
    nome = Column(VARCHAR(50), index=True)


if __name__ == '__main__':
    # Código para criar/recriar tabelas atualizadas já com alguns dados mínimos
    confirma = input('Revisar o código... '
                     'Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        from ajna_commons.flask.conf import SQL_URI
        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine)
        session = Session()

        metadata.drop_all(engine,
                          [
                              # metadata.tables['ovr_marcasencontradas'],
                              # metadata.tables['ovr_marcas'],
                              # metadata.tables['ovr_infracoesencontradas'],
                              # metadata.tables['ovr_infracoes'],
                              # metadata.tables['ovr_verificacoesfisicas']
                              # metadata.tables['ovr_imagensrvf'],
                          ])
        metadata.create_all(engine,
                            [
                                # metadata.tables['ovr_marcasencontradas'],
                                # metadata.tables['ovr_marcas'],
                                # metadata.tables['ovr_infracoesencontradas'],
                                # metadata.tables['ovr_infracoes'],
                                # metadata.tables['ovr_verificacoesfisicas'],
                                # metadata.tables['ovr_imagensrvf'],
                            ])
        """"
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
        """
