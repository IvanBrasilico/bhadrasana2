import sys


sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from bhadrasana.models import db_session

import click


@click.command()
@click.option('--inicio', default=None,
              help='Dia de início (dia/mês/ano) - padrão inicio deste mês')
@click.option('--fim', default=None,
              help='Dia de fim - padrão hoje')
def run(inicio, fim):
    print(inicio, fim)


if __name__ == '__main__':
    run()