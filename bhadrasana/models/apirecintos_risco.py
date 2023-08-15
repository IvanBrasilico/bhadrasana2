import json
import sys
from typing import Type, Tuple, Union

import numpy as np
import pandas as pd
from dateutil import parser
from sqlalchemy import BigInteger, Column, DateTime, Boolean, String, UniqueConstraint, exists, Numeric

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from ajna_commons.flask.log import logger
from bhadrasana.models import Base, BaseRastreavel, BaseDumpable

metadata = Base.metadata


class Motorista(Base):
    __tablename__ = 'risco_motoristas'
    id = Column(BigInteger(), primary_key=True)
    cpf = Column(String(11), unique=True)
    cnh = Column(String(15), unique=True)
    nome = Column(String(50), index=True)
    nome_da_mae = Column(String(50), index=True)
    classificacao = Column(String(1), index=True)  # 1 - Atenção; 2 - Cuidado; 3 - Bandido
    carga = Column(String(100))
    descricao_transportadora = Column(String(100))
    observacoes = Column(String(200))


if __name__ == '__main__':  # pragma: no-cover
    confirma = input('Revisar o código... Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        from ajna_commons.flask.conf import SQL_URI
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        # Sair por segurança. Comentar linha abaixo para funcionar
        # sys.exit(0)
        metadata.drop_all(engine, [metadata.tables['risco_motoristas'],])
        metadata.create_all(engine, [metadata.tables['risco_motoristas'],])
        df_cpfs = pd.read_excel('data/motoristas.xlsx')
        df_ocorrencias = pd.read_excel('data/motoristas.xlsx', sheet_name='2')
        print(df_ocorrencias.head())
        print(len(df_ocorrencias))
        print(df_cpfs.head())
        print(len(df_cpfs))
        df_cpfs = df_cpfs.dropna()
        print(len(df_cpfs))
        df_ocorrencias = df_ocorrencias.dropna()
        df_ocorrencias = df_ocorrencias[df_ocorrencias.classificacao != 'sem registro ']
        print(len(df_ocorrencias))
        df_merge = df_cpfs.merge(df_ocorrencias, on='nome', how='left')
        print(f'len df_merge: {len(df_merge)}')
        df_merge = df_merge.dropna().drop_duplicates()
        print(f'len df_merge: {len(df_merge)}')
        df_merge['carga'] = df_merge.groupby(['nome'])['carga'].transform(lambda x: ' '.join(x))
        df_merge = df_merge.drop_duplicates()
        print(f'len df_merge: {len(df_merge)}')
        df_merge.to_sql('risco_motoristas', engine)

