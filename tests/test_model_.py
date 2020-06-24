import sys
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models import Base, Usuario, Setor, PerfilUsuario, perfilAcesso, \
    get_perfisusuario, Enumerado, usuario_tem_perfil

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)


class ModelTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.session = session

    def create_usuario(self, cpf, nome, telegram=''):
        usuario = self.session.query(Usuario).filter(Usuario.cpf == cpf).one_or_none()
        if usuario:
            return usuario
        usuario = Usuario()
        usuario.cpf = cpf
        usuario.nome = nome
        usuario.telegram = telegram
        self.session.add(usuario)
        self.session.commit()
        self.session.refresh(usuario)
        return usuario

    def create_setor(self, id, nome, pai_id=None):
        setor = self.session.query(Setor).filter(Setor.id == id).one_or_none()
        if setor:
            return setor
        setor = Setor()
        setor.id = id
        setor.nome = nome
        if pai_id:
            setor.pai_id = pai_id
        self.session.add(setor)
        self.session.commit()
        self.session.refresh(setor)
        return setor

    def test_Usuario(self):
        usuario = self.create_usuario('111', 'ivan', 'ivan_bot')
        assert usuario.telegram == 'ivan_bot'
        assert usuario.nome == 'ivan'

    def test_Setor(self):
        setor = self.create_setor('001', 'Setor 1')
        assert setor.nome == 'Setor 1'
        assert setor.id == '001'

    def create_estrutura(self):
        self.setor1 = self.create_setor('0001', 'Setor 1')
        self.setor11 = self.create_setor('0011', 'Setor 1.1')
        self.setor11.pai_id = self.setor1.id
        self.session.add(self.setor11)
        self.session.commit()
        self.setor2 = self.create_setor('002', 'Setor 2')
        self.supervisor1 = self.create_usuario('001', 'Supervisor1')
        self.supervisor1.setor_id = self.setor1.id
        self.supervisor2 = self.create_usuario('002', 'Supervisor2')
        self.supervisor2.setor_id = self.setor2.id
        self.session.add(self.supervisor1)
        self.session.add(self.supervisor2)
        self.session.commit()
        self.membros1 = []
        for r in range(3):
            usuario = self.create_usuario('001%s' % r, 'teste%s' % r)
            usuario.setor_id = self.setor11.id
            self.membros1.append(usuario)
            self.session.add(usuario)
        self.session.commit()

    def test_Lotacao(self):
        self.create_estrutura()
        assert self.supervisor1.setor_id == self.setor1.id
        assert self.supervisor2.setor_id == self.setor2.id
        assert self.membros1[0].setor_id == self.setor11.id

    def test_Perfis(self):
        self.create_estrutura()
        perfil = PerfilUsuario()
        perfil.cpf = self.supervisor1.cpf
        perfil.perfil = Enumerado.get_id(perfilAcesso, 'Supervisor')
        self.session.add(perfil)
        self.session.commit()
        perfis = get_perfisusuario(self.session, self.supervisor1.cpf)
        assert len(perfis) == 1
        assert perfis[0].perfil == Enumerado.get_id(perfilAcesso, 'Supervisor')
        assert Enumerado.get_tipo(perfilAcesso, perfis[0].perfil) == 'Supervisor'
        assert usuario_tem_perfil(self.session,
                                  self.supervisor1.cpf,
                                  Enumerado.get_id(perfilAcesso, 'Supervisor')) is True
        assert usuario_tem_perfil(self.session,
                                  self.supervisor1.cpf,
                                  Enumerado.get_id(perfilAcesso, 'Cadastrador')) is False
