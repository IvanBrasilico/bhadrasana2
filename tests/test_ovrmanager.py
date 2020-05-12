import sys
import unittest
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import virasana.integracao.mercante.mercantealchemy as mercante

sys.path.append('.')

from bhadrasana.models import Usuario, Setor
from bhadrasana.models.ovr import metadata, OVR, Enumerado, Recinto, \
    create_tiposevento, create_tiposprocesso, create_flags, Flag

from bhadrasana.models.ovrmanager import get_usuarios, cadastra_ovr, gera_eventoovr, \
    gera_processoovr, cadastra_tgovr, atribui_responsavel_ovr, get_recintos, \
    get_setores_filhos_recursivo, get_tipos_evento, get_tipos_processo, get_flags_choice, get_flags, get_ovr_container

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
mercante.metadata.create_all(engine, [
    mercante.metadata.tables['itensresumo']
])

create_tiposevento(session)
create_tiposprocesso(session)
create_flags(session)

from test_base import BaseTestCase

class OVRTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    def test_OVR_Evento(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        params = {
            'motivo': 'teste',
            'tipoevento_id': 1,
            'ovr_id': ovr.id
        }
        evento = gera_eventoovr(session, params)
        assert evento.motivo == params['motivo']
        assert evento.tipoevento_id == 1
        assert ovr.fase == evento.fase
        params['tipoevento_id'] = 2
        evento2 = gera_eventoovr(session, params)
        assert ovr.fase == evento2.fase
        session.refresh(ovr)
        assert len(ovr.historico) == 2

    def test_OVR_Processo(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        for tipo in Enumerado.tipoProcesso():
            params = {
                'numero': tipo[1],
                'tipoprocesso_id': tipo[0],
                'ovr_id': ovr.id
            }
            processo = gera_processoovr(session, params)
            session.refresh(processo)
            assert processo.numero == params['numero']
            assert processo.tipoprocesso_id == params['tipoprocesso_id']
        session.refresh(ovr)
        assert len(ovr.processos) == len(Enumerado.tipoProcesso())

    def test_TGOVR(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        params = {
            'descricao': 'teste',
            'qtde': 10,
            'ovr_id': ovr.id,
            'numerolote': 'CCNU1234567'
        }
        usuario = self.create_usuario('123', 'user1')
        tgovr = cadastra_tgovr(session, params, '123')
        session.refresh(tgovr)
        for key, param in params.items():
            assert getattr(tgovr, key) == param
        session.refresh(ovr)
        assert len(ovr.tgs) == 1

    def test_Responsavel(self):
        # Atribui responsável válido
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        assert ovr.responsavel_cpf is None
        assert ovr.fase == 0
        usuario = self.create_usuario('123', 'user1')
        usuario2 = self.create_usuario('456', 'user2')
        ovr = atribui_responsavel_ovr(session, ovr.id, usuario.cpf)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario.cpf
        assert ovr.fase == 1
        # Atribui outro responsável
        ovr = atribui_responsavel_ovr(session, ovr.id, usuario2.cpf)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario2.cpf
        eventos = ovr.historico
        assert len(eventos) == 2
        evento = eventos[0]
        assert evento.fase == 1
        assert evento.motivo == 'Anterior: Nenhum'
        evento = eventos[1]
        assert evento.fase == 1
        assert evento.motivo == 'Anterior: ' + usuario.cpf

    def test_Setores_Filhos(self):
        setorpai = Setor()
        setorpai.id = 1
        setorpai.nome = 'Pai de Todos'
        session.add(setorpai)
        setor1 = Setor()
        setor1.id = 2
        setor1.pai_id = 1
        setor1.nome = 'Filho 1'
        session.add(setor1)
        setor12 = Setor()
        setor12.id = 21
        setor12.pai_id = 2
        setor12.nome = 'Sub Filho 1 do Filho 1'
        session.add(setor12)
        setor2 = Setor()
        setor2.id = 3
        setor2.pai_id = 1
        setor2.nome = 'Filho 2'
        session.add(setor2)
        setor3 = Setor()
        setor3.id = 4
        setor3.pai_id = 1
        setor3.nome = 'Filho 3'
        session.add(setor3)
        setor31 = Setor()
        setor31.id = 41
        setor31.pai_id = 4
        setor31.nome = 'Sub Filho 1 do filho 3'
        session.add(setor31)
        session.commit()
        setores = get_setores_filhos_recursivo(session, setorpai)
        print([(setor.id, setor.nome) for setor in setores])
        assert len(setores) == 5

    def assert_choices(self, tipos: List[Tuple[int, float]]):
        assert tipos is not None
        assert isinstance(tipos, list)
        assert len(tipos) > 0
        umtipoevento = tipos[0]
        assert isinstance(umtipoevento, tuple)
        assert isinstance(umtipoevento[0], int)
        assert isinstance(umtipoevento[1], str)

    def test_tiposevento(self):
        tiposevento = get_tipos_evento(session)
        self.assert_choices(tiposevento)

    def test_tiposprocesso(self):
        tiposprocesso = get_tipos_processo(session)
        self.assert_choices(tiposprocesso)

    def test_flags_choice(self):
        flags = get_flags_choice(session)

    def test_flags(self):
        flags = get_flags(session)
        assert flags is not None
        assert isinstance(flags, list)
        assert len(flags) > 0
        assert isinstance(flags[0], Flag)

    def test_get_ovrs_container(self):
        ovr1, ovr2 = self.create_OVRs_test_ovrs_container()
        ces, ovrs = get_ovr_container(session, '1')
        assert len(ovrs) == 1
        assert ovr1 in ovrs
        ces, ovrs = get_ovr_container(session, '2')
        assert len(ovrs) == 1
        assert ovr1 in ovrs
        ces, ovrs = get_ovr_container(session, '3')
        assert len(ovrs) == 1
        assert ovr2 in ovrs
        ces, ovrs = get_ovr_container(session, '4')
        assert len(ovrs) == 0




if __name__ == '__main__':
    unittest.main()
