import sys
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models import Usuario, Setor
from bhadrasana.models.ovr import metadata, OVR, TipoEventoOVR, Enumerado, Recinto

from bhadrasana.models.ovrmanager import get_usuarios, cadastra_ovr, gera_eventoovr, \
    gera_processoovr, cadastra_tgovr, atribui_responsavel_ovr, get_recintos, get_setores_filhos_recursivo

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)


class TestCase(unittest.TestCase):

    def setUp(self) -> None:
        pass

    def debug(self) -> None:
        pass

    def create_tipos_evento(self):
        for fase in Enumerado.faseOVR():
            tipo = TipoEventoOVR()
            tipo.id = fase[0]
            tipo.fase = fase[0]
            tipo.descricao = 'Fase %s' % fase[1]
            session.add(tipo)
        session.commit()

    def create_usuario(self, cpf, nome):
        usuario = session.query(Usuario).filter(Usuario.cpf == cpf).one_or_none()
        if usuario:
            return usuario
        usuarios = get_usuarios(session)
        numeroatual = len(usuarios)
        usuario = Usuario()
        usuario.cpf = cpf
        usuario.nome = nome
        session.add(usuario)
        session.commit()
        usuarios = get_usuarios(session)
        assert usuarios[numeroatual][0] == usuario.cpf
        return usuario

    def create_recinto(self, nome):
        recintos = get_recintos(session)
        numeroatual = len(recintos)
        recinto = Recinto()
        recinto.nome = nome
        session.add(recinto)
        session.commit()
        recintos = get_recintos(session)
        assert recintos[numeroatual][1] == recinto.nome
        return recinto

    def create_OVR_valido(self) -> OVR:
        params = {}
        # params['id'] = 0
        recinto = self.create_recinto('Teste OVR')
        usuario = self.create_usuario('123', 'user1')
        session.refresh(recinto)
        params['fase'] = 0
        params['numero'] = 1
        params['numeroCEmercante'] = 11
        params['adata'] = '2020-01-01'
        params['ahora'] = '13:13'
        params['recinto_id'] = recinto.id
        params['user_name'] = usuario.cpf
        ovr = cadastra_ovr(session, params, '123')
        assert ovr.id is not None
        assert ovr.datahora == datetime(2020, 1, 1, 13, 13)
        assert ovr.recinto_id == recinto.id
        return ovr

    def test_OVR_Evento(self):
        ovr = self.create_OVR_valido()
        session.refresh(ovr)
        self.create_tipos_evento()
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
        tgovr = cadastra_tgovr(session, params)
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
        ovr = atribui_responsavel_ovr(session, ovr.id, usuario.cpf, 1)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario.cpf
        assert ovr.fase == 1
        # Atribui outro responsável
        ovr = atribui_responsavel_ovr(session, ovr.id, usuario2.cpf, 1)
        session.refresh(ovr)
        assert ovr.responsavel_cpf == usuario2.cpf
        eventos = ovr.historico
        assert len(eventos) == 2
        evento = eventos[0]
        assert evento.fase == 1
        assert evento.motivo == usuario.cpf

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


if __name__ == '__main__':
    unittest.main()
