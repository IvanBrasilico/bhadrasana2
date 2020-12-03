import sys
import unittest
import warnings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.models import ESomenteUsuarioResponsavel, PerfilUsuario, Enumerado, perfilAcesso

sys.path.append('.')

from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags, \
    create_tipomercadoria, create_marcas

from bhadrasana.models.ovrmanager import gera_processoovr, atribui_responsavel_ovr, excluir_processo, libera_ovr
from virasana.integracao.mercante import mercantealchemy

warnings.simplefilter('ignore')
engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
create_tiposevento(session)
create_tiposprocesso(session)
create_flags(session)
create_tipomercadoria(session)
create_marcas(session)
mercantealchemy.metadata.create_all(engine)

from .test_base import BaseTestCase


class OVRPermissoesTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    def generate_setores_usuarios(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('1', 'Setor 2')
        user1 = self.create_usuario('user_1', 'Usuario 1', setor1)
        user2 = self.create_usuario('user_2', 'Usuario 2', setor1)

    def test_OVR_Processo(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', None)
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
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', None)
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
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', 'user_1')
        with self.assertRaises(ESomenteUsuarioResponsavel):
            excluir_processo(session, processo, 'user_1')
        session.refresh(ovr)
        assert len(ovr.processos) == 1

    def test_OVR_Processo_Incluir(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', None)
        # Tentar criar novo processo (erro ao incluir)
        params = {
            'numero': '1234',
            'tipoprocesso_id': 0,
            'ovr_id': ovr.id,
            'user_name': 'user_1'
        }
        with self.assertRaises(ESomenteUsuarioResponsavel):
            processo = gera_processoovr(session, params)

    def test_OVR_Supervisor_Atribuir(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('1', 'Setor 2')
        user1 = self.create_usuario('user_1', 'Usuario 1', setor1)
        user2 = self.create_usuario('user_2', 'Usuario 2', setor1)
        ovr = self.create_OVR_valido()
        ovr.setor_id = '1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', None)
        # Atribuir responsavel, faz uma inclusão, atribui outro, tentar retomar, vai dar erro.
        # Colocar perfil Supervisor e auto-atribuir -
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
        assert ovr.responsavel_cpf == 'user_1'
        print('Atribuição 1')
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', 'user_1')
        session.refresh(ovr)
        assert ovr.responsavel_cpf == 'user_2'
        print('Atribuição 2')
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', 'user_1')
        perfilusuario = PerfilUsuario()
        perfilusuario.cpf = 'user_1'
        perfilusuario.perfil = Enumerado.get_id(perfilAcesso, 'Supervisor')
        session.add(perfilusuario)
        session.commit()
        print('Atribuição 3 - já é Supervisor')
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', 'user_1')
        assert ovr.responsavel_cpf == 'user_1'
        ### Se ovr estiver em Setor diferente com outra pessoa, deve falhar novamente!!!!
        ovr.setor_id = '2'
        ovr.responsavel_cpf = 'chapolin'
        session.add(ovr)
        session.commit()
        print('Atribuição 4 - é Supervisor mas ovr em outro Setor')
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', 'user_1')

    def test_OVR_Supervisor_Atribuir(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('1', 'Setor 2')
        user1 = self.create_usuario('user_1', 'Usuario 1', setor1)
        user2 = self.create_usuario('user_2', 'Usuario 2', setor1)
        ovr = self.create_OVR_valido()
        ovr.setor_id = '1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', None)
        # Atribuir responsavel, faz uma inclusão, atribui outro, tentar retomar, vai dar erro.
        # Colocar perfil Supervisor e auto-atribuir -
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
        assert ovr.responsavel_cpf == 'user_1'
        print('Atribuição 1')
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', 'user_1')
        session.refresh(ovr)
        assert ovr.responsavel_cpf == 'user_2'
        print('Atribuição 2')
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', 'user_1')

    def test_OVR_libera(self):
        self.generate_setores_usuarios()
        ovr = self.create_OVR_valido()
        ovr.setor_id = '1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', None)
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = libera_ovr(session, ovr.id, 'user_2')
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', None)
        evento = libera_ovr(session, ovr.id, 'user_1')
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', None)


if __name__ == '__main__':
    unittest.main()
