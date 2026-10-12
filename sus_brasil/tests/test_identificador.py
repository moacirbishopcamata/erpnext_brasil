# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

import unittest

from sus_brasil.puro import identificador as ident


class TestIdentificador(unittest.TestCase):
	def test_formata_e_confere_ida_e_volta(self):
		for seq in (1, 2, 99, 123456789, 999_999_999):
			texto = ident.formatar(seq)
			self.assertEqual(len(texto), 10)
			self.assertEqual(ident.conferir(texto), texto)
			self.assertEqual(ident.numero_de(texto), seq)

	def test_e_unico_para_sequencias_distintas(self):
		vistos = {ident.formatar(n) for n in range(1, 5001)}
		self.assertEqual(len(vistos), 5000)

	def test_um_digito_errado_sempre_e_pego(self):
		texto = ident.formatar(123456)

		for pos in range(len(texto)):
			for novo in "0123456789":
				if novo == texto[pos]:
					continue

				errado = texto[:pos] + novo + texto[pos + 1 :]

				with self.assertRaises(ident.IdentificadorInvalido, msg=errado):
					ident.conferir(errado)

	def test_troca_de_vizinhos_sempre_e_pega(self):
		for seq in (123456, 5, 987654321, 1010101):
			texto = ident.formatar(seq)

			for pos in range(len(texto) - 1):
				if texto[pos] == texto[pos + 1]:
					continue

				trocado = texto[:pos] + texto[pos + 1] + texto[pos] + texto[pos + 2 :]

				with self.assertRaises(ident.IdentificadorInvalido, msg=trocado):
					ident.conferir(trocado)

	def test_recusa_formato(self):
		for ruim in ("", "123", "abcdefghij", "12345678901", " 12 ", "١٢٣٤٥٦٧٨٩٠"):
			with self.assertRaises(ident.IdentificadorInvalido):
				ident.conferir(ruim)

	def test_sequencia_invalida(self):
		with self.assertRaises(ValueError):
			ident.formatar(0)

		with self.assertRaises(ValueError):
			ident.formatar(10**9)

	def test_largura_e_parametro(self):
		texto = ident.formatar(7, largura=6)
		self.assertEqual(len(texto), 7)
		self.assertEqual(ident.numero_de(texto, largura=6), 7)

	def test_identificador_vizinho_nao_e_aceito_como_o_mesmo(self):
		a = ident.formatar(10)
		b = ident.formatar(11)
		self.assertNotEqual(a, b)

		with self.assertRaises(ident.IdentificadorInvalido):
			ident.conferir(a[:-1] + str((int(a[-1]) + 1) % 10))


if __name__ == "__main__":
	unittest.main()
