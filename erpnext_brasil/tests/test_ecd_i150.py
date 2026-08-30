# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecd_i150.py` — registros I150/I155 (saldos periódicos).

O teste que mais importa é `test_saldo_credor_recebendo_debito_pode_virar_devedor`: a
prova de que a aritmética D/C é puramente mecânica (soma débito, subtrai crédito),
nunca condicionada à "natureza" da conta.
"""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.ecd_i150 import ContaDesconhecida, SaldoInicial, montar_i150, montar_i155
from erpnext_brasil.contabil.lancamento import Lancamento


def d(v: str) -> Decimal:
	return Decimal(v)


def lancamento(conta_debito: str, conta_credito: str, valor: str) -> Lancamento:
	return Lancamento(conta_debito=conta_debito, conta_credito=conta_credito, valor=d(valor), historico="teste")


class TestMontarI150(unittest.TestCase):
	def test_campos(self):
		linha = montar_i150(date(2026, 1, 1), date(2026, 1, 31))

		self.assertEqual(linha, {"REG": "I150", "DT_INI": date(2026, 1, 1), "DT_FIN": date(2026, 1, 31)})


class TestSaldoInicial(unittest.TestCase):
	def test_indicador_invalido_e_erro(self):
		with self.assertRaises(ValueError):
			SaldoInicial(valor=d("10.00"), indicador="X")

	def test_valor_negativo_e_erro(self):
		with self.assertRaises(ValueError):
			SaldoInicial(valor=d("-1.00"), indicador="D")


class TestMontarI155(unittest.TestCase):
	def test_ordem_dos_campos(self):
		linhas = montar_i155([lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")])

		self.assertEqual(
			list(linhas[0]),
			["REG", "COD_CTA", "COD_CCUS", "VL_SLD_INI", "IND_DC_INI", "VL_DEB", "VL_CRED", "VL_SLD_FIN", "IND_DC_FIN"],
		)

	def test_conta_sem_saldo_inicial_comeca_do_zero_devedor(self):
		linhas = montar_i155([lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")])

		self.assertEqual(linhas[0]["VL_SLD_INI"], d("0.00"))
		self.assertEqual(linhas[0]["IND_DC_INI"], "D")

	def test_debito_aumenta_saldo_devedor(self):
		linhas = montar_i155(
			[lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")],
			{"Clientes": SaldoInicial(d("500.00"), "D")},
		)
		linha_clientes = next(l for l in linhas if l["VL_DEB"] == d("1000.00"))

		self.assertEqual(linha_clientes["VL_SLD_FIN"], d("1500.00"))
		self.assertEqual(linha_clientes["IND_DC_FIN"], "D")

	def test_credito_reduz_saldo_devedor(self):
		linhas = montar_i155(
			[lancamento("ICMS a Recuperar", "Estoques", "300.00")],
			{"Estoques": SaldoInicial(d("1000.00"), "D")},
		)
		linha_estoques = next(l for l in linhas if l["VL_CRED"] == d("300.00"))

		self.assertEqual(linha_estoques["VL_SLD_FIN"], d("700.00"))
		self.assertEqual(linha_estoques["IND_DC_FIN"], "D")

	def test_saldo_credor_recebendo_debito_pode_virar_devedor(self):
		"""A aritmética D/C é mecânica — soma débito, subtrai crédito — nunca
		condicionada a 'esta conta é naturalmente credora'."""
		linhas = montar_i155(
			[lancamento("ICMS a Recolher", "Disponibilidades", "100.00")],
			{"ICMS a Recolher": SaldoInicial(d("40.00"), "C")},
		)
		linha = next(l for l in linhas if l["VL_DEB"] == d("100.00"))

		# -40 (credor) + 100 débito = +60 -> devedor.
		self.assertEqual(linha["VL_SLD_FIN"], d("60.00"))
		self.assertEqual(linha["IND_DC_FIN"], "D")

	def test_saldo_final_zero_e_devedor_por_convencao(self):
		linhas = montar_i155(
			[lancamento("Fornecedores", "Disponibilidades", "100.00")],
			{"Fornecedores": SaldoInicial(d("100.00"), "C")},
		)
		linha = next(l for l in linhas if l["VL_DEB"] == d("100.00"))

		self.assertEqual(linha["VL_SLD_FIN"], d("0.00"))
		self.assertEqual(linha["IND_DC_FIN"], "D")

	def test_so_contas_com_movimento_aparecem(self):
		linhas = montar_i155([lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")])

		self.assertEqual(len(linhas), 2)  # só Clientes e Receita, nada mais.

	def test_conta_desconhecida_levanta_erro(self):
		with self.assertRaises(ContaDesconhecida):
			montar_i155([lancamento("Conta Inventada", "Receita Bruta de Vendas e Serviços", "1.00")])

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(montar_i155([]), [])


if __name__ == "__main__":
	unittest.main()
