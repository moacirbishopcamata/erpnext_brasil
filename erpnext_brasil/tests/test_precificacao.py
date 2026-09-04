# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/precificacao.py` — preço de venda com imposto brasileiro.

O teste-âncora é `test_o_erro_de_somar_em_vez_de_dividir`: reproduz numericamente o erro
de precificação mais caro do Brasil, mostrando o prejuízo que ele produz.
"""

import unittest
from decimal import Decimal as d

from erpnext_brasil.fiscal.precificacao import (
	PrecificacaoInvalida,
	margem_efetiva,
	markup_para_margem,
	preco_de_venda,
)


class TestOErroClassico(unittest.TestCase):
	def test_o_erro_de_somar_em_vez_de_dividir(self):
		"""Custo R$ 100 com ICMS de 18%: somar dá R$ 118 e produz prejuízo."""
		resultado = preco_de_venda(custo=d("100.00"), aliquotas_por_dentro=[d("0.18")])

		self.assertEqual(resultado.preco, d("121.95"))

		# O que sobraria vendendo a 118 (o preço "somado"): 118 − 100 − (118 × 0,18).
		sobra_do_preco_errado = d("118.00") - d("100.00") - (d("118.00") * d("0.18"))

		self.assertLess(sobra_do_preco_errado, d("0.00"))

	def test_no_preco_correto_sobra_exatamente_o_custo(self):
		"""Sem margem, o preço correto cobre o custo e o imposto — nem mais, nem menos."""
		resultado = preco_de_venda(custo=d("100.00"), aliquotas_por_dentro=[d("0.18")])

		sobra = resultado.preco - resultado.custo - resultado.impostos_por_dentro

		self.assertEqual(sobra, d("0.00"))
		self.assertEqual(resultado.margem, d("0.00"))


class TestMargem(unittest.TestCase):
	def test_margem_pedida_e_a_margem_entregue(self):
		"""Pós-condição: a conta de volta confirma a margem que entrou."""
		resultado = preco_de_venda(custo=d("100.00"), margem=d("0.20"), aliquotas_por_dentro=[d("0.18")])

		self.assertAlmostEqual(resultado.margem_percentual, d("0.20"), places=3)

	def test_margem_com_varios_impostos_por_dentro(self):
		"""ICMS 18% + PIS 1,65% + COFINS 7,6% — somados no denominador."""
		resultado = preco_de_venda(
			custo=d("100.00"),
			margem=d("0.10"),
			aliquotas_por_dentro=[d("0.18"), d("0.0165"), d("0.076")],
		)

		self.assertAlmostEqual(resultado.margem_percentual, d("0.10"), places=3)

	def test_sem_imposto_o_preco_so_reflete_a_margem(self):
		resultado = preco_de_venda(custo=d("80.00"), margem=d("0.20"))

		self.assertEqual(resultado.preco, d("100.00"))


class TestImpostoPorFora(unittest.TestCase):
	"""IBS e CBS não integram a própria base: multiplicam, não dividem."""

	def test_por_fora_nao_muda_o_preco_base(self):
		sem = preco_de_venda(custo=d("100.00"), aliquotas_por_dentro=[d("0.18")])
		com = preco_de_venda(
			custo=d("100.00"), aliquotas_por_dentro=[d("0.18")], aliquotas_por_fora=[d("0.01")]
		)

		self.assertEqual(sem.preco, com.preco)

	def test_por_fora_soma_no_preco_final(self):
		resultado = preco_de_venda(custo=d("100.00"), aliquotas_por_fora=[d("0.10")])

		self.assertEqual(resultado.preco, d("100.00"))
		self.assertEqual(resultado.preco_final, d("110.00"))

	def test_a_margem_nao_muda_com_imposto_por_fora(self):
		"""Por fora é repasse: não sai do bolso de quem vende."""
		resultado = preco_de_venda(custo=d("100.00"), margem=d("0.20"), aliquotas_por_fora=[d("0.01")])

		self.assertAlmostEqual(resultado.margem_percentual, d("0.20"), places=3)

	def test_tratar_por_fora_como_por_dentro_daria_preco_diferente(self):
		"""A distinção não é rótulo: muda o número."""
		por_fora = preco_de_venda(custo=d("100.00"), aliquotas_por_fora=[d("0.10")])
		por_dentro = preco_de_venda(custo=d("100.00"), aliquotas_por_dentro=[d("0.10")])

		self.assertNotEqual(por_fora.preco_final, por_dentro.preco_final)


class TestPrecoImpossivel(unittest.TestCase):
	def test_impostos_mais_margem_acima_de_cem_por_cento(self):
		"""Não existe preço: uma implementação ingênua devolveria número negativo."""
		with self.assertRaises(PrecificacaoInvalida):
			preco_de_venda(custo=d("100.00"), margem=d("0.50"), aliquotas_por_dentro=[d("0.30"), d("0.25")])

	def test_impostos_somando_exatamente_cem_por_cento(self):
		with self.assertRaises(PrecificacaoInvalida):
			preco_de_venda(custo=d("100.00"), aliquotas_por_dentro=[d("0.60"), d("0.40")])

	def test_custo_negativo_e_erro(self):
		with self.assertRaises(PrecificacaoInvalida):
			preco_de_venda(custo=d("-1.00"))

	def test_aliquota_como_percentual_e_erro(self):
		"""`18` em vez de `0.18` — erro de ordem de grandeza, não de arredondamento."""
		with self.assertRaises(PrecificacaoInvalida):
			preco_de_venda(custo=d("100.00"), aliquotas_por_dentro=[d("18")])

	def test_float_e_recusado(self):
		"""Centavo em preço não admite binário aproximado."""
		with self.assertRaises(PrecificacaoInvalida):
			preco_de_venda(custo=100.0)


class TestMargemEfetiva(unittest.TestCase):
	"""O caminho inverso: descobrir o que um preço já praticado entrega."""

	def test_confere_com_o_preco_calculado(self):
		resultado = preco_de_venda(custo=d("100.00"), margem=d("0.20"), aliquotas_por_dentro=[d("0.18")])
		efetiva = margem_efetiva(resultado.preco, custo=d("100.00"), aliquotas_por_dentro=[d("0.18")])

		self.assertAlmostEqual(efetiva, d("0.20"), places=3)

	def test_preco_somado_revela_prejuizo(self):
		"""A tabela feita somando 18% ao custo: a margem real é negativa."""
		efetiva = margem_efetiva(d("118.00"), custo=d("100.00"), aliquotas_por_dentro=[d("0.18")])

		self.assertLess(efetiva, d("0"))

	def test_prejuizo_e_resultado_legitimo(self):
		"""Margem negativa não é erro a esconder — é o diagnóstico."""
		self.assertLess(margem_efetiva(d("50.00"), custo=d("100.00")), d("0"))

	def test_preco_zero_e_erro(self):
		with self.assertRaises(PrecificacaoInvalida):
			margem_efetiva(d("0.00"), custo=d("100.00"))


class TestMarkupParaMargem(unittest.TestCase):
	def test_markup_de_30_nao_e_margem_de_30(self):
		"""Custo 100 vira preço 130; 30 sobre 130 é 23,08%."""
		self.assertAlmostEqual(markup_para_margem(d("0.30")), d("0.2308"), places=4)

	def test_markup_de_100_e_margem_de_50(self):
		self.assertEqual(markup_para_margem(d("1.00")), d("0.5"))

	def test_markup_zero_e_margem_zero(self):
		self.assertEqual(markup_para_margem(d("0")), d("0"))

	def test_a_conversao_fecha_com_o_preco(self):
		"""Prova de ponta a ponta: markup de 30% sobre 100 tem de dar preço 130."""
		margem = markup_para_margem(d("0.30"))
		resultado = preco_de_venda(custo=d("100.00"), margem=margem)

		self.assertEqual(resultado.preco, d("130.00"))

	def test_markup_negativo_e_erro(self):
		with self.assertRaises(PrecificacaoInvalida):
			markup_para_margem(d("-0.1"))


if __name__ == "__main__":
	unittest.main()
