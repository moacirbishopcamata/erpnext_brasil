# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_bloco_0.py` — Bloco 0 do EFD-ICMS/IPI."""

import unittest
from decimal import Decimal as d

from erpnext_brasil.contabil.efd_bloco_0 import (
	ATIVIDADE_INDUSTRIAL,
	ATIVIDADE_OUTROS,
	FINALIDADE_SUBSTITUTO,
	TIPOS_ITEM,
	Identificacao,
	Item,
	Participante,
	montar_0000,
	montar_0001,
	montar_0150,
	montar_0190,
	montar_0200,
	montar_0990,
)
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido


def _identificacao(**overrides) -> Identificacao:
	base = dict(
		codigo_versao="017",
		data_inicial="01012026",
		data_final="31012026",
		nome="Empresa Teste LTDA",
		uf="RO",
		inscricao_estadual="00000000",
		codigo_municipio="1100205",
		perfil="A",
		atividade=ATIVIDADE_INDUSTRIAL,
		cnpj="11222333000181",
	)
	base.update(overrides)

	return Identificacao(**base)


class TestIdentificacao(unittest.TestCase):
	def test_valida(self):
		_identificacao()

	def test_cnpj_e_cpf_juntos_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_identificacao(cpf="11122233344")

	def test_sem_cnpj_nem_cpf_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_identificacao(cnpj="")

	def test_cpf_exige_atividade_outros(self):
		"""Regra cruzada do próprio layout: pessoa física não é industrial na EFD."""
		with self.assertRaises(EfdInvalido):
			_identificacao(cnpj="", cpf="11122233344", atividade=ATIVIDADE_INDUSTRIAL)

	def test_cpf_com_atividade_outros_e_valido(self):
		_identificacao(cnpj="", cpf="11122233344", atividade=ATIVIDADE_OUTROS)

	def test_perfil_invalido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_identificacao(perfil="D")

	def test_finalidade_invalida_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_identificacao(finalidade="2")

	def test_codigo_municipio_fora_do_formato_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_identificacao(codigo_municipio="110020")

	def test_uf_invalida_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_identificacao(uf="RON")


class TestMontar0000(unittest.TestCase):
	def test_quinze_campos_na_ordem_do_layout(self):
		campos = montar_0000(_identificacao())

		self.assertEqual(
			list(campos),
			[
				"REG",
				"COD_VER",
				"COD_FIN",
				"DT_INI",
				"DT_FIN",
				"NOME",
				"CNPJ",
				"CPF",
				"UF",
				"IE",
				"COD_MUN",
				"IM",
				"SUFRAMA",
				"IND_PERFIL",
				"IND_ATIV",
			],
		)
		self.assertEqual(campos["REG"], "0000")

	def test_finalidade_substituto(self):
		campos = montar_0000(_identificacao(finalidade=FINALIDADE_SUBSTITUTO))

		self.assertEqual(campos["COD_FIN"], "1")

	def test_uf_normalizada(self):
		self.assertEqual(montar_0000(_identificacao(uf="ro"))["UF"], "RO")


class TestMontar0001(unittest.TestCase):
	def test_com_dados_e_zero(self):
		"""Achado real: invertido em relação ao `IND_MOV_ST` do E210."""
		self.assertEqual(montar_0001(tem_dados=True)["IND_MOV"], "0")

	def test_sem_dados_e_um(self):
		self.assertEqual(montar_0001(tem_dados=False)["IND_MOV"], "1")


class TestParticipante(unittest.TestCase):
	def test_valido_com_cnpj(self):
		Participante(codigo="F001", nome="Fornecedor", codigo_pais="01058", cnpj="11222333000181")

	def test_valido_sem_cnpj_nem_cpf(self):
		"""Participante estrangeiro: o layout não exige nenhum dos dois."""
		Participante(codigo="E001", nome="Exterior Inc", codigo_pais="02496")

	def test_cnpj_e_cpf_juntos_e_erro(self):
		with self.assertRaises(EfdInvalido):
			Participante(codigo="X", nome="X", codigo_pais="01058", cnpj="11222333000181", cpf="11122233344")

	def test_codigo_vazio_e_erro(self):
		with self.assertRaises(EfdInvalido):
			Participante(codigo="", nome="X", codigo_pais="01058")

	def test_pais_vazio_e_erro(self):
		with self.assertRaises(EfdInvalido):
			Participante(codigo="X", nome="X", codigo_pais="")


