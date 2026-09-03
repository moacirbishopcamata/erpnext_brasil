# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_icms_st.py` — E200/E210/E220 (apuração do ICMS-ST)."""

import unittest
from decimal import Decimal as d

from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido
from erpnext_brasil.contabil.efd_icms_st import (
	IND_MOV_COM_OPERACOES,
	IND_MOV_SEM_OPERACOES,
	AjusteSt,
	ApuracaoSt,
	montar_e200,
	montar_e210,
	montar_e220,
)


class TestMontarE200(unittest.TestCase):
	def test_campos_na_ordem_do_layout(self):
		campos = montar_e200("MG", "01012026", "31012026")

		self.assertEqual(list(campos), ["REG", "UF", "DT_INI", "DT_FIN"])
		self.assertEqual(campos["REG"], "E200")
		self.assertEqual(campos["UF"], "MG")

	def test_uf_normalizada_para_maiuscula(self):
		self.assertEqual(montar_e200("ro", "01012026", "31012026")["UF"], "RO")

	def test_uf_fora_do_formato_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_e200("MGX", "01012026", "31012026")


class TestAjusteSt(unittest.TestCase):
	def test_codigo_valido(self):
		self.assertEqual(AjusteSt(codigo="MG100001", descricao="", valor=d("1.00")).tipo, "0")

	def test_codigo_de_operacoes_proprias_e_recusado(self):
		"""3º caractere `0` é ICMS próprio — pertence ao E111, não ao E220."""
		with self.assertRaises(EfdInvalido):
			AjusteSt(codigo="MG000001", descricao="", valor=d("1.00"))

	def test_estorno_de_credito_e_recusado(self):
		"""Achado real: a apuração da ST não tem campo de estorno."""
		with self.assertRaises(EfdInvalido):
			AjusteSt(codigo="MG110001", descricao="", valor=d("1.00"))

	def test_estorno_de_debito_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteSt(codigo="MG130001", descricao="", valor=d("1.00"))

	def test_tipo_desconhecido_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteSt(codigo="MG190001", descricao="", valor=d("1.00"))

	def test_codigo_com_tamanho_errado_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteSt(codigo="MG10", descricao="", valor=d("1.00"))

	def test_valor_negativo_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			AjusteSt(codigo="MG100001", descricao="", valor=d("-1.00"))


class TestMontarE220(unittest.TestCase):
	def test_uma_linha_por_ajuste(self):
		linhas = montar_e220(
			[
				AjusteSt(codigo="MG100001", descricao="Outros débitos ST", valor=d("50.00")),
				AjusteSt(codigo="MG140001", descricao="Dedução ST", valor=d("10.00")),
			]
		)

		self.assertEqual(len(linhas), 2)
		self.assertEqual(list(linhas[0]), ["REG", "COD_AJ_APUR", "DESCR_COMPL_AJ", "VL_AJ_APUR"])
		self.assertEqual(linhas[0]["COD_AJ_APUR"], "MG100001")
		self.assertEqual(linhas[1]["VL_AJ_APUR"], d("10.00"))

	def test_sem_ajustes_devolve_lista_vazia(self):
		self.assertEqual(montar_e220([]), [])


