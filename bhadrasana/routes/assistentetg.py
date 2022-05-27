import os
from datetime import datetime

import nltk
import numpy as np
import pandas as pd
import unicodedata
from ajna_commons.flask.log import logger
from flask import render_template, request, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from rank_bm25 import BM25Okapi
from werkzeug.utils import redirect
from wtforms import StringField

from bhadrasana.models import engine
from bhadrasana.models.ovr import Enumerado
from bhadrasana.views import get_user_save_path

nltk.download('rslp')
stemmer = nltk.stem.RSLPStemmer()
stop_words = nltk.corpus.stopwords.words('portuguese')


def remove_accents(input_str):
    """
    Função converte string em bytes, mas antes normaliza string usando NFKD

    NFKD - decompõem em dois code point e analisa compatibilidades (sem ser canonicamente equivalente)
    https://docs.python.org/3/library/unicodedata.html
    """
    nfkd_form = unicodedata.normalize('NFKD', input_str.lower())
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii


def remove_pontuacao(doc):
    return ''.join([leter for leter in doc if leter not in ['.', ',', ':', ';', '-', '+']])


def tokenize(doc):
    doc_normalized = doc.lower()
    doc_normalized = remove_pontuacao(doc_normalized)
    doc_normalized = remove_accents(doc_normalized)
    return [stemmer.stem(word.decode()) for word in doc_normalized.split()
            if (len(word) > 2 and word not in stop_words)]


class FiltroTGForm(FlaskForm):
    descricao = StringField(u'Descrição do item',
                            default='')


def monta_assistente_bm25(engine):
    SQL = 'SELECT t.ovr_id as ficha, i.* FROM ovr_itenstg i INNER JOIN ovr_tgovr t on i.tg_id=t.id;'
    df = pd.read_sql(SQL, engine)
    print('len itenstg:', len(df))
    itenstg = df.dropna(subset=['ncm'])
    print('len itenstg dropna:', len(itenstg))
    corpus = list(itenstg.descricao.values)
    corpus_normalized = [tokenize(line) for line in corpus]
    bm25n = BM25Okapi(corpus_normalized)
    return bm25n, corpus, itenstg


def monta_sugestoes(texto, n_rows=10)-> pd.DataFrame:
    doc_scores = bm25n.get_scores(tokenize(texto))
    new_df = itenstg.copy()
    new_df['pontuação'] = doc_scores
    new_df = new_df[new_df['pontuação'] > 0.]
    new_df = new_df.sort_values(axis=0, ascending=False, by='pontuação').head(n_rows)
    # print(new_df.columns)
    new_df['get_unidade'] = new_df.unidadedemedida.apply(Enumerado.unidadeMedida)
    return new_df


def remove_accents2(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str.lower())
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode('utf-8')


def monta_planilha(df, n_rows=5)-> pd.DataFrame:
    lista_dict = []
    print(df.columns)
    df.rename(remove_accents2, axis='columns', inplace=True)
    print(df.columns)
    for column in df.columns:
        if 'quantidade' in column:
            df.rename(columns={column: 'quantidade'})
        if 'unidade' in column or 'medida' in column:
            df.rename(columns={column: 'unidade'})
            break
    planilha = df.dropna(subset=['descricao'])
    for row in planilha.iterrows():
        # print(row[1])
        row_ = {}
        row_['Item'] = row[1]['item']
        row_['Código NCM'] = ''
        row_['Descrição'] = row[1]['descricao']
        row_['Marca'] = ''
        row_['Modelo'] = ''
        row_['Unid. Medida'] = row[1]['unidade']
        row_['País Procedência'] = 249
        row_['País Origem'] = 994
        row_['Quantidade'] = row[1]['quantidade']
        row_['Valor Unitário'] = ''
        lista_dict.append(row_)
        print(row_['Descrição'])
        doc_scores = bm25n.get_scores(tokenize(row_['Descrição']))
        indices = np.flip(np.argpartition(doc_scores, doc_scores.shape[0] - 3)[-5:])
        new_df = itenstg.iloc[np.flip(indices)]
        for new_row in new_df.iterrows():
            row_ = row_.copy()
            row_['Item'] = '-'
            row_['Descrição'] = new_row[1]['descricao']
            row_['Código NCM'] = new_row[1]['ncm']
            unidade = 'UN' if new_row[1]['unidadedemedida'] == 0 else 'KG'
            row_['Unid. Medida'] = unidade
            row_['Valor Unitário'] = new_row[1]['valor']
            lista_dict.append(row_)
    return pd.DataFrame(lista_dict)


