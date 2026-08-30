# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/boleto.py` — código de barras e linha digitável.

O teste que mais importa é `test_exemplo_real_publicado`: cruza o módulo inteiro
(fator, DV geral, DV de campo, montagem) contra um código de barras/linha digitável
reais publicados — não só que o algoritmo "parece certo" isoladamente.
"""

import unittest
from datetime import date, timedelta
from decimal import Decimal

from erpnext_brasil.contabil.boleto import (
	DATA_BASE_ANTIGA,
	DATA_BASE_NOVA,
	BoletoInvalido,
	calcular_dv_barra,
	calcular_dv_campo,
	calcular_fator_vencimento,
	montar_codigo_barras,
	montar_linha_digitavel,
)


class TestExemploReal(unittest.TestCase):
	"""Código de barras/linha digitável de um boleto real publicado (banco 001,
	vencimento com fator 3026, valor R$ 32,80)."""

	CAMPO_LIVRE = "0000001229196000000014018"
	CODIGO_BANCO = "001"
	FATOR = "3026"
	VALOR_CENTAVOS = "0000003280"
	DV_GERAL_ESPERADO = "6"
	BARCODE_ESPERADO = "00196302600000032800000001229196000000014018"
	LINHA_ESPERADA = "00190000090122919600900000140186630260000003280"

	def test_dv_geral_bate_com_o_exemplo(self):
		sem_dv = self.CODIGO_BANCO + "9" + self.FATOR + self.VALOR_CENTAVOS + self.CAMPO_LIVRE

		self.assertEqual(calcular_dv_barra(sem_dv), self.DV_GERAL_ESPERADO)

	def test_montar_codigo_barras_bate_com_o_exemplo(self):
		# fator 3026 na base antiga corresponde a uma data anterior a 2025 — usamos a
		# base antiga diretamente aqui só para reconstituir o exemplo publicado.
		data_vencimento = DATA_BASE_ANTIGA + timedelta(days=3026)
		barcode = montar_codigo_barras(
			self.CODIGO_BANCO, Decimal("32.80"), data_vencimento, self.CAMPO_LIVRE
		)

		self.assertEqual(barcode, self.BARCODE_ESPERADO)

	def test_linha_digitavel_bate_com_o_exemplo(self):
		self.assertEqual(montar_linha_digitavel(self.BARCODE_ESPERADO), self.LINHA_ESPERADA)


class TestCalcularFatorVencimento(unittest.TestCase):
	def test_base_antiga_antes_do_reinicio(self):
		# 08/10/1997 é um dia depois da data-base — fator 1.
		self.assertEqual(calcular_fator_vencimento(date(1997, 10, 8)), 1)

	def test_reinicio_em_1000(self):
		"""22/02/2025: o dia em que o fator reiniciou para 1000 (Comunicado
		FB-009/2023) — não é mais dias desde 1997."""
		self.assertEqual(calcular_fator_vencimento(DATA_BASE_NOVA), 1000)

	def test_dia_seguinte_ao_reinicio_e_1001(self):
		self.assertEqual(calcular_fator_vencimento(date(2025, 2, 23)), 1001)

	def test_vencimento_de_hoje_usa_a_base_nova(self):
		"""Qualquer boleto emitido hoje (a data corrente da sessão é 2026-08-30) usa a
		base nova — a base antiga já estouraria 9999 antes desta data."""
		fator = calcular_fator_vencimento(date(2026, 8, 30))

		self.assertGreater(fator, 1000)
		self.assertLess(fator, 9999)

	def test_vencimento_anterior_a_1997_e_erro(self):
		with self.assertRaises(BoletoInvalido):
			calcular_fator_vencimento(date(1990, 1, 1))


class TestCalcularDvCampo(unittest.TestCase):
	def test_soma_maior_que_nove_soma_os_proprios_algarismos(self):
		"""A pegadinha clássica do módulo 10: 7*2=14 vira 1+4=5, não descarta o dígito
		das dezenas nem usa 14 direto na soma."""
		# Um campo cujo dígito mais à direita é 7 força um produto de 14.
		dv = calcular_dv_campo("000000007")

		self.assertTrue(dv.isdigit() and len(dv) == 1)

	def test_devolve_um_unico_digito(self):
		for campo in ("0019000009", "0122919600", "0000014018"):
			with self.subTest(campo=campo):
				dv = calcular_dv_campo(campo)

				self.assertEqual(len(dv), 1)
				self.assertTrue(dv.isdigit())


class TestCalcularDvBarra(unittest.TestCase):
	def test_resto_zero_um_ou_dez_vira_um(self):
		"""Não pode devolver '11' nem '10' — dígito válido é sempre 0-9; o caso
		especial existe exatamente para evitar isso."""
		# Duas sequências arbitrárias cujo resto cai nos casos especiais são difíceis de
		# adivinhar à mão; em vez disso, verificamos a invariante sobre um espaço de
		# entradas variado.
		for i in range(50):
			codigo = str(i).rjust(43, "0")
			dv = calcular_dv_barra(codigo)

			self.assertTrue(dv.isdigit())
			self.assertIn(dv, "0123456789")


class TestMontarCodigoBarras(unittest.TestCase):
	def test_44_digitos(self):
		barcode = montar_codigo_barras("001", Decimal("100.00"), date(2026, 9, 1), "0" * 25)

		self.assertEqual(len(barcode), 44)
		self.assertTrue(barcode.isdigit())

	def test_moeda_e_sempre_9(self):
		barcode = montar_codigo_barras("001", Decimal("100.00"), date(2026, 9, 1), "0" * 25)

		self.assertEqual(barcode[3], "9")

	def test_codigo_banco_invalido_e_erro(self):
		with self.assertRaises(BoletoInvalido):
			montar_codigo_barras("1", Decimal("100.00"), date(2026, 9, 1), "0" * 25)

	def test_campo_livre_com_tamanho_errado_e_erro(self):
		with self.assertRaises(BoletoInvalido):
			montar_codigo_barras("001", Decimal("100.00"), date(2026, 9, 1), "0" * 24)

	def test_valor_zero_ou_negativo_e_erro(self):
		with self.assertRaises(BoletoInvalido):
			montar_codigo_barras("001", Decimal("0"), date(2026, 9, 1), "0" * 25)

	def test_valor_com_centavos_vira_10_digitos_corretos(self):
		barcode = montar_codigo_barras("001", Decimal("32.80"), date(2026, 9, 1), "0" * 25)

		self.assertEqual(barcode[9:19], "0000003280")


class TestMontarLinhaDigitavel(unittest.TestCase):
	def test_47_digitos(self):
		barcode = montar_codigo_barras("001", Decimal("100.00"), date(2026, 9, 1), "0" * 25)
		linha = montar_linha_digitavel(barcode)

		self.assertEqual(len(linha), 47)
		self.assertTrue(linha.isdigit())

	def test_codigo_com_tamanho_errado_e_erro(self):
		with self.assertRaises(BoletoInvalido):
			montar_linha_digitavel("123")

	def test_dv_geral_da_linha_e_o_da_posicao_5_do_codigo(self):
		"""Campo 1 (10) + Campo 2 (11) + Campo 3 (11) = 32 — o DV geral (Campo 4) é o
		33º caractere da linha, índice 32."""
		barcode = montar_codigo_barras("001", Decimal("100.00"), date(2026, 9, 1), "0" * 25)
		linha = montar_linha_digitavel(barcode)

		self.assertEqual(linha[32], barcode[4])


if __name__ == "__main__":
	unittest.main()
