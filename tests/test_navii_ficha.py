"""Testes ADVERSARIAIS da abertura de Ficha pelo NAVI-I (bhadrasana/models/navii_ficha.py).

Banco SQLite em memória com o catálogo de eventos padrão do Fichas (`create_tiposevento`) mais os eventos comuns de
produção usados na abertura ("Bloqueio de CE incluído", "Verificação Física Agendada") e um parecido que NÃO pode ser
escolhido ("Bloqueio de CE atualizado"); GridFS do Fichas simulado (mongomock).
"""
import sys
import unittest
from datetime import datetime
from unittest import mock

import mongomock
from gridfs import GridFS
from mongomock.gridfs import enable_gridfs_integration
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models import ENaoAutorizado, ESomenteUsuarioResponsavel, Setor, Usuario  # noqa: E402
from bhadrasana.models import navii_ficha as nf  # noqa: E402
from bhadrasana.models.ovr import (  # noqa: E402
    EventoOVR, Flag, OVR, Recinto, TipoEventoOVR, create_tiposevento,
)
from bhadrasana.models.rvf import ImagemRVF, RVF, metadata  # noqa: E402

enable_gridfs_integration()
AGORA = datetime(2026, 10, 17, 10, 0)
CE, CE2 = '152600000000001', '152600000000002'
ANALISTA, OUTRO, SEM_CADASTRO = '11111111111', '22222222222', '99999999999'
IMAGEM = b'\xff\xd8 imagem de escaneamento'


def dados(conteiner='ABCU1234567', ce=CE, **campos):
    padrao = dict(resumo_risco='Risco histórico ALTO: importador X', descricao_carga='Carga declarada: notebooks',
                  memoria_risco='Memória de cálculo completa', imagens=[(IMAGEM, 'img.jpg')],
                  recinto_siscomex='8931356', cnpj_consignatario='11.222.333/0001-81')
    return nf.DadosFicha(numeroCEmercante=ce, conteiner=conteiner, **{**padrao, **campos})


class NaviiFichaTestCase(unittest.TestCase):

    def setUp(self):
        engine = create_engine('sqlite://')
        metadata.create_all(engine)
        self.session = sessionmaker(bind=engine)()
        create_tiposevento(self.session)
        for nome, fase in (('Bloqueio de CE incluído', 1), ('Bloqueio de CE atualizado', 1),
                           ('Verificação Física Agendada', 2)):
            tipo = TipoEventoOVR()
            tipo.nome, tipo.fase = nome, fase
            self.session.add(tipo)
        setor = Setor()
        setor.id, setor.nome = '2', 'EQRIMP'
        self.session.add(setor)
        for cpf in (ANALISTA, OUTRO):
            usuario = Usuario()
            usuario.cpf, usuario.nome, usuario.setor_id = cpf, f'Usuário {cpf[:2]}', '2'
            self.session.add(usuario)
        recinto = Recinto()
        recinto.nome, recinto.cod_siscomex = 'BTP', '8931356'
        self.session.add(recinto)
        self.session.commit()
        self.mongo = mongomock.MongoClient()['risco']
        self.fs = GridFS(self.mongo)

    def tearDown(self):
        self.session.close()

    def abre(self, cpf=ANALISTA, **campos):
        return nf.abre_ficha_navii(self.session, self.mongo, cpf, dados(**campos), agora=AGORA)

    def eventos(self, ovr_id):
        return [e.tipoevento.nome for e in self.session.query(EventoOVR).filter(EventoOVR.ovr_id == ovr_id)
                .order_by(EventoOVR.create_date, EventoOVR.id)]

    def arquivos(self):
        return list(self.mongo['fs.files'].find())


