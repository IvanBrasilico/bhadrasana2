import sys
from datetime import datetime
from typing import List

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
        numero = self.numeroSAT
        unidade = get_sigla_unidade(self.unidade)

        return '{}/{:05d}/{}'.format(unidade, numero, ano)


def get_empresa(session, cnpj: str) -> Empresa:
    """Pesquisa empresa por CNPJ.

    Não encontrando, busca pelo CNPJ raiz e retorna primeira.
    Em caso de falha, retorna None.
    """
    if not cnpj:
        return None
    empresa = session.query(Empresa).filter(
        Empresa.cnpj == cnpj).one_or_none()
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
    if not cnpj:
        return []
    return session.query(Empresa).filter(
        Empresa.cnpj.like(cnpj[:8] + '%')).all()


def get_empresas_nome(session, nome: str, limit=10) -> List[Empresa]:
    empresas = session.query(Empresa).filter(
        Empresa.nome.like(nome + '%')).limit(limit).all()
    return [empresa for empresa in empresas]


def get_sats_cnpj(session, cnpj: str) -> List[SAT]:
    return session.query(SAT).filter(
        SAT.importador.like(cnpj[:8] + '%')).all()