class TestMontar0150(unittest.TestCase):
	def test_treze_campos_na_ordem_do_layout(self):
		campos = montar_0150(
			Participante(
				codigo="F001",
				nome="Fornecedor",
				codigo_pais="01058",
				cnpj="11222333000181",
				endereco="Rua A",
				numero="100",
				bairro="Centro",
			)
		)

		self.assertEqual(
			list(campos),
			[
				"REG",
				"COD_PART",
				"NOME",
				"COD_PAIS",
				"CNPJ",
				"CPF",
				"IE",
				"COD_MUN",
				"SUFRAMA",
				"END",
				"NUM",
				"COMPL",
				"BAIRRO",
			],
		)
		self.assertEqual(campos["BAIRRO"], "Centro")


class TestMontar0190(unittest.TestCase):
	def test_tres_campos(self):
		campos = montar_0190("UN", "Unidade")

		self.assertEqual(list(campos), ["REG", "UNID", "DESCR"])
		self.assertEqual(campos["UNID"], "UN")

	def test_unidade_vazia_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_0190("", "Unidade")

	def test_descricao_vazia_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_0190("UN", "")


class TestItem(unittest.TestCase):
	def test_valido(self):
		Item(codigo="P1", descricao="Produto", unidade_inventario="UN", tipo="00")

	def test_tipo_invalido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			Item(codigo="P1", descricao="Produto", unidade_inventario="UN", tipo="50")

	def test_todos_os_tipos_da_tabela_sao_aceitos(self):
		for tipo in TIPOS_ITEM:
			Item(codigo="P1", descricao="Produto", unidade_inventario="UN", tipo=tipo)

	def test_ncm_fora_do_formato_e_erro(self):
		with self.assertRaises(EfdInvalido):
			Item(codigo="P1", descricao="P", unidade_inventario="UN", tipo="00", codigo_ncm="123")

	def test_ncm_vazio_e_aceito(self):
		Item(codigo="P1", descricao="P", unidade_inventario="UN", tipo="09")

	def test_unidade_vazia_e_erro(self):
		with self.assertRaises(EfdInvalido):
			Item(codigo="P1", descricao="P", unidade_inventario="", tipo="00")


class TestMontar0200(unittest.TestCase):
	def test_treze_campos_incluindo_cest(self):
		"""O 13º campo (CEST) não existe no Guia de 2013 — foi acrescentado em 2017."""
		campos = montar_0200(
			Item(
				codigo="P1",
				descricao="Produto",
				unidade_inventario="UN",
				tipo="00",
				codigo_ncm="84713019",
				aliquota_icms=d("17.50"),
				cest="2810400",
			)
		)

		self.assertEqual(
			list(campos),
			[
				"REG",
				"COD_ITEM",
				"DESCR_ITEM",
				"COD_BARRA",
				"COD_ANT_ITEM",
				"UNID_INV",
				"TIPO_ITEM",
				"COD_NCM",
				"EX_IPI",
				"COD_GEN",
				"COD_LST",
				"ALIQ_ICMS",
				"CEST",
			],
		)
		self.assertEqual(campos["CEST"], "2810400")
		self.assertEqual(campos["ALIQ_ICMS"], d("17.50"))

	def test_cest_vazio_nao_e_erro(self):
		"""O layout manda não preencher quando mais de um CEST cabe no produto."""
		campos = montar_0200(Item(codigo="P1", descricao="P", unidade_inventario="UN", tipo="00"))

		self.assertEqual(campos["CEST"], "")


class TestMontar0990(unittest.TestCase):
	def test_contagem_de_linhas(self):
		campos = montar_0990(42)

		self.assertEqual(list(campos), ["REG", "QTD_LIN_0"])
		self.assertEqual(campos["QTD_LIN_0"], "42")

	def test_contagem_impossivel_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_0990(1)


if __name__ == "__main__":
	unittest.main()
