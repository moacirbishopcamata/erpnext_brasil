# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da aritmética de ICMS.

Os valores esperados foram conferidos à mão, não extraídos da implementação — é o que
separa um teste que verifica de um que apenas registra o que o código faz hoje.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import (
	arredondar,
	base_por_dentro,
	calcular_difal,
	calcular_icms,
	calcular_icms_st,
	mva_ajustada,
	reduzir_base,
)


def d(valor: str) -> Decimal:
	return Decimal(valor)


class TestArredondamento(unittest.TestCase):
	def test_meio_para_cima_e_nao_para_o_par(self):
		# O padrão do Python (ROUND_HALF_EVEN) daria 0.12 aqui; documento fiscal quer 0.13.
		self.assertEqual(arredondar(d("0.125")), d("0.13"))
		self.assertEqual(arredondar(d("0.135")), d("0.14"))

	def test_preserva_valores_ja_arredondados(self):
		self.assertEqual(arredondar(d("10.00")), d("10.00"))


class TestImpostoPorDentro(unittest.TestCase):
	def test_gross_up_nao_e_simples_acrescimo(self):
		"""R$ 100 com ICMS 18% por dentro custa 121,95 — não 118."""
		base = base_por_dentro(d("100.00"), d("0.18"))

		self.assertEqual(base, d("121.95"))
		self.assertNotEqual(base, d("118.00"))

	def test_imposto_embutido_confere_com_a_base(self):
		base = base_por_dentro(d("100.00"), d("0.18"))
		icms = calcular_icms(base, d("0.18"))

		self.assertEqual(icms.valor, d("21.95"))

		# O valor líquido volta ao ponto de partida, a menos de centavo de arredondamento.
		self.assertAlmostEqual(base - icms.valor, d("100.00"), delta=d("0.01"))

	def test_aliquota_zero_nao_altera_o_valor(self):
		self.assertEqual(base_por_dentro(d("100.00"), d("0")), d("100.00"))


class TestAliquotaComoFracao(unittest.TestCase):
	def test_percentual_em_vez_de_fracao_e_erro(self):
		"""Passar 18 em vez de 0.18 precisa falhar alto, não gerar imposto 18x maior."""
		for funcao in (base_por_dentro, lambda b, a: calcular_icms(b, a)):
			with self.subTest(funcao=funcao):
				with self.assertRaises(ValueError):
					funcao(d("100.00"), d("18"))

	def test_aliquota_negativa_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_icms(d("100.00"), d("-0.18"))


class TestReducaoDeBase(unittest.TestCase):
	def test_reducao_de_33_33_por_cento(self):
		self.assertEqual(reduzir_base(d("1000.00"), d("0.3333")), d("666.70"))

	def test_icms_com_reducao_incide_sobre_a_base_reduzida(self):
		resultado = calcular_icms(d("1000.00"), d("0.18"), percentual_reducao=d("0.30"))

		self.assertEqual(resultado.base, d("700.00"))
		self.assertEqual(resultado.valor, d("126.00"))


class TestMVAAjustada(unittest.TestCase):
	def test_ajuste_interestadual(self):
		"""MVA 40%, interestadual 12%, interna 18% -> 50,24%.

		(1,40 x 0,88 / 0,82) - 1 = 0,5024
		"""
		self.assertEqual(mva_ajustada(d("0.40"), d("0.12"), d("0.18")), d("0.5024"))

	def test_ajustada_e_maior_que_a_original(self):
		ajustada = mva_ajustada(d("0.40"), d("0.07"), d("0.18"))
		self.assertGreater(ajustada, d("0.40"))

	def test_sem_diferenca_de_aliquota_a_mva_nao_muda(self):
		self.assertEqual(mva_ajustada(d("0.40"), d("0.18"), d("0.18")), d("0.4000"))

	def test_mva_negativa_e_erro(self):
		with self.assertRaises(ValueError):
			mva_ajustada(d("-0.1"), d("0.12"), d("0.18"))


