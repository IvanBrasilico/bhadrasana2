import sys
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.models import ESomenteMesmoUsuario, ESomenteUsuarioResponsavel

sys.path.append('.')

from bhadrasana.models.ovr import metadata, Enumerado, create_tiposevento, create_tiposprocesso, create_flags, \
    create_tipomercadoria, create_marcas

from bhadrasana.models.ovrmanager import gera_processoovr, atribui_responsavel_ovr, excluir_processo

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
create_tiposevento(session)
create_tiposprocesso(session)
create_flags(session)
create_tipomercadoria(session)
create_marcas(session)

from .test_base import BaseTestCase


class OVRPermissoesTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    def test_OVR_Processo(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1')
        params = {
            'numero': '1234',
            'tipoprocesso_id': 0,
            'ovr_id': ovr.id,
            'user_name': 'user_1'
        }
        processo = gera_processoovr(session, params)
        session.refresh(processo)
        session.refresh(ovr)
        assert len(ovr.processos) == 1
        excluir_processo(session, processo, 'user_1')
        session.refresh(ovr)
        assert len(ovr.processos) == 0

    def test_OVR_Processo_Excluir(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1')
        # Recriar processo mas atribuir para outro a Ficha (erro ao excluir)
        params = {
            'numero': '1234',
            'tipoprocesso_id': 0,
            'ovr_id': ovr.id,
            'user_name': 'user_1'
        }
        processo = gera_processoovr(session, params)
        session.refresh(processo)
        session.refresh(ovr)
        assert len(ovr.processos) == 1
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2')
        with self.assertRaises(ESomenteUsuarioResponsavel):
            excluir_processo(session, processo, 'user_1')
        session.refresh(ovr)
        assert len(ovr.processos) == 1

    def test_OVR_Processo_Incluir(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2')
        # Tentar criar novo processo (erro ao incluir)
        params = {
            'numero': '1234',
            'tipoprocesso_id': 0,
            'ovr_id': ovr.id,
            'user_name': 'user_1'
        }
        with self.assertRaises(ESomenteUsuarioResponsavel):
            processo = gera_processoovr(session, params)


if __name__ == '__main__':
    unittest.main()