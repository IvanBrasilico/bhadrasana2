import os
import sys
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

WIDTH = 1100
pd.options.display.float_format = 'R$ {:,.2f}'.format

caminho_commons = os.path.join('../..', '..', 'ajna_docs', 'commons')
caminho_virasana = os.path.join('../..', '..', 'ajna_docs', 'virasana')
sys.path.append(caminho_commons)
sys.path.append('../..')
sys.path.append(caminho_virasana)

from bhadrasana.models import engine


def AnoMes(row):
    return str(row.Ano) + str(row['Mês']).zfill(2)


################ TGs

SQL_TGs = \
    '''SELECT year(tg.create_date) as Ano, ovr_id as Ficha,
    tg.id as TG, tg.valor as ValorTG
      FROM ovr_ovrs ovr
     inner join ovr_tgovr tg on ovr.id = tg.ovr_id
     where ovr.setor_id in (1, 2);'''
SQL_TGs_SUM = \
    '''SELECT year(tg.create_date) as Ano, month(tg.create_date) as Mês, 
    count(tg.id) as Qtde, sum(tg.valor) as ValorTG
      FROM ovr_ovrs ovr
     inner join ovr_tgovr tg on ovr.id = tg.ovr_id
     where ovr.setor_id in (1, 2)
     group by year(tg.create_date), month(tg.create_date);'''

SQL_TGs_NCM = \
    '''SELECT year(tg.create_date) as Ano,  substring(i.ncm, 1, 4) as NCM,
    count(i.id) as Qtde, sum(i.valor * i.qtde) as Valor
      FROM ovr_ovrs ovr
     inner join ovr_tgovr tg on ovr.id = tg.ovr_id
     inner join ovr_itenstg i on i.tg_id = tg.id
     where ovr.setor_id in (1, 2) and i.ncm is not null
     group by year(tg.create_date), substring(i.ncm, 1, 4)
     order by Ano, Valor desc;'''

df_detalhe = pd.read_sql(SQL_TGs, engine)

df_sum = pd.read_sql(SQL_TGs_SUM, engine)
df_ano_sum = df_sum.groupby(['Ano']).agg(qtde=pd.NamedAgg(column='Qtde', aggfunc='sum'),
                                         valor=pd.NamedAgg(column='ValorTG', aggfunc='sum')).reset_index()

df_ncm = pd.read_sql(SQL_TGs_NCM, engine)


def FigTotalTGPorAno():
    fig = px.bar(df_ano_sum, x='Ano', y='valor', text='qtde',
                 title='Soma do valor de TG')
    fig.update_layout(width=WIDTH)
    fig.show()
    fig = px.bar(df_detalhe, x='Ano', y='ValorTG', text='Ficha', barmode='group', text_auto=True,
                 title='Valores de TG empilhados')
    fig.update_layout(width=WIDTH)
    fig.show()


def FigTotalTGPorAnoMes():
    data = []
    for ano in df_sum.Ano.unique():
        df_filtered = df_sum[df_sum.Ano == ano]
        x = list(df_filtered['Mês'].values)
        y = list(df_filtered.ValorTG.values)
        bar = go.Bar(name=str(ano), x=x, y=y)
        data.append(bar)
    fig = go.Figure(data=data)
    fig.update_layout(title='Valor Total de TG por ano e mês')
    fig.update_layout(width=WIDTH)
    fig.show()
    print(df_sum.pivot(index='Ano', columns='Mês', values='ValorTG').fillna(0.))


def FigNCMPorAno():
    lista = []
    for ano in df_ncm.Ano.unique():
        lista.append(df_ncm[df_ncm.Ano == ano].head(10))
    df_ncm_10_mais = pd.concat(lista)
    fig = px.bar(df_ncm_10_mais, x="Ano", y="Valor", color="NCM", text_auto=True,
                 title="Soma valor perdimento por posição NCM do Item TG - 10 maiores por ano")
    fig.update_layout(width=WIDTH)
    fig.show()
    print(df_ncm_10_mais.pivot(index='NCM', columns='Ano', values='Valor').fillna(0.))


#### Fichas

