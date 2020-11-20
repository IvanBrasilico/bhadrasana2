import sys

import click
from sqlalchemy import BigInteger, Column, VARCHAR, Integer, Date
from sqlalchemy import create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

sys.path.append('.')
sys.path.append('../ajna_docs/commons')
sys.path.append('../virasana')

from bhadrasana.models.laudo import SAT

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


@click.command()
@click.option('--sql_uri')
@click.option('--laudos_uri')
def update(sql_uri, laudos_uri):
    print(sql_uri, laudos_uri)
    engine_bhad = create_engine(sql_uri)
    Session_bhad = sessionmaker(bind=engine_bhad)
    session_bhad = Session_bhad()

    # coleta o último id da tabela SAT do DB em produção que será usado para
    # verificar se há id novo no LAUDOS
    ultimo_id = session_bhad.query(func.max(SAT.id))
    ultimo_id = ultimo_id[0][0]
    print(f'ultimo id: {ultimo_id}')

    # conexão com database Laudos
    print(laudos_uri)
    engine_laudos = create_engine(laudos_uri)
    Session_laudos = sessionmaker(bind=engine_laudos)
    session_laudos = Session_laudos()

    # filtra id maiores do que o último id da base em produção
    resultados = session_laudos.query(SATLaudos).filter(SATLaudos.id > ultimo_id).all()
    print(len(resultados))
    if len(resultados) > 0:
        for n, row in enumerate(resultados):
            sat = SAT()
            sat.declaracao = row.declaracao
            sat.descricao = row.descricao
            sat.importador = row.importador
            sat.numeroSAT = row.numeroSAT
            sat.dataPedido = row.dataPedido
            sat.unidade = row.unidade
            session_bhad.add(sat)
        print(f'foram adicionados {n + 1} novos registros na tabela SATS')
        session_bhad.commit()
    else:
        print('não há novos registros')


if __name__ == '__main__':
    print('Para rodar automático, crie arquivo com a linha abaixo '
          'em /etc/cron.daily/laudos_update.sh')
    print('/home/ivan/ajna/bhadrasana2/bhadrasana-venv/bin/'
          'python bhadrasana/scripts/dados_laudo.py '
          ' --sql_uri mysql+pymysql://<uri do banco SQL do Fichas> '
          ' --laudos_uri mysql+pymysql://<uri do banco SQL do Laudos> '
          ' >> /var/log/bhadrasana2/laudos_error.log 2>&1')
    update()
