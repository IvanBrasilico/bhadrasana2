import unittest
import os
from io import BufferedReader

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bhadrasana.models.ovr import metadata, TGOVR
import virasana.integracao.mercante.mercantealchemy as mercante

from bhadrasana.models.ovrmanager import importa_planilha_tg, cadastra_tgovr

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
mercante.metadata.create_all(engine, [
    mercante.metadata.tables['itensresumo'],
    mercante.metadata.tables['conhecimentosresumo']
])

from .test_base import BaseTestCase

class Planilha:
    def __init__(self, filename, file=None):
        self.filename = filename
        self.file = file

    def __repr__(self):
        return self.filename

    def __str__(self):
        return self.filename

class OVRTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    def test_OVR_Evento(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        tg = TGOVR()
        tg.descricao = 'teste10'
        tg.qtde = 10
        tg.ovr_id = ovr.id
        tg.numerolote = 'CCNU1234567'
        session.add(tg)
        session.commit()
        # test xls file
        file_name = os.path.join(os.path.dirname(__file__), 'teste.xls')
        alert = importa_planilha_tg(session, tg, file_name)
        assert 'Campo procedencia(País Procedência, *****) não encontrado' in alert
        # test csv file
        file_name = os.path.join(os.path.dirname(__file__), 'teste_csv')
        alert = importa_planilha_tg(session, tg, file_name)
        assert 'Campo procedencia(País Procedência, *****) não encontrado' in alert
        # test ods file
        file_name = os.path.join(os.path.dirname(__file__), 'teste.ods')
        alert = importa_planilha_tg(session, tg, file_name)
        assert 'Campo procedencia(País Procedência, *****) não encontrado' in alert
        # test Exception file reading
        file_name_wrong = os.path.join(os.path.dirname(__file__), '123.abc')
        with self.assertRaises(Exception):
            alert = importa_planilha_tg(session, tg, file_name_wrong)
        # test broken file
        file_name = os.path.join(os.path.dirname(__file__), 'teste_sem_coluna_ncm.ods')
        alert = importa_planilha_tg(session, tg, file_name)
        assert alert.find("ncm") > 0
        # test broken file
        file_name = os.path.join(os.path.dirname(__file__), 'teste_sem_coluna_valor.ods')
        alert = importa_planilha_tg(session, tg, file_name)
        assert alert.find("valor") > 0
        # assert False


if __name__ == '__main__':
    unittest.main()