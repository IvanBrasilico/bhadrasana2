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
    EventoOVR, TGOVR, RoteiroOperacaoOVR, TipoMercadoria

from bhadrasana.models.ovrmanager import gera_eventoovr, \
    gera_processoovr, cadastra_tgovr, atribui_responsavel_ovr, get_setores_filhos_recursivo, get_tipos_evento, \
    get_tipos_processo, get_flags_choice, get_flags, get_ovr_container, \
    get_relatorios_choice, get_relatorio, executa_relatorio, get_setores_choice, get_setores_cpf, get_setores_usuario, \
    inclui_flag_ovr, get_tiposmercadoria_choice, get_marcas_choice, lista_tgovr, get_tgovr, cadastra_itemtg, \
    lista_itemtg, get_itemtg, get_itemtg_numero, informa_lavratura_auto, get_marcas, \
    cadastra_visualizacao, get_visualizacoes, get_ovr_filtro, cadastra_ovr, get_ovr_empresa, \
    get_ovrs_setor, exclui_item_tg, get_ovr_visao_usuario, excluir_evento, get_recintos_dte, get_recintos, \
    get_tipos_evento_todos, get_tipos_evento_comfase_choice, get_ovr_one, get_ovr, get_ovr_responsavel, \
    get_ovr_responsavel_setores, get_ovr_auditor, get_ovr_passagem, get_ovr_criadaspor, get_ovr_conhecimento, \
    get_ovr_due, exclui_flag_ovr, muda_setor_ovr, get_setores, valida_mesmo_responsavel_ovr_user_name, \
    valida_mesmo_responsavel_user_name, valida_mesmo_responsavel, get_processo, excluir_processo, \
    atualiza_valortotal_tg, get_tgovr_one, valida_novo_itemtg, get_itemtg_descricao_qtde_modelo, get_usuarios, \
    valida_lista_setores, get_usuarios_setores_choice, get_afrfb_setores, get_afrfb, get_afrfb_choice, usuario_index, \
    get_setores_filhos_id, get_setores_filhos, get_setores_filhos_recursivo_id, get_setores_unidade, \
    get_setores_unidade_choice, get_setores_cpf_choice, get_roteirosoperacao, get_delta_date

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
    params_setor = {'id': '1', 'nome': 'setor1', 'pai_id': '2', 'cod_unidade': 'ALF/STS'}

    params_usuario = {'cpf': '92368425187', 'nome': 'Tibério', 'password': 'senha', 'telegram': None, 'setor_id': '1',
                      'cargo': 0}
    new_usuario = gera_objeto(Usuario(), session=session, params=params_usuario)

    params_ovr = {'id': 1, 'numero': '1020304050', 'ano': '2020', 'tipooperacao': 0,
                  'numeroCEmercante': '999999999999999', 'numerodeclaracao': '55555555555555555555',
                  'observacoes': '', 'datahora': datetime.now(), 'dataentrada': datetime.now().date(), 'fase': 0,
                  'tipoevento_id': 1, 'recinto_id': 1, 'setor_id': '1', 'responsavel_cpf': '',
                  'last_modified': datetime.now(), 'cnpj_fiscalizado': '999988887777666', 'cpfauditorresponsavel': None}

    params_tgovr = {'id': 1, 'ovr_id': int, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
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
        session.delete(relatorio1)
        session.commit()

    def test08_get_relatorio(self):
        relatorio2 = Relatorio()
        relatorio2.nome = 'Relatório 2'
        session.add(relatorio2)
        session.commit()
        relatorio = get_relatorio(session, relatorio_id=relatorio2.id)
        assert relatorio is not None
        session.delete(relatorio2)
        session.commit()

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
        session.delete(relatorio3)
        session.commit()

    def test10_cadastra_ovr(self):
        ovr_cadastrada = cadastra_ovr(session, params=self.params_ovr, user_name=self.new_usuario.cpf)
        assert ovr_cadastrada is not None
        session.delete(ovr_cadastrada)
        session.commit()

    # Verifica se já existe uma OVR e a retorna. Caso contrário cria uma OVR nova
    def test11_get_ovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        ovr = get_ovr(session, new_ovr.id)
        assert ovr is not None
        session.delete(new_ovr)
        session.commit()

    def test12_get_ovr_one(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        ovr = get_ovr_one(session, new_ovr.id)
        assert ovr.id == 1
        session.delete(new_ovr)
        session.commit()

    # Verifica a existência de uma OVR com responsável atribuído
    def test13_get_ovr_responsavel(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
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
        ovr_criadaspor = get_ovr_criadaspor(session=session, user_name=new_ovr.responsavel_cpf,
                                            datainicio=new_ovr.datahora,
                                            datafim=datetime.now())
        assert len(ovr_criadaspor) == 1
        session.delete(new_ovr)
        session.commit()

    def test18_get_ovr_visao_usuario(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
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
        pass  # Função testada pelos testes 26 e 27. Elaborar novos testes

    def test29_atribui_responsavel_ovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel = '68068220291'
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=responsavel,
                                                  user_name=new_ovr.user_name)
        assert new_ovr.responsavel_cpf == '68068220291'
        session.delete(new_ovr)
        session.commit()

    def test30_muda_setor_ovr(self):
        setor1 = Setor(id='1', nome='Setor 1', cod_unidade='ALF/STS', pai_id='2')
        setor2 = Setor(id='2', nome='Setor 2', cod_unidade='ALF/STS', pai_id='2')
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        new_ovr.user_name = new_ovr.responsavel_cpf
        new_ovr.setor = setor1
        new_setor_ovr = muda_setor_ovr(session=session, ovr_id=new_ovr.id, setor_id=setor2.id,
                                       user_name=self.new_usuario.cpf)
        assert new_ovr.setor_id == '2'
        session.delete(new_ovr)
        session.delete(new_setor_ovr)
        session.delete(setor1)
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

    def test41_cadastra_tgovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        assert tgovr_cadastrado is not None
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.commit()

    def test42_lista_tgovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321',
                            'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        tgs = lista_tgovr(session=session, ovr_id=1)
        assert len(tgs) == 1
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.commit()

    def test43_atualiza_valortotal_tg(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg_cadastrado = cadastra_itemtg(session=session, params=new_item_tg_params)
        tg_atualizado = atualiza_valortotal_tg(session=session, tg_id=tgovr_cadastrado.id)
        assert tgovr_cadastrado.qtde == 5
        assert tgovr_cadastrado.valor == 2500
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg_cadastrado)
        session.commit()

    def test44_get_tgovr_one(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        tgovr = get_tgovr_one(session=session, tg_id=tgovr_cadastrado.id)
        assert tgovr is not None
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.commit()

    def test45_get_tgovr(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        tgovr = get_tgovr(session=session, tg_id=tgovr_cadastrado.id)
        assert tgovr is not None
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.commit()

    def test46_valida_novo_itemtg(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg_cadastrado = cadastra_itemtg(session=session, params=new_item_tg_params)
        item_tg_valido = valida_novo_itemtg(params=new_item_tg_params)
        assert len(item_tg_valido) == 0
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg_cadastrado)
        session.commit()

    def test47_cadastra_itemtg(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg_cadastrado = cadastra_itemtg(session=session, params=new_item_tg_params)
        assert item_tg_cadastrado is not None
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg_cadastrado)
        session.commit()

    def test48_lista_itemtg(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg_cadastrado = cadastra_itemtg(session=session, params=new_item_tg_params)
        itenstg = lista_itemtg(session=session, tg_id=tgovr_cadastrado.id)
        assert itenstg is not None
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg_cadastrado)
        session.commit()

    def test49_get_itemtg(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg_cadastrado = cadastra_itemtg(session=session, params=new_item_tg_params)
        itemtg = get_itemtg(session=session, itemid=item_tg_cadastrado.id)
        assert itemtg is not None
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg_cadastrado)
        session.commit()

    def test50_get_itemtg_numero(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg_cadastrado = cadastra_itemtg(session=session, params=new_item_tg_params)
        itemtg = get_itemtg_numero(session=session, tg=tgovr_cadastrado, numero=item_tg_cadastrado.numero)
        assert itemtg is not None
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg_cadastrado)
        session.commit()

    def test51_get_itemtg_descricao_qtde_modelo(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg_cadastrado = cadastra_itemtg(session=session, params=new_item_tg_params)
        itemtg = get_itemtg_descricao_qtde_modelo(session=session, tg=tgovr_cadastrado, descricao='outro item tg',
                                                  qtde='5', modelo='Shocks')
        assert itemtg is not None
        assert itemtg.numero == 2
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg_cadastrado)
        session.commit()

    def test52_exclui_item_tg(self):
        new_ovr = gera_objeto(OVR(), session=session, params=self.params_ovr)
        responsavel_ovr = atribui_responsavel_ovr(session=session, ovr_id=new_ovr.id, responsavel=self.new_usuario.cpf,
                                                  user_name=None)
        new_tgovr_params = {'ovr_id': new_ovr.id, 'numerolote': 'CCNU7654321', 'descricao': 'Uma descrição qualquer',
                            'unidadedemedida': 1, 'qtde': 10, 'valor': 20, 'tipomercadoria_id': 1, 'numerotg': '12345',
                            'afrfb': None, 'identificacao': None, 'observacoes': 'Uma observação qualquer'}
        tgovr_cadastrado = cadastra_tgovr(session=session, params=new_tgovr_params, user_name=self.new_usuario.cpf)
        new_item_tg_params = {'tg_id': tgovr_cadastrado.id, 'numero': 2, 'descricao': 'outro item tg',
                              'contramarca': 'Nike', 'modelo': 'Shocks', 'qtde': 5, 'unidadedemedida': 1, 'valor': 500,
                              'ncm': 'NCMnumber', 'marca_id': 1}
        item_tg = cadastra_itemtg(session=session, params=new_item_tg_params)
        item_tg_excluido = exclui_item_tg(session=session, tg_id=tgovr_cadastrado.id, itemtg_id=item_tg.id)
        assert len(item_tg_excluido) == 0
        session.delete(new_ovr)
        session.delete(tgovr_cadastrado)
        session.delete(item_tg)
        session.commit()

    def test53_get_usuarios(self):
        usuarios = get_usuarios(session=session)
        assert usuarios is not None

    def test54_valida_lista_setores(self):
        setor1 = Setor(id='1', nome='Setor 1', cod_unidade='ALF/STS', pai_id='1')
        setores = [setor1]
        lista_setores = valida_lista_setores(setores)
        assert len(lista_setores) == 1

    def test55_get_usuarios_setores_choice(self):
        setor1 = Setor(id='1', nome='Setor 1', cod_unidade='ALF/STS', pai_id='1')
        setores = [setor1]
        usuarios_setores = get_usuarios_setores_choice(session=session, setores=setores)
        assert len(usuarios_setores) == 1

    def test56_get_afrfb_setores(self):
        setor1 = Setor(id='1', nome='Setor 1', cod_unidade='ALF/STS', pai_id='1')
        setores = [setor1]
        afrfb_setores = get_afrfb_setores(session=session, setores=setores)
        assert len(afrfb_setores) == 1

    def test57_get_afrfb(self):
        setor1 = gera_objeto(Setor(), session=session, params=self.params_setor)
        setores = [setor1]
        afrfb = get_afrfb(session=session, cod_unidade=setor1.cod_unidade)
        assert len(afrfb) == 1
        session.delete(setor1)
        session.commit()

    def test58_get_afrfb_choice(self):
        setor1 = gera_objeto(Setor(), session=session, params=self.params_setor)
        setores = [setor1]
        afrfb = get_afrfb_choice(session=session, cod_unidade=setor1.cod_unidade)
        assert len(afrfb) == 1
        session.delete(setor1)
        session.commit()

    def test59_get_afrfb_setores_choice(self):
        setor1 = gera_objeto(Setor(), session=session, params=self.params_setor)
        setores = [setor1]
        afrfb = get_afrfb_choice(session=session, cod_unidade=setor1.cod_unidade)
        assert len(afrfb) == 1
        session.delete(setor1)
        session.commit()

    def test60_usuario_index(self):
        usuarios = [self.new_usuario]
        index_usuario = usuario_index(usuarios, pcpf=self.new_usuario.cpf)
        assert index_usuario == 0

    def test61_get_setores_filhos_id(self):
        setor1 = gera_objeto(Setor(), session=session, params=self.params_setor)
        setores_filhos_id = get_setores_filhos_id(session=session, setor_id=setor1.pai_id)
        assert len(setores_filhos_id) == 1
        session.delete(setor1)
        session.commit()

    def test62_get_setores_filhos(self):
        setor_pai = Setor(id='2', nome='Setor Pai', cod_unidade='ALF/STS', pai_id='1')
        setor_filho1 = Setor(id='3', nome='Setor filho1', cod_unidade='DIREP', pai_id='2')
        session.add(setor_pai)
        session.add(setor_filho1)
        setores_filhos = get_setores_filhos(session=session, setor=setor_pai)
        assert len(setores_filhos) == 1
        session.delete(setor_pai)
        session.delete(setor_filho1)
        session.commit()

    def test63_get_setores_filhos_recursivo_id(self):
        setor_avo = Setor(id='1', nome='Setor Avô', cod_unidade='SRRF08', pai_id='')
        setor_pai = Setor(id='2', nome='Setor Pai', cod_unidade='ALF/STS', pai_id='1')
        setor_filho1 = Setor(id='3', nome='Setor filho1', cod_unidade='DIREP', pai_id='2')
        setor_filho2 = Setor(id='4', nome='Setor filho2', cod_unidade='DITEC', pai_id='2')
        setores_filhos_recursivo = get_setores_filhos_recursivo_id(session=session, setor_id=setor_filho1.pai_id)
        pass

    def test64_get_setores(self):
        setor_avo = Setor(id='10', nome='Setor Avô', cod_unidade='SRRF08', pai_id='')
        setor_pai = Setor(id='20', nome='Setor Pai', cod_unidade='ALF/STS', pai_id='1')
        setor_filho1 = Setor(id='30', nome='Setor filho1', cod_unidade='DIREP', pai_id='2')
        setor_filho2 = Setor(id='40', nome='Setor filho2', cod_unidade='DITEC', pai_id='2')
        session.add(setor_avo)
        session.add(setor_pai)
        session.add(setor_filho1)
        session.add(setor_filho2)
        setores = get_setores(session=session)
        assert len(setores) == 4
        session.delete(setor_avo)
        session.delete(setor_pai)
        session.delete(setor_filho1)
        session.delete(setor_filho2)
        session.commit()

    def test65_get_setores_unidade(self):
        setor_avo = Setor(id='10', nome='Setor Avô', cod_unidade='SRRF08', pai_id='')
        setor_pai = Setor(id='20', nome='Setor Pai', cod_unidade='SRRF08', pai_id='1')
        setor_filho1 = Setor(id='30', nome='Setor filho1', cod_unidade='SRRF08', pai_id='2')
        setor_filho2 = Setor(id='40', nome='Setor filho2', cod_unidade='SRRF08', pai_id='2')
        session.add(setor_avo)
        session.add(setor_pai)
        session.add(setor_filho1)
        session.add(setor_filho2)
        setores_unidade = get_setores_unidade(session=session, cod_unidade=setor_avo.cod_unidade)
        assert len(setores_unidade) == 4
        session.delete(setor_avo)
        session.delete(setor_pai)
        session.delete(setor_filho1)
        session.delete(setor_filho2)
        session.commit()

    def test66_get_setores_choice(self):
        setor_avo = Setor(id='10', nome='Setor Avô', cod_unidade='SRRF08', pai_id='')
        setor_pai = Setor(id='20', nome='Setor Pai', cod_unidade='SRRF08', pai_id='1')
        setor_filho1 = Setor(id='30', nome='Setor filho1', cod_unidade='SRRF08', pai_id='2')
        setor_filho2 = Setor(id='40', nome='Setor filho2', cod_unidade='SRRF08', pai_id='2')
        session.add(setor_avo)
        session.add(setor_pai)
        session.add(setor_filho1)
        session.add(setor_filho2)
        setores_choice = get_setores_choice(session=session)
        assert len(setores_choice) == 4
        session.delete(setor_avo)
        session.delete(setor_pai)
        session.delete(setor_filho1)
        session.delete(setor_filho2)
        session.commit()

    def test67_get_setores_unidade_choice(self):
        setor_avo = Setor(id='10', nome='Setor Avô', cod_unidade='SRRF08', pai_id='')
        setor_pai = Setor(id='20', nome='Setor Pai', cod_unidade='SRRF08', pai_id='1')
        setor_filho1 = Setor(id='30', nome='Setor filho1', cod_unidade='SRRF08', pai_id='2')
        setor_filho2 = Setor(id='40', nome='Setor filho2', cod_unidade='SRRF08', pai_id='2')
        session.add(setor_avo)
        session.add(setor_pai)
        session.add(setor_filho1)
        session.add(setor_filho2)
        setores_unidade_choice = get_setores_unidade_choice(session=session, cod_unidade=setor_avo.cod_unidade)
        assert len(setores_unidade_choice) == 4
        session.delete(setor_avo)
        session.delete(setor_pai)
        session.delete(setor_filho1)
        session.delete(setor_filho2)
        session.commit()

    def test68_get_setores_usuario(self):
        setor1 = self.create_setor('1', 'Setor 1')
        usuario = self.create_usuario('68068220291', 'Juliana', setor1)
        setores_usuario = get_setores_usuario(session=session, usuario=usuario)
        assert len(setores_usuario) == 1
        session.delete(setor1)
        session.delete(usuario)
        session.commit()

    def test69_get_setores_cpf(self):
        setor1 = self.create_setor('1', 'Setor 1')
        usuario = self.create_usuario('68068220291', 'Juliana', setor1)
        setores_cpf = get_setores_cpf(session=session, cpf_usuario=usuario.cpf)
        assert len(setores_cpf) == 1
        session.delete(setor1)
        session.delete(usuario)
        session.commit()

    def test70_get_setores_cpf_choice(self):
        setor1 = self.create_setor('1', 'Setor 1')
        usuario = self.create_usuario('68068220291', 'Juliana', setor1)
        setores_cpf_choice = get_setores_cpf_choice(session=session, cpf_usuario=usuario.cpf)
        assert len(setores_cpf_choice) == 1
        session.delete(setor1)
        session.delete(usuario)
        session.commit()

    def test71_get_ovrs_setor(self):
        setor_avo = Setor(id='10', nome='Setor Avô', cod_unidade='SRRF08', pai_id='')
        setor_pai = Setor(id='20', nome='Setor Pai', cod_unidade='SRRF08', pai_id='10')
        setor_filho1 = Setor(id='30', nome='Setor filho1', cod_unidade='SRRF08', pai_id='20')
        setor_filho2 = Setor(id='40', nome='Setor filho2', cod_unidade='SRRF08', pai_id='20')
        session.add(setor_avo)
        session.add(setor_pai)
        session.add(setor_filho1)
        session.add(setor_filho2)
        new_ovr = OVR(id=1, numero='1020304050', ano='2020', tipooperacao=0,
                      numeroCEmercante='999999999999999', numerodeclaracao='55555555555555555555',
                      observacoes='', datahora=datetime.now(), dataentrada=datetime.now().date(), fase=0,
                      tipoevento_id=1, recinto_id=1, setor_id='30', setor=setor_filho1, responsavel_cpf='',
                      last_modified=datetime.now(), cnpj_fiscalizado='999988887777666', cpfauditorresponsavel=None)
        session.add(new_ovr)
        ovrs_setor = get_ovrs_setor(session=session, setor=setor_pai)
        assert len(ovrs_setor) == 1
        session.delete(setor_avo)
        session.delete(setor_pai)
        session.delete(setor_filho1)
        session.delete(setor_filho2)
        session.commit()

    def test72_get_marcas(self):
        # Já existem 6 marcas criadas anteriormente
        marca10 = Marca(id=10, nome='Marca 10')
        session.add(marca10)
        marcas = get_marcas(session=session)
        assert len(marcas) == 7
        session.delete(marca10)
        session.commit()

    def test73_get_marcas_choice(self):
        # Já existem 6 marcas criadas anteriormente
        marcas_choice = get_marcas_choice(session=session)
        self.assert_choices(marcas_choice)

    def test74_get_roteirosoperacao(self):
        new_roteiro = RoteiroOperacaoOVR(id=1, tipooperacao=0, tipoevento_id=1, descricao='Uma descrição', ordem=1,
                                         quem='Não sei')
        session.add(new_roteiro)
        roteirosoperacao = get_roteirosoperacao(session=session, tipooperacao=new_roteiro.tipooperacao)
        assert len(roteirosoperacao) == 1
        session.delete(new_roteiro)
        session.commit()

    def test75_get_itens_roteiro_checked(self):
        new_roteiro = RoteiroOperacaoOVR(id=1, tipooperacao=0, tipoevento_id=1, descricao='Uma descrição', ordem=1,
                                         quem='Não sei')
        session.add(new_roteiro)
        pass

    def test76_get_tiposmercadoria_choice(self):
        # Já existem 20 tipos de mercadoria cadastrados
        new_mercadoria = TipoMercadoria(id=21, nome='Mercadoria nova')
        session.add(new_mercadoria)
        tiposmercadoria = get_tiposmercadoria_choice(session=session)
        assert len(tiposmercadoria) == 21
        session.delete(new_mercadoria)
        session.commit()

    def test77_procura_chave_lower(self):
        pass

    def test78_muda_chaves(self):
        pass

    def test79_importa_planilha_tg(self):
        pass

    def test80_exporta_planilha_tg(self):
        pass

    def test81_exporta_planilhaovr(self):
        pass

    def test82_cadastra_visualizacao(self):
        pass

    def test83_get_visualizacoes(self):
        pass

    def test84_get_delta_date(self):
        delta_date = get_delta_date(start=datetime(2020, 12, 29), end=datetime(2020, 12, 31))
        assert delta_date == 2