class TestSubstituicaoTributaria(unittest.TestCase):
	def test_ipi_entra_na_base_da_st(self):
		"""Produtos 1000 + IPI 100, MVA 40%, próprio 12%, interna 18%.

		base ST = 1100 x 1,40 = 1540; ST = 1540 x 0,18 - 120 = 157,20
		"""
		resultado = calcular_icms_st(
			valor_produtos=d("1000.00"),
			aliquota_proprio=d("0.12"),
			aliquota_interna_destino=d("0.18"),
			mva=d("0.40"),
			ipi=d("100.00"),
		)

		self.assertEqual(resultado.base_st, d("1540.00"))
		self.assertEqual(resultado.icms_proprio, d("120.00"))
		self.assertEqual(resultado.icms_st, d("157.20"))

	def test_ipi_nao_entra_na_base_do_icms_proprio(self):
		"""A pegadinha que mais gera ST a menos: IPI compõe a ST, não o próprio."""
		com_ipi = calcular_icms_st(d("1000.00"), d("0.12"), d("0.18"), d("0.40"), ipi=d("100.00"))
		sem_ipi = calcular_icms_st(d("1000.00"), d("0.12"), d("0.18"), d("0.40"))

		self.assertEqual(com_ipi.icms_proprio, sem_ipi.icms_proprio)
		self.assertGreater(com_ipi.base_st, sem_ipi.base_st)

	def test_frete_entra_nas_duas_bases(self):
		com_frete = calcular_icms_st(d("1000.00"), d("0.12"), d("0.18"), d("0.40"), frete=d("100.00"))
		sem_frete = calcular_icms_st(d("1000.00"), d("0.12"), d("0.18"), d("0.40"))

		self.assertGreater(com_frete.icms_proprio, sem_frete.icms_proprio)
		self.assertGreater(com_frete.base_st, sem_frete.base_st)

	def test_st_nunca_e_negativa(self):
		# Próprio alto e interna baixa: a cadeia já foi mais que tributada.
		resultado = calcular_icms_st(d("1000.00"), d("0.18"), d("0.19"), d("0.00"))

		self.assertGreaterEqual(resultado.icms_st, d("0.00"))

	def test_desconto_maior_que_a_operacao_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_icms_st(d("100.00"), d("0.12"), d("0.18"), d("0.40"), descontos=d("500.00"))


class TestDIFAL(unittest.TestCase):
	def test_base_dupla(self):
		"""1000, interestadual 12%, interna 18%.

		origem = 120; base destino = (1000-120)/0,82 = 1073,17;
		destino = 193,17; DIFAL = 73,17
		"""
		resultado = calcular_difal(d("1000.00"), d("0.12"), d("0.18"))

		self.assertEqual(resultado["icms_origem"], d("120.00"))
		self.assertEqual(resultado["base_destino"], d("1073.17"))
		self.assertEqual(resultado["icms_destino"], d("193.17"))
		self.assertEqual(resultado["difal"], d("73.17"))

	def test_base_unica_da_resultado_menor(self):
		"""A metodologia muda o valor devido — por isso é parâmetro, não constante."""
		dupla = calcular_difal(d("1000.00"), d("0.12"), d("0.18"), base_dupla=True)
		unica = calcular_difal(d("1000.00"), d("0.12"), d("0.18"), base_dupla=False)

		self.assertEqual(unica["difal"], d("60.00"))
		self.assertGreater(dupla["difal"], unica["difal"])

	def test_fcp_incide_sobre_a_base_do_destino(self):
		resultado = calcular_difal(d("1000.00"), d("0.12"), d("0.18"), aliquota_fcp=d("0.02"))

		self.assertEqual(resultado["fcp"], arredondar(resultado["base_destino"] * d("0.02")))

	def test_sem_fcp_o_valor_e_zero(self):
		self.assertEqual(calcular_difal(d("1000.00"), d("0.12"), d("0.18"))["fcp"], d("0.00"))

	def test_interna_menor_que_interestadual_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_difal(d("1000.00"), d("0.18"), d("0.12"))


if __name__ == "__main__":
	unittest.main()
