"""
Módulo para consultas simples da API Recintos e para upload de arquivos


"""

import json
import random
import sys
import zipfile
from datetime import timedelta, datetime

from dateutil import parser

from flask import render_template, flash, request, redirect, jsonify
from flask_login import login_required

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from ajna_commons.flask.log import logger
from bhadrasana.models.apirecintos import AcessoVeiculo, PesagemVeiculo, EmbarqueDesembarque, InspecaoNaoInvasiva, \
    processa_json, persiste_df, ControleExtracaoRecintos
from bhadrasana.views import valid_file, csrf

CLASSES = {'1': AcessoVeiculo,
           '3': PesagemVeiculo,
           '4': EmbarqueDesembarque,
           '25': InspecaoNaoInvasiva
           }

from sqlalchemy import func
from sqlalchemy.orm import Session


def max_datahora_por_recinto(session: Session):
    # FUNDAMENTAL: Encerra transações presas do SQLAlchemy para evitar "Phantom Reads" (Cache).
    # Força a leitura dos dados mais atualizados diretamente do MySQL.
    session.commit()

    resultados = {}
    for tipo, classe in CLASSES.items():
        logger.info(f'Consultando classe: {tipo} - {classe}')
        
        # 1. Pega os recintos existentes baseados nos eventos (como já era feito)
        query_eventos = session.query(
            classe.codigoRecinto,
            func.max(classe.dataHoraTransmissao)
        ).group_by(classe.codigoRecinto)
        # Usa str().strip() para evitar que espaços ocultos quebrem o dicionário
        eventos_max = {str(row[0]).strip(): row[1] for row in query_eventos.all() if row[0]}

        # 2. Pega as marcações da nova tabela de controle
        controles = session.query(ControleExtracaoRecintos).filter(
            ControleExtracaoRecintos.tipoEvento == str(tipo).strip()
        ).all()
        controle_max = {str(c.codigoRecinto).strip(): c.ultimaDataPesquisada for c in controles}

        lista_final = []
        # 3. Mescla os dados unindo todos os recintos (evita ignorar recintos sem eventos recentes)
        todos_recintos = set(eventos_max.keys()).union(set(controle_max.keys()))
        
        for recinto in todos_recintos:
            data_evento = eventos_max.get(recinto)
            data_controle = controle_max.get(recinto)
            
            # Regra de Ouro: Sempre assume a MAIOR data disponível entre as duas tabelas!
            if data_controle and data_evento:
                data_final = max(data_controle, data_evento)
            else:
                data_final = data_controle or data_evento
                
            if data_final:
                lista_final.append((recinto, data_final))
            
        resultados[tipo] = lista_final
        
    return resultados


def max_datahora_por_recinto_lista(session: Session):
    resultados = max_datahora_por_recinto(session)
    resultados_em_lista = []
    agora = datetime.now()

    for tipoEvento, lista in resultados.items():
        # print(lista)
        for linha in lista:
            data_hora = linha[1]
            ultima_transmissao = agora - data_hora
            incluir = False
            if ultima_transmissao <= timedelta(days=1):
                incluir = True
            elif timedelta(days=1) < ultima_transmissao <= timedelta(days=3):
                incluir = random.random() < 0.50
            elif timedelta(days=3) < ultima_transmissao <= timedelta(days=7):
                incluir = random.random() < 0.5
            else:  # maior que 7 dias
                incluir = random.random() < 0.5

            if incluir:
                item = {'tipoEvento': tipoEvento,
                        'codigoRecinto': linha[0],
                        'dataHoraTransmissao': data_hora.isoformat()}
                resultados_em_lista.append(item)
    return sorted(resultados_em_lista, key=lambda x: x['dataHoraTransmissao'])


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
    print(df_eventos.head())
    persiste_df(df_eventos, classe, session)


def le_tipo_evento(lista_eventos):
    if not lista_eventos or len(lista_eventos) == 0:
        raise ValueError("A lista de eventos está vazia. Não é possível determinar o tipoEvento.")
    return str(lista_eventos[0]['dadosTransmissao']['tipoEvento'])


