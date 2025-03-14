"""
Módulo para consultas simples da API Recintos e para upload de arquivos


"""
import zipfile

from ajna_commons.flask.log import logger
from flask import render_template, flash, request, redirect, jsonify
from flask_login import login_required

from bhadrasana.forms.assistente_checkapi import ArquivoApiForm
from bhadrasana.models.apirecintos import AcessoVeiculo, PesagemVeiculo, EmbarqueDesembarque, InspecaoNaoInvasiva, processa_json, persiste_df
from bhadrasana.views import valid_file, csrf


def processa_zip(arquivo, session):
    zip_file = zipfile.ZipFile(arquivo, 'r')
    tipoevento = zip_file.read('tipoEvento.txt').decode()
    print(tipoevento)
    classes = {'1': AcessoVeiculo,
               '3': PesagemVeiculo,
               '4': EmbarqueDesembarque,
               '25': InspecaoNaoInvasiva}
    indices = {AcessoVeiculo: ['placa', 'operacao', 'tipoOperacao', 'dataHoraOcorrencia'],
               PesagemVeiculo: ['placa', 'dataHoraOcorrencia'],
               EmbarqueDesembarque: ['numeroConteiner', 'dataHoraOcorrencia'],
               InspecaoNaoInvasiva: ['numeroConteiner', 'dataHoraOcorrencia']}
    classe = classes[tipoevento]
    indice = indices[classe]
    logger.info(f'Classe: {classe}, Chave única: {indice}')
    json_texto = zip_file.read('json.txt').decode()
    df_eventos = processa_json(json_texto, classe, indice)
    persiste_df(df_eventos, classe, session)


def apirecintos_app(app):
    @app.route('/upload_arquivo_json_api', methods=['GET', 'POST'])
    @login_required
    def upload_arquivo_json_api():
        title_page = 'Upload de arquivo API Recintos'
        session = app.config.get('dbsession')
        try:
            if request.method == 'POST':
                print(request)
                file = request.files.get('file')
                validfile, mensagem = valid_file(file, extensions=['zip'])
                if not validfile:
                    flash(mensagem)
                    return redirect(request.url)
                # TODO: Retornar resultado, hoje o resultado está somente no log
                processa_zip(file, session)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('upload_arquivo_json_api.html',
                               title_page=title_page)

    @app.route('/upload_arquivo_json_api/api', methods=['POST'])
    #TODO: ativar login e mover para api ajna
    # @login_required
    @csrf.exempt
    def upload_arquivo_json_api_api():
        # Upload de arquivo API Recintos - JSON API Friendly
        session = app.config.get('dbsession')
        try:
            file = request.files.get('file')
            validfile, mensagem = valid_file(file, extensions=['zip'])
            if not validfile:
                return jsonify({'msg': 'Arquivo "file" vazio ou não incluído no POST'}), 404
            processa_zip(file, session)
        except Exception as err:
            logger.error(f'upload_arquivo_json_api_api: {err}')
            return jsonify({'msg:': str(err)}), 500
        return jsonify({'msg': 'Arquivo integrado com sucesso!!'}), 200
