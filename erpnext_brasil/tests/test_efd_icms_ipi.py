# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_icms_ipi.py` — registro E110 do EFD-ICMS/IPI.

O teste que mais importa é `test_ordem_dos_campos`: um `dict` em Python preserva ordem
de inserção, e a ordem aqui não é estética — é a ordem que o Guia Prático EFD exige na
linha de texto final (mesmo que este módulo não gere a linha em si, ver docstring).
"""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.apuracao_periodo import ApuracaoPeriodo
from erpnext_brasil.contabil.efd_icms_ipi import montar_e110


def d(v: str) -> Decimal:
	return Decimal(v)


class TestMontarE110(unittest.TestCase):
	def test_ordem_dos_campos(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))
		campos = list(montar_e110(apuracao))

		self.assertEqual(
			campos,
			[
				"REG",
				"VL_TOT_DEBITOS",
				"VL_AJ_DEBITOS",
				"VL_TOT_AJ_DEBITOS",
				"VL_ESTORNOS_CRED",
				"VL_TOT_CREDITOS",
				"VL_AJ_CREDITOS",
				"VL_TOT_AJ_CREDITOS",
				"VL_ESTORNOS_DEB",
				"VL_SLD_CREDOR_ANT",
				"VL_SLD_APURADO",
				"VL_TOT_DED",
				"VL_ICMS_RECOLHER",
				"VL_SLD_CREDOR_TRANSPORTAR",
				"DEB_ESP",
			],
		)

	def test_reg_e_fixo(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("0"), creditos=d("0"))

		self.assertEqual(montar_e110(apuracao)["REG"], "E110")

	def test_debito_maior_que_credito_preenche_a_recolher(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))
		campos = montar_e110(apuracao)

		self.assertEqual(campos["VL_TOT_DEBITOS"], d("1000.00"))
		self.assertEqual(campos["VL_TOT_CREDITOS"], d("400.00"))
		self.assertEqual(campos["VL_SLD_APURADO"], d("600.00"))
		self.assertEqual(campos["VL_ICMS_RECOLHER"], d("600.00"))
		self.assertEqual(campos["VL_SLD_CREDOR_TRANSPORTAR"], d("0.00"))

	def test_credito_maior_que_debito_preenche_saldo_credor_a_transportar(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("400.00"), creditos=d("1000.00"))
		campos = montar_e110(apuracao)

		self.assertEqual(campos["VL_SLD_APURADO"], d("0.00"))
		self.assertEqual(campos["VL_ICMS_RECOLHER"], d("0.00"))
		self.assertEqual(campos["VL_SLD_CREDOR_TRANSPORTAR"], d("600.00"))

	def test_saldo_credor_anterior_propaga_para_o_campo_proprio(self):
		apuracao = ApuracaoPeriodo(
			tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"), saldo_credor_anterior=d("50.00")
		)

		self.assertEqual(montar_e110(apuracao)["VL_SLD_CREDOR_ANT"], d("50.00"))

	def test_campos_de_ajuste_nao_modelados_ficam_zerados(self):
		"""Escopo desta versão (ver docstring do módulo): sem registro E111, os sete
		campos de ajuste são sempre zero — correto só para apuração sem ajuste real."""
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))
		campos = montar_e110(apuracao)

		campos_de_ajuste = (
			"VL_AJ_DEBITOS",
			"VL_TOT_AJ_DEBITOS",
			"VL_ESTORNOS_CRED",
			"VL_AJ_CREDITOS",
			"VL_TOT_AJ_CREDITOS",
			"VL_ESTORNOS_DEB",
			"VL_TOT_DED",
		)

		for campo in campos_de_ajuste:
			with self.subTest(campo=campo):
				self.assertEqual(campos[campo], d("0.00"))

	def test_tributo_diferente_de_icms_e_rejeitado(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("100.00"), creditos=d("0.00"))

		with self.assertRaises(ValueError):
			montar_e110(apuracao)


if __name__ == "__main__":
	unittest.main()
