# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecf_bloco_0.py` — Bloco 0 (Abertura/Identificação) da ECF."""

import unittest
from datetime import date

from erpnext_brasil.contabil.ecf_bloco_0 import (
	DadosCadastrais,
	IdentificacaoEcf,
	montar_0000,
	montar_0001,
	montar_0030,
	montar_0990,
)

IDENTIFICACAO = IdentificacaoEcf(
	cnpj="11222333000181",
	nome_empresarial="Empresa Teste Ltda",
	data_inicio=date(2026, 1, 1),
	data_fim=date(2026, 12, 31),
	codigo_versao_leiaute="0012",
	indicador_situacao_inicio_periodo="0",
	tipo_ecf="0",
)


class TestMontarZeroZeroZeroZero(unittest.TestCase):
	def test_campos_basicos(self):
		linha = montar_0000(IDENTIFICACAO)

		self.assertEqual(linha["REG"], "0000")
		self.assertEqual(linha["NOME_ESC"], "ECF")
		self.assertEqual(linha["CNPJ"], "11222333000181")
		self.assertEqual(linha["NOME"], "Empresa Teste Ltda")
		self.assertEqual(linha["DT_INI"], date(2026, 1, 1))
		self.assertEqual(linha["DT_FIN"], date(2026, 12, 31))

	def test_campos_opcionais_vazios_por_padrao(self):
		linha = montar_0000(IDENTIFICACAO)

		self.assertEqual(linha["SIT_ESPECIAL"], "")
		self.assertEqual(linha["PAT_REMAN_CIS"], "")
		self.assertIsNone(linha["DT_SIT_ESP"])
		self.assertEqual(linha["RETIFICADORA"], "0")
		self.assertEqual(linha["COD_SCP"], "")


class TestMontarZeroZeroZeroUm(unittest.TestCase):
	def test_com_dados(self):
		self.assertEqual(montar_0001(tem_dados=True), {"REG": "0001", "IND_DAD": "0"})

	def test_sem_dados(self):
		self.assertEqual(montar_0001(tem_dados=False), {"REG": "0001", "IND_DAD": "1"})


class TestMontarZeroZeroTresZero(unittest.TestCase):
	def test_campos_basicos(self):
		dados = DadosCadastrais(
			natureza_juridica="2062",
			cnae_fiscal="4711301",
			endereco="Rua Teste",
			numero="100",
			bairro="Centro",
			uf="RO",
			codigo_municipio="1100015",
			cep="76801000",
		)

		linha = montar_0030(dados)

		self.assertEqual(linha["REG"], "0030")
		self.assertEqual(linha["COD_NAT"], "2062")
		self.assertEqual(linha["CNAE_FISCAL"], "4711301")
		self.assertEqual(linha["UF"], "RO")
		self.assertEqual(linha["COD_MUN"], "1100015")
		self.assertEqual(linha["COMPL"], "")


class TestMontarZeroNoveNoveZero(unittest.TestCase):
	def test_contagem(self):
		self.assertEqual(montar_0990(15), {"REG": "0990", "QTD_LIN_0": "15"})


if __name__ == "__main__":
	unittest.main()
