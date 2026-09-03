# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/cnab240_retorno.py` — Segmentos T e U do retorno CNAB 240."""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.cnab240_retorno import (
	RetornoCnab240Invalido,
	SegmentoT,
	SegmentoU,
	foi_pago,
	ler_segmento_t,
	ler_segmento_u,
)


def _linha_segmento_t(
	*, codigo_movimento: str = "06", identificacao_titulo: str = "000000000000123456"
) -> str:
	"""Monta uma linha sintética de 240 posições com os campos confirmados nas
	posições certas — o resto preenchido com espaços, como campos não usados por
	este módulo (nunca lidos, então o valor não importa para o teste)."""
	linha = [" "] * 240
	linha[15:17] = list(codigo_movimento)
	linha[37:57] = list(identificacao_titulo.rjust(20))

	return "".join(linha)


def _linha_segmento_u(
	*, codigo_movimento: str = "06", valor_centavos: str = "000000000012345", data: str = "15062026"
) -> str:
	linha = [" "] * 240
	linha[15:17] = list(codigo_movimento)
	linha[77:92] = list(valor_centavos)
	linha[137:145] = list(data)

	return "".join(linha)


class TestLerSegmentoT(unittest.TestCase):
	def test_le_campos_corretamente(self):
		linha = _linha_segmento_t(codigo_movimento="06", identificacao_titulo="123456789")

		segmento = ler_segmento_t(linha)

		self.assertEqual(segmento.codigo_movimento, "06")
		self.assertEqual(segmento.identificacao_titulo, "123456789")

	def test_tamanho_errado_e_erro(self):
		with self.assertRaises(RetornoCnab240Invalido):
			ler_segmento_t("linha curta demais")


class TestLerSegmentoU(unittest.TestCase):
	def test_le_campos_corretamente(self):
		linha = _linha_segmento_u(codigo_movimento="06", valor_centavos="000000000012345", data="15062026")

		segmento = ler_segmento_u(linha)

		self.assertEqual(segmento.codigo_movimento, "06")
		self.assertEqual(segmento.valor_pago, Decimal("123.45"))
		self.assertEqual(segmento.data_ocorrencia, date(2026, 6, 15))

	def test_valor_nao_numerico_e_erro(self):
		linha = list(_linha_segmento_u())
		linha[77:92] = list("ABCDEFGHIJKLMNO")

		with self.assertRaises(RetornoCnab240Invalido):
			ler_segmento_u("".join(linha))

	def test_data_invalida_e_erro(self):
		linha = _linha_segmento_u(data="99992026")

		with self.assertRaises(RetornoCnab240Invalido):
			ler_segmento_u(linha)

	def test_data_usa_ano_completo_nao_2_digitos(self):
		"""Diferente do CNAB 400 (DDMMAA) — aqui é DDMMAAAA, sem suposição de século."""
		linha = _linha_segmento_u(data="01011999")

		segmento = ler_segmento_u(linha)

		self.assertEqual(segmento.data_ocorrencia, date(1999, 1, 1))

	def test_tamanho_errado_e_erro(self):
		with self.assertRaises(RetornoCnab240Invalido):
			ler_segmento_u("curto")


class TestForaPagoReaproveitaDoCnab400(unittest.TestCase):
	def test_liquidacao_e_pago(self):
		self.assertTrue(foi_pago("06"))

	def test_entrada_confirmada_nao_e_pago(self):
		self.assertFalse(foi_pago("02"))


class TestDataclasses(unittest.TestCase):
	def test_segmento_t_e_congelado(self):
		segmento = SegmentoT(identificacao_titulo="1", codigo_movimento="06")

		with self.assertRaises(FrozenInstanceError):
			segmento.codigo_movimento = "03"

	def test_segmento_u_e_congelado(self):
		segmento = SegmentoU(
			codigo_movimento="06", valor_pago=Decimal("1.00"), data_ocorrencia=date(2026, 1, 1)
		)

		with self.assertRaises(FrozenInstanceError):
			segmento.valor_pago = Decimal("2.00")


if __name__ == "__main__":
	unittest.main()
