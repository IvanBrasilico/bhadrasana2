import sys
import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import virasana.integracao.mercante.mercantealchemy as mercante
from bhadrasana.models.rvf import RVF
from bhadrasana.models.rvfmanager import lista_rvfovr

sys.path.append('.')

from bhadrasana.models import Setor, Usuario, PerfilUsuario, perfilAcesso
from bhadrasana.models.ovr import metadata, Enumerado, create_tiposevento, create_tiposprocesso, create_flags, Flag, \
    Relatorio, create_tipomercadoria, create_marcas, Marca, ItemTG, VisualizacaoOVR, OVR, ProcessoOVR

from bhadrasana.models.ovrmanager import gera_eventoovr, \
    gera_processoovr, cadastra_tgovr, atribui_responsavel_ovr, get_setores_filhos_recursivo, get_tipos_evento, \
    get_tipos_processo, get_flags_choice, get_flags, get_ovr_container, \
    get_relatorios_choice, get_relatorio, executa_relatorio, get_setores_choice, get_setores_cpf, get_setores_usuario, \
    inclui_flag_ovr, get_tiposmercadoria_choice, get_marcas_choice, lista_tgovr, get_tgovr, cadastra_itemtg, \
    lista_itemtg, get_itemtg, get_itemtg_numero, informa_lavratura_auto, get_marcas, usuario_index, \
    cadastra_visualizacao, get_visualizacoes, get_ovr_filtro, cadastra_ovr, get_ovr_empresa, \
    get_ovrs_setor, exclui_item_tg, get_ovr_visao_usuario

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
mercante.metadata.create_all(engine, [
    mercante.metadata.tables['itensresumo'],
    mercante.metadata.tables['conhecimentosresumo']
])

create_tiposevento(session)
create_tiposprocesso(session)
create_flags(session)
create_tipomercadoria(session)
create_marcas(session)

from .test_base import BaseTestCase


class OVRTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    def test_OVR_Evento(self):
        ovr = self.create_OVR_valido()
        ovr.responsavel_cpf = 'user1'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        params = {
            'motivo': 'teste',
            'tipoevento_id': 1,
            'ovr_id': ovr.id
        }
        evento = gera_eventoovr(session, params, user_name='user1')
        assert evento.motivo == params['motivo']
        assert evento.tipoevento_id == 1
        assert ovr.fase == evento.fase
        params['tipoevento_id'] = 2
        evento2 = gera_eventoovr(session, params, user_name='user1')
        assert ovr.fase == evento2.fase
        session.refresh(ovr)
        assert len(ovr.historico) == 2

    """
    def test_OVR_Desfaz_1Evento(self):
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
        assert ovr.tipoevento_id == evento.tipoevento_id
        params['tipoevento_id'] = 2
        evento2 = gera_eventoovr(session, params)
        assert ovr.fase == evento2.fase
        assert ovr.tipoevento_id == evento2.tipoevento_id
        session.refresh(ovr)
        assert len(ovr.historico) == 2
        desfaz_ultimo_eventoovr(session, ovr.id)
        assert ovr.fase == evento.fase
        assert ovr.tipoevento_id == evento.tipoevento_id
        session.refresh(ovr)
        assert len(ovr.historico) == 1
        desfaz_ultimo_eventoovr(session, ovr.id)
        assert ovr.fase == 0
        assert ovr.tipoevento_id is None

    def test_OVR_Desfaz_2Eventos(self):
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
        assert ovr.tipoevento_id == evento.tipoevento_id
        desfaz_ultimo_eventoovr(session, ovr.id)
        assert ovr.fase == 0
        assert ovr.tipoevento_id is None
    """

    def test_OVR_Processo(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        atribui_responsavel_ovr(session, ovr.id, 'user_1', None)
        for tipo in Enumerado.tipoProcesso():
            params = {
                'numero': tipo[1],
                'tipoprocesso_id': tipo[0],
                'ovr_id': ovr.id,
                'user_name': 'user_1'

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
            'numerolote': 'CCNU1234567',
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
        itemtg = cadastra_itemtg(session, {'tg_id': tg.id,
                                           'descricao': 'testeitem',
                                           'numero': 13,
                                           'qtde': 10,
                                           'valor': 5})
        assert itemtg.descricao == 'testeitem'
        assert itemtg.tg_id == tg.id
        assert itemtg.numero == 13
        assert itemtg.qtde == 10
        assert itemtg.valor == 5
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
        assert tg.qtde == 10
        assert tg.valor == 50
        itemtg2 = cadastra_itemtg(session, {'tg_id': tg.id,
                                            'descricao': 'testeitem',
                                            'numero': 13,
                                            'qtde': 50,
                                            'valor': 2})
        assert tg.qtde == 60
        assert tg.valor == 150
        exclui_item_tg(session, tg.id, itemtg2.id)
        assert tg.qtde == 10
        exclui_item_tg(session, tg.id)
        assert tg.qtde is None

    def test_Responsavel(self):
        # Atribui responsável válido
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        assert ovr.responsavel_cpf is None
        assert ovr.fase == 0
        usuario = self.create_usuario('123', 'user1')
        usuario2 = self.create_usuario('456', 'user2')
        ovr = atribui_responsavel_ovr(session, ovr.id, usuario.cpf, None)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario.cpf
        assert ovr.fase == 1
        # Atribui outro responsável
        ovr = atribui_responsavel_ovr(session, ovr.id, usuario2.cpf, usuario.cpf)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario2.cpf
        eventos = ovr.historico
        assert len(eventos) == 2
        evento = eventos[0]
        assert evento.fase == 1
        assert evento.motivo == 'Anterior: Nenhum'
        evento = eventos[1]
        assert evento.fase == 1
        # assert evento.motivo == 'Anterior: ' + usuario.cpf
        assert ovr.fase == evento.fase
        assert ovr.tipoevento_id == evento.tipoevento_id
        with self.assertRaises(Exception):
            desfaz_ultimo_eventoovr(session, ovr.id)
        assert ovr.fase == evento.fase
        assert ovr.tipoevento_id == evento.tipoevento_id
        # testa usuario_index
        list_user = [usuario, usuario2]
        index = usuario_index(list_user, usuario.cpf)
        assert index is not None
        assert isinstance(index, int)

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
        result = executa_relatorio(session, relatorio1, datainicio, datafim, '1')
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
        setores = get_setores_choice(session)
        assert isinstance(setores, list)
        setores = get_setores_cpf(session, '1')
        assert len(setores) == 1
        assert isinstance(setores[0], Setor)
        usuario_vazio = get_setores_cpf(session, '123456')
        assert len(usuario_vazio) == 0
        assert isinstance(usuario_vazio, list)
        setores = get_setores_usuario(session, usuario_setor)
        assert len(setores) == 3
        assert isinstance(setores[0], Setor)

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
        datainicio = datetime(2020, 1, 1, 0, 0)
        datafim = datetime(2020, 7, 3, 0, 0)
        ces, ovrs = get_ovr_container(session, '1')
        assert len(ovrs) == 1
        assert ovr1 in ovrs
        ces, ovrs = get_ovr_container(session, '2', datainicio, datafim)
        assert len(ovrs) == 1
        assert ovr1 in ovrs
        ces, ovrs = get_ovr_container(session, '3', datainicio, datafim)
        assert len(ovrs) == 1
        assert ovr2 in ovrs
        ces, ovrs = get_ovr_container(session, '4', datainicio, datafim)
        assert len(ovrs) == 0

    def test_get_flags(self):
        ovr1 = self.create_OVR_valido()
        ovr2 = self.create_OVR_valido()
        ovr3 = self.create_OVR_valido()
        flags = get_flags(session)
        inclui_flag_ovr(session, ovr1.id, flags[0].nome, None)
        inclui_flag_ovr(session, ovr2.id, flags[1].nome, None)
        inclui_flag_ovr(session, ovr2.id, flags[2].nome, None)
        inclui_flag_ovr(session, ovr3.id, '', None)
        session.refresh(ovr1)
        session.refresh(ovr2)
        session.refresh(ovr3)
        assert len(ovr1.flags) == 1
        assert len(ovr2.flags) == 2
        assert len(ovr3.flags) == 0
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
        ovr = informa_lavratura_auto(session, ovr.id, usuario.cpf, None)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario.cpf
        assert ovr.fase == 3
        eventos = ovr.historico
        assert len(eventos) == 1
        evento = eventos[0]
        assert evento.fase == 3
        assert evento.motivo == 'Ficha encerrada, auto lavrado'

    def test_VisualizacaoOVR(self):
        ovr1 = self.create_OVR_valido()
        ovr2 = self.create_OVR_valido()
        ovr1.numero = 'teste1'
        ovr2.numero = 'teste2'
        session.add(ovr1)
        session.add(ovr2)
        session.commit()
        session.refresh(ovr1)
        session.refresh(ovr2)
        visualizacao1 = VisualizacaoOVR()
        visualizacao2 = VisualizacaoOVR()
        visualizacao1.ovr_id = ovr1.id
        visualizacao1.user_name = 'adriano'
        visualizacao2.ovr_id = ovr1.id
        visualizacao2.user_name = 'ivan'
        session.add(visualizacao1)
        session.add(visualizacao2)
        session.commit()
        visualizacao3 = cadastra_visualizacao(session, ovr2, 'ivan')
        visualizacoes_ovr1_user1 = get_visualizacoes(session, ovr1, 'adriano')
        assert isinstance(visualizacoes_ovr1_user1, list)
        assert len(visualizacoes_ovr1_user1) == 1
        visualizacoes_ovr1_user2 = get_visualizacoes(session, ovr1, 'ivan')
        assert isinstance(visualizacoes_ovr1_user2, list)
        assert len(visualizacoes_ovr1_user2) == 1
        visualizacoes_ovr2_user1 = get_visualizacoes(session, ovr2, 'adriano')
        assert isinstance(visualizacoes_ovr2_user1, list)
        assert len(visualizacoes_ovr2_user1) == 0
        visualizacoes_ovr2_user2 = get_visualizacoes(session, ovr2, 'ivan')
        assert isinstance(visualizacoes_ovr2_user2, list)
        assert len(visualizacoes_ovr2_user2) == 1

    def create_OVR_campos(self, nome_recinto, cpf_usuario, numeroCEmercante,
                          data_registro, numero, setor, numerodeclaracao=None) -> OVR:
        params = {}
        recinto = self.create_recinto(nome_recinto)
        usuario = self.create_usuario(cpf_usuario, cpf_usuario, setor)
        self.session.refresh(recinto)
        params['numeroCEmercante'] = numeroCEmercante
        params['adata'] = data_registro
        params['ahora'] = '00:00'
        params['recinto_id'] = recinto.id
        params['user_name'] = usuario.cpf
        params['numero'] = numero
        params['numerodeclaracao'] = numerodeclaracao
        return cadastra_ovr(self.session, params, usuario.cpf)

    def test_0_FiltrosOVR(self):
        setor = Setor()
        setor.id = 9991
        setor.nome = 'Setor 1'
        session.add(setor)
        setor2 = Setor()
        setor2.id = 9992
        setor2.nome = 'Setor 2'
        session.add(setor2)
        session.commit()
        ovr1 = self.create_OVR_campos('R1', 'U1', 'C1', '2020-05-01', 'teste1', setor)
        session.refresh(ovr1)
        ovr2 = self.create_OVR_campos('R2', 'U2', 'C2', '2020-05-02', 'teste2', setor2)
        ovr3 = self.create_OVR_campos('R3', 'U3', 'C3', '2020-05-03', 'teste3', setor)
        ovr4 = self.create_OVR_campos('R4', 'U4', 'C4', '2020-05-01', 'teste4', setor, '20')
        ovrs = get_ovr_filtro(session, {})
        assert isinstance(ovrs, list)
        assert len(ovrs) == 4
        ovrs = get_ovr_filtro(session, {'numero': 'teste1'})
        assert len(ovrs) == 1
        ovrs = get_ovr_filtro(session, {'numeroCEmercante': 'C2'}, 'U2')
        assert len(ovrs) == 1
        ovrs = get_ovr_filtro(session, {'numeroCEmercante': 'C2'}, 'U1')
        assert len(ovrs) == 0
        ovrs = get_ovr_filtro(session, {'numeroCEmercante': 'Non ecsiste'})
        assert len(ovrs) == 0
        ovrs = get_ovr_filtro(session, {'numero': 'teste4'})
        assert len(ovrs) == 1
        ovrs = get_ovr_filtro(session, {'numero': 'teste'})
        assert len(ovrs) == 4
        ovrs = get_ovr_filtro(session, {'numerodeclaracao': '10'})
        assert len(ovrs) == 0
        ovrs = get_ovr_filtro(session, {'numerodeclaracao': '20'})
        assert len(ovrs) == 1
        # Teste de pesquisa por numero processo
        ovrs = get_ovr_filtro(session, {'numeroprocesso': '12345'})
        assert len(ovrs) == 0
        processo = ProcessoOVR()
        processo.ovr_id = ovr1.id
        processo.numero = '12345'
        session.add(processo)
        ovrs = get_ovr_filtro(session, {'numeroprocesso': '12345'})
        assert len(ovrs) == 1
        # Teste de pesquisa por numeroCEmercante de RVF
        rvf = RVF()
        rvf.ovr_id = ovr1.id
        rvf.numeroCEmercante = 'C2'
        session.add(rvf)
        session.commit()
        ovrs = get_ovr_filtro(session, {'numeroCEmercante': 'C2'})
        rvfs = lista_rvfovr(session, ovr1.id)
        print(rvfs)
        print(ovr1.numeroCEmercante, ovr1.id)
        print(ovr2.numeroCEmercante)
        print(rvf.numeroCEmercante, rvf.ovr_id)
        assert len(ovrs) == 2

    def test_get_ovr_empresa(self):
        ovr = self.create_OVR_valido()
        ovr.cnpj_fiscalizado = '00.280.273/0002-18'
        session.add(ovr)
        session.commit()
        session.refresh(ovr)
        ovrs = get_ovr_empresa(session, '00.280.273')
        assert len(ovrs) == 1
        assert isinstance(ovrs, list)
        with self.assertRaises(ValueError):
            get_ovr_empresa(session, '00.280')

    def test_get_ovrs_setor(self):
        ovr1 = self.create_OVR_valido()
        ovr1.setor_id = 8001
        session.add(ovr1)
        ovr2 = self.create_OVR_valido()
        ovr2.setor_id = 8002
        session.add(ovr2)
        session.commit()
        setor = Setor()
        setor.id = 8001
        setor.nome = 'Setor Teste'
        session.add(setor)
        setor12 = Setor()
        setor12.id = 8002
        setor12.pai_id = 8001
        setor12.nome = 'Filho de Setor Teste'
        session.add(setor12)
        session.commit()
        ovrs = get_ovrs_setor(session, setor)
        assert len(ovrs) == 1
        assert isinstance(ovrs, list)

    def test_get_ovrs_visao_usuario(self):
        ovr1 = self.create_OVR_valido()
        ovr1.setor_id = '9001'
        ovr1.user_name = 'user1'
        session.add(ovr1)
        ovr2 = self.create_OVR_valido()
        ovr2.setor_id = '9002'
        ovr2.cpfauditorresponsavel = 'user1'
        session.add(ovr2)
        ovr3 = self.create_OVR_valido()
        ovr3.setor_id = '9002'
        ovr3.responsavel_cpf = 'user2'
        session.add(ovr3)
        ovr4 = self.create_OVR_valido()
        ovr4.setor_id = '9001'
        session.add(ovr4)
        session.commit()
        setor = Setor()
        setor.id = '9001'
        setor.nome = 'Setor Teste'
        session.add(setor)
        setor12 = Setor()
        setor12.id = '9002'
        setor12.pai_id = '9001'
        setor12.nome = 'Filho de Setor Teste'
        session.add(setor12)
        session.commit()
        ovrs = get_ovr_visao_usuario(session,
                                     datetime(2020, 1, 1),
                                     datetime(2020, 1, 2),
                                     'user1')
        # assert len(ovrs) == 2
        assert isinstance(ovrs, list)
        ovrs = get_ovr_visao_usuario(session,
                                     datetime(2020, 1, 1),
                                     datetime(2020, 1, 2),
                                     'user2')
        # assert len(ovrs) == 1
        assert isinstance(ovrs, list)
        ovrs = get_ovr_visao_usuario(session,
                                     datetime(2020, 1, 1),
                                     datetime(2020, 1, 2),
                                     'user2',
                                     '9001')
        # assert len(ovrs) == 1
        assert isinstance(ovrs, list)
        perfil = PerfilUsuario()
        perfil.cpf = 'user2'
        perfil.perfil = Enumerado.get_id(perfilAcesso, 'Supervisor')  # Supervisor
        session.add(perfil)
        session.commit()
        ovrs = get_ovr_visao_usuario(session,
                                     datetime(2020, 1, 1),
                                     datetime(2020, 1, 2),
                                     'user2',
                                     '9001')
        #assert len(ovrs) == 3
        assert isinstance(ovrs, list)


if __name__ == '__main__':
    unittest.main()
