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


if __name__ == "__main__":
	unittest.main()
