import sys
from collections import OrderedDict
from datetime import datetime

sys.path.append('.')
sys.path.insert(0, '../ajna_docs/commons')
sys.path.insert(0, '../virasana')

from bhadrasana.models import db_session
from bhadrasana.models.ovr import OVR, ItemTG
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
    return {'CE': ovr.numeroCEmercante}


def monta_planilha_rilo(start: datetime, end: datetime) -> dict:
    result = []
    ovrs = db_session.query(OVR).filter(OVR.create_date.between(start, end)).all()
    print([ovr.id for ovr in ovrs])
    print(len(ovrs))
    for ovr in ovrs:
        lista_itens = []
        for tg in ovr.tgs:
            itenstg = lista_itemtg(db_session, tg.id)
            for itemtg in itenstg:
                lista_itens.append(itemtg)
        if len(lista_itens) > 0:
            itens_dump = [rilo_dump_itemtg(itemtg) for itemtg in itenstg[:3]]
            ovr_dict = rilo_dump_ovr(ovr)
            ovr_dict['itens'] = itens_dump
            result.append(ovr_dict)
    return result

def exporta_csv_rilo(lista_dict_planilha):
    linha = []
    cabecalhos_internos = []
    for dict_planilha in lista_dict_planilha:
        for key in dict_planilha.keys():
            if isinstance(dict_planilha[key], list):
                itemtg_dict = dict_planilha[key][0]
                cabecalhos_internos = list(itemtg_dict.keys())
        cabecalhos = [key for key in dict_planilha.keys() if not isinstance(dict_planilha[key], list)]
        print([*cabecalhos, *cabecalhos_internos])

    for dict_planilha in lista_dict_planilha:

        for key, value in dict_planilha.itens():
            linha
            if isinstance(value, list):
                itemtg_dict = dict_planilha[key][0]
                cabecalhos_internos = list(itemtg_dict.keys())
        cabecalhos = [key for key in dict_planilha.keys() if not isinstance(dict_planilha[key], list)]
        print([*cabecalhos, *cabecalhos_internos])
        #for key, value in dict_planilha:
        #     linha = []




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
    dict_planilha = monta_planilha_rilo(start, end)
    print(dict_planilha)
    exporta_csv_rilo(dict_planilha)


if __name__ == '__main__':
    print(sys.argv)
    run()