SQL_Fichas_Tempos = \
    '''SELECT year(ficha.create_date) as Ano, month(ficha.create_date) as Mês, e.fase as Estágio,
     ficha.id as Ficha, ficha.create_date as create_date, 
     min(ev.create_date) as data_evento_inicial, max(ev.create_date) as data_evento_ultimo
      FROM ovr_ovrs ficha
     inner join ovr_eventos ev on ev.ovr_id = ficha.id
     inner join Enumerado e on e.id = ficha.fase
     where ficha.setor_id in (1, 2)
     group by Ano, Mês, Ficha
     order by Ano, Mês;'''

df_fichas_tempos = pd.read_sql(SQL_Fichas_Tempos, engine)
df_fichas_tempos['Duracao'] = df_fichas_tempos.apply(lambda x: (x.data_evento_ultimo - x.create_date).days, axis=1)
df_fichas_tempos['AnoMes'] = df_fichas_tempos.apply(AnoMes, axis=1)


def FigFichasTempoTotal(df_=df_fichas_tempos):
    df_fichas_estagio = df_.groupby(['AnoMes', 'Estágio']).Ficha.count().reset_index()
    print(f'{df_fichas_estagio.Ficha.sum()} Fichas de controle no total, com os seguintes status:')
    fig = px.pie(df_fichas_estagio, names='Estágio', values='Ficha',
                 title='Quantidade de Fichas por Estágio atual')
    fig.update_traces(textposition='inside', textinfo='percent+label+value')
    fig.update_layout(width=WIDTH)
    fig.show()


def FigFichasEstagio(df_=df_fichas_tempos):
    df_fichas_estagio = df_.groupby(['AnoMes', 'Estágio']).Ficha.count().reset_index()
    fig = px.bar(df_fichas_estagio,
                 x='AnoMes', y='Ficha', color='Estágio',
                 title='Quantidade de Fichas por Estágio atual iniciadas no mês')
    fig.update_xaxes(categoryorder='category ascending')
    fig.update_layout(width=WIDTH)
    fig.show()


def FigFichasTemposMedia(df_=df_fichas_tempos):
    df_fichas_tempos_media = df_.groupby(['AnoMes', 'Estágio']).Duracao.mean().reset_index()
    fig = px.line(df_fichas_tempos_media[df_fichas_tempos_media['Estágio'].isin(['Concluída', 'Arquivada'])],
                  x='AnoMes', y='Duracao', color='Estágio',
                  title='Tempo médio de Fichas iniciadas no mês, até a conclusão ou arquivamento')
    fig.update_xaxes(categoryorder='category ascending')
    fig.update_layout(width=WIDTH)
    fig.show()


###### Outlet

SQL_TGs_OUTLET = \
    '''SELECT year(tg.create_date) as Ano, month(tg.create_date) as Mês, ovr.id as Ficha,
      tg.id as TG, tg.valor as ValorTG
      FROM ovr_ovrs ovr
     inner join ovr_tgovr tg on ovr.id = tg.ovr_id
     inner join ovr_flags_ovr flags on flags.rvf_id = ovr.id
     where flags.flag_id = 9 and tg.valor > 2000
     order by Ano, Mês;'''

SQL_Fichas_Outlet_Tempos = \
    '''SELECT year(ficha.create_date) as Ano, month(ficha.create_date) as Mês, e.fase as Estágio,
     ficha.id as Ficha, ficha.create_date as create_date, 
     min(ev.create_date) as data_evento_inicial, max(ev.create_date) as data_evento_ultimo
      FROM ovr_ovrs ficha
     inner join ovr_eventos ev on ev.ovr_id = ficha.id
     inner join ovr_flags_ovr flags on flags.rvf_id = ficha.id
     inner join Enumerado e on e.id = ficha.fase
     where flags.flag_id = 9
     group by Ano, Mês, Ficha
     order by Ano, Mês;'''

df_tgs_outlet = pd.read_sql(SQL_TGs_OUTLET, engine)
df_tgs_outlet['AnoMes'] = df_tgs_outlet.apply(AnoMes, axis=1)
df_tgs_outlet_sum = df_tgs_outlet.groupby(['AnoMes']).agg(qtde=pd.NamedAgg(column='TG', aggfunc='count'),
                                                          valor=pd.NamedAgg(column='ValorTG',
                                                                            aggfunc='sum')).reset_index()
