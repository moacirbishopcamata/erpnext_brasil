# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/destda.py` — registros de abertura e de valores da DeSTDA."""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.destda import (
	IND_GEF_ICMS,
	IND_SIT_ANTECIPACAO_SIMPLES,
	IND_SIT_DIFAL_INTERESTADUAL,
	Identificacao,
	montar_0000,
	montar_0001,
	montar_0990,
	montar_g001,
	montar_g020,
	montar_g605,
	montar_g615,
	montar_g625,
	montar_g990,
)
from erpnext_brasil.contabil.sped_texto import montar_linha

_PERIODO_INI = date(2026, 8, 1)
_PERIODO_FIM = date(2026, 8, 31)


class TestMontar0000(unittest.TestCase):
	def test_campos_basicos(self):
		identificacao = Identificacao(
			periodo_inicial=_PERIODO_INI,
			periodo_final=_PERIODO_FIM,
			nome_empresarial="Empresa Teste Ltda",
			cnpj="11222333000181",
			uf="SP",
			inscricao_estadual="123456789",
			codigo_municipio="3550308",
		)

		linha = montar_0000(identificacao)

		self.assertEqual(linha["REG"], "0000")
		self.assertEqual(linha["LFPD"], "LFPD")
		self.assertEqual(linha["NOME_EMPR"], "Empresa Teste Ltda")
		self.assertEqual(linha["CNPJ"], "11222333000181")

	def test_serializa_no_formato_pipe_delimited(self):
		identificacao = Identificacao(
			periodo_inicial=_PERIODO_INI,
			periodo_final=_PERIODO_FIM,
			nome_empresarial="Empresa Teste Ltda",
			cnpj="11222333000181",
			uf="SP",
			inscricao_estadual="123456789",
			codigo_municipio="3550308",
		)

		texto = montar_linha(montar_0000(identificacao))

		self.assertTrue(texto.startswith("|0000|LFPD|01082026|31082026|"))
		self.assertTrue(texto.endswith("|"))


class TestMontarAberturaDeBloco(unittest.TestCase):
	def test_0001_com_conteudo(self):
		self.assertEqual(montar_0001(tem_dados=True), {"REG": "0001", "IND_DAD": "0"})

	def test_0001_sem_conteudo(self):
		self.assertEqual(montar_0001(tem_dados=False), {"REG": "0001", "IND_DAD": "1"})

	def test_g001_com_conteudo(self):
		self.assertEqual(montar_g001(tem_dados=True), {"REG": "G001", "IND_DAD": "0"})


class TestMontarG020(unittest.TestCase):
	def test_campos(self):
		linha = montar_g020(IND_GEF_ICMS, _PERIODO_INI, _PERIODO_FIM)

		self.assertEqual(linha["REG"], "G020")
		self.assertEqual(linha["IND_GEF"], IND_GEF_ICMS)
		self.assertEqual(linha["DT_INI"], _PERIODO_INI)
		self.assertEqual(linha["DT_FIN"], _PERIODO_FIM)


class TestMontarG605(unittest.TestCase):
	def test_campos_e_serializacao(self):
		linha = montar_g605(
			IND_SIT_DIFAL_INTERESTADUAL, Decimal("1000.00"), Decimal("0.00"), Decimal("1000.00")
		)

		self.assertEqual(linha["IND_SIT"], IND_SIT_DIFAL_INTERESTADUAL)
		self.assertEqual(linha["VL_TOT_DA_ANTC"], Decimal("1000.00"))

		texto = montar_linha(linha)
		self.assertEqual(texto, "|G605|0|1000,00|0,00|1000,00|")

	def test_situacao_antecipacao(self):
		linha = montar_g605(
			IND_SIT_ANTECIPACAO_SIMPLES, Decimal("500.00"), Decimal("50.00"), Decimal("550.00")
		)

		self.assertEqual(linha["IND_SIT"], IND_SIT_ANTECIPACAO_SIMPLES)


class TestMontarG615(unittest.TestCase):
	def test_campos(self):
		linha = montar_g615("MG", Decimal("300.00"), Decimal("0.00"), Decimal("300.00"))

		self.assertEqual(linha["REG"], "G615")
		self.assertEqual(linha["UF"], "MG")
		self.assertEqual(linha["VL_TOT_ST_UF_DE"], Decimal("300.00"))


class TestMontarG625(unittest.TestCase):
	def test_campos(self):
		linha = montar_g625("RJ", "0", Decimal("400.00"), Decimal("0.00"), Decimal("400.00"))

		self.assertEqual(linha["REG"], "G625")
		self.assertEqual(linha["UF"], "RJ")
		self.assertEqual(linha["IND_TP_ST"], "0")


class TestMontarEncerramentoDeBloco(unittest.TestCase):
	def test_0990(self):
		self.assertEqual(montar_0990(5), {"REG": "0990", "QTD_LIN_0": "5"})

	def test_g990(self):
		self.assertEqual(montar_g990(8), {"REG": "G990", "QTD_LIN_G": "8"})


if __name__ == "__main__":
	unittest.main()
