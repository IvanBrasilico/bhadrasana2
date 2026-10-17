"""Integração: envia tests/json/consulta.json para /upload_arquivo_json_api/api_json de um
servidor do Fichas já rodando (padrão http://localhost:5005, o wsgi_debug.py).

ATENÇÃO: o servidor grava os eventos na base em que estiver conectado, e no Servidor de
produção o gunicorn escuta justamente em localhost:5005 (supervisor_bhadrasana2.conf). Por
isso o envio só acontece com BHADRASANA_TESTE_API_JSON=1. Sem isso, sem o arquivo (não
versionado, ver .gitignore) ou sem resposta da API, o teste é pulado com o motivo.

URL alternativa: BHADRASANA_TESTE_API_JSON_URL. Também roda como script:
    python tests/test_api_recintos_json.py
"""
import json
import os
from pathlib import Path

import pytest
import requests

# Caminho do arquivo de teste
ARQUIVO = Path(__file__).resolve().parent / 'json' / 'consulta.json'

# URL da API a ser testada
URL = os.environ.get('BHADRASANA_TESTE_API_JSON_URL',
                     'http://localhost:5005/upload_arquivo_json_api/api_json')

# O processamento de um arquivo grande pode demorar; só a conexão precisa ser rápida
TIMEOUT = (5, 300)


def carrega_json():
    # Carrega o JSON conforme o modelo de envio esperado (eventos dentro de partes_resultado)
    with open(ARQUIVO, encoding='utf-8') as f:
        return json.load(f)


def envia(dados_json):
    # POST com a opção json do requests (envia com Content-Type: application/json)
    return requests.post(URL, json=dados_json, timeout=TIMEOUT)


def test_upload_json_api():
    if os.environ.get('BHADRASANA_TESTE_API_JSON') != '1':
        pytest.skip('Integração com servidor real (grava na base dele): '
                    'defina BHADRASANA_TESTE_API_JSON=1 para enviar')
    if not ARQUIVO.exists():
        pytest.skip(f'Arquivo {ARQUIVO} não encontrado (não versionado)')
    dados_json = carrega_json()
    try:
        resp = envia(dados_json)
    except (requests.ConnectionError, requests.Timeout) as err:
        pytest.skip(f'API não respondeu em {URL}: {err}')
    assert resp.status_code == 200, resp.text


if __name__ == '__main__':
    dados_json = carrega_json()
    print("Tamanho da lista 'partes_resultado':", len(dados_json["partes_resultado"]))
    resp = envia(dados_json)
    print("Status:", resp.status_code)
    try:
        print("Response:", resp.json())
    except Exception:
        print("Response (raw):", resp.text)