df_fichas_outlet_tempos = pd.read_sql(SQL_Fichas_Outlet_Tempos, engine)
df_fichas_outlet_tempos['Duracao'] = df_fichas_outlet_tempos.apply(
    lambda x: (x.data_evento_ultimo - x.create_date).days, axis=1)
df_fichas_outlet_tempos['AnoMes'] = df_fichas_outlet_tempos.apply(AnoMes, axis=1)


def FigTotalTGOutlet():
    fig = px.bar(df_tgs_outlet_sum, x='AnoMes', y='valor', text='qtde',
                 title='Soma do valor de TG')
    fig.update_layout(width=WIDTH)
    fig.show()
    fig = px.bar(df_tgs_outlet, x='AnoMes', y='ValorTG', text='Ficha', barmode='group', text_auto=True,
                 title='Valores de TG empilhados')
    fig.update_layout(width=WIDTH)
    fig.show()


SQL_PENDENTE_OUTLET = \
    '''SELECT r.nome as Recinto, ficha.id as 'Ficha', rvf.id as 'RVF', rvf.datahora 'Data de Abertura',
     ficha.numeroCEmercante, rvf.numerolote as Contêiner
     FROM ovr_ovrs ficha
     INNER JOIN ovr_verificacoesfisicas rvf ON  rvf.ovr_id = ficha.id
     inner join ovr_flags_ovr flags on flags.rvf_id = ficha.id
     INNER JOIN ovr_recintos r ON r.id = ficha.recinto_id
     where flags.flag_id = 9 AND ficha.fase <3
     ORDER BY r.nome, rvf.datahora'''

df_pendente_outlet = pd.read_sql(SQL_PENDENTE_OUTLET, engine)
today_ = datetime.today()
df_pendente_outlet['Dias sem conclusão'] = \
    df_pendente_outlet.apply(lambda x: (today_ - x['Data de Abertura']).days, axis=1)
lista_ovr = ', '.join([str(i) for i in df_pendente_outlet.Ficha.values])

SQL_EVENTOS = \
    '''SELECT ovr_id as Ficha, tipoevento_id, t.nome, e.create_date, motivo FROM ovr_eventos e
    inner join ovr_tiposevento t on e.tipoevento_id = t.id  where ovr_id in (%s)
    ORDER BY ovr_id;'''

df_eventos = pd.read_sql(SQL_EVENTOS % lista_ovr, engine)

SQL_PROCESSOS = \
    '''SELECT ovr_id, numero, tipoprocesso_id, tipoProcesso, create_date FROM ovr_processos p
    inner join Enumerado e on e.id = p.tipoprocesso_id where ovr_id in (%s)
    ORDER BY ovr_id;'''

df_processos = pd.read_sql(SQL_PROCESSOS % lista_ovr, engine)

# Tipos de Evento : 36 Em análise da Fiscalização
#                    7 Aguardando quantificação do Recinto
#                   21 Termo de Guarda informado
#                   8 Recebimento de quantificação do Recinto
df_pendente_outlet = df_pendente_outlet.set_index('Ficha')
df_pendente_outlet = df_pendente_outlet.join(
    df_eventos[df_eventos.tipoevento_id == 36].drop_duplicates(
        ('Ficha', 'tipoevento_id'))[['Ficha', 'motivo']].set_index('Ficha')
)
df_pendente_outlet = df_pendente_outlet.rename(columns={'motivo': 'Parecer'}).fillna('--')
tipos_eventos = {36: 'Análise',
                 7: 'TG solicitado',
                 21: 'TG recebido'}
for tipoevento_id, descricao in tipos_eventos.items():
    df_pendente_outlet = df_pendente_outlet.join(
        df_eventos[df_eventos.tipoevento_id == tipoevento_id].drop_duplicates(
            ('Ficha', 'tipoevento_id'))[['Ficha', 'create_date']].set_index('Ficha')
    )
    df_pendente_outlet = df_pendente_outlet.rename(columns={'create_date': descricao}).fillna('Sem evento')
