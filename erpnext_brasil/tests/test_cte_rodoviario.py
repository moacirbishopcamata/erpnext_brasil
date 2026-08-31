# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/cte_rodoviario.py` — modal rodoviário do CT-e (`infModal/rodo`)."""

import unittest

from erpnext_brasil.fiscal.cte_rodoviario import RntrcInvalido, montar_rodo, validar_rntrc


class TestValidarRntrc(unittest.TestCase):
	def test_oito_digitos_e_valido(self):
		self.assertEqual(validar_rntrc("12345678"), "12345678")

	def test_isento_e_valido(self):
		"""ISENTO é o valor de quem transporta com frota própria e está dispensado do
		registro na ANTT — não é formato inválido, é um segundo valor literal legítimo."""
		self.assertEqual(validar_rntrc("isento"), "ISENTO")

	def test_menos_de_oito_digitos_e_invalido(self):
		with self.assertRaises(RntrcInvalido):
			validar_rntrc("1234567")

	def test_letras_fora_de_isento_e_invalido(self):
		with self.assertRaises(RntrcInvalido):
			validar_rntrc("ABCD1234")

	def test_vazio_e_invalido(self):
		with self.assertRaises(RntrcInvalido):
			validar_rntrc("")


class TestMontarRodo(unittest.TestCase):
	def test_sem_ordens_de_coleta(self):
		grupo = montar_rodo("12345678")

		self.assertEqual(grupo, {"RNTRC": "12345678"})
		self.assertNotIn("occ", grupo)

	def test_com_ordens_de_coleta(self):
		ordem = {"nOcc": "1", "dEmi": "2026-08-31"}

		grupo = montar_rodo("12345678", ordens_coleta=[ordem])

		self.assertEqual(grupo["occ"], [ordem])

	def test_rntrc_invalido_propaga_erro(self):
		with self.assertRaises(RntrcInvalido):
			montar_rodo("abc")


if __name__ == "__main__":
	unittest.main()
