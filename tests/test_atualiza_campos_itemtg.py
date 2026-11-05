"""Testes de atualiza_campos_itemtg (botão "atualizar" e Enter na tela de itens do TG)."""
import unittest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bhadrasana.models.ovr import metadata, TGOVR, ItemTG
from bhadrasana.models.ovrmanager import atualiza_campos_itemtg

engine = create_engine('sqlite://')
Session = sessionmaker(bind=engine)
session = Session()
metadata.create_all(engine)


class AtualizaCamposItemTGTestCase(unittest.TestCase):

    def setUp(self):
        self.tg = TGOVR()
        self.tg.numerolote = 'TESTE'
        self.tg.descricao = 'TG de teste'
        session.add(self.tg)
        session.commit()
        self.item = ItemTG()
        self.item.tg_id = self.tg.id
        self.item.numero = 1
        self.item.descricao = 'Caneta'
        self.item.qtde = Decimal('6000')
        self.item.valor = Decimal('0.20')
        self.item.unidadedemedida = 0
        session.add(self.item)
        session.commit()

    def test_valor_em_formato_brasileiro(self):
        atualiza_campos_itemtg(session, self.item.id, {'valor': 'R$ 1,10'})
        session.refresh(self.item)
        self.assertEqual(self.item.valor, Decimal('1.10'))
        self.assertEqual(self.item.descricao, 'Caneta')
        self.assertEqual(self.item.qtde, Decimal('6000'))

    def test_varios_campos_e_total_do_tg(self):
        atualiza_campos_itemtg(session, self.item.id,
                               {'descricao': ' Caneta azul ', 'qtde': '10',
                                'valor': '2,50', 'ncm': '96081000'})
        session.refresh(self.item)
        session.refresh(self.tg)
        self.assertEqual(self.item.descricao, 'Caneta azul')
        self.assertEqual(self.item.qtde, Decimal('10'))
        self.assertEqual(self.item.valor, Decimal('2.50'))
        self.assertEqual(self.item.ncm, '96081000')
        self.assertEqual(self.tg.qtde, Decimal('10'))
        self.assertEqual(self.tg.valor, Decimal('25.00'))

    def test_obrigatorio_em_branco_e_recusado(self):
        for campo in ('descricao', 'qtde', 'valor'):
            with self.assertRaises(ValueError, msg=campo):
                atualiza_campos_itemtg(session, self.item.id, {campo: '  '})
        session.refresh(self.item)
        self.assertEqual(self.item.valor, Decimal('0.20'))
        self.assertEqual(self.item.descricao, 'Caneta')

    def test_valor_invalido_nao_altera_nada(self):
        with self.assertRaises(ValueError):
            atualiza_campos_itemtg(session, self.item.id,
                                   {'descricao': 'Outra', 'valor': 'abc'})
        session.refresh(self.item)
        self.assertEqual(self.item.descricao, 'Caneta')
        self.assertEqual(self.item.valor, Decimal('0.20'))

    def test_ncm_em_branco_vira_nulo(self):
        atualiza_campos_itemtg(session, self.item.id, {'ncm': ''})
        session.refresh(self.item)
        self.assertIsNone(self.item.ncm)

    def test_campo_nao_editavel_e_item_inexistente(self):
        with self.assertRaises(KeyError):
            atualiza_campos_itemtg(session, self.item.id, {'tg_id': '999'})
        with self.assertRaises(KeyError):
            atualiza_campos_itemtg(session, 999999, {'valor': '1'})
        with self.assertRaises(KeyError):
            atualiza_campos_itemtg(session, None, {'valor': '1'})


if __name__ == '__main__':
    unittest.main()
