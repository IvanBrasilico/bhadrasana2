import os

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
    stop_words = nltk.corpus.stopwords.words('portuguese')
    doc_normalized = doc.lower()
    doc_normalized = remove_pontuacao(doc_normalized)
    doc_normalized = remove_accents(doc_normalized)
    return [word for word in doc_normalized.split() if (len(word) > 2 and word not in stop_words)]


class FiltroTGForm(FlaskForm):
    descricao = StringField(u'Descrição do item',
                            default='')


def monta_assistente_bm25(engine):
    SQL = 'SELECT * FROM ovr_itenstg'
    df = pd.read_sql(SQL, engine)
    itenstg = df.dropna(subset=['ncm'])
    corpus = list(itenstg.descricao.values)
    corpus_normalized = [tokenize(line) for line in corpus]
    bm25n = BM25Okapi(corpus_normalized)
    return bm25n, corpus, itenstg


def monta_sugestoes(texto, n_rows=10):
    doc_scores = bm25n.get_scores(tokenize(texto))
    indices = np.flip(np.argpartition(doc_scores, doc_scores.shape[0] - 3)[-n_rows:])
    new_df = itenstg.iloc[np.flip(indices)]
    print(new_df.columns)
    new_df['get_unidade'] = new_df.unidadedemedida.apply(Enumerado.unidadeMedida)
    return new_df.to_dict('records')


def remove_accents2(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str.lower())
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode('utf-8')

def monta_planilha(df, n_rows=5):
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
                resultados = monta_sugestoes(filtro_form.descricao.data, 20)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('assistente_tg.html', oform=filtro_form,
                               resultados=resultados, title_page=title_page)


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
        return render_template('assistente_tg.html',oform=FiltroTGForm())
