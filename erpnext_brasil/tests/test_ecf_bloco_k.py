# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecf_bloco_k.py` — Bloco K (Saldos das Contas Contábeis) da ECF.

O teste que mais importa é `test_k155_reaproveita_i155_com_indicadores_renomeados`:
confirma o achado central do módulo -- K155 não reimplementa a aritmética de saldo, só
renomeia os dois campos indicadores.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.ecd_i050 import MapeamentoReferencial
from erpnext_brasil.contabil.ecd_i150 import SaldoInicial, montar_i155
from erpnext_brasil.contabil.ecf_bloco_k import (
	ContaDesconhecida,
	montar_k001,
	montar_k155,
	montar_k156,
	montar_k990,
)
from erpnext_brasil.contabil.lancamento import Lancamento

LANCAMENTOS = [
	Lancamento(
		conta_debito="Clientes",
		conta_credito="Receita Bruta de Vendas e Serviços",
		valor=Decimal("100.00"),
		historico="Venda",
	)
]


class TestMontarK001(unittest.TestCase):
	def test_com_dados(self):
		self.assertEqual(montar_k001(tem_dados=True), {"REG": "K001", "IND_DAD": "0"})

	def test_sem_dados(self):
		self.assertEqual(montar_k001(tem_dados=False), {"REG": "K001", "IND_DAD": "1"})


class TestMontarK155(unittest.TestCase):
	def test_k155_reaproveita_i155_com_indicadores_renomeados(self):
		"""Achado central: os sete campos financeiros são idênticos ao I155; só
		IND_DC_INI/IND_DC_FIN viram IND_VL_SLD_INI/IND_VL_SLD_FIN."""
		linhas_i155 = montar_i155(LANCAMENTOS)
		linhas_k155 = montar_k155(LANCAMENTOS)

		for linha_i, linha_k in zip(linhas_i155, linhas_k155, strict=True):
			self.assertEqual(linha_k["REG"], "K155")
			for campo in ("COD_CTA", "COD_CCUS", "VL_SLD_INI", "VL_DEB", "VL_CRED", "VL_SLD_FIN"):
				self.assertEqual(linha_k[campo], linha_i[campo])
			self.assertEqual(linha_k["IND_VL_SLD_INI"], linha_i["IND_DC_INI"])
			self.assertEqual(linha_k["IND_VL_SLD_FIN"], linha_i["IND_DC_FIN"])
			self.assertNotIn("IND_DC_INI", linha_k)
			self.assertNotIn("IND_DC_FIN", linha_k)

	def test_com_saldo_inicial(self):
		saldos = {"Clientes": SaldoInicial(valor=Decimal("50.00"), indicador="D")}

		linhas = montar_k155(LANCAMENTOS, saldos)

		self.assertEqual(linhas[0]["VL_SLD_INI"], Decimal("50.00"))

	def test_uma_linha_por_conta_com_movimento(self):
		self.assertEqual(len(montar_k155(LANCAMENTOS)), 2)


class TestMontarK156(unittest.TestCase):
	def test_uma_linha_por_mapeamento_com_movimento(self):
		mapeamentos = [
			MapeamentoReferencial(conta="Clientes", codigo_referencial="1.01.03.01"),
		]

		linhas = montar_k156(LANCAMENTOS, mapeamentos)

		self.assertEqual(len(linhas), 1)
		self.assertEqual(linhas[0]["REG"], "K156")
		self.assertEqual(linhas[0]["COD_CTA_REF"], "1.01.03.01")
		self.assertNotIn("COD_CTA", linhas[0])
		self.assertNotIn("COD_CCUS", linhas[0])

	def test_valores_batem_com_i155(self):
		mapeamentos = [MapeamentoReferencial(conta="Clientes", codigo_referencial="1.01.03.01")]

		linhas_i155 = montar_i155(LANCAMENTOS)
		linhas_k156 = montar_k156(LANCAMENTOS, mapeamentos)

		linha_clientes = next(
			linha for linha in linhas_i155 if linha["VL_SLD_FIN"] == linhas_k156[0]["VL_SLD_FIN"]
		)
		self.assertEqual(linhas_k156[0]["VL_DEB"], linha_clientes["VL_DEB"])
		self.assertEqual(linhas_k156[0]["IND_VL_SLD_INICIAL"], linha_clientes["IND_DC_INI"])
		self.assertEqual(linhas_k156[0]["IND_VL_SLD_FIN"], linha_clientes["IND_DC_FIN"])

	def test_conta_mapeada_sem_movimento_nao_gera_linha(self):
		mapeamentos = [MapeamentoReferencial(conta="Estoques", codigo_referencial="1.01.04.01")]

		self.assertEqual(montar_k156(LANCAMENTOS, mapeamentos), [])

	def test_conta_desconhecida_levanta_erro(self):
		mapeamentos = [MapeamentoReferencial(conta="Conta Inexistente", codigo_referencial="9.99")]

		with self.assertRaises(ContaDesconhecida):
			montar_k156(LANCAMENTOS, mapeamentos)


class TestMontarK990(unittest.TestCase):
	def test_contagem(self):
		self.assertEqual(montar_k990(7), {"REG": "K990", "QTD_LIN": "7"})


if __name__ == "__main__":
	unittest.main()