def consulta_itens(texto)-> pd.DataFrame:
    print(texto)
    sql = 'SELECT o.id as Ficha, t.numerotg as "Número TG",' + \
          ' DATE(o.datahora) as "Início da Ação", DATE(o.last_modified) "Fim da Ação",' + \
          ' DATE(t.create_date) as "Data do TG",' + \
          ' i.NCM as NCM, i.descricao as "Descrição",' + \
          ' i.valor as "Valor Unitário", ' + \
          ' i.qtde as  Quantidade, i.unidadedemedida' + \
          ' FROM ovr_itenstg i' + \
          ' INNER JOIN ovr_tgovr t on i.tg_id=t.id' + \
          ' INNER JOIN ovr_ovrs o on o.id=t.ovr_id'
    if 'NCM' in texto:
        ncms = texto.replace(';', ' ').replace(',', ' ').replace(':', ' ').split()[1:]
        ncms = [ncm + '%' for ncm in ncms]
        print(ncms)
        sql = sql + ' WHERE ncm like %s'
        for _ in ncms[1:]:
            sql = sql + ' OR ncm like %s'
        print(sql)
        sql = sql + ' ORDER BY o.datahora'
        df = pd.read_sql(sql, engine, params=ncms)
    else:
        sql = sql + ' WHERE i.descricao like %s and ncm is not null'
        sql = sql + ' ORDER BY o.datahora'
        df = pd.read_sql(sql, engine, params=['%' + texto.strip() + '%'])
    df['Unidade'] = df.unidadedemedida.apply(Enumerado.unidadeMedida)
    df['Valor Total'] = df['Valor Unitário'] * df['Quantidade']
    df.drop('unidadedemedida', axis=1, inplace=True)

    def converte_data(x):
        try:
            return datetime.strftime(x, '%d/%m/%Y')
        except:
            return ''

    df['Início da Ação'] = df['Início da Ação'].apply(converte_data)
    df['Fim da Ação'] = df['Fim da Ação'].apply(converte_data)
    df['Data do TG'] = df['Data do TG'].apply(converte_data)
    print('len df:', len(df))
    return df


bm25n, corpus, itenstg = monta_assistente_bm25(engine)


def assistentetg_app(app):
    @app.route('/assistente_tg', methods=['POST', 'GET'])
    @login_required
    def assistente_tg():
        filtro_form = FiltroTGForm()
        title_page = 'Assistente de TG'
        resultados = []
        try:
            if request.method == 'POST' and filtro_form.validate():
                filtro_form = FiltroTGForm(request.form)
                if request.form.get('exportar') is not None:
                    resultados = consulta_itens(filtro_form.descricao.data)
                else:
                    resultados = monta_sugestoes(filtro_form.descricao.data, 50)
                if (request.form.get('exportar') is not None) or\
                        (request.form.get('exportar_texto') is not None):
                    out_filename = '{}_{}.xls'.format('PesquisaItens_',
                                                      '_'.join(filtro_form.descricao.data.split())
                                                      )
                    resultados.to_excel(os.path.join(get_user_save_path(), out_filename),
                                        index=False)
                    return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('assistente_tg.html', oform=filtro_form,
                               resultados=resultados.to_dict('records'),
                               title_page=title_page)

    @app.route('/assistente_tg_planilha', methods=['POST'])
    @login_required
    def assistente_tg_planilha():
        try:
            planilha = request.files['planilha']
            df = pd.read_excel(planilha)
            df_out = monta_planilha(df, 5)
            out_filename = 'TG ' + planilha.filename
            df_out.to_excel(os.path.join(get_user_save_path(), out_filename), index=False)
            return redirect('static/%s/%s' % (current_user.name, out_filename))
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('assistente_tg.html', oform=FiltroTGForm())
