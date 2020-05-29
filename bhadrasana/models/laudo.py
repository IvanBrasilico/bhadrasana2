import sys
from datetime import datetime

from sqlalchemy import BigInteger, Column, VARCHAR, Integer, Date
from sqlalchemy.ext.declarative import declarative_base

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

Base = declarative_base()


class Empresa(Base):
    __tablename__ = 'laudo_empresas'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    cnpj = Column(VARCHAR(15), index=True)
    nome = Column(VARCHAR(255), index=True)


def get_sigla_unidade(unidade):
    # TODO: Importar Unidades
    return '0817800'


class SAT(Base):
    __tablename__ = 'laudo_sats'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    declaracao = Column(VARCHAR(255), index=True)
    descricao = Column(VARCHAR(255))
    importador = Column(VARCHAR(15), index=True)
    numeroSAT = Column(BigInteger().with_variant(Integer, 'sqlite'), index=True)
    dataPedido = Column(Date, index=True)
    unidade = Column(BigInteger().with_variant(Integer, 'sqlite'), index=True)

    def get_numero(self):
        ano = datetime.strftime(self.dataPedido, '%Y')
        numero = str(self.numeroSAT)
        unidade = get_sigla_unidade(self.unidade)

        return '%s/%s/%s' % (unidade, numero, ano)
