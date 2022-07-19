import locale
import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pymongo import MongoClient

from gerencial import engine, AnoMes, WIDTH

caminho_commons = os.path.join('../..', '..', 'ajna_docs', 'commons')
caminho_virasana = os.path.join('../..', '..', 'ajna_docs', 'virasana')
sys.path.append('../..')
sys.path.append(caminho_commons)
sys.path.append(caminho_virasana)

from ajna_commons.flask.conf import DATABASE, MONGODB_URI

locale.setlocale(locale.LC_ALL, 'pt_BR')

conn = MongoClient(host=MONGODB_URI)
mongodb = conn[DATABASE]

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
    SELECT year(rvf.datahora) as Ano, month(rvf.datahora) as Mês, rvf.datahora,
      r.nome as recinto,
      ovr.id as Ficha, rvf.id as RVF, rvf.descricao as relato, rvf.numerolote as Conteiner,
      a.id as Apreensao, a.descricao, t.descricao, a.peso as Peso
      FROM ovr_ovrs ovr
     inner join ovr_verificacoesfisicas rvf on rvf.ovr_id = ovr.id
     inner join ovr_apreensoes_rvf a on a.rvf_id = rvf.id
     inner join ovr_tiposapreensao t on t.id = a.tipo_id
     inner join ovr_recintos r on r.id = ovr.recinto_id
     where ovr.setor_id in (1, 2, 3)  and ovr.tipooperacao != 6
     order by Ano, Mês, Ficha, RVF, Apreensao;'''


def FigFichasTempoTotal(df_=df_fichas_tempos):
    df_fichas_estagio = df_.groupby(['AnoMes', 'Estágio']).Ficha.count().reset_index()
    print(f'{df_fichas_estagio.Ficha.sum()} Fichas de controle no total, com os seguintes status:')
    fig = px.pie(df_fichas_estagio, names='Estágio', values='Ficha',
                 title='Quantidade de Fichas por Estágio atual')
    fig.update_layout(width=WIDTH)
    fig.update_traces(textposition='inside', textinfo='percent+label+value')
    fig.show()


def FigFichasEstagio(df_=df_fichas_tempos):
    df_fichas_estagio = df_.groupby(['AnoMes', 'Estágio']).Ficha.count().reset_index()
    fig = px.bar(df_fichas_estagio,
                 x='AnoMes', y='Ficha', color='Estágio',
                 title='Quantidade de Fichas por Estágio atual iniciadas no mês')
    fig.update_layout(width=WIDTH)
    fig.update_xaxes(categoryorder='category ascending')
    fig.show()


def FigFichasTemposMedia(df_=df_fichas_tempos):
    df_fichas_tempos_media = df_.groupby(['AnoMes', 'Estágio']).Duracao.mean().reset_index()
    fig = px.line(df_fichas_tempos_media[df_fichas_tempos_media['Estágio'].isin(['Concluída', 'Arquivada'])],
                  x='AnoMes', y='Duracao', color='Estágio',
                  title='Tempo médio de Fichas iniciadas no mês, até a conclusão ou arquivamento')
    fig.update_layout(width=WIDTH)
    fig.update_xaxes(categoryorder='category ascending')
    fig.show()


def TemAlerta(row):
    days_ = 1000
    correto = None
    conteiner = row['Conteiner']
    if not conteiner:
        return False
    cursor = mongodb['fs.files'].find({'metadata.numeroinformado': conteiner,
                                       'metadata.contentType': 'image/jpeg'})
    for line in cursor:
        metadata = line['metadata']
        dataescaneamento = metadata['dataescaneamento']
        days = abs((dataescaneamento - row['datahora']).days)
        if days < days_:
            days_ = days
            correto = metadata
    if correto:
        try:
            return correto['xml']['alerta']
        except:
            return False


df_apreensoes = pd.read_sql(SQL_APREENSOES, engine)
df_apreensoes['AnoMes'] = df_apreensoes.apply(AnoMes, axis=1)
df_apreensoes['Alerta'] = df_apreensoes.apply(TemAlerta, axis=1)
df_apreensoes_ano_sum = df_apreensoes.groupby(['Ano']).agg(
    qtde=pd.NamedAgg(column='Apreensao', aggfunc='count'),
    peso=pd.NamedAgg(column='Peso', aggfunc='sum')).reset_index()
df_apreensoes_ano_mes_sum = df_apreensoes.groupby(['AnoMes']).agg(
    qtde=pd.NamedAgg(column='Apreensao', aggfunc='count'),
    peso=pd.NamedAgg(column='Peso', aggfunc='sum')).reset_index()
df_apreensoes_sum = df_apreensoes.groupby(['Ano', 'Mês']).agg(
    qtde=pd.NamedAgg(column='Apreensao', aggfunc='count'),
    peso=pd.NamedAgg(column='Peso', aggfunc='sum')).reset_index()


def FiltraApreensoes(mindatahora=None, maxdatahora= None):
    df_apreensoes_loc = df_apreensoes.copy()
    if mindatahora is None:
        mindatahora = df_apreensoes[~ df_apreensoes.Conteiner.isna()].datahora.min()
    else:
        df_apreensoes_loc = df_apreensoes_loc[df_apreensoes_loc.datahora > mindatahora]
    if maxdatahora is None:
        maxdatahora = df_apreensoes[~ df_apreensoes.Conteiner.isna()].datahora.max()
    else:
        df_apreensoes_loc = df_apreensoes_loc[df_apreensoes_loc.datahora < maxdatahora]
    return df_apreensoes_loc, mindatahora, maxdatahora


def EstatisticasAlertas(mindatahora=None, maxdatahora= None):
    df_apreensoes_loc, mindatahora, maxdatahora = FiltraApreensoes(mindatahora, maxdatahora)
    total_apreensoes_conteiner = (~ df_apreensoes_loc.Conteiner.isna()).sum()
    total_apreensoes_alerta = df_apreensoes_loc.Alerta.sum()
    total_imagens = mongodb['fs.files'].count_documents({
        'metadata.contentType': 'image/jpeg',
        'metadata.dataescaneamento': {'$gte': mindatahora, '$lt': maxdatahora}}
    )
    total_imagens_alerta = mongodb['fs.files'].count_documents({
        'metadata.contentType': 'image/jpeg',
        'metadata.dataescaneamento': {'$gte': mindatahora, '$lt': maxdatahora},
        'metadata.xml.alerta': True}
    )
    print(f'Estatísticas para alertas entre {mindatahora:%d/%m/%Y} e {maxdatahora:%d/%m/%Y}.\n')
    percent_alerta = int((total_imagens_alerta / total_imagens) * 10_000) / 100
    print(f'Imagens: \t\t{total_imagens:n} \t{total_imagens_alerta:n} com alerta ({percent_alerta:n}%)')
    percent_apreensoes_alerta = int((total_apreensoes_alerta / total_apreensoes_conteiner) * 10_000) / 100
    print(
        f'Apreensões: \t\t{total_apreensoes_conteiner:n} \t\t{total_apreensoes_alerta:n} com alerta ({percent_apreensoes_alerta:n}%)')
    precisao_alerta = int((total_apreensoes_alerta / total_imagens_alerta) * 10_000) / 100
    print(f'Precisão Alertas: \t{total_imagens_alerta:n} / \t{total_apreensoes_alerta:n} ({precisao_alerta:n}%)')
    return df_apreensoes_loc


def AlertasporTerminal(mindatahora=None, maxdatahora= None):
    df_apreensoes_loc, mindatahora, maxdatahora = FiltraApreensoes(mindatahora, maxdatahora)
    cursor = mongodb['fs.files'].aggregate([
        {'$match': {'metadata.contentType': 'image/jpeg',
                    'metadata.dataescaneamento': {'$gte': mindatahora, '$lt': maxdatahora},
                    'metadata.xml.alerta': True}},
        {'$group': {'_id': '$metadata.recinto', 'alertas': {'$sum': 1}}}
    ])
    recintos_alertas = dict()
    for row in cursor:
        recintos_alertas[row['_id']] = {'alertas': row['alertas']}
    cursor = mongodb['fs.files'].aggregate([
        {'$match': {'metadata.contentType': 'image/jpeg',
                    'metadata.dataescaneamento': {'$gte': mindatahora, '$lt': maxdatahora}}},
        {'$group': {'_id': '$metadata.recinto', 'imagens': {'$sum': 1}}}
    ])
    for row in cursor:
        try:
            recintos_alertas[row['_id']].update({'imagens': row['imagens']})
        except:
            recintos_alertas[row['_id']] = {'imagens': row['imagens'], 'alertas': 0}
    df_alertas = pd.DataFrame.from_dict(recintos_alertas, orient='index')
    df_alertas['ratio'] = df_alertas.alertas / df_alertas.imagens
    return df_alertas


def FigTotalApreensaoPorAno():
    df_apreensoes_ano_sum.peso = df_apreensoes_ano_sum.peso.astype(int)
    fig = px.bar(df_apreensoes_ano_sum, x='Ano', y='qtde', text='peso',
                 title='Soma dos pesos de apreensões')
    fig.update_layout(width=WIDTH)
    fig.show()
    fig = px.bar(df_apreensoes, x='Ano', y='Peso', text='Ficha', barmode='group', text_auto=True,
                 title='Pesos de apreensões empilhados')
    fig.update_layout(width=WIDTH)
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
    fig.update_layout(title='Peso de apreensões por ano e mês')
    fig.update_layout(width=WIDTH)
    fig.show()
    print(df_apreensoes_sum.pivot(index='Ano', columns='Mês', values='peso').fillna(0.))
    print(df_apreensoes_sum.pivot(index='Ano', columns='Mês', values='qtde').fillna(0.))


#### Tempos de demora de inspeção

SQL_RVFS = '''
select id, year(datahora) as Ano, month(datahora) as Mês, create_date, datahora
from ovr_verificacoesfisicas 
where datahora is not null and create_date != '0'
'''

df_rvfs_datas = pd.read_sql(SQL_RVFS, engine)
df_rvfs_datas['dias'] = df_rvfs_datas.apply(lambda row: (row['datahora'] - row['create_date']).days + 1, axis=1)
df_rvfs_datas['AnoMes'] = df_rvfs_datas.apply(AnoMes, axis=1)


def FigDemoraInspecao():
    # Abaixo, tempo entre a programação da RVF e a realização de Inspeção não invasiva
    df_rvfs_datas_p = df_rvfs_datas.loc[df_rvfs_datas.dias >= 0]
    dfp = df_rvfs_datas_p.groupby(['AnoMes']).dias.mean().reset_index()
    fig = px.bar(dfp, x='AnoMes', y='dias', title='Média de dias: tempo entre agendamento/não invasiva e verificação')
    fig.show()


def FigDemoraCadastramento():
    # Casos em que há uma demora no cadastramento, isto é, data de cadastramento é maior que a data da verificação
    df_rvfs_datas_n = df_rvfs_datas.loc[df_rvfs_datas.dias < 0]
    # Corrigir aqueles que foram carregados automaticamente (importação da planilha EQCOM)
    limite_inferior = df_rvfs_datas_n['dias'].quantile(0.50)
    df_rvfs_datas_n.loc[df_rvfs_datas_n['dias'] < limite_inferior, 'dias'] = limite_inferior
    dfn = df_rvfs_datas_n.groupby(['AnoMes']).dias.mean().reset_index()
    dfn = df_rvfs_datas_n.groupby(['AnoMes']).agg(
        dias=pd.NamedAgg(column='dias', aggfunc='mean'),
        qtde=pd.NamedAgg(column='dias', aggfunc='count')).reset_index()
    fig = px.bar(dfn, x='AnoMes', y='dias', text='qtde',
                 title='Média de dias: demora entre verificação e registro')
    fig.show()
