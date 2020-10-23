import sys
from collections import OrderedDict
from datetime import datetime
from typing import List

import pandas as pd

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from bhadrasana.models import db_session
from bhadrasana.models.ovr import OVR, ItemTG, TGOVR
from bhadrasana.models.ovrmanager import lista_itemtg

import click


def rilo_dump_itemtg(itemtg: ItemTG) -> dict:
    return OrderedDict((
        ('TAX AND DUTY HS CODE', itemtg.hscode),
        ('DESCRIPTION', itemtg.descricao),
        ('QUANTITY', itemtg.qtde_str),
        ('UNIT', itemtg.get_unidadedemedida),
        ('VALUE', itemtg.valor_str)
    )
    )


def rilo_dump_ovr(ovr: OVR) -> dict:
    return OrderedDict((
        ('COUNTRY OF SEIZURE', 'BRASIL'),
        ('NATIONAL REF', 'DIREP08/%s/STS/ALF/%s' %
         (datetime.strftime(ovr.create_date, '%Y'), ovr.id)),
        ('OFFENCE DATE', datetime.strftime(ovr.create_date, '%d/%m/%y')),
        ('OFFENCE TIME', datetime.strftime(datetime.now(), '%H:%M')),
        ('OFFENCE LOCATION', 'SANTOS'),
        ('OFFENCE LOCATION TYPE', 'PORTO MARITIMO'),
        ('SERVICE', 'ALFANDEGA'),
        ('COMMON FIELDS - ALL COMMODITIES', ''),
        ('CONCEALMENT', ''),
        ('CONCEALMENT DETAILS', ''),
        ('BAGGAGE BRAND', ''),
        ('ABANDANDEB BAGGAGE', ''),
        ('COVERLOAD USED', ''),
        ('TYPE OF COVERLOAD', ''),
        ('COVERLOAD HS CODE', ''),
        ('DESCRIPTION OF COVERLOAD', ''),
        ('COUNTRY OF ORIGIN', ''),
        ('DIRECTION', 'IMPORT'),
        ('LINKAGE TO TRADE BASED MONEY LAUNDRING', ''),
        ('STATUS OF GOODS', ''),
        ('COUNTRY INITIATING CONTROLLED DELIVERY', ''),
        ('INDICATORS RELATED TO TERRORISM', 'UNKNOWN'),
        ('SEIZURE MADE WITHIN AN OPERATION', ''),
        ('TAX/DUTY OTHER FIELDS', ''),
        ('CE', ovr.numeroCEmercante)
    ))


def monta_planilha_rilo(start: datetime, end: datetime, setor_id: str) -> List[dict]:
    result = []
    ovrs = db_session.query(OVR).join(TGOVR).filter(TGOVR.create_date.between(start, end)). \
        filter(OVR.setor_id == setor_id).all()
    print([ovr.id for ovr in ovrs])
    print(len(ovrs))
    for ovr in ovrs:
        for tg in ovr.tgs:
            itenstg = lista_itemtg(db_session, tg.id)
            if len(itenstg) > 0:
                itens_dump = [rilo_dump_itemtg(itemtg) for itemtg in itenstg]
                for ind, item_dump in enumerate(itens_dump):
                    print(ind)
                    if ind == 0:
                        linha = rilo_dump_ovr(ovr)
                    for key, value in item_dump.items():
                        linha[key] = value
                    result.append(linha)
                    keys = linha.keys()
                    linha = OrderedDict()
                    for key in keys:
                        linha[key] = ''
    return result


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
    setor_id = '2'
    dict_planilha = monta_planilha_rilo(start, end, setor_id)
    print(dict_planilha)
    df = pd.DataFrame.from_dict(dict_planilha)
    print(df.head())
    df.to_csv('test_RILO.csv')


if __name__ == '__main__':
    print(sys.argv)
    run()
