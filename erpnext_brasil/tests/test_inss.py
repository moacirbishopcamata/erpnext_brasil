# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/inss.py` — contribuição previdenciária do empregado.

O teste que mais importa é `test_bate_com_calculo_faixa_a_faixa`: confere o método da
parcela a deduzir contra a soma progressiva calculada faixa a faixa, de um jeito
totalmente independente da tabela publicada — não só repete os mesmos números.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.folha.inss import ANO_VIGENTE, TETO_POR_ANO, INSSInvalido, calcular_inss


def d(v: str) -> Decimal:
	return Decimal(v)


def _calculo_faixa_a_faixa(salario: Decimal) -> Decimal:
	"""Soma progressiva independente do método da parcela a deduzir — usada só para
	conferir `calcular_inss`, nunca para calcular de verdade."""
	faixas = (
		(d("0.00"), d("1621.00"), d("0.075")),
		(d("1621.00"), d("2902.84"), d("0.09")),
		(d("2902.84"), d("4354.27"), d("0.12")),
		(d("4354.27"), d("8475.55"), d("0.14")),
	)
	base = min(salario, d("8475.55"))
	total = d("0.00")

	for inicio, fim, aliquota in faixas:
		if base <= inicio:
			break
		total += (min(base, fim) - inicio) * aliquota

	return total.quantize(d("0.01"))


class TestCalcularInss(unittest.TestCase):
	def test_bate_com_calculo_faixa_a_faixa(self):
		for salario in (
			"1000.00",
			"1621.00",
			"2000.00",
			"2902.84",
			"3500.00",
			"4354.27",
			"6000.00",
			"8475.55",
		):
			with self.subTest(salario=salario):
				esperado = _calculo_faixa_a_faixa(d(salario))
				obtido = calcular_inss(d(salario))

				# Tolerância de 1 centavo: o método da parcela a deduzir e a soma
				# faixa a faixa podem divergir por arredondamento intermediário.
				self.assertLessEqual(abs(obtido - esperado), d("0.01"))

	def test_primeira_faixa(self):
		self.assertEqual(calcular_inss(d("1000.00")), d("75.00"))

	def test_no_limite_da_primeira_faixa(self):
		self.assertEqual(calcular_inss(d("1621.00")), d("121.58"))

	def test_segunda_faixa(self):
		self.assertEqual(calcular_inss(d("2000.00")), d("155.68"))

	def test_no_teto(self):
		self.assertEqual(calcular_inss(TETO_POR_ANO[ANO_VIGENTE]), d("988.09"))

	def test_acima_do_teto_desconta_o_mesmo_que_no_teto(self):
		self.assertEqual(calcular_inss(d("20000.00")), calcular_inss(TETO_POR_ANO[ANO_VIGENTE]))

	def test_salario_negativo_e_erro(self):
		with self.assertRaises(INSSInvalido):
			calcular_inss(d("-1.00"))

	def test_salario_zero_e_zero(self):
		self.assertEqual(calcular_inss(d("0.00")), d("0.00"))

	def test_ano_sem_tabela_embutida_e_erro(self):
		with self.assertRaises(INSSInvalido):
			calcular_inss(d("2000.00"), ano=2027)

	def test_nunca_excede_o_desconto_maximo(self):
		desconto_no_teto = calcular_inss(TETO_POR_ANO[ANO_VIGENTE])

		for salario in ("50000.00", "1000000.00"):
			with self.subTest(salario=salario):
				self.assertEqual(calcular_inss(d(salario)), desconto_no_teto)


if __name__ == "__main__":
	unittest.main()
