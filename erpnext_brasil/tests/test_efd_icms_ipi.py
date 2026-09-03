# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_icms_ipi.py` — registros E110 (ICMS) e E520 (IPI) do EFD.

O teste que mais importa é `test_ordem_dos_campos`: um `dict` em Python preserva ordem
de inserção, e a ordem aqui não é estética — é a ordem que o Guia Prático EFD exige na
linha de texto final (mesmo que este módulo não gere a linha em si, ver docstring).
"""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.apuracao_periodo import ApuracaoPeriodo
from erpnext_brasil.contabil.efd_icms_ipi import (
	Ajuste,
	AjusteIpi,
	EfdInvalido,
	montar_e110,
	montar_e111,
	montar_e520,
	montar_e530,
)


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


class TestAjuste(unittest.TestCase):
	def test_codigo_precisa_ter_8_caracteres(self):
		"""Corrigido em 2026-09-03: a versão anterior exigia 4 caracteres, o que
		rejeitaria todo código real da tabela 5.1.1 (`GO040024`, `PE000001`)."""
		with self.assertRaises(EfdInvalido):
			Ajuste(codigo="MG00", descricao="teste", valor=d("10.00"))

	def test_codigo_real_de_oito_caracteres_e_aceito(self):
		"""`GO040024` é um código literal citado pelo próprio Guia Prático."""
		ajuste = Ajuste(codigo="GO040024", descricao="ICMS próprio", valor=d("10.00"))

		self.assertEqual(ajuste.tipo, "4")

	def test_codigo_de_st_e_recusado_no_e111(self):
		"""3º caractere `1` é ICMS-ST — pertence ao E220, não ao E111."""
		with self.assertRaises(EfdInvalido):
			Ajuste(codigo="MG100001", descricao="teste", valor=d("10.00"))

	def test_quarto_caractere_precisa_ser_tipo_valido(self):
		with self.assertRaises(EfdInvalido):
			Ajuste(codigo="MG090001", descricao="teste", valor=d("10.00"))

	def test_valor_negativo_e_rejeitado(self):
		with self.assertRaises(EfdInvalido):
			Ajuste(codigo="MG000001", descricao="teste", valor=d("-1.00"))

	def test_tipo_e_o_quarto_caractere(self):
		self.assertEqual(Ajuste(codigo="MG000001", descricao="", valor=d("1.00")).tipo, "0")
		self.assertEqual(Ajuste(codigo="MG040001", descricao="", valor=d("1.00")).tipo, "4")


class TestMontarE111(unittest.TestCase):
	def test_uma_linha_por_ajuste_na_ordem_oficial(self):
		ajustes = [
			Ajuste(codigo="MG000001", descricao="Outros débitos", valor=d("50.00")),
			Ajuste(codigo="MG040001", descricao="Dedução do período", valor=d("10.00")),
		]
		linhas = montar_e111(ajustes)

		self.assertEqual(len(linhas), 2)
		self.assertEqual(list(linhas[0]), ["REG", "COD_AJ_APUR", "DESCR_COMPL_AJ", "VL_AJ_APUR"])
		self.assertEqual(linhas[0]["COD_AJ_APUR"], "MG000001")
		self.assertEqual(linhas[0]["VL_AJ_APUR"], d("50.00"))

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(montar_e111([]), [])


class TestMontarE110ComAjustes(unittest.TestCase):
	def test_outros_debitos_soma_em_vl_tot_aj_debitos(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))
		ajustes = [Ajuste(codigo="MG000001", descricao="", valor=d("50.00"))]
		campos = montar_e110(apuracao, ajustes)

		self.assertEqual(campos["VL_TOT_AJ_DEBITOS"], d("50.00"))
		# 1000 débito + 50 ajuste - 400 crédito = 650 a recolher.
		self.assertEqual(campos["VL_ICMS_RECOLHER"], d("650.00"))

	def test_cada_tipo_vai_para_o_campo_certo(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))
		ajustes = [
			Ajuste(codigo="MG000001", descricao="", valor=d("10.00")),  # outros débitos
			Ajuste(codigo="MG010001", descricao="", valor=d("20.00")),  # estorno de crédito
			Ajuste(codigo="MG020001", descricao="", valor=d("30.00")),  # outros créditos
			Ajuste(codigo="MG030001", descricao="", valor=d("40.00")),  # estorno de débito
			Ajuste(codigo="MG040001", descricao="", valor=d("5.00")),  # dedução
			Ajuste(codigo="MG050001", descricao="", valor=d("15.00")),  # débito especial
		]
		campos = montar_e110(apuracao, ajustes)

		self.assertEqual(campos["VL_TOT_AJ_DEBITOS"], d("10.00"))
		self.assertEqual(campos["VL_ESTORNOS_CRED"], d("20.00"))
		self.assertEqual(campos["VL_TOT_AJ_CREDITOS"], d("30.00"))
		self.assertEqual(campos["VL_ESTORNOS_DEB"], d("40.00"))
		self.assertEqual(campos["VL_TOT_DED"], d("5.00"))
		self.assertEqual(campos["DEB_ESP"], d("15.00"))

	def test_debito_especial_nao_entra_na_formula_do_saldo(self):
		"""DEB_ESP é informativo (débito extemporâneo) — não é somado/subtraído do
		saldo apurado, conforme a definição oficial do campo."""
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))
		sem_ajuste = montar_e110(apuracao, [])
		com_debito_especial = montar_e110(apuracao, [Ajuste(codigo="MG050001", descricao="", valor=d("999.00"))])

		self.assertEqual(sem_ajuste["VL_ICMS_RECOLHER"], com_debito_especial["VL_ICMS_RECOLHER"])

	def test_ajuste_pode_transformar_devedor_em_credor(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("100.00"), creditos=d("90.00"))
		# +10 devedor antes do ajuste; +30 de outros créditos vira -20 (credor).
		campos = montar_e110(apuracao, [Ajuste(codigo="MG020001", descricao="", valor=d("30.00"))])

		self.assertEqual(campos["VL_ICMS_RECOLHER"], d("0.00"))
		self.assertEqual(campos["VL_SLD_CREDOR_TRANSPORTAR"], d("20.00"))

	def test_deducao_maior_que_saldo_devedor_levanta_erro(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("100.00"), creditos=d("90.00"))

		with self.assertRaises(EfdInvalido):
			montar_e110(apuracao, [Ajuste(codigo="MG040001", descricao="", valor=d("50.00"))])

	def test_sem_ajustes_e_igual_ao_comportamento_anterior(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))

		self.assertEqual(montar_e110(apuracao), montar_e110(apuracao, []))


class TestMontarE520(unittest.TestCase):
	def test_ordem_dos_campos(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("100.00"), creditos=d("40.00"))
		campos = list(montar_e520(apuracao))

		self.assertEqual(
			campos,
			["REG", "VL_SD_ANT_IPI", "VL_DEB_IPI", "VL_CRED_IPI", "VL_OD_IPI", "VL_OC_IPI", "VL_SC_IPI", "VL_SD_IPI"],
		)

	def test_reg_e_fixo(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("0"), creditos=d("0"))

		self.assertEqual(montar_e520(apuracao)["REG"], "E520")

	def test_debito_maior_que_credito_preenche_vl_sd_ipi(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("100.00"), creditos=d("40.00"))
		campos = montar_e520(apuracao)

		self.assertEqual(campos["VL_DEB_IPI"], d("100.00"))
		self.assertEqual(campos["VL_CRED_IPI"], d("40.00"))
		self.assertEqual(campos["VL_SD_IPI"], d("60.00"))
		self.assertEqual(campos["VL_SC_IPI"], d("0.00"))

	def test_credito_maior_que_debito_preenche_vl_sc_ipi(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("40.00"), creditos=d("100.00"))
		campos = montar_e520(apuracao)

		self.assertEqual(campos["VL_SD_IPI"], d("0.00"))
		self.assertEqual(campos["VL_SC_IPI"], d("60.00"))

	def test_vl_sc_ipi_e_vl_sd_ipi_sao_mutuamente_exclusivos(self):
		for debitos, creditos in (("100.00", "40.00"), ("40.00", "100.00"), ("50.00", "50.00")):
			with self.subTest(debitos=debitos, creditos=creditos):
				campos = montar_e520(ApuracaoPeriodo(tributo="IPI", debitos=d(debitos), creditos=d(creditos)))

				self.assertTrue(campos["VL_SC_IPI"] == d("0.00") or campos["VL_SD_IPI"] == d("0.00"))

	def test_saldo_credor_anterior_vai_para_vl_sd_ant_ipi(self):
		apuracao = ApuracaoPeriodo(
			tributo="IPI", debitos=d("100.00"), creditos=d("40.00"), saldo_credor_anterior=d("10.00")
		)

		self.assertEqual(montar_e520(apuracao)["VL_SD_ANT_IPI"], d("10.00"))

	def test_campos_de_ajuste_nao_modelados_ficam_zerados(self):
		"""Escopo desta versão (ver docstring do módulo): sem registro E530, VL_OD_IPI
		e VL_OC_IPI são sempre zero — correto só para apuração sem ajuste real."""
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("100.00"), creditos=d("40.00"))
		campos = montar_e520(apuracao)

		self.assertEqual(campos["VL_OD_IPI"], d("0.00"))
		self.assertEqual(campos["VL_OC_IPI"], d("0.00"))

	def test_tributo_diferente_de_ipi_e_rejeitado(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("100.00"), creditos=d("0.00"))

		with self.assertRaises(ValueError):
			montar_e520(apuracao)


class TestAjusteIpi(unittest.TestCase):
	def test_codigo_precisa_ter_3_digitos(self):
		with self.assertRaises(EfdInvalido):
			AjusteIpi(codigo="10", descricao="teste", valor=d("10.00"))

	def test_codigo_fora_da_faixa_e_rejeitado(self):
		with self.assertRaises(EfdInvalido):
			AjusteIpi(codigo="200", descricao="teste", valor=d("10.00"))

	def test_codigo_100_reservado_e_rejeitado_ao_ler_ind_aj(self):
		with self.assertRaises(EfdInvalido):
			_ = AjusteIpi(codigo="100", descricao="teste", valor=d("10.00")).ind_aj

	def test_faixa_001_a_099_e_credito(self):
		self.assertEqual(AjusteIpi(codigo="050", descricao="", valor=d("1.00")).ind_aj, "1")

	def test_faixa_101_a_199_e_debito(self):
		self.assertEqual(AjusteIpi(codigo="150", descricao="", valor=d("1.00")).ind_aj, "0")

	def test_valor_negativo_e_rejeitado(self):
		with self.assertRaises(EfdInvalido):
			AjusteIpi(codigo="050", descricao="teste", valor=d("-1.00"))

	def test_ind_doc_invalido_e_rejeitado(self):
		with self.assertRaises(EfdInvalido):
			AjusteIpi(codigo="050", descricao="teste", valor=d("1.00"), documento_indicador="7")

	def test_ind_doc_padrao_e_outros(self):
		self.assertEqual(AjusteIpi(codigo="050", descricao="", valor=d("1.00")).documento_indicador, "9")


class TestMontarE530(unittest.TestCase):
	def test_ordem_dos_campos(self):
		linhas = montar_e530([AjusteIpi(codigo="050", descricao="teste", valor=d("10.00"))])

		self.assertEqual(
			list(linhas[0]), ["REG", "IND_AJ", "VL_AJ", "COD_AJ", "IND_DOC", "NUM_DOC", "DESCR_AJ"]
		)

	def test_reg_e_fixo(self):
		linhas = montar_e530([AjusteIpi(codigo="050", descricao="", valor=d("10.00"))])

		self.assertEqual(linhas[0]["REG"], "E530")

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(montar_e530([]), [])


class TestMontarE520ComAjustes(unittest.TestCase):
	def test_ajuste_de_debito_soma_em_vl_od_ipi(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("1000.00"), creditos=d("400.00"))
		ajustes = [AjusteIpi(codigo="150", descricao="", valor=d("50.00"))]
		campos = montar_e520(apuracao, ajustes)

		self.assertEqual(campos["VL_OD_IPI"], d("50.00"))
		self.assertEqual(campos["VL_SD_IPI"], d("650.00"))

	def test_ajuste_de_credito_soma_em_vl_oc_ipi(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("1000.00"), creditos=d("400.00"))
		ajustes = [AjusteIpi(codigo="050", descricao="", valor=d("100.00"))]
		campos = montar_e520(apuracao, ajustes)

		self.assertEqual(campos["VL_OC_IPI"], d("100.00"))
		self.assertEqual(campos["VL_SD_IPI"], d("500.00"))

	def test_ajuste_pode_transformar_devedor_em_credor(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("100.00"), creditos=d("90.00"))
		campos = montar_e520(apuracao, [AjusteIpi(codigo="050", descricao="", valor=d("30.00"))])

		self.assertEqual(campos["VL_SD_IPI"], d("0.00"))
		self.assertEqual(campos["VL_SC_IPI"], d("20.00"))

	def test_sem_ajustes_e_igual_ao_comportamento_anterior(self):
		apuracao = ApuracaoPeriodo(tributo="IPI", debitos=d("1000.00"), creditos=d("400.00"))

		self.assertEqual(montar_e520(apuracao), montar_e520(apuracao, []))


if __name__ == "__main__":
	unittest.main()
