import sys
from datetime import datetime


sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from bhadrasana.models import db_session
from bhadrasana.models.ovr import OVR
from bhadrasana.models.ovrmanager import lista_itemtg

import click


def exporta_planilha_rilo(start: datetime, end: datetime):
    ovrs = db_session.query(OVR).filter(OVR.create_date.between(start, end)).all()
    print([ovr.id for ovr in ovrs])
    print(len(ovrs))
    for ovr in ovrs:
        for tg in ovr.tgs:
            itenstg = lista_itemtg(db_session, tg.id)
            for itemtg in tg.itens:
                print(itemtg.descricao)


@click.command()
@click.option('--inicio', default=None,
              help='Dia de início (dia/mês/ano) - padrão inicio deste mês')
@click.option('--fim', default=None,
              help='Dia de fim - padrão hoje')
def run(inicio, fim):
    print(inicio, fim)
    start = datetime.strptime(inicio, '%d/%m/%Y')
    end = datetime.strptime(fim, '%d/%m/%Y')
    print(start, end)
    exporta_planilha_rilo(start, end)

if __name__ == '__main__':
    print(sys.argv)
    run()
