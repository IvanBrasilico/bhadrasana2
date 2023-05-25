"""
Módulo para facilitar o agrupamento e exportação das OVRs mensais :-p

Permite visualizar a produção mensal, e traduzir para linguagem/código do Secta e-OVR

"""
from datetime import datetime

import pandas as pd

pd.options.display.float_format = '{:,.2f}'.format
from ajna_commons.flask.log import logger
from flask import render_template, flash, request
from flask_login import login_required
from sqlalchemy import extract

from bhadrasana.models.exporta_secta_e_ovr import preenche_linha_ovr, preenche_linha_operacao
from bhadrasana.models.ovr import OVR, EventoOVR
from bhadrasana.views import get_user_save_path


def get_fichas_portipo(db_session, ano, mes):
    lista_ovrs = db_session.query(OVR).join(EventoOVR) \
        .filter(OVR.setor_id.in_((1, 2, 3))) \
        .filter(EventoOVR.fase >= 3) \
        .filter(extract('year', EventoOVR.create_date) == ano) \
        .filter(extract('month', EventoOVR.create_date) == mes) \
        .order_by(OVR.tipooperacao, OVR.id).all()
    lista_fichas = set()
    for ovr in lista_ovrs:
        lista_fichas.add(ovr)
    lista_final = []
    for ficha in lista_fichas:
        try:
            linha_ovr = preenche_linha_ovr(ficha, ano, mes)
            linha_operacao = preenche_linha_operacao(db_session, ficha, linha_ovr['Modalidade'])
            linha_final = linha_ovr.copy()
            linha_final.update(linha_operacao)
            lista_final.append(linha_final)
        except Exception as err:
            logger.info(str(err))
            continue
    df = pd.DataFrame(lista_final)
    print(df.head())
    df = df.sort_values('Nome')
    return df


def eovr_app(app):
    @app.route('/eovr')
    @login_required
    def evor():
        title_page = 'Assistente de Exportação para OVR'
        session = app.config.get('dbsession')
        df_ovrs = None
        df_operacoes = None
        ano_mes_padrao = f'{datetime.now().year}-{str(datetime.now().month).zfill(2)}'
        ano_mes = request.values.get('ano_mes', ano_mes_padrao)
        nome = request.values.get('nome')
        ano = int(ano_mes[:4])
        mes = int(ano_mes[5:7])
        try:
            if nome is not None:
                df = pd.read_excel(f'{get_user_save_path()}e_ovr{ano_mes}.xlsx', engine="openpyxl")
                df_operacoes = df[df.Nome == nome]
            else:
                df = get_fichas_portipo(session, ano, mes)
                df.to_excel(f'{get_user_save_path()}e_ovr{ano_mes}.xlsx')
            df_ovrs = df.groupby(df.Nome).agg(
                quantidade=pd.NamedAgg(column='Documentos de origem', aggfunc='count'),
                perdimentos=pd.NamedAgg(column='Perdimento', aggfunc='sum'),
                apreensoes=pd.NamedAgg(column='Apreensao', aggfunc='sum'),
            ).reset_index()
            return render_template(f'eovr.html',
                                   ano_mes=ano_mes,
                                   title_page=title_page,
                                   df_ovrs=df_ovrs,
                                   df_operacoes=df_operacoes)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('eovr.html',
                               title_page=title_page,
                               ano_mes=ano_mes,
                               df_ovrs=df_ovrs)
