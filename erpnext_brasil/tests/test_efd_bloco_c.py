# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_bloco_c.py` — Bloco C do EFD-ICMS/IPI (documentos fiscais)."""

import unittest
from decimal import Decimal as d

from erpnext_brasil.contabil.efd_bloco_c import (
	EMISSAO_PROPRIA,
	IND_FRT_VALIDOS,
	MODELO_NFCE,
	MODELO_NFE,
	OPERACAO_SAIDA,
	DocumentoFiscal,
	RegistroAnalitico,
	montar_c001,
	montar_c100,
	montar_c190,
	montar_c990,
)
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave

CHAVE = montar_chave("35", "2601", "11222333000181", MODELO_NFE, "1", "1", "1", "12345678")
CHAVE_NFCE = montar_chave("35", "2601", "11222333000181", MODELO_NFCE, "1", "2", "1", "12345678")


def _documento(**overrides) -> DocumentoFiscal:
	base = dict(
		operacao=OPERACAO_SAIDA,
		emissao=EMISSAO_PROPRIA,
		codigo_modelo=MODELO_NFE,
		codigo_situacao="00",
		numero="1",
		data_emissao="15012026",
		valor_documento=d("1000.00"),
		indicador_pagamento="0",
		indicador_frete="0",
		codigo_participante="C001",
		chave_acesso=CHAVE,
	)
	base.update(overrides)

	return DocumentoFiscal(**base)


class TestDocumentoFiscal(unittest.TestCase):
	def test_valido(self):
		_documento()

	def test_operacao_invalida_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(operacao="2")

	def test_emissao_invalida_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(emissao="2")

	def test_situacao_invalida_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(codigo_situacao="99")

	def test_numero_vazio_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(numero="")


class TestIndicadorFrete(unittest.TestCase):
	def test_todos_os_seis_valores_vigentes_sao_aceitos(self):
		"""Tabela vigente desde 01/01/2018: 0-4 e 9."""
		for codigo in IND_FRT_VALIDOS:
			_documento(indicador_frete=codigo)

	def test_transporte_proprio_e_aceito(self):
		"""Códigos 3 e 4 não existiam antes de 2018 — usar uma fonte antiga os
		rejeitaria."""
		self.assertIn("3", IND_FRT_VALIDOS)
		self.assertIn("4", IND_FRT_VALIDOS)

	def test_valor_fora_da_tabela_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(indicador_frete="5")


class TestChaveDeAcesso(unittest.TestCase):
	def test_chave_obrigatoria_para_nfe(self):
		with self.assertRaises(EfdInvalido):
			_documento(chave_acesso="")

	def test_chave_dispensada_com_numeracao_inutilizada(self):
		"""Única exceção do guia à obrigatoriedade da chave."""
		_documento(codigo_situacao="05", chave_acesso="")

	def test_chave_invalida_e_erro(self):
		"""Reaproveita `validar_chave` da família NF-e — dígito verificador de verdade."""
		with self.assertRaises(EfdInvalido):
			_documento(chave_acesso="1" * 44)

	def test_documento_em_papel_nao_exige_chave(self):
		_documento(codigo_modelo="01", chave_acesso="")


class TestRegrasDaNfce(unittest.TestCase):
	def test_nfce_valida_sem_participante_nem_st(self):
		_documento(codigo_modelo=MODELO_NFCE, chave_acesso=CHAVE_NFCE, codigo_participante="")

	def test_nfce_com_participante_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(codigo_modelo=MODELO_NFCE, chave_acesso=CHAVE_NFCE, codigo_participante="C001")

	def test_nfce_com_icms_st_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(
				codigo_modelo=MODELO_NFCE,
				chave_acesso=CHAVE_NFCE,
				codigo_participante="",
				valor_icms_st=d("10.00"),
			)

	def test_nfce_com_ipi_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(
				codigo_modelo=MODELO_NFCE,
				chave_acesso=CHAVE_NFCE,
				codigo_participante="",
				valor_ipi=d("5.00"),
			)

	def test_nfe_com_icms_st_e_valido(self):
		"""A proibição é só da NFC-e — a NF-e informa normalmente."""
		_documento(valor_icms_st=d("10.00"))


