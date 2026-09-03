# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecf_bloco_j.py` — Bloco J (Plano de Contas e Mapeamento) da ECF.

O teste que mais importa é `test_j050_e_i050_com_reg_trocado`: confirma o achado central
do módulo -- J050 não reimplementa nada, só troca o REG do que a ECD já produz.
"""

import unittest

from erpnext_brasil.contabil.ecd_i050 import MapeamentoReferencial, montar_i050, montar_i051
from erpnext_brasil.contabil.ecf_bloco_j import (
	CentroCusto,
	montar_j001,
	montar_j050,
	montar_j051,
	montar_j100,
	montar_j990,
)
from erpnext_brasil.contabil.plano_de_contas import listar_nomes

DATA = "01012026"


class TestMontarJ001(unittest.TestCase):
	def test_com_dados(self):
		self.assertEqual(montar_j001(tem_dados=True), {"REG": "J001", "IND_DAD": "0"})

	def test_sem_dados(self):
		self.assertEqual(montar_j001(tem_dados=False), {"REG": "J001", "IND_DAD": "1"})


class TestMontarJ050(unittest.TestCase):
	def test_uma_linha_por_conta_da_arvore(self):
		self.assertEqual(len(montar_j050(DATA)), len(listar_nomes()))

	def test_j050_e_i050_com_reg_trocado(self):
		"""Achado central do módulo: J050 não reimplementa nada, é I050 com REG
		trocado -- todos os outros campos batem exatamente."""
		linhas_i050 = montar_i050(DATA)
		linhas_j050 = montar_j050(DATA)

		for linha_i, linha_j in zip(linhas_i050, linhas_j050, strict=True):
			self.assertEqual(linha_j["REG"], "J050")
			for campo in ("DT_ALT", "COD_NAT", "IND_CTA", "NIVEL", "COD_CTA", "COD_CTA_SUP", "CTA"):
				self.assertEqual(linha_j[campo], linha_i[campo])

	def test_cod_nat_fica_dentro_do_subconjunto_01_a_04(self):
		"""J050 admite COD_NAT até '09', mas este projeto só produz contas dos quatro
		grupos do Art. 178/187 -- nunca '05'/'09'."""
		for linha in montar_j050(DATA):
			self.assertIn(linha["COD_NAT"], ("01", "02", "03", "04"))


class TestMontarJ051(unittest.TestCase):
	def test_j051_e_i051_com_reg_trocado(self):
		"""Mesmo achado do J050: J051 é I051 com REG trocado."""
		conta = listar_nomes()[0]
		mapeamentos = [
			MapeamentoReferencial(conta=conta, codigo_referencial="1.01.01.01", centro_custo="001")
		]

		pares_i051 = montar_i051(mapeamentos)
		pares_j051 = montar_j051(mapeamentos)

		for (nome_i, linha_i), (nome_j, linha_j) in zip(pares_i051, pares_j051, strict=True):
			self.assertEqual(nome_i, nome_j)
			self.assertEqual(linha_j["REG"], "J051")
			for campo in ("COD_CCUS", "COD_CTA_REF"):
				self.assertEqual(linha_j[campo], linha_i[campo])


class TestMontarJ100(unittest.TestCase):
	def test_um_item_por_centro_de_custo(self):
		centros = [CentroCusto(codigo="001", nome="Administrativo"), CentroCusto(codigo="002", nome="Vendas")]

		linhas = montar_j100(centros, DATA)

		self.assertEqual(len(linhas), 2)
		self.assertEqual(
			linhas[0], {"REG": "J100", "DT_ALT": DATA, "COD_CCUS": "001", "CCUS": "Administrativo"}
		)

	def test_lista_vazia(self):
		self.assertEqual(montar_j100([], DATA), [])


class TestMontarJ990(unittest.TestCase):
	def test_contagem(self):
		self.assertEqual(montar_j990(42), {"REG": "J990", "QTD_LIN": "42"})


if __name__ == "__main__":
	unittest.main()