class TestMontarE210(unittest.TestCase):
	def test_ordem_dos_quinze_campos(self):
		campos = montar_e210(ApuracaoSt(retencao=d("100.00")))

		self.assertEqual(
			list(campos),
			[
				"REG",
				"IND_MOV_ST",
				"VL_SLD_CRED_ANT_ST",
				"VL_DEVOL_ST",
				"VL_RESSARC_ST",
				"VL_OUT_CRED_ST",
				"VL_AJ_CREDITOS_ST",
				"VL_RETENCAO_ST",
				"VL_OUT_DEB_ST",
				"VL_AJ_DEBITOS_ST",
				"VL_SLD_DEV_ANT_ST",
				"VL_DEDUCOES_ST",
				"VL_ICMS_RECOL_ST",
				"VL_SLD_CRED_ST_TRANSPORTAR",
				"DEB_ESP_ST",
			],
		)

	def test_so_retencao_vira_imposto_a_recolher(self):
		campos = montar_e210(ApuracaoSt(retencao=d("100.00")))

		self.assertEqual(campos["VL_SLD_DEV_ANT_ST"], d("100.00"))
		self.assertEqual(campos["VL_ICMS_RECOL_ST"], d("100.00"))
		self.assertEqual(campos["VL_SLD_CRED_ST_TRANSPORTAR"], d("0.00"))

	def test_credito_maior_que_debito_vira_saldo_a_transportar(self):
		campos = montar_e210(ApuracaoSt(retencao=d("10.00"), saldo_credor_anterior=d("30.00")))

		self.assertEqual(campos["VL_SLD_DEV_ANT_ST"], d("0.00"))
		self.assertEqual(campos["VL_ICMS_RECOL_ST"], d("0.00"))
		self.assertEqual(campos["VL_SLD_CRED_ST_TRANSPORTAR"], d("20.00"))

	def test_devolucao_e_ressarcimento_sao_credito(self):
		campos = montar_e210(ApuracaoSt(retencao=d("100.00"), devolucao=d("15.00"), ressarcimento=d("25.00")))

		self.assertEqual(campos["VL_DEVOL_ST"], d("15.00"))
		self.assertEqual(campos["VL_RESSARC_ST"], d("25.00"))
		self.assertEqual(campos["VL_ICMS_RECOL_ST"], d("60.00"))

	def test_ajustes_somam_no_campo_certo(self):
		campos = montar_e210(
			ApuracaoSt(retencao=d("100.00")),
			[
				AjusteSt(codigo="MG100001", descricao="", valor=d("10.00")),  # outros débitos
				AjusteSt(codigo="MG120001", descricao="", valor=d("30.00")),  # outros créditos
				AjusteSt(codigo="MG140001", descricao="", valor=d("5.00")),  # dedução
				AjusteSt(codigo="MG150001", descricao="", valor=d("7.00")),  # débito especial
			],
		)

		self.assertEqual(campos["VL_OUT_DEB_ST"], d("10.00"))
		self.assertEqual(campos["VL_OUT_CRED_ST"], d("30.00"))
		self.assertEqual(campos["VL_DEDUCOES_ST"], d("5.00"))
		self.assertEqual(campos["DEB_ESP_ST"], d("7.00"))

	def test_deducao_entra_so_depois_do_saldo_devedor(self):
		"""`VL_SLD_DEV_ANT_ST` é o saldo **antes** das deduções — a dedução aparece
		só no campo seguinte."""
		campos = montar_e210(
			ApuracaoSt(retencao=d("100.00")),
			[AjusteSt(codigo="MG140001", descricao="", valor=d("40.00"))],
		)

		self.assertEqual(campos["VL_SLD_DEV_ANT_ST"], d("100.00"))
		self.assertEqual(campos["VL_ICMS_RECOL_ST"], d("60.00"))

	def test_debito_especial_fica_fora_da_conta(self):
		"""Valor extra-apuração: aparece no campo, não muda o imposto a recolher —
		mesmo tratamento do `DEB_ESP` no E110."""
		campos = montar_e210(
			ApuracaoSt(retencao=d("100.00")),
			[AjusteSt(codigo="MG150001", descricao="", valor=d("999.00"))],
		)

		self.assertEqual(campos["DEB_ESP_ST"], d("999.00"))
		self.assertEqual(campos["VL_ICMS_RECOL_ST"], d("100.00"))

	def test_deducao_maior_que_saldo_devedor_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_e210(
				ApuracaoSt(retencao=d("10.00")),
				[AjusteSt(codigo="MG140001", descricao="", valor=d("50.00"))],
			)

	def test_ind_mov_sem_operacoes_quando_tudo_zerado(self):
		campos = montar_e210(ApuracaoSt(retencao=d("0.00")))

		self.assertEqual(campos["IND_MOV_ST"], IND_MOV_SEM_OPERACOES)

	def test_ind_mov_com_operacoes_quando_ha_qualquer_valor(self):
		campos = montar_e210(ApuracaoSt(retencao=d("0.00"), saldo_credor_anterior=d("1.00")))

		self.assertEqual(campos["IND_MOV_ST"], IND_MOV_COM_OPERACOES)

	def test_ind_mov_com_operacoes_quando_so_ha_ajuste(self):
		campos = montar_e210(
			ApuracaoSt(retencao=d("0.00")),
			[AjusteSt(codigo="MG150001", descricao="", valor=d("1.00"))],
		)

		self.assertEqual(campos["IND_MOV_ST"], IND_MOV_COM_OPERACOES)

	def test_ajustes_vinculados_a_documento_ficam_zerados(self):
		"""Fora de escopo declarado, mesma decisão do E110."""
		campos = montar_e210(ApuracaoSt(retencao=d("100.00")))

		self.assertEqual(campos["VL_AJ_CREDITOS_ST"], d("0.00"))
		self.assertEqual(campos["VL_AJ_DEBITOS_ST"], d("0.00"))

	def test_valor_negativo_na_apuracao_e_erro(self):
		with self.assertRaises(EfdInvalido):
			ApuracaoSt(retencao=d("-1.00"))


if __name__ == "__main__":
	unittest.main()
