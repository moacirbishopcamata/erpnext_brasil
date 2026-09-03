# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_bloco_9.py` — controle e encerramento do arquivo EFD.

O teste que mais importa é `TestContagemAutoReferente`: prova que a contagem do `9900`
inclui a si mesma e aos demais registros do Bloco 9, que é exatamente onde a aritmética
erra silenciosamente.
"""

import unittest

from erpnext_brasil.contabil.efd_bloco_9 import (
	montar_9001,
	montar_9900,
	montar_9990,
	montar_9999,
	montar_bloco_9,
)
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido


class TestRegistrosIndividuais(unittest.TestCase):
	def test_9001_com_dados(self):
		self.assertEqual(montar_9001()["IND_MOV"], "0")

	def test_9001_sem_dados(self):
		self.assertEqual(montar_9001(tem_dados=False)["IND_MOV"], "1")

	def test_9900_campos(self):
		campos = montar_9900("C100", 3)

		self.assertEqual(list(campos), ["REG", "REG_BLC", "QTD_REG_BLC"])
		self.assertEqual(campos["REG_BLC"], "C100")
		self.assertEqual(campos["QTD_REG_BLC"], "3")

	def test_9900_com_zero_ocorrencias_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_9900("C100", 0)

	def test_9990_campos(self):
		campos = montar_9990(7)

		self.assertEqual(list(campos), ["REG", "QTD_LIN_9"])
		self.assertEqual(campos["QTD_LIN_9"], "7")

	def test_9990_contagem_impossivel_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_9990(2)

	def test_9999_campos(self):
		campos = montar_9999(100)

		self.assertEqual(list(campos), ["REG", "QTD_LIN"])
		self.assertEqual(campos["QTD_LIN"], "100")


class TestContagemAutoReferente(unittest.TestCase):
	"""Um arquivo mínimo: Bloco 0 com 0000/0001/0990 e Bloco C com C001/C100/C190/C990.

	São 7 tipos distintos e 7 linhas fora do Bloco 9. Logo:
	- tipos totais = 7 + 4 = 11 → 11 linhas 9900
	- Bloco 9 = 1 (9001) + 11 (9900) + 1 (9990) = 13
	- arquivo = 7 + 13 + 1 (9999) = 21
	"""

	def setUp(self):
		self.contagem = {
			"0000": 1,
			"0001": 1,
			"0990": 1,
			"C001": 1,
			"C100": 1,
			"C190": 1,
			"C990": 1,
		}
		self.linhas = montar_bloco_9(self.contagem)

	def test_quantidade_de_linhas_9900(self):
		noves = [linha for linha in self.linhas if linha["REG"] == "9900"]

		self.assertEqual(len(noves), 11)

	def test_o_9900_totaliza_a_si_mesmo(self):
		"""O ponto exato onde a conta erra sozinha."""
		linha = next(linha for linha in self.linhas if linha.get("REG_BLC") == "9900")

		self.assertEqual(linha["QTD_REG_BLC"], "11")

	def test_o_9900_totaliza_os_demais_registros_do_bloco_9(self):
		por_registro = {
			linha["REG_BLC"]: linha["QTD_REG_BLC"] for linha in self.linhas if linha["REG"] == "9900"
		}

		self.assertEqual(por_registro["9001"], "1")
		self.assertEqual(por_registro["9990"], "1")
		self.assertEqual(por_registro["9999"], "1")

	def test_quantidade_de_linhas_do_bloco_9(self):
		encerramento = next(linha for linha in self.linhas if linha["REG"] == "9990")

		self.assertEqual(encerramento["QTD_LIN_9"], "13")

	def test_quantidade_de_linhas_do_arquivo(self):
		fim = next(linha for linha in self.linhas if linha["REG"] == "9999")

		self.assertEqual(fim["QTD_LIN"], "21")

	def test_o_total_do_arquivo_bate_com_a_contagem_real(self):
		"""Pós-condição de verdade: o `9999` tem de bater com a soma das linhas dos
		demais blocos mais as linhas do Bloco 9 efetivamente produzidas."""
		fim = next(linha for linha in self.linhas if linha["REG"] == "9999")

		linhas_reais = sum(self.contagem.values()) + len(self.linhas)

		self.assertEqual(int(fim["QTD_LIN"]), linhas_reais)

	def test_o_total_do_bloco_9_bate_com_as_linhas_produzidas(self):
		encerramento = next(linha for linha in self.linhas if linha["REG"] == "9990")

		# O 9999 é nível 0 (do arquivo), não pertence ao Bloco 9.
		linhas_do_bloco = len([linha for linha in self.linhas if linha["REG"] != "9999"])

		self.assertEqual(int(encerramento["QTD_LIN_9"]), linhas_do_bloco)

	def test_ordem_das_linhas(self):
		self.assertEqual(self.linhas[0]["REG"], "9001")
		self.assertEqual(self.linhas[-2]["REG"], "9990")
		self.assertEqual(self.linhas[-1]["REG"], "9999")

	def test_linhas_9900_em_ordem_deterministica(self):
		codigos = [linha["REG_BLC"] for linha in self.linhas if linha["REG"] == "9900"]

		self.assertEqual(codigos, sorted(codigos))


class TestContagemComRepeticao(unittest.TestCase):
	def test_registro_repetido_conta_certo(self):
		"""Vinte notas: `C100` aparece 20 vezes, mas é **um** tipo (uma linha 9900)."""
		linhas = montar_bloco_9({"0000": 1, "0001": 1, "0990": 1, "C001": 1, "C100": 20, "C990": 1})

		por_registro = {linha["REG_BLC"]: linha["QTD_REG_BLC"] for linha in linhas if linha["REG"] == "9900"}

		self.assertEqual(por_registro["C100"], "20")
		self.assertEqual(por_registro["9900"], "10")  # 6 tipos + 4 do Bloco 9

	def test_total_do_arquivo_com_repeticao(self):
		contagem = {"0000": 1, "0001": 1, "0990": 1, "C001": 1, "C100": 20, "C990": 1}
		linhas = montar_bloco_9(contagem)

		fim = next(linha for linha in linhas if linha["REG"] == "9999")

		self.assertEqual(int(fim["QTD_LIN"]), sum(contagem.values()) + len(linhas))


class TestValidacoesDeEntrada(unittest.TestCase):
	def test_contagem_vazia_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_bloco_9({})

	def test_registro_do_bloco_9_na_entrada_e_erro(self):
		"""A quantidade deles é justamente o que a função calcula."""
		with self.assertRaises(EfdInvalido):
			montar_bloco_9({"0000": 1, "9900": 3})

	def test_contagem_zero_na_entrada_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_bloco_9({"0000": 1, "C100": 0})


if __name__ == "__main__":
	unittest.main()
