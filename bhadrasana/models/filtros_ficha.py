from sqlalchemy import and_

from bhadrasana.models.ovr import TGOVR
from bhadrasana.models.rvf import ApreensaoRVF, RVF


class FiltrosFicha:
    """Classe para ajudar a montar os filtros da Pesquisa Ficha"""

    def __init__(self, pfiltro: dict, tables: list, filtro):
        """ Recebe dados do filtro em montagem

        :param pfiltro: dicionário da tela com campos para montar filtro
        :param tables: lista de classes SQLAlchemy a incluir no join
        :param filtro: lista de filtros SQLAlchemy a colocar no filter
        """
        self.pfiltro = pfiltro
        self.tables = tables
        self.filtro = filtro

    def process(self):
        """Percorre todos os métodos da classe, para que estes processem pfiltro e
        adicionem tabelas e filtros se necessário.

        """
        print('process')
        filter_methods_names = [item for item in dir(self)
                                if item.startswith('filtro')]
        print(filter_methods_names)
        for method_name in filter_methods_names:
            method = getattr(self, method_name)
            if callable(method):
                print(method, type(method))
                method()

    def filtro_temtg(self):
        print('***********************temtgfiltro',
              self.pfiltro.get('temtg'), type(self.pfiltro.get('temtg')))
        if self.pfiltro.get('temtg'):
            self.filtro = and_(TGOVR.id.isnot(None), self.filtro)
            self.tables.extend([TGOVR])

    def filtro_temapreensao(self):
        print('************************temapreensaofiltro',
              self.pfiltro.get('temapreensao'), type(self.pfiltro.get('temapreensao')))
        if self.pfiltro.get('temapreensao'):
            self.filtro = and_(ApreensaoRVF.id.isnot(None), self.filtro)
            self.tables.extend([RVF, ApreensaoRVF])
