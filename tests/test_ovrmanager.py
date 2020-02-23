import unittest
import sys
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models.ovr import metadata, Usuario, OVR, TipoEventoOVR, Enumerado

from bhadrasana.models.ovrmanager import get_usuarios, cadastra_ovr, gera_eventoovr, get_ovr, gera_processoovr, \
    cadastra_tgovr

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

    def create_OVR_valido(self) -> OVR:
        params = {}
        # params['id'] = 0
        params['fase'] = 0
        params['numero'] = 1
        params['numeroCEmercante'] = 11
        params['adata'] = '2020-01-01'
        params['ahora'] = '13:13'
        ovr = cadastra_ovr(session, params)
        assert ovr.id is not None
        assert ovr.datahora == datetime(2020, 1, 1, 13, 13)
        return ovr

    def test_usuarios(self):
        usuarios = get_usuarios(session)
        assert usuarios == []
        usuario = Usuario()
        usuario.cpf = '1'
        session.add(usuario)
        session.commit()
        usuarios = get_usuarios(session)
        assert usuarios[0][0] == usuario.cpf

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

    if __name__ == '__main__':
        unittest.main()
