import os
import sys
import plotly.graph_objects as go
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

pd.options.display.float_format = 'R$ {:,.2f}'.format

caminho_commons = os.path.join('..', '..', 'ajna_docs', 'commons')
caminho_virasana = os.path.join('..', '..', 'ajna_docs', 'virasana')
sys.path.append(caminho_commons)
sys.path.append('..')
sys.path.append(caminho_virasana)

from bhadrasana.models import engine

SQL_TGs = \
'''
SELECT year(tg.create_date) as Ano, ovr_id as Ficha,
tg.id as TG, tg.valor as ValorTG
  FROM ovr_ovrs ovr
 inner join ovr_tgovr tg on ovr.id = tg.ovr_id
 where ovr.setor_id in (1, 2);'''
SQL_TGs_SUM = \
'''
SELECT year(tg.create_date) as Ano, month(tg.create_date) as Mês, 
count(tg.id) as Qtde, sum(tg.valor) as ValorTG
  FROM ovr_ovrs ovr
 inner join ovr_tgovr tg on ovr.id = tg.ovr_id
 where ovr.setor_id in (1, 2)
 group by year(tg.create_date), month(tg.create_date);'''

SQL_TGs_NCM = \
'''
SELECT year(tg.create_date) as Ano,  substring(i.ncm, 1, 4) as NCM,
count(i.id) as Qtde, sum(i.valor * i.qtde) as Valor
  FROM ovr_ovrs ovr
 inner join ovr_tgovr tg on ovr.id = tg.ovr_id
 inner join ovr_itenstg i on i.tg_id = tg.id
 where ovr.setor_id in (1, 2) and i.ncm is not null
 group by year(tg.create_date), substring(i.ncm, 1, 4)
 order by Ano, Valor desc;'''

df_detalhe = pd.read_sql(SQL_TGs, engine)
df_sum = pd.read_sql(SQL_TGs_SUM, engine)
df_ano_sum = df_sum.groupby(df_sum.Ano).sum()

df_ncm = pd.read_sql(SQL_TGs_NCM, engine)


def FigTotalPorAno():
    fig = px.bar(df_ano_sum, y='ValorTG', text='Qtde')
    fig.show()
    fig = px.bar(df_detalhe, x='Ano', y='ValorTG', text='Ficha', barmode='group', text_auto=True)
    fig.show()
    
def FigTotalPorAnoMes():
    data = []
    for ano in df_sum.Ano.unique():
        df_filtered = df_sum[df_sum.Ano==ano]
        x = list(df_filtered['Mês'].values)
        y = list(df_filtered.ValorTG.values)
        bar = go.Bar(name=str(ano), x=x, y=y)
        data.append(bar)
    fig = go.Figure(data=data)
    fig.show()
    print(df_sum.pivot(index='Ano', columns='Mês', values='ValorTG').fillna(0.))
    
def FigNCMPorAno():
    lista = []
    for ano in df_ncm.Ano.unique():
        lista.append(df_ncm[df_ncm.Ano == ano].head(10))
    df_ncm_10_mais = pd.concat(lista)
    fig = px.bar(df_ncm_10_mais, x="Ano", y="Valor", color="NCM", text_auto=True)
    fig.show()
    print(df_ncm_10_mais.pivot(index='NCM', columns='Ano', values='Valor').fillna(0.))

