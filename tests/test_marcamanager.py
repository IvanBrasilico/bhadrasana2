import sys
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append('.')

from bhadrasana.models.ovr import metadata, create_marcas, RepresentanteMarca, Marca, Representacao, TipoEventoOVR, \
    TiposEventoAssistente, Assistente
from bhadrasana.models.ovrmanager import MarcaManager, get_tiposevento_assistente, get_tiposevento_assistente_choice
from bhadrasana.models.rvf import RVF

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)
create_marcas(session)


def create_representacoes(session):
    representante1 = RepresentanteMarca()
    representante1.cnpj = '1'
    representante1.nome = 'Adidas_Burberry'
    session.add(representante1)
    representante2 = RepresentanteMarca()
    representante2.cnpj = '2'
    representante2.nome = 'Apple_Disney'
    session.add(representante2)
    session.commit()
    session.refresh(representante1)
    session.refresh(representante2)
    adidas = session.query(Marca).filter(Marca.nome == 'Adidas').one()
    burberry = session.query(Marca).filter(Marca.nome == 'Burberry').one()
    apple = session.query(Marca).filter(Marca.nome == 'Apple').one()
    disney = session.query(Marca).filter(Marca.nome == 'Disney').one()
    representacoes_tuplas = (
        (adidas, representante1),
        (burberry, representante1),
        (apple, representante2),
        (disney, representante2)
    )
    for tupla in representacoes_tuplas:
        representacao = Representacao()
        representacao.marca_id = tupla[0].id
        representacao.representante_id = tupla[1].id
        representacao.inicio = datetime.today()
        session.add(representacao)
    session.commit()


create_representacoes(session)

from tests.test_base import BaseTestCase




class OVRTestCase(BaseTestCase):

    def setUp(self) -> None:
        super().setUp(session)

    def debug(self) -> None:
        pass

    def test_MarcaManager_cria(self):
        marca_manager = MarcaManager(self.session)
        assert marca_manager is not None
        assert marca_manager.session is not None

    def test_MarcaManager_cria(self):
        marca_manager = MarcaManager(self.session)
        assert marca_manager is not None
        assert marca_manager.session is not None

    def test_marcas_choice(self):
        manager = MarcaManager(self.session)
        marcas = manager.get_marcas_choice()
        self.assert_choices(marcas)

    def test_marcas(self):
        marcas = MarcaManager(self.session).get_marcas()
        assert marcas is not None
        assert isinstance(marcas, list)
        assert len(marcas) > 0
        assert isinstance(marcas[0], Marca)

    def test_representacoes(self):
        marcas = MarcaManager(self.session).get_marcas_ativas_representante('1')
        assert marcas is not None
        assert isinstance(marcas, list)
        assert len(marcas) == 2
        assert isinstance(marcas[0], Marca)
        marcas_nome = [marca.nome for marca in marcas]
        assert 'Adidas' in marcas_nome
        assert 'Burberry' in marcas_nome
        assert 'Apple' not in marcas_nome
        marcas = MarcaManager(self.session).get_marcas_ativas_representante('2')
        assert marcas is not None
        assert len(marcas) == 2
        assert isinstance(marcas[0], Marca)
        marcas_nome = [marca.nome for marca in marcas]
        assert 'Adidas' not in marcas_nome
        assert 'Apple' in marcas_nome
        assert 'Disney' in marcas_nome

    def test_representacoes_marcas_rvf(self):
        adidas = session.query(Marca).filter(Marca.nome == 'Adidas').one()
        burberry = session.query(Marca).filter(Marca.nome == 'Burberry').one()
        apple = session.query(Marca).filter(Marca.nome == 'Apple').one()
        rvf = RVF()
        rvf.numeroCEmercante = '1'
        rvf.marcasencontradas.append(adidas)
        rvf.marcasencontradas.append(burberry)
        rvf.marcasencontradas.append(apple)
        session.add(rvf)
        session.commit()
        session.refresh(rvf)
        representante1 = session.query(RepresentanteMarca). \
            filter(RepresentanteMarca.id == '1').one()
        representante2 = session.query(RepresentanteMarca). \
            filter(RepresentanteMarca.id == '2').one()
        marcas = MarcaManager(self.session).get_marcas_rvf_por_representante(rvf.id)
        assert marcas is not None
        assert isinstance(marcas, dict)
        print(marcas)
        marcas1 = marcas[representante1]
        assert len(marcas1) == 2
        marcas_nome = [marca.nome for marca in marcas1]
        assert 'Adidas' in marcas_nome
        assert 'Burberry' in marcas_nome
        assert 'Apple' not in marcas_nome
        marcas2 = marcas[representante2]
        assert len(marcas2) == 1
        marcas_nome = [marca.nome for marca in marcas2]
        assert 'Adidas' not in marcas_nome
        assert 'Burberry' not in marcas_nome
        assert 'Apple' in marcas_nome
        assert 'Disney' not in marcas_nome


    def test_tiposeventos_marcas(self):
        manager = MarcaManager(self.session)
        tipoevento1 = TipoEventoOVR()
        tipoevento1.nome = 'Pedir Laudo de Marca'
        tipoevento2 = TipoEventoOVR()
        tipoevento2.nome = 'Laudo de Marca recebido'
        self.session.add(tipoevento1, tipoevento2)
        self.session.commit()
        tiposeventos_assistente = get_tiposevento_assistente(self.session, Assistente.Marcas)
        assert len(tiposeventos_assistente) == 0
        tea1 = TiposEventoAssistente()
        tea1.assistente = Assistente.Marcas.value
        tea1.tipoevento = tipoevento1
        self.session.add(tea1)
        self.session.commit()
        tiposeventos_assistente = get_tiposevento_assistente(self.session, Assistente.Marcas)
        assert len(tiposeventos_assistente) == 1
        tea2 = TiposEventoAssistente()
        tea2.assistente = Assistente.Marcas.value
        tea2.tipoevento = tipoevento2
        self.session.add(tea2)
        self.session.commit()
        tiposeventos_assistente = get_tiposevento_assistente_choice(self.session, Assistente.Marcas)
        assert len(tiposeventos_assistente) == 2





if __name__ == '__main__':
    unittest.main()
