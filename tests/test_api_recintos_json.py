import requests
import json

# Caminho do arquivo de teste
ARQUIVO = 'tests/json/formato_contagil.json'

# URL da API a ser testada
URL = 'http://localhost:5005/upload_arquivo_json_api/api_json'  # altere a porta/host se necessário

# Carrega o JSON conforme o modelo de envio esperado (eventos dentro de partes_resultado)
with open(ARQUIVO, encoding='utf-8') as f:
    dados_json = json.load(f)

# Para API, deve-se enviar o conteúdo dos eventos, conforme rotina da aplicação:
# payload será apenas o array de eventos já extraído do JSON
eventos = dados_json['partes_resultado']['eventos']

# Realiza o POST utilizando a opção json do requests (envia com Content-Type: application/json)
resp = requests.post(URL, json=eventos)

print("Status:", resp.status_code)
try:
    print("Response:", resp.json())
except Exception:
    print("Response (raw):", resp.text)