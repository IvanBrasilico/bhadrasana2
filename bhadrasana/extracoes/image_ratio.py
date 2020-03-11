""""Análise do ratio de imagens por Recinto/Escâner.

Extrai e sumariza relação largura/altura de imagens agrupando por
por Recinto/Escâner para permitir a detecção de imagens que estão
sendo geradas com poucos pulsos de X-Ray/pouca informação e consequentemente
terão a qualidade prejudicada.

O script salva os resultados em um dicionário e salva dict com pickle.
Use o comando abaixo para carregar e analisar em um notebook ou outro script

with open('sizes_recinto.pickle', 'rb') as handle:
    sizes_recinto = pickle.load(handle)

Options:
  --inicio TEXT    Dia de início (dia/mês/ano) - padrão ontem
  --fim TEXT       Dia de fim (dia/mês/ano) - padrão hoje
  --limit INTEGER  Limite de registros - padrão 100

"""
import io
import pickle
import sys
import time
from collections import defaultdict

sys.path.insert(0, '.')
sys.path.insert(0, '../ajna_docs/commons')

from bhadrasana.main import mongodb as db
from ajna_commons.utils.images import mongo_image
from PIL import Image
from datetime import date, datetime, timedelta

import click

today = date.today()
str_today = datetime.strftime(today, '%d/%m/%Y')
yesterday = today - timedelta(days=1)
str_yesterday = datetime.strftime(yesterday, '%d/%m/%Y')


@click.command()
@click.option('--inicio', default=str_yesterday,
              help='Dia de início (dia/mês/ano) - padrão ontem')
@click.option('--fim', default=str_today,
              help='Dia de fim (dia/mês/ano) - padrão hoje')
@click.option('--limit', default=100,
              help='Limite de registros - padrão 100')
def do(inicio, fim, limit):
    print('Iniciando...')
    start = datetime.strptime(inicio, '%d/%m/%Y')
    end = datetime.strptime(fim + ' 23:59:59', '%d/%m/%Y %H:%M:%S')
    out_filename =  'sizes_recinto%s%s%s.pickle' % (end.year, end.month, end.day)
    s0 = time.time()
    sizes_recinto = defaultdict(list)
    query = {'metadata.contentType': 'image/jpeg',
                               'metadata.recinto': {'$exists': True},
                               'metadata.dataescaneamento': {'$gte': start, '$lt': end}}
    projection = {'_id': 1, 'metadata.recinto': 1}
    #r = requests.post('https://ajna.labin.rf08.srf/virasana/grid_data', json=params, verify=False)
    cursor = db.fs.files.find(query, projection).limit(limit)
    for count, doc in enumerate(cursor):
        _id = doc['_id']
        image = Image.open(io.BytesIO(mongo_image(db, _id)))
        # print(image.size)
        sizes_recinto[doc['metadata']['recinto']].append(image.size)
    s1 = time.time()
    # print(sizes_recinto)
    print('{:0.2f} segundos para processar {:d} registros'.format((s1 - s0), count))
    print('Resultado salvo em %s' % out_filename)
    with open(out_filename, 'wb') as handle:
        pickle.dump(sizes_recinto, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # with open('sizes_recinto.pickle', 'rb') as handle:
    #    sizes_recinto = pickle.load(handle)


if __name__ == '__main__':
    do()
