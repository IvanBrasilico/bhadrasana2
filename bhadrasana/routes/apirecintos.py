"""
Módulo para consultas simples da API Recintos e para upload de arquivos


"""
import sys
import zipfile
from datetime import timedelta, datetime

from flask import render_template, flash, request, redirect, jsonify
from flask_login import login_required

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from ajna_commons.flask.log import logger
from bhadrasana.models.apirecintos import AcessoVeiculo, PesagemVeiculo, EmbarqueDesembarque, InspecaoNaoInvasiva, \
    processa_json, persiste_df
from bhadrasana.views import valid_file, csrf

CLASSES = {'1': AcessoVeiculo,
           '3': PesagemVeiculo,
           '4': EmbarqueDesembarque,
           '25': InspecaoNaoInvasiva}

from sqlalchemy import func
from sqlalchemy.orm import Session


def max_datahora_por_recinto(session: Session):
    resultados = {}
    for tipo, classe in CLASSES.items():
        logger.info(f'Consultando classe: {tipo} - {classe}')
        query = session.query(
            classe.codigoRecinto,
            func.max(classe.dataHoraTransmissao)
        ).group_by(classe.codigoRecinto)
        resultados[tipo] = query.all()  # lista de tuplas (codigoRecinto, max_dataHoraTransmissao)
    return resultados

def max_datahora_por_recinto_lista(session: Session):
    resultados = max_datahora_por_recinto(session)
    resultados_em_lista = []
    for tipoEvento, lista in resultados.items():
        item = {'tipoEvento': tipoEvento,
                'codigoRecinto': lista[0],
                'dataHoraTransmissao': lista[1].isoformat()}
        resultados_em_lista.append(item)
    return resultados_em_lista

def traduz_parametros(tipoevento: str):
    """Esta função encapsula as informações de classes e indices. TODO: encapsular nas classes esta info

    :param tipoevento: string do tipo classes abaixo. Informação de domínio da API Recintos
    """

    indices = {AcessoVeiculo: ['placa', 'operacao', 'tipoOperacao', 'dataHoraOcorrencia'],
               PesagemVeiculo: ['placa', 'dataHoraOcorrencia'],
               EmbarqueDesembarque: ['numeroConteiner', 'dataHoraOcorrencia'],
               InspecaoNaoInvasiva: ['numeroConteiner', 'dataHoraOcorrencia']}
    try:
        classe = CLASSES[tipoevento]
    except KeyError:
        raise ValueError(f'Tipo de evento inválido ou não suportado: {tipoevento}')
    indice = indices[classe]
    logger.info(f'Classe: {classe}, Chave única: {indice}')
    return classe, indice


def processar_json_puro(session, json_texto, classe, indice):
    """

    :param session:
    :param json_texto: texto json com conteúdo de um tipo de evento, lista de eventos de um recinto em um período
    :param classe:
    :param indice:
    """
    df_eventos = processa_json(json_texto, classe, indice)
    persiste_df(df_eventos, classe, session)


def le_tipo_evento(json_texto):
    # TODO: Ver como ler o primeiro tipoevento do json (tipo é único no arquivo)
    return '1'


def processa_arquivo(arquivo, session):
    if arquivo.filename.endswith('.json'):
        json_texto = arquivo.read().decode()
        tipoevento = le_tipo_evento(json_texto)
    else:
        zip_file = zipfile.ZipFile(arquivo, 'r')
        tipoevento = zip_file.read('tipoEvento.txt').decode()
        json_texto = zip_file.read('json.txt').decode()
    logger.debug(tipoevento)
    classe, indice = traduz_parametros(tipoevento)
    processar_json_puro(session, json_texto, classe, indice)


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
                validfile, mensagem = valid_file(file, extensions=['zip', 'json'])
                if not validfile:
                    flash(mensagem)
                    return redirect(request.url)
                # TODO: Retornar resultado, hoje o resultado está somente no log
                processa_arquivo(session, file)
        except Exception as err:
            logger.error(err, exc_info=True)
            flash('Erro! Detalhes no log da aplicação.')
            flash(str(type(err)))
            flash(str(err))
        return render_template('upload_arquivo_json_api.html',
                               title_page=title_page)

    @app.route('/upload_arquivo_json_api/api', methods=['POST'])
    # TODO: ativar login e mover para api ajna
    # @login_required
    @csrf.exempt
    def upload_arquivo_json_api_api():
        # Upload de arquivo API Recintos - JSON API Friendly
        session = app.config.get('dbsession')
        try:
            file = request.files.get('file')
            validfile, mensagem = valid_file(file, extensions=['zip', 'json'])
            if not validfile:
                return jsonify({'msg': 'Arquivo "file" vazio ou não incluído no POST'}), 404
            processa_arquivo(session, file)
        except Exception as err:
            logger.error(f'upload_arquivo_json_api_api: {err}')
            return jsonify({'msg': str(err)}), 500
        return jsonify({'msg': 'Arquivo integrado com sucesso!!'}), 200

    @app.route('/api_recintos/maisrecentes', methods=['GET'])
    # TODO: ativar login e mover para api ajna
    # @login_required
    @csrf.exempt
    def api_recintos_lista_integracao():
        session = app.config.get('dbsession')
        result = {}
        try:
            # Exemplo
            # max_data = datetime.now() - timedelta(hours=1)
            # max_data_iso = max_data.isoformat()
            # result = [{'tipoEvento': '1': 'codigoRecinto': '8931359', 'dataHoraTransmissao': max_data_iso]}
            result = max_datahora_por_recinto_lista(session)
        except Exception as err:
            logger.error(f'api_recintos_lista_integracao: {err}')
            return jsonify({'msg': str(err), 'maisrecentes': result}), 500
        return jsonify({'msg': '', 'maisrecentes': result}), 200


if __name__ == '__main__':  # pragma: no-cover
    from ajna_commons.flask.conf import SQL_URI
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import logging

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

    engine = create_engine(SQL_URI)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    print(max_datahora_por_recinto_lista(session))


