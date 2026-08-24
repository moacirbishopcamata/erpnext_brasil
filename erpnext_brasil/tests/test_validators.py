# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes das funções puras de validação fiscal.

Rodam sem bench, sem site e sem banco:

    python -m unittest discover -s erpnext_brasil/tests -t .

O valor `12.ABC.345/01DE-35` é o exemplo de CNPJ alfanumérico divulgado pela Receita
Federal; serve de âncora para a mudança de julho de 2026.
"""

import unittest

from erpnext_brasil.fiscal.validators import (
	ValidacaoFiscalError,
	formatar_cnpj,
	formatar_cpf,
	limpar,
	validar_cnpj,
	validar_cpf,
	validar_cpf_cnpj,
)


class TestCNPJ(unittest.TestCase):
	def test_aceita_cnpj_numerico_com_e_sem_mascara(self):
		self.assertEqual(validar_cnpj("11.222.333/0001-81"), "11222333000181")
		self.assertEqual(validar_cnpj("11222333000181"), "11222333000181")

	def test_aceita_cnpj_alfanumerico(self):
		self.assertEqual(validar_cnpj("12.ABC.345/01DE-35"), "12ABC34501DE35")

	def test_aceita_alfanumerico_em_minusculas(self):
		# O usuário digita como quiser; a normalização é responsabilidade do validador.
		self.assertEqual(validar_cnpj("12abc34501de35"), "12ABC34501DE35")

	def test_rejeita_dv_incorreto(self):
		for invalido in ("11222333000182", "12ABC34501DE34"):
			with self.assertRaises(ValidacaoFiscalError):
				validar_cnpj(invalido)

	def test_rejeita_sequencia_repetida(self):
		with self.assertRaises(ValidacaoFiscalError):
			validar_cnpj("11.111.111/1111-11")

	def test_rejeita_comprimento_errado(self):
		for invalido in ("", "123", "112223330001811"):
			with self.assertRaises(ValidacaoFiscalError):
				validar_cnpj(invalido)

	def test_rejeita_dv_nao_numerico(self):
		# Os dois últimos dígitos continuam numéricos mesmo no CNPJ alfanumérico.
		with self.assertRaises(ValidacaoFiscalError):
			validar_cnpj("12ABC34501DEAB")

	def test_formatacao_preserva_letras(self):
		self.assertEqual(formatar_cnpj("12ABC34501DE35"), "12.ABC.345/01DE-35")


class TestCPF(unittest.TestCase):
	def test_aceita_cpf_valido(self):
		self.assertEqual(validar_cpf("111.444.777-35"), "11144477735")

	def test_rejeita_dv_incorreto(self):
		with self.assertRaises(ValidacaoFiscalError):
			validar_cpf("111.444.777-36")

	def test_rejeita_sequencia_repetida(self):
		with self.assertRaises(ValidacaoFiscalError):
			validar_cpf("00000000000")

	def test_rejeita_letras(self):
		with self.assertRaises(ValidacaoFiscalError):
			validar_cpf("1114447773A")

	def test_formatacao(self):
		self.assertEqual(formatar_cpf("11144477735"), "111.444.777-35")


class TestDespacho(unittest.TestCase):
	def test_decide_pelo_comprimento(self):
		self.assertEqual(validar_cpf_cnpj("111.444.777-35"), "11144477735")
		self.assertEqual(validar_cpf_cnpj("11.222.333/0001-81"), "11222333000181")

	def test_rejeita_comprimento_intermediario(self):
		with self.assertRaises(ValidacaoFiscalError) as ctx:
			validar_cpf_cnpj("1234567890123")

		self.assertIn("11 (CPF) ou 14 (CNPJ)", str(ctx.exception))


class TestLimpeza(unittest.TestCase):
	def test_remove_mascara_e_normaliza(self):
		self.assertEqual(limpar(" 12.abc.345/01de-35 "), "12ABC34501DE35")

	def test_valor_vazio(self):
		self.assertEqual(limpar(None), "")
		self.assertEqual(limpar(""), "")


if __name__ == "__main__":
	unittest.main()
