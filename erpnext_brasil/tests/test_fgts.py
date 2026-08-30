# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/fgts.py` — depósito mensal e multa rescisória do FGTS."""

import unittest
from decimal import Decimal

from erpnext_brasil.folha.fgts import (
	ALIQUOTA_APRENDIZ,
	ALIQUOTA_MULTA_POR_MOTIVO,
	ALIQUOTA_PADRAO,
	FGTSInvalido,
	calcular_deposito_mensal,
	calcular_multa_rescisoria,
)


def d(v: str) -> Decimal:
	return Decimal(v)


class TestCalcularDepositoMensal(unittest.TestCase):
	def test_aliquota_padrao_e_8_por_cento(self):
		self.assertEqual(ALIQUOTA_PADRAO, d("0.08"))
		self.assertEqual(calcular_deposito_mensal(d("2000.00")), d("160.00"))

	def test_aprendiz_usa_2_por_cento(self):
		self.assertEqual(ALIQUOTA_APRENDIZ, d("0.02"))
		self.assertEqual(calcular_deposito_mensal(d("1000.00"), aprendiz=True), d("20.00"))

	def test_remuneracao_zero_e_zero(self):
		self.assertEqual(calcular_deposito_mensal(d("0.00")), d("0.00"))

	def test_remuneracao_negativa_e_erro(self):
		with self.assertRaises(FGTSInvalido):
			calcular_deposito_mensal(d("-1.00"))


class TestCalcularMultaRescisoria(unittest.TestCase):
	def test_sem_justa_causa_e_40_por_cento(self):
		self.assertEqual(calcular_multa_rescisoria(d("10000.00"), "sem_justa_causa"), d("4000.00"))

	def test_acordo_e_metade_da_multa_cheia(self):
		total = d("10000.00")
		cheia = calcular_multa_rescisoria(total, "sem_justa_causa")
		acordo = calcular_multa_rescisoria(total, "acordo")

		self.assertEqual(acordo, cheia / 2)
		self.assertEqual(acordo, d("2000.00"))

	def test_culpa_reciproca_ou_forca_maior_e_20_por_cento(self):
		self.assertEqual(
			calcular_multa_rescisoria(d("10000.00"), "culpa_reciproca_ou_forca_maior"), d("2000.00")
		)

	def test_justa_causa_nao_gera_multa(self):
		self.assertEqual(calcular_multa_rescisoria(d("10000.00"), "justa_causa"), d("0.00"))

	def test_pedido_de_demissao_nao_gera_multa(self):
		self.assertEqual(calcular_multa_rescisoria(d("10000.00"), "pedido_de_demissao"), d("0.00"))

	def test_termino_de_contrato_determinado_nao_gera_multa(self):
		self.assertEqual(
			calcular_multa_rescisoria(d("10000.00"), "termino_de_contrato_determinado"), d("0.00")
		)

	def test_motivo_desconhecido_e_erro_nao_zero_silencioso(self):
		with self.assertRaises(FGTSInvalido):
			calcular_multa_rescisoria(d("10000.00"), "motivo_inventado")

	def test_total_negativo_e_erro(self):
		with self.assertRaises(FGTSInvalido):
			calcular_multa_rescisoria(d("-1.00"), "sem_justa_causa")

	def test_todos_os_motivos_da_tabela_sao_calculaveis(self):
		for motivo in ALIQUOTA_MULTA_POR_MOTIVO:
			with self.subTest(motivo=motivo):
				calcular_multa_rescisoria(d("5000.00"), motivo)


if __name__ == "__main__":
	unittest.main()