def extrai_eventos(json_texto):
    # Caso arquivo seja no formato aniita, extrai a partir do conteúdo dos eventos.
    json_raw = json.loads(''.join(json_texto))
    json_raw = json_raw['partes_resultado']['eventos']
    # json_raw = [json_original for json_original in json_raw['json_original']]
    tipoevento = le_tipo_evento(json_raw)
    novo_json_texto = json.dumps(json_raw)
    return novo_json_texto, tipoevento


def processa_arquivo(session, arquivo):
    if arquivo.filename.endswith('.json'):
        json_texto = arquivo.read().decode()
        json_texto, tipoevento = extrai_eventos(json_texto)
    else:
        zip_file = zipfile.ZipFile(arquivo, 'r')
        tipoevento = zip_file.read('tipoEvento.txt').decode()
        json_texto = zip_file.read('json.txt').decode()
    logger.debug(tipoevento)
    classe, indice = traduz_parametros(tipoevento)
    processar_json_puro(session, json_texto, classe, indice)


def limpa_json_apirecintos(json_raw):
    lista_partes = json_raw['partes_resultado']
    lista_eventos = []
    for parte in lista_partes:
        for evento in parte['eventos']:
            dadosTransmissao = evento['dadosTransmissao']
            jsonOriginal = evento['jsonOriginal']
            if isinstance(jsonOriginal, str):
                jsonOriginal = json.loads(jsonOriginal)
            lista_eventos.append({'jsonOriginal': jsonOriginal, 'dadosTransmissao': dadosTransmissao})
    return lista_eventos


def processa_json_post(session, json_raw):
    json_raw = limpa_json_apirecintos(json_raw)
    tipoevento = le_tipo_evento(json_raw)
    logger.debug(tipoevento)
    logger.debug(json_raw)
    classe, indice = traduz_parametros(tipoevento)
    json_texto = json.dumps(json_raw)
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

    @app.route('/upload_arquivo_json_api/api_json', methods=['POST'])
    # TODO: ativar login e mover para api ajna
    # @login_required
    @csrf.exempt
    def upload_arquivo_json_api_api_json():
        # Upload de arquivo API Recintos - JSON API Friendly
        session = app.config.get('dbsession')
        try:
            json_recebido = request.json
            logger.debug("Passou em json_recebido****")
            processa_json_post(session, json_recebido)
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


    @app.route('/api_recintos/atualiza_ponteiro', methods=['POST'])
    # TODO: ativar login e mover para api ajna
    # @login_required
    @csrf.exempt
    def api_recintos_atualiza_ponteiro():

        session = app.config.get('dbsession')
        try:
            dados = request.json
            recinto = dados.get('codigoRecinto')
            tipo = dados.get('tipoEvento')
            data_str = dados.get('dataFim')

            if not all([recinto, tipo, data_str]):
                return jsonify({'msg': 'Faltam parâmetros (codigoRecinto, tipoEvento, dataFim)'}), 400

            # Converte a data string do Jython para objeto DateTime
            nova_data = parser.isoparse(data_str).replace(tzinfo=None, microsecond=0)

            # Busca se já existe um controle para esse recinto e evento
            controle = session.query(ControleExtracaoRecintos).filter(
                ControleExtracaoRecintos.codigoRecinto == str(recinto),
                ControleExtracaoRecintos.tipoEvento == str(tipo)
            ).first()

            if controle:
                # Só atualiza se a nova data for realmente maior que a anterior (evita retrocessos)
                if nova_data > controle.ultimaDataPesquisada:
                    controle.ultimaDataPesquisada = nova_data
            else:
                # Se não existir, insere o registro inicial
                novo_controle = ControleExtracaoRecintos(
                    codigoRecinto=str(recinto), 
                    tipoEvento=str(tipo), 
                    ultimaDataPesquisada=nova_data
                )
                session.add(novo_controle)

            session.commit()
            return jsonify({'msg': 'Ponteiro atualizado com sucesso!'}), 200

        except Exception as err:
            session.rollback()
            logger.error(f'api_recintos_atualiza_ponteiro erro: {err}')
            return jsonify({'msg': str(err)}), 500


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
