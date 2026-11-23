"""Gera o pacote ZIP de estudos de caso para apresentação (23/11/2026).

O ZIP traz, por caso, os dados da Ficha e do CE para o slide de abertura, a imagem de escaneamento
do contêiner, uma amostra das fotos da RVF em miniatura e o SKILL.md com as instruções para uma IA
montar o PowerPoint. Detalhes em bhadrasana/estudo_de_caso/pacote.py.

Na raiz do bhadrasana2, com o ambiente do Fichas (a configuração do ajna_commons dá o SQL e o
Mongo das imagens de escaneamento; MONGODB_RISCO, o Mongo das fotos):

    python bhadrasana/scripts/estudo_de_caso.py                 # 5 maiores Operações, sem filtro
    python bhadrasana/scripts/estudo_de_caso.py --ano 2026      # Fichas abertas em 2026
    python bhadrasana/scripts/estudo_de_caso.py --ficha 123456  # uma Ficha

Só lê: nada é gravado no banco nem no GridFS.
"""
import os
import sys
from pathlib import Path

import click

sys.path.insert(0, '.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
sys.path.insert(0, '../ajna_api')

from bhadrasana.estudo_de_caso import pacote  # noqa: E402


def conecta():
    """(sessão SQL, Mongo das imagens de escaneamento, Mongo das fotos), como o main.py."""
    from pymongo import MongoClient

    from ajna_commons.flask.conf import DATABASE, MONGODB_URI
    from bhadrasana.models import db_session

    uri_risco = os.environ.get('MONGODB_RISCO')
    if not uri_risco:
        raise click.ClickException('Defina MONGODB_RISCO (o Mongo das fotos do Fichas), como no '
                                   'servidor do Fichas.')
    mongodb = MongoClient(host=MONGODB_URI)[DATABASE]
    return db_session, mongodb, MongoClient(host=uri_risco)['risco']


@click.command()
@click.option('--ficha', type=int,
              help='Id da Ficha (o da URL /ovr?id=...). Sem --ficha: as maiores Operações.')
@click.option('--ano', type=int,
              help='Só as Fichas abertas no ano (o atalho de ano do Dashboard de Operações).')
@click.option('--quantidade', type=click.IntRange(1, 50), default=pacote.QUANTIDADE_OPERACOES,
              show_default=True, help='Quantas Operações (sem --ficha).')
@click.option('--fotos', type=click.IntRange(0, 50), default=pacote.QUANTIDADE_FOTOS,
              show_default=True, help='Fotos da RVF por caso: as primeiras e um sorteio.')
@click.option('--saida', type=click.Path(), default='.', show_default=True,
              help='Pasta do ZIP ou o caminho do arquivo .zip.')
@click.option('--referencias', type=click.Path(), default=str(pacote.REFERENCIAS_NAVI_I),
              help='Pasta das tabelas do NAVI-I (portos e NCM); sem ela, só os códigos.')
def gera(ficha, ano, quantidade, fotos, saida, referencias):
    """Gera o pacote de estudos de caso: de uma Ficha (--ficha), das maiores Operações no ano
    (--ano) ou de todo o período."""
    if ficha and ano:
        raise click.UsageError('Use --ficha ou --ano, não os dois.')
    destino = Path(saida)
    if destino.suffix.lower() != '.zip':
        destino = destino / pacote.nome_do_pacote(ficha, ano)
    session, mongodb, mongo_risco = conecta()
    try:
        indice = pacote.gera_pacote(session, mongodb, mongo_risco, destino, ficha_id=ficha,
                                    ano=ano, quantidade=quantidade, quantidade_fotos=fotos,
                                    referencias=referencias)
    except ValueError as erro:
        raise click.ClickException(str(erro))
    finally:
        session.remove()
    for caso in indice['casos']:
        origem = f" – {caso['operacao']}" if caso['operacao'] else ''
        click.echo(f"{caso['titulo_sugerido']}{origem}: Ficha {caso['ficha']}, {caso['valor']}, "
                   f"{caso['escaneamentos']} escaneamento(s), {caso['fotos']} foto(s), "
                   f"{caso['avisos']} aviso(s)")
    if not indice['parametros']['nomes_de_portos_e_ncm']:
        click.echo('Sem as tabelas do NAVI-I: portos e NCMs saem só com o código (--referencias).')
    click.echo(f'Pacote gravado em {destino.resolve()}')


if __name__ == '__main__':
    gera()
