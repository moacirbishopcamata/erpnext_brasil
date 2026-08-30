# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecd_i050.py` — registro I050 da ECD (plano de contas).

O teste que mais importa é `test_patrimonio_liquido_usa_cod_nat_03_nao_02`: é a
pegadinha específica deste módulo — `Patrimônio Líquido` mora dentro de `Passivo` em
`plano_de_contas.py` (mesmo `root_type`), mas a ECD exige `COD_NAT` diferente para os
dois.
"""

import unittest

from erpnext_brasil.contabil.ecd_i050 import (
	COD_NAT_ATIVO,
	COD_NAT_PASSIVO,
	COD_NAT_PATRIMONIO_LIQUIDO,
	COD_NAT_RESULTADO,
	montar_i050,
)
from erpnext_brasil.contabil.plano_de_contas import listar_nomes, montar_codigos

DATA = "01012026"


def _por_nome(linhas: list[dict], nome: str) -> dict:
	return next(linha for linha in linhas if linha["CTA"] == nome)


class TestMontarI050(unittest.TestCase):
	def setUp(self):
		self.linhas = montar_i050(DATA)

	def test_uma_linha_por_conta_da_arvore(self):
		self.assertEqual(len(self.linhas), len(listar_nomes()))

	def test_ordem_dos_campos(self):
		self.assertEqual(
			list(self.linhas[0]),
			["REG", "DT_ALT", "COD_NAT", "IND_CTA", "NIVEL", "COD_CTA", "COD_CTA_SUP", "CTA"],
		)

	def test_reg_e_dt_alt_fixos(self):
		self.assertTrue(all(linha["REG"] == "I050" for linha in self.linhas))
		self.assertTrue(all(linha["DT_ALT"] == DATA for linha in self.linhas))

	def test_ativo_usa_cod_nat_01(self):
		self.assertEqual(_por_nome(self.linhas, "Ativo")["COD_NAT"], COD_NAT_ATIVO)
		self.assertEqual(_por_nome(self.linhas, "Clientes")["COD_NAT"], COD_NAT_ATIVO)

	def test_patrimonio_liquido_usa_cod_nat_03_nao_02(self):
		"""A pegadinha: mesmo root_type de Passivo (COD_NAT 02) em plano_de_contas.py,
		mas a ECD exige 03 para o subgrupo Patrimônio Líquido."""
		self.assertEqual(_por_nome(self.linhas, "Passivo Circulante")["COD_NAT"], COD_NAT_PASSIVO)
		self.assertEqual(_por_nome(self.linhas, "Patrimônio Líquido")["COD_NAT"], COD_NAT_PATRIMONIO_LIQUIDO)
		# e as folhas dentro de Patrimônio Líquido herdam o 03, não o 02 do avô Passivo.
		self.assertEqual(_por_nome(self.linhas, "Capital Social")["COD_NAT"], COD_NAT_PATRIMONIO_LIQUIDO)

	def test_receita_e_despesa_compartilham_cod_nat_04(self):
		self.assertEqual(_por_nome(self.linhas, "Receita")["COD_NAT"], COD_NAT_RESULTADO)
		self.assertEqual(_por_nome(self.linhas, "Despesa")["COD_NAT"], COD_NAT_RESULTADO)

	def test_ind_cta_s_para_grupo_a_para_folha(self):
		self.assertEqual(_por_nome(self.linhas, "Ativo")["IND_CTA"], "S")
		self.assertEqual(_por_nome(self.linhas, "Clientes")["IND_CTA"], "A")

	def test_nivel_e_a_profundidade_do_codigo(self):
		self.assertEqual(_por_nome(self.linhas, "Ativo")["NIVEL"], 1)
		self.assertEqual(_por_nome(self.linhas, "Ativo Circulante")["NIVEL"], 2)
		self.assertEqual(_por_nome(self.linhas, "Clientes")["NIVEL"], 3)

	def test_cod_cta_sup_e_o_codigo_do_pai(self):
		codigos = montar_codigos()

		self.assertEqual(_por_nome(self.linhas, "Ativo")["COD_CTA_SUP"], "")
		self.assertEqual(_por_nome(self.linhas, "Ativo Circulante")["COD_CTA_SUP"], codigos["Ativo"])
		self.assertEqual(_por_nome(self.linhas, "Clientes")["COD_CTA_SUP"], codigos["Ativo Circulante"])


if __name__ == "__main__":
	unittest.main()
