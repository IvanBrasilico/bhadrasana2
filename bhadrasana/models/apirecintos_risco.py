import sys

import pandas as pd
from sqlalchemy import BigInteger, Column, String, Integer

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from bhadrasana.models import Base

metadata = Base.metadata

RiscoMotorista = {
    'ATENÇÃO': '1',
    'CUIDADO': '2',
    'BANDIDO': '3'
}

DescricaoRiscoMotorista = dict([(v, k) for k, v in RiscoMotorista.items()])


class Motorista(Base):
    __tablename__ = 'risco_motoristas'
    id = Column(BigInteger(), primary_key=True)
    cpf = Column(String(11), unique=True)
    cnh = Column(String(15), unique=True)
    nome = Column(String(50), index=True)
    nome_da_mae = Column(String(50), index=True)
    classificacao = Column(String(1), index=True)  # 1 - Atenção; 2 - Cuidado; 3 - Bandido
    carga = Column(String(100))
    carga_qtde = Column(Integer())
    descricao_transportadora = Column(String(100))
    observacoes = Column(String(200))
    def get_risco(self):
        return f'{DescricaoRiscoMotorista[self.classificacao]} - {self.carga} - {self.carga_qtde} ocorrências'


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
        metadata.drop_all(engine, [metadata.tables['risco_motoristas'], ])
        metadata.create_all(engine, [metadata.tables['risco_motoristas'], ])
        df_cpfs = pd.read_excel('notebooks/data/motoristas.xlsx')
        print('CPFs:')
        print(df_cpfs.head())
        print(len(df_cpfs))
        df_cpfs = df_cpfs.dropna()
        print(len(df_cpfs))
        df_ocorrencias = pd.read_excel('notebooks/data/motoristas.xlsx', sheet_name='2')
        print(df_ocorrencias.head())
        print(f'Ocorrências: {len(df_ocorrencias)}')
        df_ocorrencias = df_ocorrencias.dropna()
        df_ocorrencias = df_ocorrencias[df_ocorrencias.classificacao != 'sem registro ']
        print(f'Ocorrências: {len(df_ocorrencias)}')
        df_merge = df_cpfs.merge(df_ocorrencias, on='nome', how='left')
        df_merge = df_merge.merge(df_merge.groupby(['nome'])['carga'].count().reset_index(), on='nome',
                                  suffixes=['', '_qtde'])
        print(df_merge.head())
        print(f'len df_merge: {len(df_merge)}')
        df_merge = df_merge.dropna().drop_duplicates()
        print(f'len df_merge: {len(df_merge)}')
        df_merge['carga'] = df_merge.groupby(['nome'])['carga'].transform(lambda x: ', '.join(x))
        df_merge = df_merge.drop_duplicates()
        df_merge['cpf'] = df_merge['cpf'].apply(lambda x: ''.join([c for c in x if c.isnumeric()]))
        df_merge['classificacao'] = df_merge['classificacao'].apply(lambda x: RiscoMotorista[x.strip()])
        print(df_merge.head())
        print(f'len final df_merge: {len(df_merge)}')
        df_merge.to_sql('risco_motoristas', engine, if_exists='append', index=False)
