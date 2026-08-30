# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/cnab400_retorno.py` — leitura do registro detalhe do retorno.

O teste que mais importa é `test_confirmacao_de_entrada_nao_e_pago`: o erro que
`FOI_PAGO` existe para evitar — código "02" (confirmação de entrada) não é a mesma
coisa que dinheiro recebido, mesmo soando "positivo".
"""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.cnab400_retorno import (
	CODIGOS_OCORRENCIA,
	CODIGOS_OCORRENCIA_CORROBORADOS,
	RegistroDetalhe,
	RetornoCnabInvalido,
	foi_pago,
	ler_registro_detalhe,
)


def _linha(nosso_numero="", codigo="", data="", valor="") -> str:
	"""Monta uma linha de 400 posições com os campos relevantes nas posições certas
	(1-indexed): nosso número 71-82, código 109-110, data 147-152, valor 254-266."""
	linha = list(" " * 400)
	linha[70:82] = list(nosso_numero.ljust(12))
	linha[108:110] = list(codigo.rjust(2, "0"))
	linha[146:152] = list(data.rjust(6, "0"))
	linha[253:266] = list(valor.rjust(13, "0"))

	return "".join(linha)


class TestLerRegistroDetalhe(unittest.TestCase):
	def test_le_os_quatro_campos(self):
		linha = _linha(nosso_numero="000123456789", codigo="06", data="150326", valor="0000000010000")
		registro = ler_registro_detalhe(linha)

		self.assertEqual(registro.nosso_numero, "000123456789")
		self.assertEqual(registro.codigo_ocorrencia, "06")
		self.assertEqual(registro.data_ocorrencia, date(2026, 3, 15))
		self.assertEqual(registro.valor, Decimal("100.00"))

	def test_tamanho_diferente_de_400_e_erro(self):
		with self.assertRaises(RetornoCnabInvalido):
			ler_registro_detalhe("123")

	def test_data_invalida_e_erro(self):
		linha = _linha(codigo="06", data="329926", valor="0000000010000")  # dia 32, mês 99

		with self.assertRaises(RetornoCnabInvalido):
			ler_registro_detalhe(linha)

	def test_valor_nao_numerico_e_erro(self):
		linha = list(_linha(codigo="06", data="150326", valor="0000000010000"))
		linha[253:266] = list("ABCDEFGHIJKLM")

		with self.assertRaises(RetornoCnabInvalido):
			ler_registro_detalhe("".join(linha))

	def test_nosso_numero_e_lido_sem_espacos_a_mais(self):
		registro = ler_registro_detalhe(_linha(nosso_numero="123", codigo="06", data="150326", valor="1"))

		self.assertEqual(registro.nosso_numero, "123")


class TestFoiPago(unittest.TestCase):
	def test_liquidacao_normal_e_pago(self):
		self.assertTrue(foi_pago("06"))

	def test_liquidacao_apos_baixa_e_pago(self):
		self.assertTrue(foi_pago("17"))

	def test_confirmacao_de_entrada_nao_e_pago(self):
		"""O erro que FOI_PAGO existe para evitar: '02' soa positivo, mas é só a
		confirmação de que o banco recebeu o registro — não é dinheiro recebido."""
		self.assertFalse(foi_pago("02"))

	def test_baixa_nao_e_pago(self):
		self.assertFalse(foi_pago("09"))

	def test_codigo_desconhecido_nao_e_pago(self):
		self.assertFalse(foi_pago("99"))


class TestTabelaDeCodigos(unittest.TestCase):
	def test_os_quatro_codigos_mais_comuns_estao_corroborados(self):
		self.assertEqual(CODIGOS_OCORRENCIA_CORROBORADOS, frozenset({"02", "03", "06", "09"}))

	def test_todo_codigo_corroborado_existe_na_tabela_principal(self):
		self.assertTrue(CODIGOS_OCORRENCIA_CORROBORADOS.issubset(CODIGOS_OCORRENCIA))

	def test_todo_codigo_de_foi_pago_existe_na_tabela_principal(self):
		from erpnext_brasil.contabil.cnab400_retorno import FOI_PAGO

		self.assertTrue(FOI_PAGO.issubset(CODIGOS_OCORRENCIA))


if __name__ == "__main__":
	unittest.main()
