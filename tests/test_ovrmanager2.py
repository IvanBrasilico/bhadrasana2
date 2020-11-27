import sys
from time import strftime

sys.path.append('.')
sys.path.append('../virasana')
sys.path.append('../bhadrasana')
sys.path.append('../ajna_docs/commons')

import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import virasana.integracao.mercante.mercantealchemy as mercante
from bhadrasana.models.rvf import RVF
from bhadrasana.models.rvfmanager import lista_rvfovr

from bhadrasana.models import Setor, Usuario, PerfilUsuario, perfilAcesso, gera_objeto, delete_objeto, \
    get_usuario_validando, ESomenteUsuarioResponsavel
from bhadrasana.models.ovr import metadata, Enumerado, create_tiposevento, create_tiposprocesso, create_flags, Flag, \
    Relatorio, create_tipomercadoria, create_marcas, Marca, ItemTG, VisualizacaoOVR, OVR, ProcessoOVR, Recinto, \
    EventoOVR

from bhadrasana.models.ovrmanager import gera_eventoovr, \
    gera_processoovr, cadastra_tgovr, atribui_responsavel_ovr, get_setores_filhos_recursivo, get_tipos_evento, \
    get_tipos_processo, get_flags_choice, get_flags, get_ovr_container, \
    get_relatorios_choice, get_relatorio, executa_relatorio, get_setores_choice, get_setores_cpf, get_setores_usuario, \
    inclui_flag_ovr, get_tiposmercadoria_choice, get_marcas_choice, lista_tgovr, get_tgovr, cadastra_itemtg, \
    lista_itemtg, get_itemtg, get_itemtg_numero, informa_lavratura_auto, get_marcas, usuario_index, \
    cadastra_visualizacao, get_visualizacoes, get_ovr_filtro, cadastra_ovr, get_ovr_empresa, \
    get_ovrs_setor, exclui_item_tg, get_ovr_visao_usuario, excluir_evento, get_recintos_dte, get_recintos, \
    get_tipos_evento_todos, get_tipos_evento_comfase_choice, get_ovr_one, get_ovr, get_ovr_responsavel, \
    get_ovr_responsavel_setores, get_ovr_auditor, get_ovr_passagem, get_ovr_criadaspor, get_ovr_conhecimento, \
    get_ovr_due, exclui_flag_ovr, muda_setor_ovr, get_setores, valida_mesmo_responsavel_ovr_user_name, \
    valida_mesmo_responsavel_user_name, valida_mesmo_responsavel, get_processo, excluir_processo

