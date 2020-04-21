import os
import sys

from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

from models.rvf import Infracao

sys.path.insert(0, '.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')
from bhadrasana.models import ovr, rvf
from bhadrasana.models.ovr import TipoMercadoria, tipoStatusOVREspecial, \
    TipoEventoOVR, tipoStatusOVR, Marca

SQL_URI_HOM = os.environ('SQL_URI_HOM')
if 'dbmercante' in SQL_URI_HOM:
    sys.exit('Configurar para Banco de Dados de homologação!!!')
engine = create_engine(SQL_URI_HOM)
Session = sessionmaker(bind=engine)
session = Session()

# metadata.drop_all(engine)
ovr.metadata.create_all(engine)
# rvf.metadata.drop_all(engine)
rvf.metadata.create_all(engine)

for nome in ('Adidas',
             'Burberry',
             'Tag Hauer',
             'Nike',
             'Apple',
             'Disney'):
    marca = Marca()
    marca.nome = nome
    session.add(marca)
session.commit()
fases = [0, 1, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 4]
for nome, fase in zip(tipoStatusOVR, fases):
    evento = TipoEventoOVR()
    evento.nome = nome
    evento.fase = fase
    session.add(evento)
for nome, especial, fase in tipoStatusOVREspecial:
    evento = TipoEventoOVR()
    evento.nome = nome
    evento.fase = fase
    evento.eventoespecial = especial
    session.add(evento)
session.commit()

tiposmercadoria = ['Alimentos',
                   'Automotivo',
                   'Bagagem',
                   'Brinquedos',
                   'Eletro-eletrônico'
                   'Livro',
                   'Informática',
                   'Máquinas',
                   'Papel',
                   'Têxtil',
                   'Químico',
                   'Ferramenta',
                   'Obras de metal',
                   'Obras de borracha',
                   'Obras de vidro',
                   'Obras de plástico',
                   'Bebidas',
                   'Medicamento',
                   'Sem valor comercial',
                   'Container vazio']
for nome in tiposmercadoria:
    tipomercadoria = TipoMercadoria()
    tipomercadoria.nome = nome
    session.add(tipomercadoria)
session.commit()

for nome in ('Falsa declaração de conteúdo',
             'Interposição',
             'Contrafação',
             'Quantidade divergente',
             'Fraude de valor',
             'Mercadoria não declarada',
             'Contrabando - produto proibido',
             'Drogas',
             'Armas',
             'Cigarros'):
    infracao = Infracao()
    infracao.nome = nome
    session.add(infracao)
session.commit()
