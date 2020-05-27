import sys
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.models.rvfmanager import cadastra_rvf, get_rvfs_filtro
from .test_base import BaseTestCase

sys.path.append('.')

from bhadrasana.models.rvf import metadata, RVF

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)


class RVFTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    def test_get_rvfs_container(self):
        rvf = RVF()
        rvf.numeroCEmercante = '1'
        session.add(rvf)
        session.commit()
        filtro = {'numeroCEmercante': '1'}
        rvfs = get_rvfs_filtro(session, filtro)
        assert len(rvfs) == 1



if __name__ == '__main__':
    unittest.main()
