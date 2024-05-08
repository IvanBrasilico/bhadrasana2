import sys

import pandas as pd
from sqlalchemy import BigInteger, Column, String, Integer

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from bhadrasana.models import Base

metadata = Base.metadata

RiscoEmpresa = {
    '1) ALTO RISCO': 1,
    '2) RISCO INTERMEDIARIO': 2,
    '3) SEM HISTORICO': 3,
    '4) BAIXO RISCO': 4
}

DescricaoRiscoEmpresa = dict([(v, k) for k, v in RiscoEmpresa.items()])


class MatrizCorad(Base):
    __tablename__ = 'matriz_risco_corad'
    id = Column(BigInteger(), primary_key=True)
    cod_emp_interv_rad = Column(String(8), unique=True)
    nome_emp_interv_rad = Column(String(200), index=True)
    classificacao_aniita_imp = Column(Integer(), index=True)
    classificacao_aniita_exp = Column(Integer(), index=True)
    '''situacao_cadastral
    submodal_habilit
    ua_local_jur_aduan_itv_rad
    rf_jur_aduan_itv_rad
    data_atualizacao'''

    def converte_linha(self, linha):
        self.cod_emp_interv_rad = linha[1]
        self.nome_emp_interv_rad = linha[2]
        self.classificacao_aniita_imp = RiscoEmpresa[linha[3]]
        self.classificacao_aniita_exp = RiscoEmpresa[linha[4]]


if __name__ == '__main__':  # pragma: no-cover
    confirma = input('Revisar o código... Esta ação pode apagar TODAS as tabelas. Confirma??')
    if confirma == 'S':
        from ajna_commons.flask.conf import SQL_URI
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(SQL_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        # metadata.drop_all(engine, [metadata.tables['matriz_risco_corad'], ])
        metadata.create_all(engine, [metadata.tables['matriz_risco_corad'], ])

        df_corad = pd.read_csv('C:/Users/25052288840/Downloads/matriz_risco_corad.csv')
        print(df_corad.head())
        print(len(df_corad))
        df_corad = df_corad.dropna()
        print(len(df_corad))
        for row in df_corad.iterrows():
            instancia = MatrizCorad()
            instancia.converte_linha(row[1])
            session.add(instancia)
            '''
            print(instancia.nome_emp_interv_rad)
            print(instancia.classificacao_aniita_imp)
            print(instancia.classificacao_aniita_exp)
            break
            '''
        session.commit()
