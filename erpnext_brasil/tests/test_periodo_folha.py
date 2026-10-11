# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/periodo.py` e da costura que o usa (RT-01 da revisão total).

O teste que mais importa é `TestACosturaPassaOAno`: lê o código de `integracao/folha.py` e falha se
`calcular_inss` ou `calcular_irrf` forem chamados sem `ano=`. Foi essa omissão que fez a folha de qualquer
período usar a tabela de 2026 sem erro.
"""

import ast
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from erpnext_brasil.folha.inss import INSSInvalido, calcular_inss
from erpnext_brasil.folha.irrf import IRRFInvalido, calcular_irrf
from erpnext_brasil.folha.periodo import PeriodoInvalido, ano_do_periodo

INTEGRACAO = Path(__file__).resolve().parents[1] / "integracao" / "folha.py"


class TestAnoDoPeriodo(unittest.TestCase):
	def test_o_ano_e_o_do_fim_do_periodo(self):
		self.assertEqual(ano_do_periodo("2027-01-31", "2027-01-01"), 2027)

	def test_periodo_que_cruza_a_virada_vale_pelo_ano_em_que_termina(self):
		self.assertEqual(ano_do_periodo("2027-01-15", "2026-12-16"), 2027)

	def test_sem_fim_vale_o_inicio(self):
		self.assertEqual(ano_do_periodo(None, "2026-06-01"), 2026)
		self.assertEqual(ano_do_periodo("", "2026-06-01"), 2026)

	def test_aceita_date_e_datetime(self):
		self.assertEqual(ano_do_periodo(date(2025, 3, 31)), 2025)
		self.assertEqual(ano_do_periodo(datetime(2025, 3, 31, 10, 0)), 2025)

	def test_sem_nenhuma_data_recusa_em_vez_de_supor_o_ano_corrente(self):
		with self.assertRaises(PeriodoInvalido):
			ano_do_periodo(None, None)

	def test_data_ilegivel_recusa(self):
		with self.assertRaises(PeriodoInvalido):
			ano_do_periodo("31/01/2027")


class TestAnoSemTabelaRecusa(unittest.TestCase):
	"""O que a integração passa a receber ao entregar o ano certo: erro, não tabela de outro ano."""

	def test_inss_de_2027_recusa(self):
		with self.assertRaises(INSSInvalido):
			calcular_inss(Decimal("5000"), ano=ano_do_periodo("2027-01-31"))

	def test_irrf_de_2027_recusa(self):
		with self.assertRaises(IRRFInvalido):
			calcular_irrf(Decimal("5000"), Decimal("4500"), ano=2027)


class TestACosturaPassaOAno(unittest.TestCase):
	def test_a_integracao_nunca_chama_o_calculo_sem_ano(self):
		arvore = ast.parse(INTEGRACAO.read_text(encoding="utf-8"))
		chamadas = [
			n
			for n in ast.walk(arvore)
			if isinstance(n, ast.Call)
			and isinstance(n.func, ast.Name)
			and n.func.id in {"calcular_inss", "calcular_irrf"}
		]

		self.assertEqual(len(chamadas), 2, "esperava uma chamada de INSS e uma de IRRF")

		for chamada in chamadas:
			self.assertIn(
				"ano",
				{k.arg for k in chamada.keywords},
				f"{chamada.func.id} chamado sem ano= em integracao/folha.py:{chamada.lineno}",
			)


if __name__ == "__main__":
	unittest.main()
