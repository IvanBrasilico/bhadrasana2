"""Testes de normaliza_valor_br (valor digitado no registro de resultado da Ficha)."""
import unittest
from decimal import Decimal

from bhadrasana.models.ovrmanager import normaliza_valor_br


class NormalizaValorBRTestCase(unittest.TestCase):

    def test_formato_brasileiro(self):
        for texto in ('26.663,49', '26663,49', 'R$ 26.663,49', ' R$26.663,49 '):
            self.assertEqual(normaliza_valor_br(texto), Decimal('26663.49'), texto)
        self.assertEqual(normaliza_valor_br('1.234.567,8'), Decimal('1234567.8'))
        self.assertEqual(normaliza_valor_br('0,5'), Decimal('0.5'))

    def test_formato_ingles(self):
        self.assertEqual(normaliza_valor_br('26663.49'), Decimal('26663.49'))
        self.assertEqual(normaliza_valor_br('26,663.49'), Decimal('26663.49'))

    def test_sem_separador_e_numeros(self):
        self.assertEqual(normaliza_valor_br('26663'), Decimal('26663'))
        self.assertEqual(normaliza_valor_br(100), Decimal('100'))
        self.assertEqual(normaliza_valor_br(100.5), Decimal('100.5'))
        self.assertEqual(normaliza_valor_br(Decimal('5.50')), Decimal('5.50'))

    def test_ponto_sem_virgula_e_lido_como_decimal(self):
        # Caso ambíguo documentado: "1.000" é lido como 1,000 (uma unidade), não mil.
        self.assertEqual(normaliza_valor_br('1.000'), Decimal('1.000'))

    def test_em_branco_e_invalidos(self):
        for texto in ('', '   ', None):
            with self.assertRaises(ValueError, msg=repr(texto)):
                normaliza_valor_br(texto)
        for texto in ('abc', '12a,5', 'NaN', 'Infinity', 'R$'):
            with self.assertRaises(ValueError, msg=repr(texto)):
                normaliza_valor_br(texto)


if __name__ == '__main__':
    unittest.main()
