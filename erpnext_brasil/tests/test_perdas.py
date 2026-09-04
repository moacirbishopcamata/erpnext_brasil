# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/perdas.py` — baixa de estoque e estorno de crédito.

O teste-âncora é `test_a_perda_custa_mais_que_o_estoque_baixado`: uma perda de R$ 1.000
não custa R$ 1.000, e sistema que só dá baixa contábil subestima o prejuízo e deixa
passivo fiscal para trás.
"""

import unittest
from decimal import Decimal as d

from erpnext_brasil.contabil.perdas import (
	TIPO_FURTO_OU_ROUBO,
	TIPO_QUEBRA_NORMAL,
	TIPO_VENCIMENTO,
	TIPOS_DE_PERDA,
	PerdaInvalida,
	TipoDePerda,
	apurar_perda,
)

CREDITOS = {"ICMS": d("180.00"), "PIS": d("16.50"), "COFINS": d("76.00")}


class TestEstornoDeCredito(unittest.TestCase):
	def test_a_perda_custa_mais_que_o_estoque_baixado(self):
		"""LC 87/96, art. 21: mercadoria que perece exige estorno do crédito."""
		resultado = apurar_perda(d("1000.00"), TipoDePerda(TIPO_VENCIMENTO), CREDITOS)

		self.assertEqual(resultado.valor_do_estoque, d("1000.00"))
		self.assertEqual(resultado.creditos_estornados, d("272.50"))
		self.assertEqual(resultado.custo_total_da_perda, d("1272.50"))

	def test_furto_estorna(self):
		resultado = apurar_perda(d("500.00"), TipoDePerda(TIPO_FURTO_OU_ROUBO), CREDITOS)

		self.assertTrue(resultado.estorna)
		self.assertGreater(resultado.creditos_estornados, d("0.00"))

	def test_estornos_discriminados_por_tributo(self):
		"""Quem lança precisa saber qual crédito devolver, não só o total."""
		resultado = apurar_perda(d("1000.00"), TipoDePerda(TIPO_VENCIMENTO), CREDITOS)

		self.assertEqual(resultado.estornos_por_tributo["ICMS"], d("180.00"))
		self.assertEqual(resultado.estornos_por_tributo["COFINS"], d("76.00"))

	def test_sem_credito_tomado_nao_ha_o_que_estornar(self):
		"""Quem não creditou na entrada não devolve nada — a perda é só o estoque."""
		resultado = apurar_perda(d("1000.00"), TipoDePerda(TIPO_VENCIMENTO))

		self.assertEqual(resultado.creditos_estornados, d("0.00"))
		self.assertEqual(resultado.custo_total_da_perda, d("1000.00"))


class TestQuebraNormal(unittest.TestCase):
	"""A exceção que muda o resultado: perda inerente ao processo não estorna."""

	def test_quebra_normal_nao_estorna(self):
		resultado = apurar_perda(d("1000.00"), TipoDePerda(TIPO_QUEBRA_NORMAL), CREDITOS)

		self.assertFalse(resultado.estorna)
		self.assertEqual(resultado.creditos_estornados, d("0.00"))

	def test_quebra_normal_custa_so_o_estoque(self):
		"""A mercadoria foi consumida pela atividade tributada — o crédito continua
		legítimo."""
		resultado = apurar_perda(d("1000.00"), TipoDePerda(TIPO_QUEBRA_NORMAL), CREDITOS)

		self.assertEqual(resultado.custo_total_da_perda, d("1000.00"))

	def test_a_mesma_perda_custa_diferente_conforme_o_tipo(self):
		"""A distinção não é de tamanho, é de natureza — e muda o número."""
		normal = apurar_perda(d("1000.00"), TipoDePerda(TIPO_QUEBRA_NORMAL), CREDITOS)
		vencida = apurar_perda(d("1000.00"), TipoDePerda(TIPO_VENCIMENTO), CREDITOS)

		self.assertLess(normal.custo_total_da_perda, vencida.custo_total_da_perda)


class TestTipoDePerda(unittest.TestCase):
	def test_todos_os_tipos_declarados_sao_aceitos(self):
		for nome in TIPOS_DE_PERDA:
			with self.subTest(tipo=nome):
				TipoDePerda(nome)

	def test_tipo_desconhecido_e_erro(self):
		with self.assertRaises(PerdaInvalida):
			TipoDePerda("Sumiu")

	def test_so_a_quebra_normal_nao_estorna(self):
		nao_estornam = [nome for nome in TIPOS_DE_PERDA if not TipoDePerda(nome).estorna_credito]

		self.assertEqual(nao_estornam, [TIPO_QUEBRA_NORMAL])


class TestValidacoes(unittest.TestCase):
	def test_valor_zero_e_erro(self):
		"""Baixa de valor zero não é perda, é lançamento sem efeito."""
		with self.assertRaises(PerdaInvalida):
			apurar_perda(d("0.00"), TipoDePerda(TIPO_VENCIMENTO))

	def test_valor_negativo_e_erro(self):
		with self.assertRaises(PerdaInvalida):
			apurar_perda(d("-10.00"), TipoDePerda(TIPO_VENCIMENTO))

	def test_float_e_recusado(self):
		with self.assertRaises(PerdaInvalida):
			apurar_perda(1000.0, TipoDePerda(TIPO_VENCIMENTO))

	def test_credito_negativo_e_erro(self):
		with self.assertRaises(PerdaInvalida):
			apurar_perda(d("100.00"), TipoDePerda(TIPO_VENCIMENTO), {"ICMS": d("-1.00")})


class TestSimetriaComACompra(unittest.TestCase):
	"""Estorna-se exatamente o que se creditou — a simetria não é coincidência."""

	def test_o_estorno_espelha_o_credito_da_aquisicao(self):
		from erpnext_brasil.contabil.custo_aquisicao import (
			TributoDaAquisicao,
			custo_de_aquisicao,
		)

		compra = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[
				TributoDaAquisicao("ICMS", d("180.00"), recuperavel=True),
				TributoDaAquisicao("PIS", d("16.50"), recuperavel=True),
			],
		)

		perda = apurar_perda(compra.custo, TipoDePerda(TIPO_VENCIMENTO), compra.creditos_por_tributo)

		self.assertEqual(perda.creditos_estornados, compra.creditos)
		self.assertEqual(perda.custo_total_da_perda, compra.total_pago)


if __name__ == "__main__":
	unittest.main()
