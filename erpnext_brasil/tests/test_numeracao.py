# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/numeracao.py` — as regras do `nNF` e da `serie`.

Teste-âncora: `test_serie_do_xml_nao_e_a_do_registro_d100` — o mesmo conceito com formato
diferente em dois artefatos, que é a armadilha recorrente deste projeto.

A alocação sob concorrência (`integracao/numeracao_fiscal.py`) não é exercitada aqui:
depende de transação e trava de linha, e só um teste de bench a prova. Lacuna registrada
em `docs/gaps.md`.
"""

import unittest

from erpnext_brasil.fiscal.documento.numeracao import (
	NUMERO_MAXIMO,
	NUMERO_MINIMO,
	NumeracaoInvalida,
	primeiro_numero,
	proximo_numero,
	validar_numero,
	validar_serie,
)


class TestNumero(unittest.TestCase):
	def test_a_faixa_e_a_do_xsd(self):
		"""TNF: [1-9][0-9]{0,8} — de 1 a 999.999.999."""
		self.assertEqual(NUMERO_MINIMO, 1)
		self.assertEqual(NUMERO_MAXIMO, 999_999_999)
		self.assertEqual(validar_numero(NUMERO_MAXIMO), "999999999")

	def test_aceita_int_e_str(self):
		"""O número vive como inteiro no banco e como texto no XML."""
		self.assertEqual(validar_numero(42), "42")
		self.assertEqual(validar_numero("42"), "42")

	def test_zero_a_esquerda_e_recusado(self):
		"""O primeiro dígito é [1-9]: '007' não é 7 para o schema."""
		for invalido in ("007", "0042", "0"):
			with self.subTest(numero=invalido):
				with self.assertRaises(NumeracaoInvalida):
					validar_numero(invalido)

	def test_zero_e_recusado(self):
		with self.assertRaises(NumeracaoInvalida):
			validar_numero(0)

	def test_acima_do_maximo_e_recusado(self):
		with self.assertRaises(NumeracaoInvalida):
			validar_numero(NUMERO_MAXIMO + 1)

	def test_negativo_e_recusado(self):
		with self.assertRaises(NumeracaoInvalida):
			validar_numero(-1)

	def test_espaco_em_volta_e_tolerado(self):
		self.assertEqual(validar_numero("  42 "), "42")


class TestSerie(unittest.TestCase):
	def test_zero_e_serie_valida(self):
		"""TSerie começa com a alternativa literal `0`."""
		self.assertEqual(validar_serie("0"), "0")
		self.assertEqual(validar_serie(0), "0")

	def test_serie_do_xml_nao_e_a_do_registro_d100(self):
		"""O achado: '000' vale no SPED e **não** vale no XML.

		O `SER` do registro `D100` exige três posições, informando '000' quando não há
		série. O `TSerie` do XSD recusa zero à esquerda. Transportar o formato de um para o
		outro produz documento rejeitado — e é o erro natural de quem implementou o SPED
		antes.
		"""
		from erpnext_brasil.contabil.efd_bloco_d import MODELOS_COM_SERIE_DE_TRES_POSICOES

		self.assertIn("57", MODELOS_COM_SERIE_DE_TRES_POSICOES)

		with self.assertRaises(NumeracaoInvalida) as erro:
			validar_serie("000")

		self.assertIn("D100", str(erro.exception))

	def test_faixa_de_um_a_novecentos_e_noventa_e_nove(self):
		self.assertEqual(validar_serie("999"), "999")

		with self.assertRaises(NumeracaoInvalida):
			validar_serie("1000")

	def test_zero_a_esquerda_e_recusado(self):
		for invalido in ("00", "01", "007"):
			with self.subTest(serie=invalido):
				with self.assertRaises(NumeracaoInvalida):
					validar_serie(invalido)


class TestSequencia(unittest.TestCase):
	def test_a_primeira_nota_e_o_numero_um(self):
		self.assertEqual(primeiro_numero(), "1")

	def test_o_proximo_e_sempre_o_sucessor_imediato(self):
		"""Nunca "o próximo livre": pular esconde lacuna que exige inutilização."""
		self.assertEqual(proximo_numero("1"), "2")
		self.assertEqual(proximo_numero(41), "42")

	def test_faixa_esgotada_falha_alto(self):
		"""A continuação é abrir série nova, não reiniciar a contagem."""
		with self.assertRaises(NumeracaoInvalida) as erro:
			proximo_numero(NUMERO_MAXIMO)

		self.assertIn("série nova", str(erro.exception))

	def test_o_sucessor_continua_valido_para_o_xsd(self):
		"""Pós-condição: o que sai daqui entra no XML sem nova validação."""
		for atual in ("1", "9", "99", "999999998"):
			with self.subTest(atual=atual):
				validar_numero(proximo_numero(atual))

	def test_nao_avanca_a_partir_de_numero_invalido(self):
		"""Somar um a lixo produziria lixo com cara de número."""
		with self.assertRaises(NumeracaoInvalida):
			proximo_numero("0")


if __name__ == "__main__":
	unittest.main()
