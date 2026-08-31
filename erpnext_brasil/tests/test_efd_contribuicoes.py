# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_contribuicoes.py` — registros M200/M210/M600/M610."""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.efd_contribuicoes import (
	ConsolidacaoContribuicao,
	DetalhamentoContribuicao,
	EfdContribuicoesInvalido,
	montar_m200,
	montar_m210,
	montar_m600,
	montar_m610,
)
from erpnext_brasil.contabil.sped_texto import montar_linha


def d(v: str) -> Decimal:
	return Decimal(v)


class TestMontarM210(unittest.TestCase):
	def test_reg_e_m210(self):
		registro = montar_m210(DetalhamentoContribuicao(cod_cont="01", vl_rec_brt=d("0"), vl_bc_cont=d("0")))

		self.assertEqual(registro["REG"], "M210")

	def test_usa_sufixo_pis_nao_cofins(self):
		registro = montar_m210(DetalhamentoContribuicao(cod_cont="01", vl_rec_brt=d("0"), vl_bc_cont=d("0")))

		self.assertIn("VL_AJUS_ACRES_BC_PIS", registro)
		self.assertIn("ALIQ_PIS", registro)
		self.assertNotIn("VL_AJUS_ACRES_BC_COFINS", registro)

	def test_base_ajustada_soma_acrescimo_subtrai_reducao(self):
		registro = montar_m210(
			DetalhamentoContribuicao(
				cod_cont="01",
				vl_rec_brt=d("10000.00"),
				vl_bc_cont=d("10000.00"),
				vl_ajus_acres_bc=d("500.00"),
				vl_ajus_reduc_bc=d("200.00"),
			)
		)

		self.assertEqual(registro["VL_BC_CONT_AJUS"], d("10300.00"))

	def test_valor_do_periodo_aplica_a_formula_oficial(self):
		# VL_CONT_PER = 11 + 12 - 13 - 14 + 15
		registro = montar_m210(
			DetalhamentoContribuicao(
				cod_cont="01",
				vl_rec_brt=d("0"),
				vl_bc_cont=d("0"),
				vl_cont_apur=d("165.00"),
				vl_ajus_acres=d("10.00"),
				vl_ajus_reduc=d("5.00"),
				vl_cont_difer=d("20.00"),
				vl_cont_difer_ant=d("8.00"),
			)
		)

		self.assertEqual(registro["VL_CONT_PER"], d("158.00"))

	def test_cod_cont_vazio_e_erro(self):
		with self.assertRaises(EfdContribuicoesInvalido):
			DetalhamentoContribuicao(cod_cont="", vl_rec_brt=d("0"), vl_bc_cont=d("0"))


class TestMontarM610(unittest.TestCase):
	def test_reg_e_m610(self):
		registro = montar_m610(DetalhamentoContribuicao(cod_cont="01", vl_rec_brt=d("0"), vl_bc_cont=d("0")))

		self.assertEqual(registro["REG"], "M610")

	def test_usa_sufixo_cofins_nao_pis(self):
		registro = montar_m610(DetalhamentoContribuicao(cod_cont="01", vl_rec_brt=d("0"), vl_bc_cont=d("0")))

		self.assertIn("VL_AJUS_ACRES_BC_COFINS", registro)
		self.assertIn("ALIQ_COFINS", registro)
		self.assertNotIn("VL_AJUS_ACRES_BC_PIS", registro)

	def test_mesma_formula_do_m210(self):
		entrada = DetalhamentoContribuicao(
			cod_cont="01", vl_rec_brt=d("0"), vl_bc_cont=d("0"), vl_cont_apur=d("760.00")
		)

		self.assertEqual(montar_m610(entrada)["VL_CONT_PER"], d("760.00"))


class TestMontarM200(unittest.TestCase):
	def test_reg_e_m200(self):
		registro = montar_m200(ConsolidacaoContribuicao())

		self.assertEqual(registro["REG"], "M200")

	def test_formula_completa_oficial(self):
		# NC_DEV = 02-03-04; NC_REC = 05-06-07; CUM_REC = 09-10-11; TOTAL = 08+12
		registro = montar_m200(
			ConsolidacaoContribuicao(
				vl_tot_cont_nc_per=d("1000.00"),
				vl_tot_cred_desc=d("100.00"),
				vl_tot_cred_desc_ant=d("50.00"),
				vl_ret_nc=d("20.00"),
				vl_out_ded_nc=d("10.00"),
				vl_tot_cont_cum_per=d("500.00"),
				vl_ret_cum=d("5.00"),
				vl_out_ded_cum=d("5.00"),
			)
		)

		self.assertEqual(registro["VL_TOT_CONT_NC_DEV"], d("850.00"))
		self.assertEqual(registro["VL_CONT_NC_REC"], d("820.00"))
		self.assertEqual(registro["VL_CONT_CUM_REC"], d("490.00"))
		self.assertEqual(registro["VL_TOT_CONT_REC"], d("1310.00"))

	def test_tudo_zero_e_valido(self):
		registro = montar_m200(ConsolidacaoContribuicao())

		self.assertEqual(registro["VL_TOT_CONT_REC"], d("0.00"))


class TestMontarM600(unittest.TestCase):
	def test_reg_e_m600(self):
		registro = montar_m600(ConsolidacaoContribuicao())

		self.assertEqual(registro["REG"], "M600")

	def test_mesma_formula_do_m200(self):
		entrada = ConsolidacaoContribuicao(vl_tot_cont_nc_per=d("300.00"))

		self.assertEqual(montar_m600(entrada)["VL_TOT_CONT_NC_DEV"], d("300.00"))


class TestSerializacaoReal(unittest.TestCase):
	"""Testa contra `sped_texto.montar_linha` de verdade, mesma disciplina de
	`test_sped_texto.py` para os outros registros EFD."""

	def test_m210_serializa_sem_erro(self):
		registro = montar_m210(
			DetalhamentoContribuicao(
				cod_cont="01", vl_rec_brt=d("10000.00"), vl_bc_cont=d("10000.00"), aliquota=d("0.0165")
			)
		)
		linha = montar_linha(registro)

		self.assertTrue(linha.startswith("|M210|"))

	def test_m200_serializa_sem_erro(self):
		registro = montar_m200(ConsolidacaoContribuicao(vl_tot_cont_nc_per=d("100.00")))
		linha = montar_linha(registro)

		self.assertTrue(linha.startswith("|M200|"))


if __name__ == "__main__":
	unittest.main()
