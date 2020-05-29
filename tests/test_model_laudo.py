import sys
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models.laudo import Base, SAT, Empresa

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)


class LaudoTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.session = session

    def create_sat(self, numero, datapedido):
        sat = self.session.query(SAT).filter(SAT.numeroSAT == numero).one_or_none()
        if sat:
            return sat
        sat = SAT()
        sat.numeroSAT = numero
        sat.dataPedido = datapedido
        self.session.add(sat)
        self.session.commit()
        sat = self.session.query(SAT).filter(SAT.numeroSAT == numero).one_or_none()
        return sat

    def test_SAT(self):
        datapedido = datetime(2020, 1, 1)
        sat = self.create_sat(1, datapedido)
        assert sat.get_numero() == '0817800/1/2020'

    def create_empresa(self, cnpj, nome):
        empresa = self.session.query(Empresa).filter(Empresa.cnpj == cnpj).one_or_none()
        if empresa:
            return empresa
        empresa = Empresa()
        empresa.nome = nome
        empresa.cnpj = cnpj
        self.session.add(empresa)
        self.session.commit()
        empresa = self.session.query(Empresa).filter(Empresa.cnpj == cnpj).one_or_none()
        return empresa


    def test_Empresa(self):
        empresa = self.create_empresa('00000001', 'BB')
        assert empresa.nome == 'BB'
