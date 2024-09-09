"""
Módulo para consultas simples da API Recintos e para upload de arquivos


"""
import zipfile

from ajna_commons.flask.log import logger
from flask import render_template, flash, request, redirect
from flask_login import login_required

from bhadrasana.forms.assistente_checkapi import ArquivoApiForm
from bhadrasana.models.apirecintos import AcessoVeiculo, PesagemVeiculo, InspecaoNaoInvasiva, processa_json, persiste_df
from bhadrasana.views import valid_file


def processa_zip(arquivo, session):
    zip_file = zipfile.ZipFile(arquivo, 'r')
    tipoevento = zip_file.read('tipoEvento.txt').decode()
    print(tipoevento)
    classes = {'1': AcessoVeiculo,
               '3': PesagemVeiculo,
               '25': InspecaoNaoInvasiva}
    indices = {AcessoVeiculo: ['placa', 'operacao', 'dataHoraOcorrencia'],
               PesagemVeiculo: ['placa', 'dataHoraOcorrencia'],
               InspecaoNaoInvasiva: ['numeroConteiner', 'dataHoraOcorrencia']}
    classe = classes[tipoevento]
    indice = indices[classe]
    print(classe, indice)
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
                file = request.files.get('file')
                validfile, mensagem = valid_file(file, extensions=['zip'])
                if not validfile:
                    flash(mensagem)
                    return redirect(request.url)
                content = file.read()
                # TODO: Retornar resultado, hoje o resultado está somente no log
                processa_zip(content, session)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('upload_arquivo_json_api.html',
                               title_page=title_page)


    if request.method == 'POST':
        # check if the post request has the file part
        img_search = app.config['img_search']
        index = consulta_padma(content, 'index')
        # print(index)
        try:
            code = index.get('predictions')[0].get('code')
        except Exception as err:
            logger.error(err)
            code = None
        if code is not None:
            _ = img_search.get_chunk(file.filename, index=code)
            return redirect(url_for('similar', _id=file.filename))
        else:
            flash('Erro ao consultar index no PADMA. Checar logs do PADMA')
    return render_template('upload_file.html')
