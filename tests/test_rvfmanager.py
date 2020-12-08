import sys
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.models import ENaoAutorizado, Usuario, ESomenteMesmoUsuario
from bhadrasana.models import ovr
from bhadrasana.models.rvfmanager import get_rvfs_filtro, cadastra_rvf, programa_rvf_container
from .test_base import BaseTestCase

sys.path.append('.')

from bhadrasana.models.rvf import metadata, RVF, ImagemRVF

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
ovr.create_tiposevento(session)
usuario = Usuario()
usuario.cpf = 'teste'
session.add(usuario)
usuario2 = Usuario()
usuario2.cpf = 'teste2'
session.add(usuario2)
session.commit()


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

    def test_evento_InspecaoNaoInvasiva(self):
        aovr = ovr.OVR()
        aovr.numeroCEmercante = '123'
        user_name = 'teste3'
        session.add(aovr)
        session.commit()
        session.refresh(aovr)
        with self.assertRaises(ENaoAutorizado):
            rvf = cadastra_rvf(session, user_name, {}, aovr.id)
        rvf = cadastra_rvf(session, 'teste', {'inspecaonaoinvasiva': True}, aovr.id)
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

    def test_evento_RVF(self):
        aovr = ovr.OVR()
        aovr.numeroCEmercante = '1234'
        aovr.responsavel_cpf = 'teste'
        session.add(aovr)
        session.commit()
        session.refresh(aovr)
        # Não gera evento, mas gera rvf nova para a OVR
        rvf = cadastra_rvf(session, 'teste', {}, aovr.id)
        assert len(rvf.ovr.historico) == 0
        # Gera evento InspecaoNaoInvasiva
        rvf = cadastra_rvf(session, 'teste', {'id': rvf.id,
                                              'numerolote': '1',
                                              'inspecaonaoinvasiva': True})
        assert len(rvf.ovr.historico) == 1
        # Não gera evento
        rvf = cadastra_rvf(session, 'teste', {'id': rvf.id,
                                              'numerolote': '1',
                                              'inspecaonaoinvasiva': True})
        assert len(rvf.ovr.historico) == 1
        rvf = cadastra_rvf(session, 'teste', {'id': rvf.id,
                                              'numerolote': '1',
                                              'inspecaonaoinvasiva': False})
        assert len(rvf.ovr.historico) == 1
        # Gera evento RVF (mais de 3 imagens e inspecaonaoinvasiva False
        for i in range(5):
            imagem_rvf = ImagemRVF()
            imagem_rvf.rvf_id = rvf.id
            session.add(imagem_rvf)
        session.commit()
        session.refresh(rvf)
        rvf = cadastra_rvf(session, 'teste', {'id': rvf.id,
                                              'numerolote': '1',
                                              'inspecaonaoinvasiva': False})
        assert len(rvf.ovr.historico) == 2


    def test_programa_RVF(self):
        aovr = ovr.OVR()
        aovr.numeroCEmercante = '123'
        aovr.user_name = 'teste'
        session.add(aovr)
        session.commit()
        session.refresh(aovr)
        # Testar que programa_rvf não gera evento, mas depois a edição gera!!!
        # (e que gera somente um evento)
        rvf = programa_rvf_container(None, None,  # Não testará imagens, apenas eventos
                                     session, aovr, 'ABCD123456', '')
        assert rvf.ovr_id == aovr.id
        assert rvf.numeroCEmercante == aovr.numeroCEmercante
        assert rvf.numerolote == 'ABCD123456'
        assert rvf.user_name is None
        assert len(rvf.ovr.historico) == 0
        rvf = cadastra_rvf(session, 'teste', {'id': rvf.id,
                                              'numerolote': '1',
                                              'inspecaonaoinvasiva': True})
        assert rvf.numerolote == '1'
        assert rvf.user_name == 'teste'
        assert rvf.descricao is None
        assert len(rvf.ovr.historico) == 1
        rvf = cadastra_rvf(session, 'teste', {'id': rvf.id,
                                              'numerolote': '2',
                                              'descricao': 'TESTANDO'})
        assert rvf.numerolote == '2'
        assert rvf.descricao == 'TESTANDO'
        assert len(rvf.ovr.historico) == 1


if __name__ == '__main__':
    unittest.main()
