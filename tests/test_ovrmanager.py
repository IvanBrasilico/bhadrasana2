import sys
import unittest
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import virasana.integracao.mercante.mercantealchemy as mercante

sys.path.append('.')

from bhadrasana.models import Setor, Usuario
from bhadrasana.models.ovr import metadata, Enumerado, create_tiposevento, create_tiposprocesso, create_flags, Flag, \
    Relatorio, create_tipomercadoria, create_marcas, Marca, ItemTG

from bhadrasana.models.ovrmanager import gera_eventoovr, \
    gera_processoovr, cadastra_tgovr, atribui_responsavel_ovr, get_setores_filhos_recursivo, get_tipos_evento, \
    get_tipos_processo, get_flags_choice, get_flags, get_ovr_container, \
    get_relatorios_choice, get_relatorio, executa_relatorio, get_setores, get_setores_cpf, get_setores_usuario, \
    inclui_flag_ovr, get_tiposmercadoria_choice, get_marcas_choice, lista_tgovr, get_tgovr, cadastra_itemtg, \
    lista_itemtg, get_itemtg, get_itemtg_numero, informa_lavratura_auto, get_marcas

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
create_tipomercadoria(session)
create_marcas(session)

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
        tgs = lista_tgovr(session, ovr.id)
        assert len(tgs) == 1
        assert tgs[0] == ovr.tgs[0]
        tg = get_tgovr(session, tgs[0].id)
        assert tg.descricao == tgs[0].descricao
        itemtg = cadastra_itemtg(session, {'tg_id': tg.id, 'descricao': 'testeitem', 'numero': 13})
        assert itemtg.descricao == 'testeitem'
        assert itemtg.tg_id == tg.id
        assert itemtg.numero == 13
        itens = lista_itemtg(session, tg.id)
        assert itens[0] == itemtg
        _itemtg = get_itemtg(session, itemtg.id)
        assert _itemtg == itemtg
        # assert _itemtg.id == itemtg.id
        assert _itemtg.descricao == itemtg.descricao
        assert _itemtg.numero == itemtg.numero
        _itemtg = get_itemtg_numero(session, tg, 13)
        assert _itemtg is not None
        assert isinstance(_itemtg, ItemTG)
        _itemtg = get_itemtg_numero(session, tg, 0)
        assert _itemtg is not None
        assert isinstance(_itemtg, ItemTG)



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

    def test_relatorios(self):
        ovr = self.create_OVR_valido()
        relatorio = Relatorio()
        relatorio.nome = 'teste1'
        relatorio.sql = 'SELECT * FROM ovr_ovrs where create_date' + \
                        ' BETWEEN :datainicio AND :datafim'
        relatorio2 = Relatorio()
        relatorio2.nome = 'teste2'
        relatorio2.sql = 'SELECT * FROM ovr_relatorios'
        session.add(relatorio)
        session.add(relatorio2)
        session.commit()
        relatorios = get_relatorios_choice(session)
        assert len(relatorios) == 2
        assert relatorios[0][1] == 'teste1'
        self.assert_choices(relatorios)
        relatorio1 = get_relatorio(session, 1)
        assert relatorio.nome == relatorio1.nome
        assert relatorio.sql == relatorio1.sql
        datainicio = datetime.now() - timedelta(days=1)
        datafim = datetime.now() + timedelta(days=1)
        result = executa_relatorio(session, '1', relatorio1, datainicio, datafim)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0

    def test_Setores_Usuarios(self):
        setorpai = Setor()
        setorpai.id = 11
        setorpai.nome = 'Pai de Todos'
        session.add(setorpai)
        setor1 = Setor()
        setor1.id = 12
        setor1.pai_id = 11
        setor1.nome = 'Filho 1'
        session.add(setor1)
        setor2 = Setor()
        setor2.id = 13
        setor2.pai_id = 11
        setor2.nome = 'Filho 2'
        session.add(setor2)
        usuario_setor = Usuario()
        usuario_setor.cpf = 'chefe'
        usuario_setor.nome = 'user_setorpai'
        usuario_setor.setor_id = setorpai.id
        session.add(usuario_setor)
        usuario_setor1 = Usuario()
        usuario_setor1.cpf = '1'
        usuario_setor1.nome = 'user_setor1'
        usuario_setor1.setor_id = setor1.id
        session.add(usuario_setor1)
        usuario_setor2 = Usuario()
        usuario_setor2.cpf = '2'
        usuario_setor2.nome = 'user_setor2'
        usuario_setor2.setor_id = setor2.id
        session.add(usuario_setor2)
        session.commit()
        setores = get_setores(session)
        assert isinstance(setores, list)
        setores = get_setores_cpf(session, '1')
        assert len(setores) == 1
        assert isinstance(setores[0], Setor)
        setores = get_setores_usuario(session, usuario_setor)
        assert len(setores) == 3
        assert isinstance(setores[0], Setor)

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

    def test_get_flags(self):
        ovr1 = self.create_OVR_valido()
        ovr2 = self.create_OVR_valido()
        flags = get_flags(session)
        inclui_flag_ovr(session, ovr1.id, flags[0].nome)
        inclui_flag_ovr(session, ovr2.id, flags[1].nome)
        inclui_flag_ovr(session, ovr2.id, flags[2].nome)
        session.refresh(ovr1)
        session.refresh(ovr2)
        assert len(ovr1.flags) == 1
        assert len(ovr2.flags) == 2
        assert ovr1.flags[0] == flags[0]
        assert ovr2.flags[0] == flags[1]
        assert ovr2.flags[1] == flags[2]

    def test_tipos_mercadoria(self):
        tiposmercadoria = get_tiposmercadoria_choice(session)
        self.assert_choices(tiposmercadoria)

    def test_marcas_choice(self):
        marcas = get_marcas_choice(session)
        self.assert_choices(marcas)

    def test_marcas(self):
        marcas = get_marcas(session)
        assert marcas is not None
        assert isinstance(marcas, list)
        assert len(marcas) > 0
        assert isinstance(marcas[0], Marca)

    def test_Lavratura(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        assert ovr.fase == 0
        usuario = self.create_usuario('123', 'user1')
        usuario2 = self.create_usuario('456', 'user2')
        ovr = informa_lavratura_auto(session, ovr.id, usuario.cpf)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario.cpf
        assert ovr.fase == 3
        eventos = ovr.historico
        assert len(eventos) == 1
        evento = eventos[0]
        assert evento.fase == 3
        assert evento.motivo == 'Ficha encerrada, auto lavrado'


if __name__ == '__main__':
    unittest.main()
