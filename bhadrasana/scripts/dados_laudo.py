import os
from sqlalchemy import create_engine, func
from sqlalchemy import BigInteger, Column, VARCHAR, Integer, Date
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from models.laudo import SAT

Base = declarative_base()


# classe utilizada para consultar tabela 'sats' do db LAUDOS
class SATLaudos(Base):
    __tablename__ = 'sats'
    id = Column(BigInteger().with_variant(Integer, 'sqlite'),
                primary_key=True)
    declaracao = Column(VARCHAR(255), index=True)
    descricao = Column(VARCHAR(255))
    importador = Column(VARCHAR(15), index=True)
    numeroSAT = Column(BigInteger().with_variant(Integer, 'sqlite'), index=True)
    dataPedido = Column(Date, index=True)
    unidade = Column(BigInteger().with_variant(Integer, 'sqlite'), index=True)


if __name__ == '__main__':
    SQL_URI_LAUDOS = os.environ.get('SQL_URI_LAUDOS')  # conexao com db LAUDOS
    # SQL_URI_STAGING = os.environ.get('SQL_URI_STAGING')  # conexao com staging
    SQL_URI = os.environ.get('SQL_URI')  # conexao com produção

    # engine_bhad = create_engine(SQL_URI_STAGING)  # staging
    engine_bhad = create_engine(SQL_URI)  # producao
    Session_bhad = sessionmaker(bind=engine_bhad)
    session_bhad = Session_bhad()

    # coleta o último id da tabela SAT do DB em produção que será usado para
    # verificar se há id novo no LAUDOS
    ultimo_id = session_bhad.query(func.max(SAT.id))
    ultimo_id = ultimo_id[0][0]
    print(f'ultimo id: {ultimo_id}')

    # conexão com database Laudos
    engine_laudos = create_engine(SQL_URI_LAUDOS)
    Session_laudos = sessionmaker(bind=engine_laudos)
    session_laudos = Session_laudos()

    # filtra id maiores do que o último id da base em produção
    resultados = session_laudos.query(SATLaudos).filter(SATLaudos.id > ultimo_id)
    len_resultados = 0
    for result in resultados:
        len_resultados += 1
    print(f'foram encontrados {len_resultados} registros a serem adicionados')

    if len_resultados > 0:
        num_result = 0
        for n, row in enumerate(resultados):
            sat = SAT()
            sat.declaracao = row.declaracao
            sat.descricao = row.descricao
            sat.importador = row.importador
            sat.numeroSAT = row.numeroSAT
            sat.dataPedido = row.dataPedido
            sat.unidade = row.unidade
            session_bhad.add(sat)
            num_result = n + 1
        print(f'foram adicionados {num_result} novos registros na tabela SATS')
        session_bhad.commit()
    else:
        print('não há novos registros')