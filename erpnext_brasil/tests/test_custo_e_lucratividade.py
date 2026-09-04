# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/custo_aquisicao.py` e `contabil/lucratividade.py`.

Dois testes-âncora:

- `test_o_mesmo_produto_custa_diferente_conforme_o_regime` — a consequência
  contraintuitiva do RIR/2018 art. 301: quem credita tem custo menor;
- `test_margem_sobre_a_bruta_da_numero_falso` — por que a ordem do Art. 187 importa.
"""

import unittest
from decimal import Decimal as d

from erpnext_brasil.contabil.custo_aquisicao import (
	CustoInvalido,
	TributoDaAquisicao,
	custo_de_aquisicao,
)
from erpnext_brasil.contabil.lucratividade import LucratividadeInvalida, apurar_lucratividade


class TestCustoDeAquisicao(unittest.TestCase):
	def test_sem_tributo_recuperavel_o_custo_e_o_valor_pago(self):
		resultado = custo_de_aquisicao(valor_mercadoria=d("1000.00"))

		self.assertEqual(resultado.custo, d("1000.00"))
		self.assertEqual(resultado.creditos, d("0.00"))

	def test_o_mesmo_produto_custa_diferente_conforme_o_regime(self):
		"""RIR/2018 art. 301, §3º: quem credita tem custo menor — mesma nota."""
		icms = d("180.00")

		credita = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[TributoDaAquisicao("ICMS", icms, recuperavel=True)],
		)
		nao_credita = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[TributoDaAquisicao("ICMS", icms, recuperavel=False)],
		)

		self.assertEqual(credita.custo, d("820.00"))
		self.assertEqual(nao_credita.custo, d("1000.00"))

	def test_tributo_por_dentro_nao_recuperavel_nao_soma(self):
		"""ICMS já está no valor da mercadoria — somá-lo dobraria o imposto."""
		resultado = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[TributoDaAquisicao("ICMS", d("180.00"), recuperavel=False, por_dentro=True)],
		)

		self.assertEqual(resultado.custo, d("1000.00"))

	def test_ipi_por_fora_nao_recuperavel_soma_ao_custo(self):
		"""IPI não está no valor da mercadoria: é dinheiro pago a mais."""
		resultado = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[TributoDaAquisicao("IPI", d("100.00"), recuperavel=False, por_dentro=False)],
		)

		self.assertEqual(resultado.custo, d("1100.00"))

	def test_ipi_por_fora_recuperavel_nao_soma(self):
		"""Industrial credita o IPI: paga, mas não é custo."""
		resultado = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[TributoDaAquisicao("IPI", d("100.00"), recuperavel=True, por_dentro=False)],
		)

		self.assertEqual(resultado.custo, d("1000.00"))
		self.assertEqual(resultado.creditos, d("100.00"))

	def test_frete_e_seguro_integram_o_custo(self):
		"""Art. 301: o custo compreende transporte e seguro até o estabelecimento."""
		resultado = custo_de_aquisicao(valor_mercadoria=d("1000.00"), frete=d("80.00"), seguro=d("20.00"))

		self.assertEqual(resultado.custo, d("1100.00"))

	def test_desconto_reduz_o_custo(self):
		resultado = custo_de_aquisicao(valor_mercadoria=d("1000.00"), descontos=d("100.00"))

		self.assertEqual(resultado.custo, d("900.00"))

	def test_creditos_discriminados_por_tributo(self):
		"""Quem lança precisa saber qual conta de crédito recebe o quê."""
		resultado = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[
				TributoDaAquisicao("ICMS", d("180.00"), recuperavel=True),
				TributoDaAquisicao("PIS", d("16.50"), recuperavel=True),
				TributoDaAquisicao("COFINS", d("76.00"), recuperavel=True),
			],
		)

		self.assertEqual(resultado.creditos_por_tributo["ICMS"], d("180.00"))
		self.assertEqual(resultado.creditos_por_tributo["PIS"], d("16.50"))
		self.assertEqual(resultado.creditos, d("272.50"))

	def test_custo_mais_creditos_fecha_com_o_pago(self):
		"""Pós-condição: nada some nem é contado duas vezes."""
		resultado = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			frete=d("50.00"),
			tributos=[TributoDaAquisicao("ICMS", d("180.00"), recuperavel=True)],
		)

		self.assertEqual(resultado.total_pago, d("1050.00"))

	def test_credito_maior_que_a_nota_e_erro(self):
		with self.assertRaises(CustoInvalido):
			custo_de_aquisicao(
				valor_mercadoria=d("100.00"),
				tributos=[TributoDaAquisicao("ICMS", d("500.00"), recuperavel=True)],
			)

	def test_desconto_maior_que_tudo_e_erro(self):
		with self.assertRaises(CustoInvalido):
			custo_de_aquisicao(valor_mercadoria=d("100.00"), descontos=d("200.00"))

	def test_tributo_sem_nome_e_erro(self):
		with self.assertRaises(CustoInvalido):
			TributoDaAquisicao("  ", d("10.00"))

	def test_float_e_recusado(self):
		with self.assertRaises(CustoInvalido):
			custo_de_aquisicao(valor_mercadoria=1000.0)


class TestLucratividade(unittest.TestCase):
	def _apuracao(self):
		return apurar_lucratividade(
			receita_bruta=d("1000.00"),
			deducoes=d("265.00"),
			custo=d("600.00"),
			despesas_operacionais=d("50.00"),
		)

	def test_a_cadeia_do_artigo_187(self):
		r = self._apuracao()

		self.assertEqual(r.receita_liquida, d("735.00"))
		self.assertEqual(r.lucro_bruto, d("135.00"))
		self.assertEqual(r.resultado_operacional, d("85.00"))

	def test_margem_sobre_a_bruta_da_numero_falso(self):
		"""13,5% (sobre a bruta) contra 18,4% (sobre a líquida) — só o segundo responde."""
		r = self._apuracao()

		sobre_bruta = r.lucro_bruto / r.receita_bruta

		self.assertAlmostEqual(r.margem_bruta, d("0.1837"), places=3)
		self.assertNotAlmostEqual(r.margem_bruta, sobre_bruta, places=3)

	def test_carga_e_separada_da_margem(self):
		"""O que o empresário chama de "imposto que pago" não é margem."""
		self.assertAlmostEqual(self._apuracao().carga_sobre_faturamento, d("0.265"), places=3)

	def test_prejuizo_e_resultado_valido(self):
		r = apurar_lucratividade(receita_bruta=d("100.00"), custo=d("150.00"))

		self.assertLess(r.lucro_bruto, d("0.00"))

	def test_deducao_maior_que_a_receita_e_erro(self):
		"""Receita líquida negativa é erro de lançamento, não operação real."""
		with self.assertRaises(LucratividadeInvalida):
			apurar_lucratividade(receita_bruta=d("100.00"), deducoes=d("150.00"))

	def test_receita_zerada_nao_divide_por_zero(self):
		r = apurar_lucratividade(receita_bruta=d("0.00"))

		self.assertEqual(r.margem_bruta, d("0.00"))
		self.assertEqual(r.carga_sobre_faturamento, d("0.00"))

	def test_valor_negativo_e_erro(self):
		with self.assertRaises(LucratividadeInvalida):
			apurar_lucratividade(receita_bruta=d("-1.00"))


class TestPrecoECustoFecham(unittest.TestCase):
	"""A costura entre os três módulos: precificar, custear e apurar têm de concordar."""

	def test_margem_precificada_reaparece_sobre_o_faturamento(self):
		"""Precificar com 20% sobre o preço reaparece como 20% sobre a receita bruta."""
		from erpnext_brasil.fiscal.precificacao import preco_de_venda

		custo = d("100.00")
		aliquota = d("0.18")

		preco = preco_de_venda(custo=custo, margem=d("0.20"), aliquotas_por_dentro=[aliquota]).preco

		apuracao = apurar_lucratividade(
			receita_bruta=preco,
			deducoes=(preco * aliquota).quantize(d("0.01")),
			custo=custo,
		)

		self.assertAlmostEqual(apuracao.margem_bruta_sobre_faturamento, d("0.20"), places=2)

	def test_a_mesma_operacao_tem_duas_margens_diferentes(self):
		"""Achado do teste de costura: 20% sobre o preço é 24,4% sobre a líquida.

		As duas estão certas; o denominador é que muda. Comparar uma com a outra é como
		se conclui que a margem melhorou quando só mudou a régua.
		"""
		from erpnext_brasil.fiscal.precificacao import preco_de_venda

		custo = d("100.00")
		aliquota = d("0.18")
		preco = preco_de_venda(custo=custo, margem=d("0.20"), aliquotas_por_dentro=[aliquota]).preco

		apuracao = apurar_lucratividade(
			receita_bruta=preco,
			deducoes=(preco * aliquota).quantize(d("0.01")),
			custo=custo,
		)

		self.assertAlmostEqual(apuracao.margem_bruta_sobre_faturamento, d("0.20"), places=2)
		self.assertAlmostEqual(apuracao.margem_bruta, d("0.244"), places=2)
		self.assertGreater(apuracao.margem_bruta, apuracao.margem_bruta_sobre_faturamento)

	def test_custo_com_credito_melhora_a_margem_apurada(self):
		"""Quem credita tem custo menor e, com o mesmo preço, margem maior."""
		from erpnext_brasil.fiscal.precificacao import preco_de_venda

		com_credito = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[TributoDaAquisicao("ICMS", d("180.00"), recuperavel=True)],
		).custo
		sem_credito = custo_de_aquisicao(valor_mercadoria=d("1000.00")).custo

		preco = preco_de_venda(custo=sem_credito, margem=d("0.10")).preco

		margem_de_quem_credita = apurar_lucratividade(receita_bruta=preco, custo=com_credito).margem_bruta
		margem_de_quem_nao_credita = apurar_lucratividade(receita_bruta=preco, custo=sem_credito).margem_bruta

		self.assertGreater(margem_de_quem_credita, margem_de_quem_nao_credita)


if __name__ == "__main__":
	unittest.main()
