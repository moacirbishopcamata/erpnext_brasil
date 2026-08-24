# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de IPI e PIS/COFINS.

Como em `test_icms.py`, os valores esperados foram calculados à mão. Os dois testes
mais importantes deste arquivo não verificam aritmética, e sim regra jurídica: quando o
IPI compõe a base do ICMS, e quanto custa manter o ICMS na base de PIS/COFINS.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import calcular_icms
from erpnext_brasil.fiscal.impostos.ipi import (
	calcular_ipi,
	calcular_ipi_por_unidade,
	ipi_compoe_base_icms,
)
from erpnext_brasil.fiscal.impostos.pis_cofins import (
	ALIQUOTAS_CUMULATIVO,
	ALIQUOTAS_NAO_CUMULATIVO,
	aliquotas_do_regime,
	calcular_pis_cofins,
)


def d(valor: str) -> Decimal:
	return Decimal(valor)


class TestIPI(unittest.TestCase):
	def test_ad_valorem(self):
		resultado = calcular_ipi(d("1000.00"), d("0.10"))

		self.assertEqual(resultado.base, d("1000.00"))
		self.assertEqual(resultado.valor, d("100.00"))

	def test_frete_e_despesas_entram_na_base(self):
		resultado = calcular_ipi(
			d("1000.00"), d("0.10"), frete=d("80.00"), seguro=d("20.00"), descontos=d("100.00")
		)

		self.assertEqual(resultado.base, d("1000.00"))
		self.assertEqual(resultado.valor, d("100.00"))

	def test_por_unidade(self):
		resultado = calcular_ipi_por_unidade(d("100"), d("0.50"))

		self.assertEqual(resultado.valor, d("50.00"))
		self.assertEqual(resultado.base, d("100.00"))

	def test_aliquota_como_percentual_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_ipi(d("1000.00"), d("10"))

	def test_base_negativa_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_ipi(d("100.00"), d("0.10"), descontos=d("500.00"))


class TestIPINaBaseDoICMS(unittest.TestCase):
	"""CF art. 155, §2º, XI — a regra que gera autuação quando ignorada."""

	def test_nao_compoe_entre_contribuintes_para_revenda(self):
		self.assertFalse(ipi_compoe_base_icms(True, True))

	def test_compoe_na_venda_a_consumidor_final(self):
		self.assertTrue(ipi_compoe_base_icms(True, False))

	def test_compoe_quando_destinatario_nao_e_contribuinte(self):
		self.assertTrue(ipi_compoe_base_icms(False, True))
		self.assertTrue(ipi_compoe_base_icms(False, False))

	def test_a_mesma_venda_gera_icms_diferente_conforme_o_destino(self):
		"""Consequência prática: mesma mercadoria, dois destinos, ICMS distinto."""
		produtos = d("1000.00")
		ipi = calcular_ipi(produtos, d("0.10"))

		self.assertEqual(ipi.valor, d("100.00"))

		# Revenda entre contribuintes: IPI fora da base.
		base_revenda = produtos
		# Consumidor final: IPI dentro da base.
		base_consumidor = produtos + ipi.valor

		icms_revenda = calcular_icms(base_revenda, d("0.18"))
		icms_consumidor = calcular_icms(base_consumidor, d("0.18"))

		self.assertEqual(icms_revenda.valor, d("180.00"))
		self.assertEqual(icms_consumidor.valor, d("198.00"))

		# Tratar os dois casos igual erra o ICMS em R$ 18,00 numa nota de mil reais.
		self.assertEqual(icms_consumidor.valor - icms_revenda.valor, d("18.00"))


class TestRegimesPISCOFINS(unittest.TestCase):
	def test_aliquotas_cumulativo(self):
		self.assertEqual(aliquotas_do_regime("cumulativo"), ALIQUOTAS_CUMULATIVO)
		self.assertEqual(ALIQUOTAS_CUMULATIVO, (d("0.0065"), d("0.03")))

	def test_aliquotas_nao_cumulativo(self):
		self.assertEqual(aliquotas_do_regime("nao_cumulativo"), ALIQUOTAS_NAO_CUMULATIVO)
		self.assertEqual(ALIQUOTAS_NAO_CUMULATIVO, (d("0.0165"), d("0.076")))

	def test_regime_desconhecido_orienta_sobre_o_simples(self):
		with self.assertRaises(ValueError) as ctx:
			aliquotas_do_regime("simples")

		self.assertIn("Simples Nacional", str(ctx.exception))

	def test_regime_errado_muda_a_contribuicao_em_mais_de_quatro_vezes(self):
		cumulativo = calcular_pis_cofins(d("1000.00"), "cumulativo")
		nao_cumulativo = calcular_pis_cofins(d("1000.00"), "nao_cumulativo")

		self.assertEqual(cumulativo.total, d("36.50"))
		self.assertEqual(nao_cumulativo.total, d("92.50"))


class TestExclusaoDoICMS(unittest.TestCase):
	"""RE 574.706 — o ICMS destacado não compõe a base de PIS/COFINS."""

	def test_exclusao_e_o_padrao(self):
		resultado = calcular_pis_cofins(d("1000.00"), "cumulativo", icms_destacado=d("180.00"))

		self.assertEqual(resultado.base, d("820.00"))
		self.assertEqual(resultado.pis, d("5.33"))
		self.assertEqual(resultado.cofins, d("24.60"))

	def test_manter_o_icms_na_base_recolhe_a_maior(self):
		com_exclusao = calcular_pis_cofins(d("1000.00"), "cumulativo", icms_destacado=d("180.00"))
		sem_exclusao = calcular_pis_cofins(
			d("1000.00"), "cumulativo", icms_destacado=d("180.00"), excluir_icms=False
		)

		self.assertEqual(com_exclusao.total, d("29.93"))
		self.assertEqual(sem_exclusao.total, d("36.50"))
		self.assertEqual(sem_exclusao.total - com_exclusao.total, d("6.57"))

	def test_outras_exclusoes_tambem_reduzem_a_base(self):
		resultado = calcular_pis_cofins(
			d("1000.00"), "cumulativo", icms_destacado=d("180.00"), outras_exclusoes=d("20.00")
		)

		self.assertEqual(resultado.base, d("800.00"))

	def test_exclusao_maior_que_a_receita_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_pis_cofins(d("100.00"), "cumulativo", icms_destacado=d("500.00"))


class TestRegimesEspeciais(unittest.TestCase):
	def test_monofasico_com_aliquota_zero_na_revenda(self):
		resultado = calcular_pis_cofins(
			d("1000.00"), "nao_cumulativo", aliquota_pis=d("0"), aliquota_cofins=d("0")
		)

		self.assertEqual(resultado.pis, d("0.00"))
		self.assertEqual(resultado.cofins, d("0.00"))
		# A base permanece escriturada mesmo com contribuição zero.
		self.assertEqual(resultado.base, d("1000.00"))

	def test_aliquota_sobrescrita_como_percentual_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_pis_cofins(d("1000.00"), "cumulativo", aliquota_pis=d("1.65"))


if __name__ == "__main__":
	unittest.main()
