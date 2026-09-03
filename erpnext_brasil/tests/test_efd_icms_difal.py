# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_icms_difal.py` — E300/E310/E311 (apuração do DIFAL e do FCP)."""

import unittest
from decimal import Decimal as d

from erpnext_brasil.contabil.efd_icms_difal import (
	IND_MOV_COM_OPERACOES,
	IND_MOV_SEM_OPERACOES,
	AjusteDifal,
	ApuracaoDifal,
	montar_e300,
	montar_e310,
	montar_e311,
)
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido


class TestMontarE300(unittest.TestCase):
	def test_campos_na_ordem_do_layout(self):
		campos = montar_e300("MG", "01012026", "31012026")

		self.assertEqual(list(campos), ["REG", "UF", "DT_INI", "DT_FIN"])
		self.assertEqual(campos["REG"], "E300")

	def test_uf_normalizada(self):
		self.assertEqual(montar_e300("ro", "01012026", "31012026")["UF"], "RO")

	def test_uf_invalida_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_e300("M", "01012026", "31012026")


class TestAjusteDifal(unittest.TestCase):
	def test_codigo_valido(self):
		self.assertEqual(AjusteDifal(codigo="MG200001", descricao="", valor=d("1.00")).tipo, "0")

	def test_codigo_de_operacoes_proprias_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteDifal(codigo="MG000001", descricao="", valor=d("1.00"))

	def test_codigo_de_st_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteDifal(codigo="MG100001", descricao="", valor=d("1.00"))

	def test_estorno_e_aceito_diferente_do_e220(self):
		"""No E310 o estorno tem destino (campos 'outros'), diferente da ST."""
		self.assertEqual(AjusteDifal(codigo="MG210001", descricao="", valor=d("1.00")).tipo, "1")
		self.assertEqual(AjusteDifal(codigo="MG230001", descricao="", valor=d("1.00")).tipo, "3")

	def test_tipo_desconhecido_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteDifal(codigo="MG290001", descricao="", valor=d("1.00"))

	def test_tamanho_errado_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteDifal(codigo="MG20", descricao="", valor=d("1.00"))

	def test_valor_negativo_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteDifal(codigo="MG200001", descricao="", valor=d("-1.00"))


class TestMontarE311(unittest.TestCase):
	def test_uma_linha_por_ajuste(self):
		linhas = montar_e311([AjusteDifal(codigo="MG200001", descricao="Outros débitos", valor=d("5.00"))])

		self.assertEqual(list(linhas[0]), ["REG", "COD_AJ_APUR", "DESCR_COMPL_AJ", "VL_AJ_APUR"])
		self.assertEqual(linhas[0]["REG"], "E311")

	def test_sem_ajustes_devolve_lista_vazia(self):
		self.assertEqual(montar_e311([]), [])


