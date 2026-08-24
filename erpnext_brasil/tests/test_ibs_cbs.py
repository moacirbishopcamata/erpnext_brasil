# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de IBS e CBS.

Além da aritmética, dois testes guardam decisões que uma refatoração futura poderia
desfazer sem perceber: que IBS/CBS são calculados **por fora** (ao contrário do ICMS), e
que as alíquotas de 2027 em diante não podem ser inventadas pelo código.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.ibs_cbs import (
	ALIQUOTA_TESTE_CBS_2026,
	ALIQUOTA_TESTE_IBS_2026,
	aliquotas_do_ano,
	calcular_ibs_cbs,
	exige_campos_no_documento,
)
from erpnext_brasil.fiscal.impostos.icms import base_por_dentro


def d(valor: str) -> Decimal:
	return Decimal(valor)


class TestAliquotaTeste(unittest.TestCase):
	def test_soma_um_por_cento(self):
		self.assertEqual(ALIQUOTA_TESTE_IBS_2026 + ALIQUOTA_TESTE_CBS_2026, d("0.010"))

	def test_reparticao_entre_os_dois(self):
		self.assertEqual(ALIQUOTA_TESTE_CBS_2026, d("0.009"))
		self.assertEqual(ALIQUOTA_TESTE_IBS_2026, d("0.001"))

	def test_calculo_em_2026(self):
		resultado = calcular_ibs_cbs(d("1000.00"), ano=2026)

		self.assertEqual(resultado.ibs, d("1.00"))
		self.assertEqual(resultado.cbs, d("9.00"))
		self.assertEqual(resultado.total, d("10.00"))

	def test_ano_teste_e_informativo(self):
		"""Em 2026 a apuração não gera recolhimento — mas os campos são obrigatórios."""
		self.assertTrue(calcular_ibs_cbs(d("1000.00"), ano=2026).informativo)

	def test_ano_posterior_com_aliquotas_informadas_nao_e_informativo(self):
		resultado = calcular_ibs_cbs(
			d("1000.00"), ano=2027, aliquota_ibs=d("0.001"), aliquota_cbs=d("0.088")
		)

		self.assertFalse(resultado.informativo)


class TestAliquotasNaoInventadas(unittest.TestCase):
	def test_ano_sem_norma_levanta_erro_em_vez_de_chutar(self):
		for ano in (2027, 2029, 2033):
			with self.subTest(ano=ano):
				with self.assertRaises(ValueError) as ctx:
					aliquotas_do_ano(ano)

				self.assertIn("não estão embutidas", str(ctx.exception))

	def test_ano_posterior_funciona_com_aliquotas_explicitas(self):
		resultado = calcular_ibs_cbs(
			d("1000.00"), ano=2030, aliquota_ibs=d("0.15"), aliquota_cbs=d("0.088")
		)

		self.assertEqual(resultado.ibs, d("150.00"))
		self.assertEqual(resultado.cbs, d("88.00"))


class TestCalculoPorFora(unittest.TestCase):
	"""IBS e CBS não integram a própria base; o ICMS integra."""

	def test_nao_ha_gross_up(self):
		resultado = calcular_ibs_cbs(d("1000.00"), ano=2026)

		# A base permanece o valor da operação, sem embutimento.
		self.assertEqual(resultado.base, d("1000.00"))

	def test_difere_do_icms_sobre_a_mesma_aliquota(self):
		"""Mesma alíquota, resultados diferentes — é a diferença estrutural da reforma."""
		aliquota = d("0.009")

		por_fora = calcular_ibs_cbs(d("1000.00"), ano=2026, aliquota_ibs=d("0"), aliquota_cbs=aliquota)
		base_embutida = base_por_dentro(d("1000.00"), aliquota)

		self.assertEqual(por_fora.base, d("1000.00"))
		self.assertGreater(base_embutida, d("1000.00"))
		self.assertEqual(base_embutida, d("1009.08"))

	def test_imposto_seletivo_integra_a_base(self):
		resultado = calcular_ibs_cbs(d("1000.00"), ano=2026, imposto_seletivo=d("50.00"))

		self.assertEqual(resultado.base, d("1050.00"))
		self.assertEqual(resultado.ibs, d("1.05"))
		self.assertEqual(resultado.cbs, d("9.45"))

	def test_seletivo_negativo_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_ibs_cbs(d("1000.00"), imposto_seletivo=d("-1"))


class TestObrigatoriedadeNoDocumento(unittest.TestCase):
	"""A tolerância do Ato Conjunto RFB/CGIBS 1/2025 terminou em 03/08/2026."""

	def test_antes_da_data_era_tolerado(self):
		self.assertFalse(exige_campos_no_documento(2026, 8, 2))
		self.assertFalse(exige_campos_no_documento(2026, 7, 31))
		self.assertFalse(exige_campos_no_documento(2026, 1, 1))

	def test_a_partir_da_data_o_documento_e_rejeitado_sem_os_campos(self):
		self.assertTrue(exige_campos_no_documento(2026, 8, 3))
		self.assertTrue(exige_campos_no_documento(2026, 8, 24))
		self.assertTrue(exige_campos_no_documento(2026, 12, 31))

	def test_anos_seguintes(self):
		self.assertTrue(exige_campos_no_documento(2027, 1, 1))


class TestValidacaoDeAliquota(unittest.TestCase):
	def test_percentual_em_vez_de_fracao_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_ibs_cbs(d("1000.00"), ano=2030, aliquota_ibs=d("15"), aliquota_cbs=d("8.8"))


if __name__ == "__main__":
	unittest.main()
