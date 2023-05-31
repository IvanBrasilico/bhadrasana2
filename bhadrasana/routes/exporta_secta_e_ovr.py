"""
Módulo para facilitar o agrupamento e exportação das OVRs mensais :-p

Permite visualizar a produção mensal, e traduzir para linguagem/código do Secta e-OVR

"""
import json
from datetime import datetime

import pandas as pd

from bhadrasana.models.exporta_secta_e_ovr import get_fichas_portipo

pd.options.display.float_format = '{:,.2f}'.format
from ajna_commons.flask.log import logger
from flask import render_template, flash, request, jsonify
from flask_login import login_required

from bhadrasana.views import get_user_save_path


def monta_payload_json_ovr(df_, nome) -> dict:
    df_operacoes = df_[df_.Nome == nome]
    df_ovr = df_operacoes.loc[:, 'Nome':'Motivação']
    ovr = json.loads(df_ovr.head(1).to_json(orient='records'))
    df_operacoes = df_operacoes.loc[:, 'Órgão':'Apreensao'].drop(columns=['Servidores'])
    operacoes = json.loads(df_operacoes.to_json(orient='records'))
    payload = {**ovr[0], 'operacoes': operacoes}
    return payload


def monta_payload_json(df_, nome_ovr='') -> list:
    if nome_ovr:
        return [monta_payload_json_ovr(df_, nome_ovr)]
    else:
        return [monta_payload_json_ovr(df_, lnome) for lnome in df_.Nome.unique()]


def eovr_app(app):
    @app.route('/eovr', methods=['POST', 'GET'])
    @app.route('/exporta_e_ovr', methods=['POST', 'GET'])
    @login_required
    def exporta_e_ovr():
        title_page = 'Assistente de Exportação para OVR'
        session = app.config.get('dbsession')
        df = None
        df_ovrs = None
        df_operacoes = None
        ano_mes_padrao = f'{datetime.now().year}-{str(datetime.now().month).zfill(2)}'
        ano_mes = request.values.get('ano_mes', ano_mes_padrao)
        nome = request.values.get('nome')
        ano = int(ano_mes[:4])
        mes = int(ano_mes[5:7])
        try:
            if nome:  # Exibir operações da OVR selecionada
                df = pd.read_excel(f'{get_user_save_path()}e_ovr{ano_mes}.xlsx', engine="openpyxl")
                df_operacoes = df[df.Nome == nome]
            else:
                df = get_fichas_portipo(session, ano, mes)
                df.to_excel(f'{get_user_save_path()}e_ovr{ano_mes}.xlsx')
            if request.values.get('json'):
                return jsonify(monta_payload_json(df, nome))
            df_ovrs = df.groupby(df.Nome).agg(
                quantidade=pd.NamedAgg(column='Documentos de origem', aggfunc='count'),
                perdimentos=pd.NamedAgg(column='Perdimento', aggfunc='sum'),
                apreensoes=pd.NamedAgg(column='Apreensao', aggfunc='sum'),
                K9=pd.NamedAgg(column='K9', aggfunc='sum'),
                Lancha=pd.NamedAgg(column='Lancha', aggfunc='sum'),
                Drone=pd.NamedAgg(column='Drone', aggfunc='sum'),
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
                               df_ovrs=df_ovrs,
                               df_operacoes=df_operacoes)
