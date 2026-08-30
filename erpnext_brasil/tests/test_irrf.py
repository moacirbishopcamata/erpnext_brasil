# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/irrf.py` — Imposto de Renda Retido na Fonte sobre a folha.

`TestExemplosOficiaisRFB` é o teste que mais importa: reproduz, um a um, os 5 exemplos
publicados por `gov.br/receitafederal` para a Lei 15.270/2025 (João, José, Maria, Rita,
Vera) — rendimento bruto, base de cálculo já pronta (INSS/desconto simplificado já
aplicado pela própria RFB no exemplo) e o IRRF final esperado. Nenhum desses números foi
inventado: são os mesmos publicados pela fonte oficial.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.folha.irrf import (
	ANO_VIGENTE,
	IRRFInvalido,
	calcular_desconto_simplificado,
	calcular_irrf,
	calcular_irrf_tradicional,
	calcular_redutor,
)


def d(v: str) -> Decimal:
	return Decimal(v)


class TestExemplosOficiaisRFB(unittest.TestCase):
	"""Os 5 exemplos de `gov.br/receitafederal` para a Lei 15.270/2025 — base de
	cálculo e rendimento bruto exatamente como publicados, IRRF final conferido."""

	def test_joao(self):
		# Bruto R$ 3.036,00, desconto simplificado R$ 607,20, base R$ 2.428,80 —
		# já isento na 1ª faixa, redutor nem chega a ser necessário.
		self.assertEqual(calcular_irrf(d("3036.00"), d("2428.80")), d("0.00"))

	def test_jose(self):
		# Bruto R$ 4.000,00, desconto simplificado R$ 607,20, base R$ 3.392,80 —
		# tradicional R$ 114,76 (3ª faixa), redutor R$ 446,04 zera o imposto.
		self.assertEqual(calcular_irrf(d("4000.00"), d("3392.80")), d("0.00"))

	def test_maria(self):
		# Bruto R$ 5.000,00, desconto simplificado R$ 607,20, base R$ 4.392,80 —
		# tradicional R$ 312,89 (4ª faixa), redutor praticamente igual, zera.
		self.assertEqual(calcular_irrf(d("5000.00"), d("4392.80")), d("0.00"))

	def test_rita(self):
		# Bruto R$ 6.000,00, INSS R$ 649,60, base R$ 5.350,40 — tradicional
		# R$ 562,63 (5ª faixa), redutor R$ 179,75, final R$ 382,88.
		self.assertEqual(calcular_irrf(d("6000.00"), d("5350.40")), d("382.88"))

	def test_vera(self):
		# Bruto R$ 7.607,20, desconto simplificado R$ 607,20, base R$ 7.000,00 —
		# acima de ~R$ 7.350,00 o redutor já é zero pela própria fórmula, IRRF
		# igual ao tradicional puro (5ª faixa).
		self.assertEqual(calcular_irrf(d("7607.20"), d("7000.00")), d("1016.27"))


class TestCalcularIrrfTradicional(unittest.TestCase):
	def test_isento_no_limite(self):
		self.assertEqual(calcular_irrf_tradicional(d("2428.80")), d("0.00"))

	def test_segunda_faixa(self):
		self.assertEqual(calcular_irrf_tradicional(d("2826.65")), d("29.84"))

	def test_faixa_maxima(self):
		self.assertEqual(calcular_irrf_tradicional(d("10000.00")), d("1841.27"))

	def test_base_negativa_e_erro(self):
		with self.assertRaises(IRRFInvalido):
			calcular_irrf_tradicional(d("-1.00"))

	def test_ano_sem_tabela_embutida_e_erro(self):
		with self.assertRaises(IRRFInvalido):
			calcular_irrf_tradicional(d("3000.00"), ano=2027)


class TestCalcularRedutor(unittest.TestCase):
	def test_redutor_maximo_sem_renda(self):
		self.assertEqual(calcular_redutor(d("0.00")), d("978.62"))

	def test_redutor_cai_a_zero_apos_certo_ponto(self):
		# 978.62 / 0.133145 ≈ 7349,99 — acima disso a fórmula já é negativa.
		self.assertEqual(calcular_redutor(d("7350.00")), d("0.00"))
		self.assertEqual(calcular_redutor(d("50000.00")), d("0.00"))

	def test_rendimento_negativo_e_erro(self):
		with self.assertRaises(IRRFInvalido):
			calcular_redutor(d("-1.00"))

	def test_ano_sem_formula_embutida_e_erro(self):
		with self.assertRaises(IRRFInvalido):
			calcular_redutor(d("3000.00"), ano=2027)


class TestCalcularDescontoSimplificado(unittest.TestCase):
	def test_abaixo_do_teto(self):
		self.assertEqual(calcular_desconto_simplificado(d("2000.00")), d("500.00"))

	def test_no_teto(self):
		self.assertEqual(calcular_desconto_simplificado(d("3000.00")), d("607.20"))

	def test_acima_do_teto_satura(self):
		self.assertEqual(calcular_desconto_simplificado(d("100000.00")), d("607.20"))

	def test_rendimento_negativo_e_erro(self):
		with self.assertRaises(IRRFInvalido):
			calcular_desconto_simplificado(d("-1.00"))


class TestAnoVigente(unittest.TestCase):
	def test_ano_vigente_e_2026(self):
		self.assertEqual(ANO_VIGENTE, 2026)


if __name__ == "__main__":
	unittest.main()
