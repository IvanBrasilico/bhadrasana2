import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from gerencial import engine, AnoMes

pd.options.display.float_format = '{:,.2f}'.format

SQL_Fichas_Tempos_Exp = \
    '''SELECT year(ficha.create_date) as Ano, month(ficha.create_date) as Mês, e.fase as Estágio,
     ficha.id as Ficha, ficha.create_date as create_date, 
     min(ev.create_date) as data_evento_inicial, max(ev.create_date) as data_evento_ultimo
      FROM ovr_ovrs ficha
     inner join ovr_eventos ev on ev.ovr_id = ficha.id
     inner join Enumerado e on e.id = ficha.fase
     where ficha.setor_id = 3
     group by Ano, Mês, Ficha
     order by Ano, Mês;'''

df_fichas_tempos = pd.read_sql(SQL_Fichas_Tempos_Exp, engine)
df_fichas_tempos['Duracao'] = df_fichas_tempos.apply(lambda x: (x.data_evento_ultimo - x.create_date).days, axis=1)
df_fichas_tempos['AnoMes'] = df_fichas_tempos.apply(AnoMes, axis=1)

SQL_APREENSOES = \
    '''
    SELECT year(ovr.datahora) as Ano, month(ovr.datahora) as Mês,
      ovr.id as Ficha, rvf.id as RVF, rvf.descricao as relato,
      a.id as Apreensao, a.descricao, t.descricao, a.peso as Peso
      FROM ovr_ovrs ovr
     inner join ovr_verificacoesfisicas rvf on rvf.ovr_id = ovr.id
     inner join ovr_apreensoes_rvf a on a.rvf_id = rvf.id
     inner join ovr_tiposapreensao t on t.id = a.tipo_id
     where ovr.setor_id in (1, 2, 3)
     order by Ano, Mês, Ficha, RVF, Apreensao;'''


def FigFichasTempoTotal(df_=df_fichas_tempos):
    df_fichas_estagio = df_.groupby(['AnoMes', 'Estágio']).Ficha.count().reset_index()
    print(f'{df_fichas_estagio.Ficha.sum()} Fichas de controle no total, com os seguintes status:')
    fig = px.pie(df_fichas_estagio, names='Estágio', values='Ficha')
    fig.update_traces(textposition='inside', textinfo='percent+label+value')
    fig.show()


def FigFichasEstagio(df_=df_fichas_tempos):
    df_fichas_estagio = df_.groupby(['AnoMes', 'Estágio']).Ficha.count().reset_index()
    fig = px.bar(df_fichas_estagio,
                 x='AnoMes', y='Ficha', color='Estágio')
    fig.update_xaxes(categoryorder='category ascending')
    fig.show()


def FigFichasTemposMedia(df_=df_fichas_tempos):
    df_fichas_tempos_media = df_.groupby(['AnoMes', 'Estágio']).Duracao.mean().reset_index()
    fig = px.line(df_fichas_tempos_media[df_fichas_tempos_media['Estágio'].isin(['Concluída', 'Arquivada'])],
                  x='AnoMes', y='Duracao', color='Estágio')
    fig.update_xaxes(categoryorder='category ascending')
    fig.show()


df_apreensoes = pd.read_sql(SQL_APREENSOES, engine)
df_apreensoes['AnoMes'] = df_apreensoes.apply(AnoMes, axis=1)
df_apreensoes['AnoMes'] = df_apreensoes.apply(AnoMes, axis=1)
df_apreensoes_ano_sum = df_apreensoes.groupby(['Ano']).agg(
    qtde=pd.NamedAgg(column='Apreensao', aggfunc='count'),
    peso=pd.NamedAgg(column='Peso', aggfunc='sum')).reset_index()
df_apreensoes_ano_mes_sum = df_apreensoes.groupby(['AnoMes']).agg(
    qtde=pd.NamedAgg(column='Apreensao', aggfunc='count'),
    peso=pd.NamedAgg(column='Peso', aggfunc='sum')).reset_index()
df_apreensoes_sum = df_apreensoes.groupby(['Ano', 'Mês']).agg(
    qtde=pd.NamedAgg(column='Apreensao', aggfunc='count'),
    peso=pd.NamedAgg(column='Peso', aggfunc='sum')).reset_index()


def FigTotalApreensaoPorAno():
    fig = px.bar(df_apreensoes_ano_sum, x='Ano', y='qtde', text='peso')
    fig.show()
    fig = px.bar(df_apreensoes, x='Ano', y='Peso', text='Ficha', barmode='group', text_auto=True)
    fig.show()


def FigTotalApreensaoPorAnoMes():
    data = []
    for ano in df_apreensoes_sum.Ano.unique():
        df_filtered = df_apreensoes_sum[df_apreensoes_sum.Ano == ano]
        x = list(df_filtered['Mês'].values)
        y = list(df_filtered.peso.values)
        text = list(df_filtered.qtde.values)
        bar = go.Bar(name=str(ano), x=x, y=y, text=text)
        data.append(bar)
    fig = go.Figure(data=data)
    fig.show()
    print(df_apreensoes_sum.pivot(index='Ano', columns='Mês', values='peso').fillna(0.))
    print(df_apreensoes_sum.pivot(index='Ano', columns='Mês', values='qtde').fillna(0.))
