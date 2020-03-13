""""Exporta imagens e bboxes gravados em predictions para formato yolo

Extrai imagens e bouding boxes já previstas para formato YOLO
Para permitir correções das marcações e treinamento de novos modelos


Options:
  --inicio TEXT    Dia de início (dia/mês/ano) - padrão menos 10 dias
  --fim TEXT       Dia de fim (dia/mês/ano) - padrão hoje
  --limit INTEGER  Limite de registros - padrão 100

"""
import time

from utils import str_yesterday, str_today, parse_datas

import click


@click.command()
@click.option('--inicio', default=str_yesterday,
              help='Dia de início (dia/mês/ano) - padrão ontem')
@click.option('--fim', default=str_today,
              help='Dia de fim (dia/mês/ano) - padrão hoje')
@click.option('--limit', default=100,
              help='Limite de registros - padrão 100')
def do(inicio, fim, limit):
    print('Iniciando...')
    start, end = parse_datas(inicio, fim)
    s0 = time.time()
    s1 = time.time()
    print(start, end)
    count = 0
    print('{:0.2f} segundos para processar {:d} registros'.format((s1 - s0), count))
    print('Resultado salvo no diretório %s' % end)


if __name__ == '__main__':
    do()
