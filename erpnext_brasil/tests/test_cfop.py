# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/cfop.py` — determinação do CFOP para o núcleo de dezesseis
códigos cobertos (compra, venda, devolução de venda, devolução de compra)."""

import unittest

from erpnext_brasil.fiscal.cfop import (
	FINALIDADE_COMERCIALIZACAO,
	FINALIDADE_INDUSTRIALIZACAO,
	CfopInvalido,
	cfop_compra,
	cfop_devolucao_compra,
	cfop_devolucao_venda,
	cfop_entrada_para_industrializacao,
	cfop_remessa_para_industrializacao,
	cfop_retorno_da_industrializacao_realizada,
	cfop_retorno_de_industrializacao,
	cfop_venda,
)


class TestCfopCompra(unittest.TestCase):
	def test_industrializacao_mesmo_estado(self):
		self.assertEqual(cfop_compra(mesmo_estado=True, finalidade=FINALIDADE_INDUSTRIALIZACAO), "1101")

	def test_industrializacao_outro_estado(self):
		self.assertEqual(cfop_compra(mesmo_estado=False, finalidade=FINALIDADE_INDUSTRIALIZACAO), "2101")

	def test_comercializacao_mesmo_estado(self):
		self.assertEqual(cfop_compra(mesmo_estado=True, finalidade=FINALIDADE_COMERCIALIZACAO), "1102")

	def test_comercializacao_outro_estado(self):
		self.assertEqual(cfop_compra(mesmo_estado=False, finalidade=FINALIDADE_COMERCIALIZACAO), "2102")

	def test_finalidade_invalida_e_erro(self):
		with self.assertRaises(CfopInvalido):
			cfop_compra(mesmo_estado=True, finalidade="uso_e_consumo")


class TestCfopVenda(unittest.TestCase):
	def test_producao_propria_mesmo_estado(self):
		self.assertEqual(cfop_venda(mesmo_estado=True, producao_propria=True), "5101")

	def test_producao_propria_outro_estado(self):
		self.assertEqual(cfop_venda(mesmo_estado=False, producao_propria=True), "6101")

	def test_mercadoria_de_terceiros_mesmo_estado(self):
		self.assertEqual(cfop_venda(mesmo_estado=True, producao_propria=False), "5102")

	def test_mercadoria_de_terceiros_outro_estado(self):
		self.assertEqual(cfop_venda(mesmo_estado=False, producao_propria=False), "6102")


class TestCfopDevolucaoVenda(unittest.TestCase):
	def test_producao_propria_mesmo_estado(self):
		self.assertEqual(cfop_devolucao_venda(mesmo_estado=True, producao_propria=True), "1201")

	def test_producao_propria_outro_estado(self):
		self.assertEqual(cfop_devolucao_venda(mesmo_estado=False, producao_propria=True), "2201")

	def test_mercadoria_de_terceiros_mesmo_estado(self):
		self.assertEqual(cfop_devolucao_venda(mesmo_estado=True, producao_propria=False), "1202")

	def test_mercadoria_de_terceiros_outro_estado(self):
		self.assertEqual(cfop_devolucao_venda(mesmo_estado=False, producao_propria=False), "2202")


class TestCfopDevolucaoCompra(unittest.TestCase):
	def test_industrializacao_mesmo_estado(self):
		self.assertEqual(
			cfop_devolucao_compra(mesmo_estado=True, finalidade=FINALIDADE_INDUSTRIALIZACAO), "5201"
		)

	def test_industrializacao_outro_estado(self):
		self.assertEqual(
			cfop_devolucao_compra(mesmo_estado=False, finalidade=FINALIDADE_INDUSTRIALIZACAO), "6201"
		)

	def test_comercializacao_mesmo_estado(self):
		self.assertEqual(
			cfop_devolucao_compra(mesmo_estado=True, finalidade=FINALIDADE_COMERCIALIZACAO), "5202"
		)

	def test_comercializacao_outro_estado(self):
		self.assertEqual(
			cfop_devolucao_compra(mesmo_estado=False, finalidade=FINALIDADE_COMERCIALIZACAO), "6202"
		)

	def test_finalidade_invalida_e_erro(self):
		with self.assertRaises(CfopInvalido):
			cfop_devolucao_compra(mesmo_estado=True, finalidade="ativo_imobilizado")


class TestSimetriaEntreParesEspelhados(unittest.TestCase):
	"""cfop_devolucao_venda é o espelho de cfop_venda — mesmos dois últimos dígitos
	(a finalidade), mas a devolução é ENTRADA (venda original é SAÍDA): o primeiro
	dígito não é o mesmo, e sim o par 5→1/6→2 (mesmo estado/outro estado, saída para
	entrada). cfop_devolucao_compra é o espelho de cfop_compra pela razão oposta."""

	def test_devolucao_de_venda_espelha_venda(self):
		correspondencia_primeiro_digito = {"5": "1", "6": "2"}

		for mesmo_estado in (True, False):
			for producao_propria in (True, False):
				venda = cfop_venda(mesmo_estado, producao_propria)
				devolucao = cfop_devolucao_venda(mesmo_estado, producao_propria)

				self.assertEqual(correspondencia_primeiro_digito[venda[0]], devolucao[0])
				self.assertEqual(venda[2:], devolucao[2:])
				self.assertEqual(venda[1], "1")
				self.assertEqual(devolucao[1], "2")

	def test_devolucao_de_compra_espelha_compra(self):
		for mesmo_estado in (True, False):
			for finalidade in (FINALIDADE_INDUSTRIALIZACAO, FINALIDADE_COMERCIALIZACAO):
				compra = cfop_compra(mesmo_estado, finalidade)
				devolucao = cfop_devolucao_compra(mesmo_estado, finalidade)

				# Compra é grupo 1xxx/2xxx (entrada); devolução de compra é 5xxx/6xxx
				# (saída) -- só os dois últimos dígitos e o "1" x "5"/"2" x "6" batem.
				self.assertEqual(compra[2:], devolucao[2:])


class TestCfopImportacaoExportacao(unittest.TestCase):
	"""Compra/venda com o exterior — mesmo segundo e últimos dois dígitos das
	operações domésticas, só o primeiro dígito muda (`1`/`2`→`3`, `5`/`6`→`7`)."""

	def test_compra_importacao_industrializacao(self):
		self.assertEqual(
			cfop_compra(mesmo_estado=True, finalidade=FINALIDADE_INDUSTRIALIZACAO, exterior=True), "3101"
		)

	def test_compra_importacao_comercializacao(self):
		self.assertEqual(
			cfop_compra(mesmo_estado=True, finalidade=FINALIDADE_COMERCIALIZACAO, exterior=True), "3102"
		)

	def test_compra_importacao_ignora_mesmo_estado(self):
		"""Importação não distingue UF de origem -- mesmo_estado=False dá o mesmo
		resultado que mesmo_estado=True quando exterior=True."""
		com_true = cfop_compra(mesmo_estado=True, finalidade=FINALIDADE_INDUSTRIALIZACAO, exterior=True)
		com_false = cfop_compra(mesmo_estado=False, finalidade=FINALIDADE_INDUSTRIALIZACAO, exterior=True)

		self.assertEqual(com_true, com_false)

	def test_venda_exportacao_producao_propria(self):
		self.assertEqual(cfop_venda(mesmo_estado=True, producao_propria=True, exterior=True), "7101")

	def test_venda_exportacao_mercadoria_de_terceiros(self):
		self.assertEqual(cfop_venda(mesmo_estado=True, producao_propria=False, exterior=True), "7102")

	def test_venda_exportacao_ignora_mesmo_estado(self):
		com_true = cfop_venda(mesmo_estado=True, producao_propria=True, exterior=True)
		com_false = cfop_venda(mesmo_estado=False, producao_propria=True, exterior=True)

		self.assertEqual(com_true, com_false)


class TestCfopIndustrializacaoPorEncomenda(unittest.TestCase):
	def test_remessa_para_industrializacao_mesmo_estado(self):
		self.assertEqual(cfop_remessa_para_industrializacao(mesmo_estado=True), "5901")

	def test_remessa_para_industrializacao_outro_estado(self):
		self.assertEqual(cfop_remessa_para_industrializacao(mesmo_estado=False), "6901")

	def test_entrada_para_industrializacao_mesmo_estado(self):
		self.assertEqual(cfop_entrada_para_industrializacao(mesmo_estado=True), "1901")

	def test_entrada_para_industrializacao_outro_estado(self):
		self.assertEqual(cfop_entrada_para_industrializacao(mesmo_estado=False), "2901")

	def test_retorno_de_industrializacao_mesmo_estado(self):
		self.assertEqual(cfop_retorno_de_industrializacao(mesmo_estado=True), "1902")

	def test_retorno_de_industrializacao_outro_estado(self):
		self.assertEqual(cfop_retorno_de_industrializacao(mesmo_estado=False), "2902")

	def test_retorno_da_industrializacao_realizada_mesmo_estado(self):
		self.assertEqual(cfop_retorno_da_industrializacao_realizada(mesmo_estado=True), "5902")

	def test_retorno_da_industrializacao_realizada_outro_estado(self):
		self.assertEqual(cfop_retorno_da_industrializacao_realizada(mesmo_estado=False), "6902")


if __name__ == "__main__":
	unittest.main()
