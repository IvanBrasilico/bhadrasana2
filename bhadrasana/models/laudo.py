import sys
from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, Column, VARCHAR, Integer, Date
from sqlalchemy.ext.declarative import declarative_base

from bhadrasana.models import BaseDumpable

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

Base = declarative_base()
metadata = Base.metadata


class Empresa(Base, BaseDumpable):
    __tablename__ = 'laudo_empresas'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    cnpj = Column(VARCHAR(15), index=True)
    nome = Column(VARCHAR(255), index=True)


class NCM(Base, BaseDumpable):
    __tablename__ = 'laudo_ncm'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    title = Column(VARCHAR(20), index=True)
    contents = Column(VARCHAR(2000), index=True)


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
        numero = self.numeroSAT
        unidade = get_sigla_unidade(self.unidade)

        return '{}/{:05d}/{}'.format(unidade, numero, ano)


def get_empresa(session, cnpj: str) -> Empresa:
    """Pesquisa empresa por CNPJ.

    Não encontrando, busca pelo CNPJ raiz e retorna primeira.
    Em caso de falha, retorna None.
    Retorna exceção se parâmetro menor que 8 dígitos
    """
    # Se CNPJ não é numérico, não tenta buscar dados da empresa.
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos.')
    if not cnpj.isnumeric():
        raise ValueError('CNPJ deve ser informado somente com números.')
    empresa = session.query(Empresa).filter(
        Empresa.cnpj == cnpj).first()
    if not empresa:
        empresa = session.query(Empresa).filter(
            Empresa.cnpj.like(cnpj[:8] + '%')).limit(1).first()
        # logger.info(str(session.query(Empresa).filter(
        #    Empresa.cnpj.like(cnpj[:8] + '%'))))
        # logger.info(cnpj[:8])
        # logger.info(empresa.nome)
    return empresa


def get_empresas(session, cnpj: str) -> List[Empresa]:
    """Retorna lista de empresas com o CNPJ parcial.
     Se passado CNPJ completo, corta em 8 dígitos (raiz)
    """
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos.')
    return session.query(Empresa).filter(
        Empresa.cnpj.like(cnpj[:8] + '%')).all()


def get_empresas_nome(session, nome: str, limit=10) -> List[Empresa]:
    if not nome or len(nome) < 3:
        raise ValueError('Nome deve ser informado, com mínimo de 3 dígitos.')
    empresas = session.query(Empresa).filter(
        Empresa.nome.like(nome + '%')).limit(limit).all()
    return [empresa for empresa in empresas]


def get_ncm(session, codigo: str) -> NCM:
    """Retorna NCM com o código passado
    """
    if not codigo or len(codigo) < 9:
        raise ValueError('Código deve ser informado no formato 9999.99.99')
    return session.query(NCM).filter(
        NCM.title == codigo).one_or_none()


def get_sats_cnpj(session, cnpj: str) -> List[SAT]:
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos.')
    return session.query(SAT).filter(
        SAT.importador.like(cnpj[:8] + '%')).all()
