import sys
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.models import ENaoAutorizado, Usuario, ESomenteMesmoUsuario
from bhadrasana.models import ovr
from bhadrasana.models.rvfmanager import get_rvfs_filtro, cadastra_rvf
from .test_base import BaseTestCase

sys.path.append('.')

from bhadrasana.models.rvf import metadata, RVF

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
ovr.create_tiposevento(session)


class RVFTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)
        metadata.create_all(engine,
                            [
                                metadata.tables['ovr_marcasencontradas'],
                                metadata.tables['ovr_lacres'],
                                metadata.tables['ovr_lacresverificados'],
                                metadata.tables['ovr_infracoes'],
                                metadata.tables['ovr_verificacoesfisicas'],
                                metadata.tables['ovr_imagensrvf'],
                            ])

    def tearDown(self) -> None:
        metadata.drop_all(engine,
                          [
                              metadata.tables['ovr_marcasencontradas'],
                              metadata.tables['ovr_lacres'],
                              metadata.tables['ovr_lacresverificados'],
                              metadata.tables['ovr_infracoes'],
                              metadata.tables['ovr_verificacoesfisicas'],
                              metadata.tables['ovr_imagensrvf'],
                          ])

    def debug(self) -> None:
        pass

    def test_get_rvfs_ce(self):
        rvf = RVF()
        rvf.numeroCEmercante = '1'
        session.add(rvf)
        rvf2 = RVF()
        rvf2.numeroCEmercante = '2'
        session.add(rvf2)
        session.commit()
        filtro = {'numeroCEmercante': '1'}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 1
        filtro = {'numeroCEmercante': '2'}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 1
        filtro = {'numeroCEmercante': '3'}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 0

    def test_get_rvfs_container(self):
        rvf = RVF()
        rvf.numerolote = 'ABCD'  # parcial
        session.add(rvf)
        rvf2 = RVF()
        rvf2.numerolote = 'b'  # case insensitive
        session.add(rvf2)
        session.commit()
        filtro = {'numerolote': 'A'}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 1
        assert rvfs[0].numerolote == 'ABCD'
        filtro = {'numerolote': 'B'}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 1
        assert rvfs[0].numerolote == 'b'
        filtro = {'numerolote': 'C'}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 0

    def test_get_rvfs_datas(self):
        rvf = RVF()
        rvf.datahora = datetime(2020, 1, 1, 0, 0, 1)
        session.add(rvf)
        rvf2 = RVF()
        rvf2.datahora = datetime(2020, 1, 2, 0, 0, 1)
        session.add(rvf2)
        rvf3 = RVF()
        rvf3.datahora = datetime(2020, 1, 3, 0, 0, 1)
        session.add(rvf3)
        session.commit()
        filtro = {'datainicio': datetime(2020, 1, 1),
                  'datafim': datetime(2020, 1, 2)}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 2
        filtro = {'datainicio': datetime(2020, 1, 4),
                  'datafim': datetime(2020, 1, 5)}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 0

    def test_evento_RVF(self):
        aovr = ovr.OVR()
        aovr.numeroCEmercante = '123'
        aovr.user_name = 'teste'
        session.add(aovr)
        session.commit()
        session.refresh(aovr)
        with self.assertRaises(ENaoAutorizado):
            rvf = cadastra_rvf(session, aovr.user_name, {}, aovr.id)
        usuario = Usuario()
        usuario.cpf = 'teste'
        session.add(usuario)
        usuario2 = Usuario()
        usuario2.cpf = 'teste2'
        session.add(usuario2)
        session.commit()
        rvf = cadastra_rvf(session, aovr.user_name, {}, aovr.id)
        assert rvf.ovr_id == aovr.id
        assert rvf.numeroCEmercante == aovr.numeroCEmercante
        evento = rvf.ovr.historico[0]
        assert evento.ovr_id == aovr.id
        assert rvf.numerolote is None
        with self.assertRaises(ESomenteMesmoUsuario):
            rvf = cadastra_rvf(session, 'teste2', {'id': rvf.id,
                                                   'numerolote': '1'})
        rvf = cadastra_rvf(session, 'teste', {'id': rvf.id,
                                               'numerolote': '1'})
        assert rvf.numerolote == '1'


if __name__ == '__main__':
    unittest.main()
