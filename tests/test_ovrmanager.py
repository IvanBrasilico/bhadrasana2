import unittest
import sys
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models.ovr import metadata, Usuario, OVR, TipoEventoOVR, Enumerado

from bhadrasana.models.ovrmanager import get_usuarios, cadastra_ovr, gera_eventoovr, get_ovr

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
        self.create_tipos_evento()
        params = {
            'motivo': 'teste',
            'tipoevento_id': 1
        }
        evento = gera_eventoovr(session, params)
        assert evento.motivo == params['motivo']
        assert evento.tipoevento_id == 1
        ovr_modificada = get_ovr(session, id=1)
        assert ovr_modificada.fase == evento.fase


    if __name__ == '__main__':
        unittest.main()
