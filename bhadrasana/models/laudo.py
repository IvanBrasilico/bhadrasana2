import sys
from datetime import datetime
from typing import List

from sqlalchemy import BigInteger, CHAR, Column, VARCHAR, Integer, Date, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from virasana.integracao.bagagens.viajantesalchemy import Pessoa

from bhadrasana.models import BaseDumpable

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

Base = declarative_base()
metadata = Base.metadata


class Empresa(Base, BaseDumpable):
    """Só leitura: o cadastro de CNPJ da navi_cnpj (carga do ContÁgil pelo NAVI-Dados, E15).

    Até 11/2026 era a laudo_empresas, que ficou no banco como histórico. A navi_cnpj tem uma linha
    por estabelecimento (CNPJ de 14 dígitos) e nenhum CPF; a tabela é do NAVI-Dados, e só o pedaço
    usado aqui está mapeado. Plano: navi-dados/PLANO_EMPRESA_NAVI_CNPJ.md.
    """

    __tablename__ = 'navi_cnpj'
    cnpj = Column(CHAR(14), primary_key=True)
    nome = Column('nome_empresarial_pj', VARCHAR(255))


@event.listens_for(Session, 'before_flush')
def _empresa_so_leitura(session, contexto, instancias):
    """Recusa gravar Empresa pelo ORM: o cadastro de CNPJ entra só pelo NAVI-Dados."""
    for objeto in (*session.new, *session.dirty, *session.deleted):
        if isinstance(objeto, Empresa):
            raise RuntimeError('Empresa é só leitura (navi_cnpj): o cadastro de CNPJ '
                               'entra pelo NAVI-Dados (E15)')


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

    Não encontrando, busca pelo CNPJ raiz e retorna o primeiro na ordem do CNPJ
    (a matriz, 0001, quando está no cadastro).
    CPF (11 dígitos) retorna None: a navi_cnpj só tem CNPJ, e a raiz do CPF acharia
    uma empresa errada.
    Em caso de falha, retorna None.
    Retorna exceção se parâmetro menor que 8 dígitos
    """
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos.')
    if len(cnpj) == 11:
        return None
    empresa = session.query(Empresa).filter(
        Empresa.cnpj == cnpj).first()
    if not empresa:
        empresa = session.query(Empresa).filter(
            Empresa.cnpj.like(cnpj[:8] + '%')).order_by(Empresa.cnpj).first()
    return empresa


def get_empresas(session, cnpj: str, limit=None) -> List[Empresa]:
    """Retorna os estabelecimentos da raiz do CNPJ, na ordem do CNPJ (a matriz primeiro).

    Se passado CNPJ completo, corta em 8 dígitos (raiz).
    """
    if not cnpj or len(cnpj) < 8:
        raise ValueError('CNPJ deve ser informado com mínimo de 8 dígitos.')
    consulta = session.query(Empresa).filter(
        Empresa.cnpj.like(cnpj[:8] + '%')).order_by(Empresa.cnpj)
    if limit:
        consulta = consulta.limit(limit)
    return consulta.all()


def get_empresas_nome(session, nome: str, limit=10) -> List[Empresa]:
    """Uma empresa por raiz de CNPJ, na ordem do nome.

    Cada raiz vem com o primeiro CNPJ dela na ordem (em geral a matriz). A consulta lê
    até limit * 20 linhas: uma empresa com mais filiais que isso dentro do filtro ocupa a
    janela, e a lista vem menor (refinar o nome). O índice em nome_empresarial_pj atende
    o filtro e a ordem.
    """
    if not nome or len(nome) < 3:
        raise ValueError('Nome deve ser informado, com mínimo de 3 dígitos.')
    por_raiz = {}
    consulta = session.query(Empresa).filter(
        Empresa.nome.like(nome + '%')).order_by(Empresa.nome, Empresa.cnpj).limit(limit * 20)
    for empresa in consulta:
        por_raiz.setdefault(empresa.cnpj[:8], empresa)
        if len(por_raiz) == limit:
            break
    return list(por_raiz.values())

def get_pessoas_nome(session, nome: str, limit=10) -> List[Empresa]:
    if not nome or len(nome) < 3:
        raise ValueError('Nome deve ser informado, com mínimo de 3 dígitos.')
    pessoas = session.query(Pessoa).filter(
        Pessoa.nome.like('%' + nome + '%')).limit(limit).all()
    return [pessoa for pessoa in pessoas]


def get_pessoa(session, cpf: str) -> Pessoa:
    """Pesquisa Pessoa por CPF.

    Em caso de falha, retorna None.
    """
    return session.query(Pessoa).filter(Pessoa.cpf == cpf).one_or_none()

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