class TestMontarC100(unittest.TestCase):
	def test_vinte_e_nove_campos_na_ordem_do_layout(self):
		campos = montar_c100(_documento())

		self.assertEqual(
			list(campos),
			[
				"REG",
				"IND_OPER",
				"IND_EMIT",
				"COD_PART",
				"COD_MOD",
				"COD_SIT",
				"SER",
				"NUM_DOC",
				"CHV_NFE",
				"DT_DOC",
				"DT_E_S",
				"VL_DOC",
				"IND_PGTO",
				"VL_DESC",
				"VL_ABAT_NT",
				"VL_MERC",
				"IND_FRT",
				"VL_FRT",
				"VL_SEG",
				"VL_OUT_DA",
				"VL_BC_ICMS",
				"VL_ICMS",
				"VL_BC_ICMS_ST",
				"VL_ICMS_ST",
				"VL_IPI",
				"VL_PIS",
				"VL_COFINS",
				"VL_PIS_ST",
				"VL_COFINS_ST",
			],
		)
		self.assertEqual(len(campos), 29)

	def test_valores_passam_intactos(self):
		campos = montar_c100(_documento(valor_documento=d("1234.56"), valor_icms=d("180.00")))

		self.assertEqual(campos["VL_DOC"], d("1234.56"))
		self.assertEqual(campos["VL_ICMS"], d("180.00"))
		self.assertEqual(campos["CHV_NFE"], CHAVE)


class TestRegistroAnalitico(unittest.TestCase):
	def test_valido(self):
		RegistroAnalitico(cst_icms="000", cfop="5102", valor_operacao=d("1000.00"))

	def test_cst_fora_do_formato_e_erro(self):
		with self.assertRaises(EfdInvalido):
			RegistroAnalitico(cst_icms="00", cfop="5102", valor_operacao=d("1000.00"))

	def test_cfop_fora_do_formato_e_erro(self):
		with self.assertRaises(EfdInvalido):
			RegistroAnalitico(cst_icms="000", cfop="510", valor_operacao=d("1000.00"))


class TestMontarC190(unittest.TestCase):
	def test_doze_campos_na_ordem_do_layout(self):
		campos = montar_c190(
			RegistroAnalitico(
				cst_icms="000",
				cfop="5102",
				valor_operacao=d("1000.00"),
				valor_bc_icms=d("1000.00"),
				valor_icms=d("180.00"),
				aliquota_icms=d("18.00"),
			)
		)

		self.assertEqual(
			list(campos),
			[
				"REG",
				"CST_ICMS",
				"CFOP",
				"ALIQ_ICMS",
				"VL_OPR",
				"VL_BC_ICMS",
				"VL_ICMS",
				"VL_BC_ICMS_ST",
				"VL_ICMS_ST",
				"VL_RED_BC",
				"VL_IPI",
				"COD_OBS",
			],
		)
		self.assertEqual(len(campos), 12)
		self.assertEqual(campos["VL_ICMS"], d("180.00"))


class TestAberturaEEncerramento(unittest.TestCase):
	def test_c001_com_dados_e_zero(self):
		self.assertEqual(montar_c001(tem_dados=True)["IND_MOV"], "0")

	def test_c001_sem_dados_e_um(self):
		self.assertEqual(montar_c001(tem_dados=False)["IND_MOV"], "1")

	def test_c990_conta_linhas(self):
		campos = montar_c990(10)

		self.assertEqual(list(campos), ["REG", "QTD_LIN_C"])
		self.assertEqual(campos["QTD_LIN_C"], "10")

	def test_c990_contagem_impossivel_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_c990(1)


if __name__ == "__main__":
	unittest.main()
