from datetime import timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
from ajna_commons.flask.log import logger

from bhadrasana.models.ovr import OKRResultMeta


def bar_plotly(linhas: list, nome: str) -> str:
    """Renderiza gráfico no plotly e serializa via HTTP/HTML."""
    meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
             5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
             9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    try:
        # Converter decimal para float
        linhas_float = []
        for linha in linhas[1:]:
            linha_float = []
            for item in linha:
                if isinstance(item, Decimal):
                    linha_float.append(float(item))
                else:
                    linha_float.append(item)
            linhas_float.append(linha_float)
        df = pd.DataFrame(linhas_float, columns=linhas[0])
        df['strmes'] = df['Mês'].apply(lambda x: meses[int(x)])
        df['Ano e Mês'] = df['Ano'].astype(str) + '-' + df['Mês'].astype(str).str.zfill(2) \
                          + '-' + df['strmes'].astype(str) + ' de ' + df['Ano'].astype(str)
        df = df.drop(columns=['Ano', 'Mês', 'strmes'])
        print(df.head())
        df = df.groupby(['Ano e Mês']).sum()  # Apenas para dar a ordem correta
        df = df.reset_index()
        # print(linhas)
        print(df.head())
        # print(df.dtypes)
        x = df['Ano e Mês'].tolist()
        df = df.drop(columns=['Ano e Mês'])
        numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
        data = [go.Bar(x=x, y=df[column].tolist(), name=column)
                for column in numeric_columns]
        plot = plotly.offline.plot({
            'data': data,
            'layout': go.Layout(title=nome + ' soma mensal',
                                xaxis=go.layout.XAxis(type='category'))
        },
            show_link=False,
            output_type='div',
            image_width=400)
        return plot
    except Exception as err:
        logger.error(str(err), exc_info=True)
        return ''


def gauge_plotly(resultado: str, meta: int, medicao: int, delta: int = None,
                 font_size=50) -> str:
    """Desenha um gauge indicator com plotly.

    medicao: nivel do gauge
    meta: nível máximo do gauge
    delta: percentual de tempo do periodo decorrido, para referencia
    """
    if not delta:
        delta = meta
    return go.Indicator(
        mode='gauge+number',
        domain={'x': [0, 1], 'y': [0, 1]},
        value=medicao,
        # color=lcolor,
        gauge={'axis': {'range': [0, meta]},
               'threshold': {
                   'line': {'color': 'red', 'width': 4},
                   'thickness': 0.75,
                   'value': delta}
               },
        title={'text': resultado},
        number={"font": {"size": font_size}}
    )

def gauge_plotly_plot(resultado: str, meta: int, medicao: int, delta: int = None) -> str:
    """Desenha um gauge indicator com plotly.

    resultado: nome do gráfico
    medicao: nivel do gauge
    meta: nível máximo do gauge
    delta: percentual de tempo do periodo decorrido, para referencia
    """
    data = [gauge_plotly(resultado, meta, medicao, delta, 40)]
    plot = plotly.offline.plot({
        'data': data,
    },
        show_link=False,
        output_type='div')
    return plot


def burndown_plotly(resultado: OKRResultMeta) -> str:
    data_inicial = resultado.objective.inicio.date()
    data_final = resultado.objective.fim.date()
    periodo = data_final - data_inicial
    df_medicoes = pd.DataFrame([row for row in resultado.resultados],
                               columns=['data', 'result'])
    df_medicoes['result'] = df_medicoes.result.astype(float)
    df_burndown = pd.DataFrame([(data_inicial + timedelta(days=r), 0.)
                                for r in range(-1, periodo.days)],
                               columns=['data', 'result'])
    df_burndown = pd.merge(df_burndown, df_medicoes, on='data', how='left').fillna(0.)
    df_burndown['result'] = df_burndown['result_x'] + df_burndown['result_y']
    meta = resultado.ameta
    df_burndown['cumulativo'] = df_burndown.result.cumsum().apply(lambda x: meta - x)
    incremento = float(meta) / float(periodo.days)
    df_burndown['esperado'] = [(meta - r * incremento) for r in range(len(df_burndown))]
    # print(df_burndown.head())
    fig = go.Figure(data=[
        go.Bar(x=df_burndown.index, y=df_burndown.result, name='Diário'),
        go.Scatter(x=df_burndown.index, y=df_burndown.cumulativo,
                   name='Evolução',
                   line=dict(color='green')),
        go.Scatter(x=df_burndown.index, y=df_burndown.esperado,
                   name='Alvo',
                   line=dict(color='firebrick', width=4, dash='dot'))
    ])
    fig.update_layout(title='"Burndown" - %s' % resultado.result.nome,
                      xaxis_title='Dia do período',
                      yaxis_title='Medição')
    plot = plotly.offline.plot({
        'data': fig,
    },
        show_link=False,
        output_type='div',
        image_width=300
    )
    return plot
