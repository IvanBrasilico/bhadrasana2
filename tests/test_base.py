import sys
import unittest
from datetime import datetime

sys.path.append('.')

from bhadrasana.models import Usuario
from bhadrasana.models.ovr import OVR, Recinto
import virasana.integracao.mercante.mercantealchemy as mercante

from bhadrasana.models.ovrmanager import get_usuarios, cadastra_ovr, get_recintos


class BaseTestCase(unittest.TestCase):

    def setUp(self, session) -> None:
        self.session = session

    def debug(self) -> None:
        pass

    def create_usuario(self, cpf, nome):
        usuario = self.session.query(Usuario).filter(Usuario.cpf == cpf).one_or_none()
        if usuario:
            return usuario
        usuarios = get_usuarios(self.session)
        numeroatual = len(usuarios)
        usuario = Usuario()
        usuario.cpf = cpf
        usuario.nome = nome
        self.session.add(usuario)
        self.session.commit()
        usuarios = get_usuarios(self.session)
        assert usuarios[numeroatual][0] == usuario.cpf
        return usuario

    def create_recinto(self, nome):
        recintos = get_recintos(self.session)
        numeroatual = len(recintos)
        recinto = Recinto()
        recinto.nome = nome
        self.session.add(recinto)
        self.session.commit()
        recintos = get_recintos(self.session)
        assert recintos[numeroatual][1] == recinto.nome
        return recinto

    def create_usuario(self, cpf, nome):
        usuario = self.session.query(Usuario).filter(Usuario.cpf == cpf).one_or_none()
        if usuario:
            return usuario
        usuarios = get_usuarios(self.session)
        numeroatual = len(usuarios)
        usuario = Usuario()
        usuario.cpf = cpf
        usuario.nome = nome
        self.session.add(usuario)
        self.session.commit()
        usuarios = get_usuarios(self.session)
        assert usuarios[numeroatual][0] == usuario.cpf
        return usuario

    def create_recinto(self, nome):
        recinto = self.session.query(Recinto).filter(Recinto.nome == nome).one_or_none()
        if recinto:
            return recinto
        recintos = get_recintos(self.session)
        numeroatual = len(recintos)
        recinto = Recinto()
        recinto.nome = nome
        self.session.add(recinto)
        self.session.commit()
        recintos = get_recintos(self.session)
        assert recintos[numeroatual][1] == recinto.nome
        return recinto

    def create_OVR_valido(self, numeroCEmercante=None) -> OVR:
        params = {}
        # params['id'] = 0
        recinto = self.create_recinto('Teste OVR')
        usuario = self.create_usuario('123', 'user1')
        self.session.refresh(recinto)
        if numeroCEmercante:
            params['numeroCEmercante'] = numeroCEmercante
        else:
            params['numeroCEmercante'] = 11
        params['adata'] = '2020-01-01'
        params['ahora'] = '13:13'
        params['recinto_id'] = recinto.id
        params['user_name'] = usuario.cpf
        ovr = cadastra_ovr(self.session, params, '123')
        assert ovr.id is not None
        assert ovr.datahora == datetime(2020, 1, 1, 13, 13)
        assert ovr.recinto_id == recinto.id
        return ovr

    def create_OVR(self, params, user_name) -> OVR:
        ovr = cadastra_ovr(self.session, params, user_name)
        return ovr

    def create_OVRs_test_ovrs_container(self) -> OVR:
        ovr1 = self.create_OVR_valido('1234')
        ovr2 = self.create_OVR_valido('12345')
        item1 = mercante.Item()
        item1.numeroCEmercante = '1234'
        item1.codigoConteiner = '1'
        item2 = mercante.Item()
        item2.numeroCEmercante = '1234'
        item2.codigoConteiner = '2'
        item3 = mercante.Item()
        item3.numeroCEmercante = '12345'
        item3.codigoConteiner = '3'
        item4 = mercante.Item()
        item4.numeroCEmercante = 'non_ecsiste_ovr'
        item4.codigoConteiner = '4'
        self.session.add(item1)
        self.session.add(item2)
        self.session.add(item3)
        self.session.add(item4)
        self.session.commit()
        return ovr1, ovr2