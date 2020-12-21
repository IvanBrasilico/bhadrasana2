import sys
import unittest
import warnings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.forms.ovr import TGOVRForm
from bhadrasana.models import ESomenteUsuarioResponsavel, PerfilUsuario, Enumerado, perfilAcesso
from bhadrasana.models.rvfmanager import cadastra_rvf

sys.path.append('.')

from bhadrasana.models.ovr import metadata, create_tiposevento, create_tiposprocesso, create_flags, \
    create_tipomercadoria, create_marcas

from bhadrasana.models.ovrmanager import gera_processoovr, atribui_responsavel_ovr, excluir_processo, libera_ovr, \
    lista_tgovr, cadastra_tgovr
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
        setor2 = self.create_setor('2', 'Setor 2')
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

    def test_OVR_Processo_Sem_Responsavel(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        # user_1 cria novo processo em uma ficha sem responsável atribuído
        # sistema não deixa ele excluir sem se autoatribuir
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

    def test_OVR_Supervisor_Varias_Atribuicoes(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('2', 'Setor 2')
        setor3 = self.create_setor('3', 'Setor 3', '1')
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
        ### Continua falhando quando o setor da ficha seja filho do setor do usuário supervisor
        ovr.setor_id = '3'
        ovr.responsavel_cpf = 'chaves'
        session.add(ovr)
        session.commit()
        print('Atribuição 5 - é Supervisor mas ovr em outro Setor filho')
        # with self.assertRaises(ESomenteUsuarioResponsavel):
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', 'chaves')
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', 'chaves')
        assert ovr.responsavel_cpf == 'user_1'

    def test_OVR_Supervisor_Atribuir(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('2', 'Setor 2')
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
        # Falha quando user_2 tenta liberar a OVR
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = libera_ovr(session, ovr.id, 'user_2')
        # Falha quando user_2 tenta se autoatribuir a OVR
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', None)
        # user_1 libera a OVR
        evento = libera_ovr(session, ovr.id, 'user_1')
        assert ovr.responsavel_cpf is None
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', None)
        assert ovr.responsavel_cpf == 'user_2'

    # Auditor (atribui_responsavel_ovr)
    def test_definir_auditor(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('2', 'Setor 2')
        user1 = self.create_usuario('1111', 'Usuario 1', setor1)
        user2 = self.create_usuario('2222', 'Usuario 2', setor1)
        ovr = self.create_OVR_valido()
        ovr.setor_id = '1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        assert ovr.responsavel_cpf is None
        # user1 atribui ficha a si mesmo
        evento1 = atribui_responsavel_ovr(session, ovr.id, user1.cpf, None)
        assert ovr.responsavel_cpf == user1.cpf
        # TESTE: user1 define auditor como user2
        assert ovr.cpfauditorresponsavel is None
        evento2 = atribui_responsavel_ovr(session, ovr.id, user2.cpf, user1.cpf, True)
        assert ovr.responsavel_cpf == user1.cpf
        assert ovr.cpfauditorresponsavel == user2.cpf
        # TESTE: Falha quando user_2 tenta se autoatribuir a OVR, não é responsável
        with self.assertRaises(ESomenteUsuarioResponsavel):
           evento3 = atribui_responsavel_ovr(session, ovr.id, user2.cpf, user2.cpf)
        assert ovr.cpfauditorresponsavel == user2.cpf
        # TESTE: Falha quando user_2 tenta definir auditor
        with self.assertRaises(ESomenteUsuarioResponsavel):
            evento4 = atribui_responsavel_ovr(session, ovr.id, user2.cpf, user2.cpf, True)
        assert ovr.responsavel_cpf == user1.cpf
        assert ovr.cpfauditorresponsavel == user2.cpf


    # TODO: testes de:
    #  Transferir para outro Setor (muda_setor_ovr),
    #  Lavratura do AI (informa_lavratura_auto),
    #  Informar Evento (gera_eventoovr),
    #  ItensTG,

    # RVF > cadastra_rvf
    def test_cadastra_RVF(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('2', 'Setor 2')
        user1 = self.create_usuario('user_1', 'Usuario 1', setor1)
        user2 = self.create_usuario('user_2', 'Usuario 2', setor1)
        ovr = self.create_OVR_valido()
        ovr.setor_id = '1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        rvf = cadastra_rvf(session, 'user_1', {}, ovr.id)
        assert rvf.user_name == 'user_1'

    def test_cadastra_RVF_outro_user(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('2', 'Setor 2')
        user1 = self.create_usuario('user_1', 'Usuario 1', setor1)
        user2 = self.create_usuario('user_2', 'Usuario 2', setor1)
        ovr = self.create_OVR_valido()
        ovr.setor_id = '1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        # Atribui OVR ao user_2
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', None)
        assert ovr.responsavel_cpf == 'user_2'
        # user_1 tenta cadastrar RVF
        with self.assertRaises(ESomenteUsuarioResponsavel):
            rvf = cadastra_rvf(session, 'user_1', {}, ovr.id)
        # user_2 cadastra RVF
        rvf = cadastra_rvf(session, 'user_2', {}, ovr.id)
        assert rvf.user_name == 'user_2'

    # TGOVR - rota: /tgovr
    def test_cadastra_TG(self):
        setor1 = self.create_setor('1', 'Setor 1')
        setor2 = self.create_setor('2', 'Setor 2')
        user1 = self.create_usuario('user_1', 'Usuario 1', setor1)
        user2 = self.create_usuario('user_2', 'Usuario 2', setor1)
        ovr = self.create_OVR_valido()
        ovr.setor_id = '1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        # Atribui OVR ao user_1
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_1', None)
        assert ovr.responsavel_cpf == 'user_1'
        # lista TGs dessa OVR
        lista_tgs = lista_tgovr(session, ovr.id)
        assert len(lista_tgs) == 0
        # user_1 cadastra TGOVR
        params = {
            'ovr_id': ovr.id,
            'unidadedemedida': 1,
            'numerolote': 'teste',
            'descricao': 'teste_desc',
        }
        tg = cadastra_tgovr(session, params, 'user_1')
        assert tg.user_name == 'user_1'
        assert tg.unidadedemedida == 1
        # lista TGs dessa OVR
        lista_tgs = lista_tgovr(session, ovr.id)
        assert len(lista_tgs) == 1
        # Atribui OVR ao user_2
        evento = atribui_responsavel_ovr(session, ovr.id, 'user_2', 'user_1')
        assert ovr.responsavel_cpf == 'user_2'
        # user_2 cadastra TGOVR
        params = {
            'ovr_id': ovr.id,
            'unidadedemedida': 1,
            'numerolote': 'teste user 2',
            'descricao': 'teste_desc user 2',
        }
        tg = cadastra_tgovr(session, params, 'user_2')
        assert tg.user_name == 'user_2'
        assert tg.unidadedemedida == 1
        # lista TGs dessa OVR
        lista_tgs = lista_tgovr(session, ovr.id)
        assert len(lista_tgs) == 2
        # user_1 tenta cadastrar TGOVR
        params = {
            'ovr_id': ovr.id,
            'unidadedemedida': 1,
            'numerolote': 'teste user 1',
            'descricao': 'teste_desc user 1 falhou',
        }
        with self.assertRaises(ESomenteUsuarioResponsavel):
            tg = cadastra_tgovr(session, params, 'user_1')
        assert tg.user_name == 'user_2'
        assert tg.unidadedemedida == 1
        # lista TGs dessa OVR
        lista_tgs = lista_tgovr(session, ovr.id)
        assert len(lista_tgs) == 2



if __name__ == '__main__':
    unittest.main()
