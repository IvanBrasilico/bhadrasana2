import sys
from datetime import datetime


sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
sys.path.insert(0, '../ajna_api')

from ajna_commons.flask.conf import SQL_URI

from sqlalchemy import BigInteger, Column, DateTime, func, VARCHAR, Table, \
    Numeric, Integer, create_engine, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import relationship, sessionmaker

from bhadrasana.models import Base, BaseRastreavel, BaseDumpable

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

lacresverificados_table = Table('ovr_lacresverificados', metadata,
                                Column('rvf_id', BigInteger(),
                                       ForeignKey('ovr_verificacoesfisicas.id')),
                                Column('lacre_id', BigInteger(),
                                       ForeignKey('ovr_lacres.id')),
                                )

k9sutilizados_table = Table('ovr_k9sutilizados', metadata,
                                Column('rvf_id', BigInteger(),
                                       ForeignKey('ovr_verificacoesfisicas.id')),
                                Column('k9_id', BigInteger(),
                                       ForeignKey('ovr_k9s.id')),
                                )

class RVF(BaseRastreavel, BaseDumpable):
    __tablename__ = 'ovr_verificacoesfisicas'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    ovr_id = Column(BigInteger(), ForeignKey('ovr_ovrs.id'), index=True)
    ovr = relationship('OVR')
    numeroCEmercante = Column(VARCHAR(15), index=True)
    numerolote = Column(VARCHAR(20), index=True)
    descricao = Column(VARCHAR(5000), index=True)
    descricao_interna = Column(VARCHAR(5000), index=True)
    peso = Column(Numeric(10, 2), index=True)
    volume = Column(Numeric(10, 2), index=True)
    imagens = relationship('ImagemRVF', back_populates='rvf')
    marcasencontradas = relationship('Marca',
                                     secondary=marcasencontradas_table)
    infracoesencontradas = relationship('Infracao',
                                        secondary=infracoesencontradas_table)
    lacresverificados = relationship('Lacre',
                                     secondary=lacresverificados_table)
    k9_apontou = Column(Boolean, index=True)
    k9sutilizados = relationship('K9',
                                     secondary=k9sutilizados_table)
    apreensoes = relationship('ApreensaoRVF',
                              back_populates='rvf')
    datahora = Column(TIMESTAMP, index=True)
    last_modified = Column(DateTime, index=True,
                           onupdate=func.current_timestamp())
    inspecaonaoinvasiva = Column(Boolean, default=False)

    def dump(self, exclude=None, explode=True, imagens=True):
        dumped = super().dump(exclude)
        dumped['peso'] = str(dumped['peso'])
        dumped['volume'] = str(dumped['volume'])
        dumped['datahora'] = datetime.strftime(self.datahora, '%d-%m-%Y %H:%M:%S')
        if explode:
            if imagens:
                dumped['imagens'] = [imagem.dump(explode=True) for imagem in self.imagens]
            dumped['infracoesencontradas'] = [infracao.nome
                                              for infracao in self.infracoesencontradas]
            dumped['marcasencontradas'] = [marca.nome
                                           for marca in self.marcasencontradas]
            dumped['lacresverificados'] = [lacre.numero
                                           for lacre in self.lacresverificados]
            dumped['apreensoes'] = [apreensao.dump()
                                    for apreensao in self.apreensoes]
            dumped['k9sutilizados'] = [k9.nome
                                           for k9 in self.k9sutilizados]

        return dumped


class ImagemRVF(BaseRastreavel, BaseDumpable):
    __tablename__ = 'ovr_imagensrvf'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    imagem = Column(VARCHAR(100))  # _id da imagem no GrifFS
    descricao = Column(VARCHAR(1000), index=True)
    tg_id = Column(BigInteger(), index=True)
    itemtg_id = Column(BigInteger(), index=True)
    marca_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                      ForeignKey('ovr_marcas.id'))
    marca = relationship(Marca)
    ordem = Column(Integer(), index=True)
    dataModificacao = Column(DateTime())
    rvf_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_verificacoesfisicas.id'))
    rvf = relationship(RVF)

    def dump(self, exclude=None, explode=True):
        dumped = super().dump(exclude)
        if explode:
            if self.marca:
                dumped['marca_descricao'] = self.marca.nome
        return dumped

    @property
    def get_data_modificacao(self):
        if self.dataModificacao is None:
            return datetime.min
        return self.dataModificacao


class Infracao(Base):
    __tablename__ = 'ovr_infracoes'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    nome = Column(VARCHAR(50), index=True)


class Lacre(Base):
    __tablename__ = 'ovr_lacres'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    numero = Column(VARCHAR(50), index=True)


class K9(Base):
    __tablename__ = 'ovr_k9s'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    nome = Column(VARCHAR(50), index=True)


class TipoApreensao(Base):
    __tablename__ = 'ovr_tiposapreensao'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    descricao = Column(VARCHAR(50), index=True)


class ApreensaoRVF(BaseRastreavel, BaseDumpable):
    """Classe para registrar apreensão de drogas em verificação física."""
    __tablename__ = 'ovr_apreensoes_rvf'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True)
    rvf_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                    ForeignKey('ovr_verificacoesfisicas.id'))
    rvf = relationship('RVF')
    descricao = Column(VARCHAR(200), index=True)
    tipo_id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                     ForeignKey('ovr_tiposapreensao.id'))
    tipo = relationship(TipoApreensao)
    peso = Column(Numeric(7, 2))

    def get_peso(self):
        if self.peso is None:
            return '0.00'
        return '{:0.2f}'.format(float(self.peso))

    def dump(self, exclude=None, explode=True):
        dumped = {}  # super().dump(exclude)
        dumped['peso'] = self.get_peso()
        dumped['descricao'] = self.descricao
        dumped['tipo'] = self.tipo.descricao
        return dumped


def create_infracoes(session):
    """Cria testes para classe Infracao"""
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


if __name__ == '__main__':
    # Código para criar/recriar tabelas atualizadas já com alguns dados mínimos
    confirma = input('Revisar o código... '
                     'Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        # sys.exit(0)

        # metadata.drop_all(engine, [ ])
        metadata.create_all(engine,
                            [
                                metadata.tables['ovr_k9s'],
                                metadata.tables['ovr_k9sutilizados']
                            ])

        # create_infracoes(session)
