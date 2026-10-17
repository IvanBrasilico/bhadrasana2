"""Configuração comum do pytest: repositórios irmãos no sys.path.

Os testes importam virasana, ajna_commons (o vivo fica em ../ajna_docs/commons) e ajnaapi
(../ajna_api), que não são instalados via pip. Cada módulo de teste incluía esses caminhos por
conta própria, então a coleta dependia da ordem: rodar um arquivo isolado (ex.:
test_routes_ovr.py, que importa virasana antes do sys.path.append) falhava com
ModuleNotFoundError.
"""
import sys
from pathlib import Path

PROJETOS = Path(__file__).resolve().parent.parent.parent

for caminho in (PROJETOS / 'virasana', PROJETOS / 'ajna_docs' / 'commons'):
    if caminho.is_dir() and str(caminho) not in sys.path:
        sys.path.append(str(caminho))

# Mesma prioridade que os módulos de teste já davam (sys.path.insert(0, '../ajna_api')).
AJNA_API = PROJETOS / 'ajna_api'
if AJNA_API.is_dir() and str(AJNA_API) not in sys.path:
    sys.path.insert(0, str(AJNA_API))
