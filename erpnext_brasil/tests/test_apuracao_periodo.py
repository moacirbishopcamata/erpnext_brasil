# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/apuracao_periodo.py` — fechamento periódico de ICMS/IPI.

O teste que mais importa é `test_a_recolher_e_saldo_credor_sao_mutuamente_exclusivos`:
os dois nunca podem ser diferentes de zero ao mesmo tempo, senão a apuração afirma duas
coisas contraditórias sobre o mesmo período.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.apuracao_periodo import (
	TRIBUTOS_APURAVEIS,
	ApuracaoInvalida,
	ApuracaoPeriodo,
	apurar_periodo,
)
from erpnext_brasil.contabil.lancamento import Lancamento


def d(v: str) -> Decimal:
	return Decimal(v)


def lancamento(conta_debito: str, conta_credito: str, valor: str) -> Lancamento:
	return Lancamento(conta_debito=conta_debito, conta_credito=conta_credito, valor=d(valor), historico="teste")


class TestApuracaoPeriodo(unittest.TestCase):
	def test_debito_maior_que_credito_e_a_recolher(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))

		self.assertEqual(apuracao.a_recolher, d("600.00"))
		self.assertEqual(apuracao.saldo_credor_a_transportar, d("0.00"))

	def test_credito_maior_que_debito_e_saldo_credor(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("400.00"), creditos=d("1000.00"))

		self.assertEqual(apuracao.a_recolher, d("0.00"))
		self.assertEqual(apuracao.saldo_credor_a_transportar, d("600.00"))

	def test_a_recolher_e_saldo_credor_sao_mutuamente_exclusivos(self):
		for debitos, creditos in (("1000.00", "400.00"), ("400.00", "1000.00"), ("500.00", "500.00")):
			with self.subTest(debitos=debitos, creditos=creditos):
				apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d(debitos), creditos=d(creditos))

				self.assertTrue(apuracao.a_recolher == d("0.00") or apuracao.saldo_credor_a_transportar == d("0.00"))

	def test_saldo_credor_anterior_soma_ao_credito_do_periodo(self):
		apuracao = ApuracaoPeriodo(
			tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"), saldo_credor_anterior=d("700.00")
		)

		# 1000 débito - 400 crédito do período - 700 crédito transportado = -100 (credor)
		self.assertEqual(apuracao.saldo_credor_a_transportar, d("100.00"))
		self.assertEqual(apuracao.a_recolher, d("0.00"))

	def test_tributo_fora_da_allowlist_e_rejeitado(self):
		with self.assertRaises(ApuracaoInvalida):
			ApuracaoPeriodo(tributo="PIS", debitos=d("100.00"), creditos=d("0.00"))

	def test_valor_negativo_e_rejeitado(self):
		with self.assertRaises(ApuracaoInvalida):
			ApuracaoPeriodo(tributo="ICMS", debitos=d("-1.00"), creditos=d("0.00"))

	def test_pis_e_cofins_nao_estao_na_allowlist(self):
		"""Escopo deliberado (ver docstring do módulo) — não esquecimento."""
		self.assertEqual(TRIBUTOS_APURAVEIS, frozenset({"ICMS", "IPI"}))


class TestApurarPeriodo(unittest.TestCase):
	def test_soma_debitos_e_creditos_de_uma_lista_de_lancamentos(self):
		lancamentos = [
			lancamento("ICMS sobre Vendas", "ICMS a Recolher", "180.00"),
			lancamento("ICMS sobre Vendas", "ICMS a Recolher", "90.00"),
			lancamento("ICMS a Recuperar", "Estoques", "50.00"),
		]

		apuracao = apurar_periodo("ICMS", lancamentos)

		self.assertEqual(apuracao.debitos, d("270.00"))
		self.assertEqual(apuracao.creditos, d("50.00"))
		self.assertEqual(apuracao.a_recolher, d("220.00"))

	def test_ignora_lancamentos_de_outro_tributo(self):
		lancamentos = [
			lancamento("ICMS sobre Vendas", "ICMS a Recolher", "180.00"),
			lancamento("Clientes", "IPI a Recolher", "100.00"),
			lancamento("IPI a Recuperar", "Estoques", "30.00"),
		]

		apuracao_icms = apurar_periodo("ICMS", lancamentos)
		apuracao_ipi = apurar_periodo("IPI", lancamentos)

		self.assertEqual(apuracao_icms.debitos, d("180.00"))
		self.assertEqual(apuracao_icms.creditos, d("0.00"))
		self.assertEqual(apuracao_ipi.debitos, d("100.00"))
		self.assertEqual(apuracao_ipi.creditos, d("30.00"))

	def test_lista_vazia_e_apuracao_zerada(self):
		apuracao = apurar_periodo("ICMS", [])

		self.assertEqual(apuracao.debitos, d("0.00"))
		self.assertEqual(apuracao.a_recolher, d("0.00"))

	def test_saldo_credor_anterior_propaga(self):
		apuracao = apurar_periodo("ICMS", [], saldo_credor_anterior=d("50.00"))

		self.assertEqual(apuracao.saldo_credor_a_transportar, d("50.00"))


if __name__ == "__main__":
	unittest.main()