class TestAbertura(NaviiFichaTestCase):

    def test_nova_ficha_completa(self):
        r = self.abre(imagens=[(IMAGEM + bytes([i]), f'img{i}.jpg') for i in range(6)])
        self.assertEqual((r.acao, r.imagens), ('nova', nf.MAX_IMAGENS))   # 6 dadas, 4 gravadas
        ovr = self.session.query(OVR).one()
        self.assertEqual((ovr.tipooperacao, ovr.numeroCEmercante, ovr.setor_id, ovr.responsavel_cpf, ovr.user_name),
                         (1, CE, '2', ANALISTA, ANALISTA))
        self.assertEqual(ovr.cnpj_fiscalizado, '11222333000181')
        self.assertEqual(ovr.recinto.cod_siscomex, '8931356')
        self.assertTrue(ovr.observacoes.startswith('[NAVI-I] Risco histórico ALTO'))
        self.assertEqual([f.nome for f in ovr.flags], ['NAVI-I'])
        rvf = self.session.query(RVF).one()
        self.assertEqual((rvf.ovr_id, rvf.numerolote, rvf.numeroCEmercante, rvf.inspecaonaoinvasiva, rvf.user_name),
                         (ovr.id, 'ABCU1234567', CE, True, ANALISTA))
        self.assertEqual((rvf.descricao, rvf.descricao_interna),
                         ('Carga declarada: notebooks', 'Memória de cálculo completa'))
        self.assertEqual([i.ordem for i in rvf.imagens], [1, 2, 3, 4])
        arquivos = self.arquivos()
        self.assertEqual(len(arquivos), 4)
        self.assertEqual({a['metadata']['rvf_id'] for a in arquivos}, {str(rvf.id)})
        self.assertEqual({str(a['_id']) for a in arquivos}, {i.imagem for i in rvf.imagens})
        self.assertEqual(self.eventos(ovr.id), ['Atribuição de responsável', 'Inspeção não invasiva'])
        self.assertEqual(ovr.fase, 1)

    def test_eventos_opcionais_por_nome_exato(self):
        r = self.abre(bloqueio_incluido=True, verificacao_agendada=True)
        self.assertEqual(self.eventos(r.ovr_id), ['Atribuição de responsável', 'Inspeção não invasiva',
                                                  'Bloqueio de CE incluído', 'Verificação Física Agendada'])
        ovr = self.session.get(OVR, r.ovr_id)
        self.assertEqual((ovr.fase, ovr.tipoevento.nome), (2, 'Verificação Física Agendada'))   # o último manda

    def test_opcionais_ausentes_do_catalogo_sao_ignorados(self):
        for nome in ('Bloqueio de CE incluído', 'Verificação Física Agendada'):
            self.session.query(TipoEventoOVR).filter(TipoEventoOVR.nome == nome).delete()
        self.session.commit()
        self.assertEqual(nf.previa(self.session, ANALISTA, CE, 'X')['opcoes'], {'bloqueio': False, 'agendada': False})
        r = self.abre(bloqueio_incluido=True, verificacao_agendada=True)
        self.assertEqual(self.eventos(r.ovr_id), ['Atribuição de responsável', 'Inspeção não invasiva'])

    def test_clique_duplo_nao_duplica_nada(self):
        primeira = self.abre()
        segunda = self.abre(conteiner='abcu 123456-7')               # o mesmo, digitado de outro jeito
        self.assertEqual((segunda.acao, segunda.ovr_id, segunda.rvf_id), ('ja_existia', primeira.ovr_id,
                                                                         primeira.rvf_id))
        self.assertEqual((self.session.query(OVR).count(), self.session.query(RVF).count(),
                          self.session.query(EventoOVR).count(), len(self.arquivos())), (1, 1, 2, 1))

    def test_outro_conteiner_do_ce_entra_na_ficha_aberta(self):
        primeira = self.abre()
        observacoes = self.session.get(OVR, primeira.ovr_id).observacoes
        segunda = self.abre(conteiner='MSCU7654321', resumo_risco='outro texto')
        self.assertEqual((segunda.acao, segunda.ovr_id), ('acrescentada', primeira.ovr_id))
        ovr = self.session.get(OVR, primeira.ovr_id)
        self.assertEqual(ovr.observacoes, observacoes)               # não mexe nas observações da Ficha
        self.assertEqual(sorted(r.numerolote for r in ovr.rvfs), ['ABCU1234567', 'MSCU7654321'])
        self.assertEqual(self.eventos(ovr.id), ['Atribuição de responsável', 'Inspeção não invasiva',
                                                'Inspeção não invasiva'])
        self.assertEqual(self.session.query(Flag).filter(Flag.nome == 'NAVI-I').count(), 1)

    def test_ficha_aberta_com_outro_responsavel_nao_recebe_nada(self):
        primeira = self.abre()
        # recusa ANTES de gravar qualquer imagem no GridFS (não grava e apaga à toa)
        with mock.patch.object(GridFS, 'put', side_effect=AssertionError('gravou imagem')):
            with self.assertRaises(ESomenteUsuarioResponsavel):
                self.abre(cpf=OUTRO, conteiner='MSCU7654321')
        self.assertEqual((self.session.query(RVF).count(), len(self.arquivos())), (1, 1))
        previa = nf.previa(self.session, OUTRO, CE, 'MSCU7654321')
        self.assertEqual((previa['acao'], previa['ficha']['id']), ('acrescentar', primeira.ovr_id))
        self.assertIn('outro responsável', previa['impedimento'])

    def test_ficha_encerrada_ou_de_outro_tipo_nao_e_reaproveitada(self):
        for tipo, fase in ((1, 4), (0, 1)):                          # repressão arquivada; FMA aberta
            ovr = OVR()
            ovr.tipooperacao, ovr.numeroCEmercante, ovr.fase = tipo, CE, fase
            self.session.add(ovr)
        self.session.commit()
        previa = nf.previa(self.session, ANALISTA, CE, 'ABCU1234567')
        self.assertEqual((previa['acao'], len(previa['outras'])), ('nova', 2))
        r = self.abre()
        self.assertEqual(r.acao, 'nova')
        self.assertEqual(self.session.query(OVR).filter(OVR.tipooperacao == 1).count(), 2)

    def test_usuario_nao_habilitado(self):
        with self.assertRaises(ENaoAutorizado):
            self.abre(cpf=SEM_CADASTRO)
        self.assertIn('não está habilitado', nf.previa(self.session, SEM_CADASTRO, CE, 'X')['impedimento'])
        self.assertEqual(self.session.query(OVR).count(), 0)

    def test_falha_no_meio_desfaz_banco_e_imagens(self):
        self.session.query(TipoEventoOVR).filter(
            TipoEventoOVR.eventoespecial == nf.EventoEspecial.InspecaoNaoInvasiva.value).delete()
        self.session.commit()
        with self.assertRaises(nf.EFichaNavii):
            self.abre()
        self.assertEqual((self.session.query(OVR).count(), self.session.query(RVF).count(),
                          self.session.query(ImagemRVF).count(), self.session.query(EventoOVR).count()),
                         (0, 0, 0, 0))
        self.assertEqual(self.arquivos(), [])                        # a imagem gravada no GridFS foi apagada

    def test_resumo_limitado_e_selo_sem_repetir(self):
        r = self.abre(resumo_risco='x' * 900)
        observacoes = self.session.get(OVR, r.ovr_id).observacoes
        self.assertEqual(len(observacoes), nf.TAMANHO_RESUMO)
        self.assertTrue(observacoes.startswith('[NAVI-I] xxx') and observacoes.endswith('…'))
        r2 = self.abre(ce=CE2, resumo_risco='[NAVI-I]   já   com selo')
        self.assertEqual(self.session.get(OVR, r2.ovr_id).observacoes, '[NAVI-I] já com selo')

    def test_mesma_imagem_em_duas_rvfs_sao_arquivos_separados(self):
        """O Fichas apaga o arquivo do GridFS ao excluir a imagem: compartilhado, sumiria das duas RVFs."""
        r1 = self.abre()
        r2 = self.abre(ce=CE2)
        imagens = [self.session.query(ImagemRVF).filter(ImagemRVF.rvf_id == r.rvf_id).one().imagem for r in (r1, r2)]
        self.assertNotEqual(imagens[0], imagens[1])
        self.assertEqual(len(self.arquivos()), 2)

    def test_flag_navii_unica(self):
        r1, r2 = self.abre(), self.abre(ce=CE2)
        flags = self.session.query(Flag).filter(Flag.nome == 'NAVI-I').all()
        self.assertEqual(len(flags), 1)
        self.assertEqual([f.id for r in (r1, r2) for f in self.session.get(OVR, r.ovr_id).flags], [flags[0].id] * 2)

    def test_dados_obrigatorios(self):
        for ce, conteiner in (('', 'ABCU1234567'), (CE, ''), (CE, ' - ')):
            with self.assertRaises(nf.EFichaNavii):
                nf.abre_ficha_navii(self.session, self.mongo, ANALISTA, nf.DadosFicha(ce, conteiner), agora=AGORA)


class TestPrevia(NaviiFichaTestCase):

    def test_acoes(self):
        self.assertEqual(nf.previa(self.session, ANALISTA, CE, 'ABCU1234567')['acao'], 'nova')
        self.abre()
        self.assertEqual(nf.previa(self.session, ANALISTA, CE, 'ABCU 123456-7')['acao'], 'ja_existe')
        previa = nf.previa(self.session, ANALISTA, CE, 'MSCU7654321')
        self.assertEqual((previa['acao'], previa['impedimento'], previa['opcoes']),
                         ('acrescentar', None, {'bloqueio': True, 'agendada': True}))
        self.assertEqual(previa['ficha']['responsavel'], 'Usuário 11')


if __name__ == '__main__':
    unittest.main()