class TestMontarE310(unittest.TestCase):
	def test_ordem_dos_vinte_e_dois_campos(self):
		campos = montar_e310(ApuracaoDifal(total_debitos=d("100.00")))

		self.assertEqual(
			list(campos),
			[
				"REG",
				"IND_MOV_FCP_DIFAL",
				"VL_SLD_CRED_ANT_DIFAL",
				"VL_TOT_DEBITOS_DIFAL",
				"VL_OUT_DEB_DIFAL",
				"VL_TOT_CREDITOS_DIFAL",
				"VL_OUT_CRED_DIFAL",
				"VL_SLD_DEV_ANT_DIFAL",
				"VL_DEDUCOES_DIFAL",
				"VL_RECOL_DIFAL",
				"VL_SLD_CRED_TRANSPORTAR_DIFAL",
				"DEB_ESP_DIFAL",
				"VL_SLD_CRED_ANT_FCP",
				"VL_TOT_DEB_FCP",
				"VL_OUT_DEB_FCP",
				"VL_TOT_CRED_FCP",
				"VL_OUT_CRED_FCP",
				"VL_SLD_DEV_ANT_FCP",
				"VL_DEDUCOES_FCP",
				"VL_RECOL_FCP",
				"VL_SLD_CRED_TRANSPORTAR_FCP",
				"DEB_ESP_FCP",
			],
		)

	def test_formula_do_saldo_devedor(self):
		"""Campo 08 = (04 + 05) - (03 + 06 + 07), quando >= 0."""
		campos = montar_e310(
			ApuracaoDifal(
				total_debitos=d("100.00"), total_creditos=d("30.00"), saldo_credor_anterior=d("10.00")
			)
		)

		self.assertEqual(campos["VL_SLD_DEV_ANT_DIFAL"], d("60.00"))
		self.assertEqual(campos["VL_RECOL_DIFAL"], d("60.00"))
		self.assertEqual(campos["VL_SLD_CRED_TRANSPORTAR_DIFAL"], d("0.00"))

	def test_credito_maior_vira_saldo_a_transportar(self):
		campos = montar_e310(ApuracaoDifal(total_debitos=d("10.00"), total_creditos=d("40.00")))

		self.assertEqual(campos["VL_SLD_DEV_ANT_DIFAL"], d("0.00"))
		self.assertEqual(campos["VL_RECOL_DIFAL"], d("0.00"))
		self.assertEqual(campos["VL_SLD_CRED_TRANSPORTAR_DIFAL"], d("30.00"))

	def test_deducao_maior_que_saldo_devedor_zera_sem_erro(self):
		"""Divergência declarada: E110/E210 levantam erro aqui; o E310 tem fórmula
		oficial com piso em zero (campo 10 = 08 - 09 quando >= 0, senão 0)."""
		campos = montar_e310(
			ApuracaoDifal(total_debitos=d("10.00")),
			[AjusteDifal(codigo="MG240001", descricao="", valor=d("50.00"))],
		)

		self.assertEqual(campos["VL_SLD_DEV_ANT_DIFAL"], d("10.00"))
		self.assertEqual(campos["VL_DEDUCOES_DIFAL"], d("50.00"))
		self.assertEqual(campos["VL_RECOL_DIFAL"], d("0.00"))

	def test_estorno_de_credito_soma_em_outros_debitos(self):
		"""Achado real: o campo se chama 'Outros débitos e estornos de créditos'."""
		campos = montar_e310(
			ApuracaoDifal(total_debitos=d("100.00")),
			[
				AjusteDifal(codigo="MG200001", descricao="", valor=d("10.00")),  # outros débitos
				AjusteDifal(codigo="MG210001", descricao="", valor=d("5.00")),  # estorno de crédito
			],
		)

		self.assertEqual(campos["VL_OUT_DEB_DIFAL"], d("15.00"))

	def test_estorno_de_debito_soma_em_outros_creditos(self):
		campos = montar_e310(
			ApuracaoDifal(total_debitos=d("100.00")),
			[
				AjusteDifal(codigo="MG220001", descricao="", valor=d("20.00")),  # outros créditos
				AjusteDifal(codigo="MG230001", descricao="", valor=d("7.00")),  # estorno de débito
			],
		)

		self.assertEqual(campos["VL_OUT_CRED_DIFAL"], d("27.00"))

	def test_debito_especial_fica_fora_da_conta(self):
		campos = montar_e310(
			ApuracaoDifal(total_debitos=d("100.00")),
			[AjusteDifal(codigo="MG250001", descricao="", valor=d("999.00"))],
		)

		self.assertEqual(campos["DEB_ESP_DIFAL"], d("999.00"))
		self.assertEqual(campos["VL_RECOL_DIFAL"], d("100.00"))

	def test_metade_fcp_usa_a_mesma_formula(self):
		campos = montar_e310(
			ApuracaoDifal(
				total_debitos_fcp=d("80.00"),
				total_creditos_fcp=d("20.00"),
				saldo_credor_anterior_fcp=d("5.00"),
				deducoes_fcp=d("15.00"),
			)
		)

		self.assertEqual(campos["VL_SLD_DEV_ANT_FCP"], d("55.00"))
		self.assertEqual(campos["VL_RECOL_FCP"], d("40.00"))
		self.assertEqual(campos["VL_SLD_CRED_TRANSPORTAR_FCP"], d("0.00"))

	def test_ajuste_do_e311_nao_vaza_para_a_metade_fcp(self):
		"""Roteamento DIFAL→FCP não é confirmado pela fonte — o ajuste fica só na
		metade DIFAL, e os campos do FCP vêm de `ApuracaoDifal`."""
		campos = montar_e310(
			ApuracaoDifal(total_debitos=d("100.00"), total_debitos_fcp=d("10.00")),
			[AjusteDifal(codigo="MG200001", descricao="", valor=d("50.00"))],
		)

		self.assertEqual(campos["VL_OUT_DEB_DIFAL"], d("50.00"))
		self.assertEqual(campos["VL_OUT_DEB_FCP"], d("0.00"))

	def test_ind_mov_sem_operacoes_quando_tudo_zerado(self):
		self.assertEqual(montar_e310(ApuracaoDifal())["IND_MOV_FCP_DIFAL"], IND_MOV_SEM_OPERACOES)

	def test_ind_mov_com_operacoes_quando_so_ha_fcp(self):
		campos = montar_e310(ApuracaoDifal(total_debitos_fcp=d("1.00")))

		self.assertEqual(campos["IND_MOV_FCP_DIFAL"], IND_MOV_COM_OPERACOES)

	def test_ind_mov_com_operacoes_quando_so_ha_debito_especial(self):
		campos = montar_e310(ApuracaoDifal(), [AjusteDifal(codigo="MG250001", descricao="", valor=d("1.00"))])

		self.assertEqual(campos["IND_MOV_FCP_DIFAL"], IND_MOV_COM_OPERACOES)

	def test_valor_negativo_na_apuracao_e_erro(self):
		with self.assertRaises(EfdInvalido):
			ApuracaoDifal(total_debitos=d("-1.00"))


if __name__ == "__main__":
	unittest.main()
