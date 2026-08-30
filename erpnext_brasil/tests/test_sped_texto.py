# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/sped_texto.py` — formatação da linha de texto do SPED.

O teste que mais importa é `test_e110_de_verdade_serializa`: prova que a camada de
formato funciona de ponta a ponta com um registro real produzido por `efd_icms_ipi.py`,
não só com `dict`s inventados para o teste.
"""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.apuracao_periodo import ApuracaoPeriodo
from erpnext_brasil.contabil.ecd_i050 import montar_i050
from erpnext_brasil.contabil.ecd_i150 import montar_i150
from erpnext_brasil.contabil.efd_icms_ipi import montar_e110
from erpnext_brasil.contabil.sped_texto import SpedTextoInvalido, formatar_campo, montar_linha


def d(v: str) -> Decimal:
	return Decimal(v)


class TestFormatarCampo(unittest.TestCase):
	def test_decimal_usa_virgula(self):
		self.assertEqual(formatar_campo(d("1234.56")), "1234,56")

	def test_decimal_inteiro_mantem_duas_casas(self):
		self.assertEqual(formatar_campo(d("100.00")), "100,00")

	def test_data_e_ddmmaaaa_sem_separador(self):
		self.assertEqual(formatar_campo(date(2026, 1, 5)), "05012026")

	def test_string_passa_direto(self):
		self.assertEqual(formatar_campo("E110"), "E110")

	def test_none_vira_vazio(self):
		self.assertEqual(formatar_campo(None), "")

	def test_string_vazia_continua_vazia(self):
		self.assertEqual(formatar_campo(""), "")

	def test_pipe_no_texto_e_rejeitado(self):
		with self.assertRaises(SpedTextoInvalido):
			formatar_campo("Descrição com | dentro")


class TestMontarLinha(unittest.TestCase):
	def test_comeca_e_termina_com_pipe(self):
		linha = montar_linha({"REG": "E110", "VL": d("100.00")})

		self.assertTrue(linha.startswith("|"))
		self.assertTrue(linha.endswith("|"))

	def test_campos_separados_por_pipe_na_ordem(self):
		linha = montar_linha({"REG": "E110", "A": "1", "B": "2"})

		self.assertEqual(linha, "|E110|1|2|")

	def test_campo_vazio_fica_entre_dois_pipes_sem_nada(self):
		linha = montar_linha({"REG": "I150", "DT_INI": None, "DT_FIN": ""})

		self.assertEqual(linha, "|I150|||")

	def test_dict_vazio_e_dois_pipes(self):
		"""Sem campo nenhum, sobra só o `|` de abertura e o de fechamento."""
		self.assertEqual(montar_linha({}), "||")


class TestIntegracaoComRegistrosReais(unittest.TestCase):
	def test_e110_de_verdade_serializa(self):
		apuracao = ApuracaoPeriodo(tributo="ICMS", debitos=d("1000.00"), creditos=d("400.00"))
		linha = montar_linha(montar_e110(apuracao))

		self.assertTrue(linha.startswith("|E110|1000,00|"))
		self.assertTrue(linha.endswith("|"))
		self.assertEqual(linha.count("|"), 16)  # 15 campos + o pipe inicial.

	def test_i050_de_verdade_serializa(self):
		linhas_i050 = montar_i050("01012026")
		primeira = montar_linha(linhas_i050[0])

		self.assertTrue(primeira.startswith("|I050|01012026|"))

	def test_i150_com_data_de_verdade_serializa(self):
		linha = montar_linha(montar_i150(date(2026, 1, 1), date(2026, 1, 31)))

		self.assertEqual(linha, "|I150|01012026|31012026|")


if __name__ == "__main__":
	unittest.main()