from typing import List, Tuple

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

    params_setor = {'id': 1, 'nome': 'setor1', 'pai_id': 2}

    params_usuario = {'cpf': '92368425187', 'nome': 'Tibério', 'password': 'senha', 'telegram': None, 'setor_id': '1'}

    params_ovr = {'id': 1, 'numero': '1020304050', 'ano': '2020', 'tipooperacao': 0,
                  'numeroCEmercante': '999999999999999', 'numerodeclaracao': '55555555555555555555',
                  'observacoes': '', 'datahora': datetime.now(), 'dataentrada': datetime.now().date(), 'fase': 0,
                  'tipoevento_id': 1, 'recinto_id': 1, 'setor_id': '1', 'responsavel_cpf': '92368425187',
                  'last_modified': datetime.now(), 'cnpj_fiscalizado': '999988887777666', 'cpfauditorresponsavel': None}

    params_tgovr = {'ovr_id': int, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                    'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                    'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}

    params_processo = {'ovr_id': int, 'tipoprocesso_id': 1, 'numero': '9999888877', 'numerolimpo': '9999888877'}

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    # Testes criados por Tibério
    def test01_get_recintos(self):
        params = {'id': 1, 'nome': 'recinto1', 'descricao': '', 'cod_dte': None, 'cod_siscomex': None,
                  'cod_unidade': None, 'cod_carga': None, 'create_date': datetime.now()}
        recinto = gera_objeto(Recinto(), session=session, params=params)
        recintos = get_recintos(session)
        self.assert_choices(recintos)
        session.delete(recinto)
        session.commit()
        assert len(get_recintos(session)) == 0

    def test02_get_recintos_dte(self):
        params = {'id': 1, 'nome': 'recinto1', 'descricao': '', 'cod_dte': 1, 'cod_siscomex': None,
                  'cod_unidade': None, 'cod_carga': None, 'create_date': datetime.now()}
        recinto = gera_objeto(Recinto(), session=session, params=params)
        recintos_dte = get_recintos_dte(session)
        self.assert_choices(recintos_dte)
        session.delete(recinto)
        session.commit()
        assert len(get_recintos_dte(session)) == 0

    def test03_get_tipos_evento(self):
        tipos_evento = get_tipos_evento(session)
        self.assert_choices(tipos_evento)

    def test04_get_tipos_evento_todos(self):
        tipos_evento = get_tipos_evento_todos(session)
        self.assert_choices(tipos_evento)

    def test05_get_tipos_evento_comfase_choice(self):
        tipos_evento = get_tipos_evento_comfase_choice(session)
        self.assert_choices(tipos_evento)

    def test06_get_tipos_processo(self):
        tipos_processo = get_tipos_processo(session)
        self.assert_choices(tipos_processo)

    def test07_get_relatorios_choice(self):
        relatorio1 = Relatorio()
        relatorio1.nome = 'Relatório 1'
        session.add(relatorio1)
        session.commit()
        relatorios = get_relatorios_choice(session)
        self.assert_choices(relatorios)

    def test08_get_relatorio(self):
        relatorio2 = Relatorio()
        relatorio2.nome = 'Relatório 2'
        session.add(relatorio2)
        session.commit()
        relatorio = get_relatorio(session, relatorio_id=relatorio2.id)
        assert relatorio is not None

    def test09_executa_relatorio(self):
        relatorio3 = Relatorio()
        relatorio3.nome = 'Relatório 3'
        relatorio3.sql = 'SELECT * FROM ovr_relatorios'
        session.add(relatorio3)
        session.commit()
        datainicio = datetime.now().date()
        datafim = datainicio
        relatorio = executa_relatorio(session, relatorio3, datainicio, datafim)
        assert relatorio is not None

    def test10_cadastra_ovr(self):
        user_name = '92368425187'
        usuario = Usuario(cpf='92368425187', nome='Tibério', setor_id='1')
        session.add(usuario)
        session.commit()
        ovr_cadastrada = cadastra_ovr(session, params=self.params_ovr, user_name=user_name)
        assert ovr_cadastrada is not None
        session.delete(ovr_cadastrada)
        session.commit()

    # Verifica se já existe uma OVR e a retorna. Caso contrário cria uma OVR nova
    def test11_get_ovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        ovr = get_ovr(session, new_ovr.id)
        assert ovr is not None
        session.delete(ovr)
        session.commit()

    def test12_get_ovr_one(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        ovr = get_ovr_one(session, new_ovr.id)
        assert ovr.id == 1
        session.delete(new_ovr)
        session.commit()

    # Verifica a existência de uma OVR
    def test13_get_ovr_responsavel(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        ovr_responsavel = get_ovr_responsavel(session, new_ovr.responsavel_cpf)
        assert ovr_responsavel is not None
        session.delete(new_ovr)
        session.commit()

    # Testa OVR que estão com responsável e sem responsável nos setores
    def test14_get_ovr_responsavel_setores(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        setor1 = gera_objeto(Setor(), session=session, params=self.params_setor)
        setor2 = gera_objeto(Setor(), session=session, params={'id': 2, 'nome': 'Setor2'})
        setores = [setor1, setor2]
        ovr_responsavel_setores = get_ovr_responsavel_setores(session, new_ovr.responsavel_cpf, setores)
        assert ovr_responsavel_setores is not None
        session.delete(new_ovr)
        session.delete(setor1)
        session.delete(setor2)
        session.commit()

    # Testa OVR que estão com responsável e sem responsável nos setores
    def test15_get_ovr_auditor(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        ovr_auditor = get_ovr_auditor(session, new_ovr.responsavel_cpf)
        assert len(ovr_auditor) == 0
        session.delete(new_ovr)
        session.commit()

    def test16_get_ovr_passagem(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        ovr_passagem = get_ovr_passagem(session=session, user_name=new_ovr.responsavel_cpf, datainicio=new_ovr.datahora,
                                        datafim=datetime.now())
        assert len(ovr_passagem) == 0
        session.delete(new_ovr)
        session.commit()

    def test17_get_ovr_criadaspor(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        ovr_criadaspor = get_ovr_criadaspor(session=session, user_name=new_ovr.responsavel_cpf, datainicio=new_ovr.datahora,
                                        datafim=datetime.now())
        assert len(ovr_criadaspor) == 1
        session.delete(new_ovr)
        session.commit()

    def test18_get_ovr_visao_usuario(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        ovr_visao_usuario = get_ovr_visao_usuario(session=session, datainicio=new_ovr.datahora, datafim=datetime.now(),
                                                  usuario_cpf=new_ovr.responsavel_cpf)
        assert len(ovr_visao_usuario) == 1
        session.delete(new_ovr)
        session.commit()

    def test19_calcula_tempos_por_fase(self):
        pass

    def test20_get_ovr_conhecimento(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        ovr_conhecimento = get_ovr_conhecimento(session=session, numero=new_ovr.numeroCEmercante)
        assert len(ovr_conhecimento) is not None
        session.delete(new_ovr)
        session.commit()

    def test21_get_ovr_due(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        ovr_due = get_ovr_due(session=session, numero=new_ovr.numerodeclaracao)
        assert len(ovr_due) is not None
        session.delete(new_ovr)
        session.commit()

    def test21_get_ovr_filtro(self):
        pass

    def test22_get_ovr_container(self):  # Incompleto
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        ovr_container = get_ovr_container(session=session, numerolote='CCNU7654321', datainicio=new_ovr.datahora,
                                          datafim=datetime.now())
        assert len(ovr_container) is not None
        session.delete(new_ovr)
        session.commit()

    def test23_get_ovr_empresa(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        ovr_empresa = get_ovr_empresa(session=session, cnpj=new_ovr.cnpj_fiscalizado, datainicio=new_ovr.datahora)
        assert len(ovr_empresa) == 1
        session.delete(new_ovr)
        session.commit()

    def test24_get_flags(self):
        flags = get_flags(session=session)
        assert len(flags) > 0

    def test25_get_flags_choice(self):
        flags_choice = get_flags_choice(session=session)
        self.assert_choices(flags_choice)

    def test26_inclui_flag_ovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        new_flag_ovr = inclui_flag_ovr(session=session, ovr_id=new_ovr.id, flag_nome='Perecível',
                                   user_name=new_ovr.responsavel_cpf)
        assert len(new_flag_ovr) == 1
        session.delete(new_ovr)
        session.commit()

    def test27_exclui_flag_ovr(self):
        flag1 = Flag(id=8, nome='Perecível')
        flag2 = Flag(id=9, nome='Alto valor agregado')
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        new_ovr.flags = [flag1, flag2]
        flag_ovr = exclui_flag_ovr(session=session, ovr_id=new_ovr.id, flag_id=new_ovr.flags[0].id)
        assert len(flag_ovr) == 1
        session.delete(new_ovr)
        session.commit()

    def test28_gerencia_flag_ovr(self):
        pass # Função testada pelos testes 26 e 27. Elaborar novos testes

    def test29_atribui_responsavel_ovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel = '68068220291'
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=responsavel,
                                                  user_name=new_ovr.user_name)
        assert new_ovr.responsavel_cpf == '68068220291'
        session.delete(new_ovr)
        session.commit()

    def test30_muda_setor_ovr(self):
        setor1 = Setor(id='1', nome='Setor 1', cod_unidade='1', pai_id='1')
        setor2 = Setor(id='2', nome='Setor 2', cod_unidade='2', pai_id='1')
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        new_ovr.setor = setor1
        new_setor_ovr = muda_setor_ovr(session=session, ovr_id=new_ovr.id, setor_id=setor2.id,
                                       user_name=new_ovr.user_name)
        assert new_ovr.setor_id == '2'
        session.delete(new_ovr)
        session.commit()

    def test31_informa_lavratura_auto(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        responsavel = '68068220291'
        lavratura_auto = informa_lavratura_auto(session=session, ovr_id=new_ovr.id, responsavel=responsavel,
                                                  user_name=new_ovr.user_name)
        assert new_ovr.responsavel_cpf == '68068220291'
        session.delete(new_ovr)
        session.commit()

    def test32_gera_eventoovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        session.delete(new_ovr)
        session.commit()
        pass

    def test33_valida_mesmo_responsavel_ovr_user_name(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        try:
            valida = valida_mesmo_responsavel_ovr_user_name(session=session, ovr=new_ovr,
                                                            user_name=new_ovr.responsavel_cpf)
        except ESomenteUsuarioResponsavel:
            self.assertRaises(valida)
        assert valida is None
        session.delete(new_ovr)
        session.commit()

    def test34_valida_mesmo_responsavel_user_name(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        valida = valida_mesmo_responsavel_user_name(session=session, ovr_id=new_ovr.id,
                                                            user_name=new_ovr.responsavel_cpf)
        assert valida is None
        session.delete(new_ovr)
        session.commit()

    def test35_valida_mesmo_responsavel(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        valida = valida_mesmo_responsavel(session=session,
                                          params={'ovr_id': new_ovr.id, 'user_name': new_ovr.responsavel_cpf})
        assert valida is None
        session.delete(new_ovr)
        session.commit()

    def test36_mesmo_responsavel(self):
        pass

    def test37_gera_processoovr(self):
        pass

    def test38_get_processo(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        new_processo = ProcessoOVR(id=1, ovr_id=new_ovr.id, ovr=new_ovr, tipoprocesso_id=1, numero='9999888877',
                                    numerolimpo='9999888877')
        processo = get_processo(session=session, processo_id=new_processo.id)
        assert processo is not None
        session.delete(new_ovr)
        session.commit()

    def test39_excluir_processo(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        new_processo = ProcessoOVR(id=2, ovr_id=new_ovr.id, ovr=new_ovr, tipoprocesso_id=1, numero='9999888877',
                                   numerolimpo='9999888877')
        new_processo.user_name = new_ovr.user_name
        session.add(new_processo)
        session.commit()
        exclui_processo = excluir_processo(session=session, processo=new_processo, user_cpf=new_ovr.responsavel_cpf)
        assert not new_ovr.processos
        session.delete(new_ovr)
        session.commit()

    def test40_excluir_evento(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel = '68068220291'
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=responsavel,
                                                  user_name=new_ovr.user_name)
        new_evento = EventoOVR(id=9, ovr_id=new_ovr.id, ovr=new_ovr, tipoevento_id=2, fase=1,
                                motivo='um motivo', excluido=False, meramente_informativo=False)
        new_evento.user_name = responsavel
        session.add(new_evento)
        session.commit()
        exclui_evento = excluir_evento(session=session, evento_id=new_evento.id, user_cpf=new_evento.user_name)
        assert new_ovr.tipoevento_id == 13
        session.delete(new_ovr)
        session.commit()