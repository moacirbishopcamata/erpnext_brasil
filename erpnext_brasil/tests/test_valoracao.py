# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Aviso de valoração LIFO (`fiscal/valoracao.py`, `integracao/valoracao_estoque.py`) — tarefas 2.1 e 2.2.

Teste-âncora: `test_o_texto_declara_que_o_dispositivo_legal_esta_pendente`. A vedação ao UEPS tem fonte
secundária e não tem o artigo do RIR/2018; o aviso que fingisse certeza seria afirmar o que a pesquisa não provou.
"""

import ast
import pathlib
import unittest

from erpnext_brasil import hooks
from erpnext_brasil.fiscal.valoracao import METODO_NAO_ADMITIDO, METODOS_ADMITIDOS, aviso_de_valoracao

INTEGRACAO = pathlib.Path(__file__).resolve().parents[1] / "integracao" / "valoracao_estoque.py"


class TestAvisoDeValoracao(unittest.TestCase):
	def test_lifo_avisa(self):
		self.assertIsNotNone(aviso_de_valoracao("LIFO"))

	def test_os_metodos_admitidos_nao_avisam(self):
		for metodo in METODOS_ADMITIDOS:
			with self.subTest(metodo=metodo):
				self.assertIsNone(aviso_de_valoracao(metodo))

	def test_metodo_nao_definido_nao_avisa(self):
		for vazio in (None, "", "  "):
			with self.subTest(valor=vazio):
				self.assertIsNone(aviso_de_valoracao(vazio))

	def test_metodo_desconhecido_nao_e_tratado_como_lifo(self):
		self.assertIsNone(
			aviso_de_valoracao("lifo"), "o ERPNext grava a opção exata; minúscula é outra coisa"
		)
		self.assertIsNone(aviso_de_valoracao("Custo padrão"))

	def test_os_valores_batem_com_as_opcoes_do_erpnext_v16(self):
		"""`Item.valuation_method` e `Stock Settings.valuation_method`: FIFO, Moving Average, LIFO."""
		self.assertEqual(METODO_NAO_ADMITIDO, "LIFO")
		self.assertEqual(set(METODOS_ADMITIDOS) | {METODO_NAO_ADMITIDO}, {"FIFO", "Moving Average", "LIFO"})

	def test_o_texto_declara_que_o_dispositivo_legal_esta_pendente(self):
		texto = aviso_de_valoracao("LIFO")

		self.assertIn("pendente", texto)
		self.assertIn("aviso, não um bloqueio", texto)
		self.assertIn("segundo as fontes consultadas", texto)

	def test_o_texto_diz_o_que_fazer(self):
		texto = aviso_de_valoracao("LIFO")

		self.assertIn("PEPS (FIFO)", texto)
		self.assertIn("custo médio", texto)
		self.assertIn("UEPS", texto)


class TestCosturaDoAviso(unittest.TestCase):
	def test_ligado_no_item_e_no_stock_settings(self):
		alvo = "erpnext_brasil.integracao.valoracao_estoque.avisar_valoracao_lifo"

		self.assertIn(alvo, hooks.doc_events["Item"]["validate"])
		self.assertEqual(hooks.doc_events["Stock Settings"]["validate"], alvo)

	def test_o_item_continua_validando_o_ncm(self):
		self.assertIn("erpnext_brasil.integracao.party.validar_ncm", hooks.doc_events["Item"]["validate"])

	def test_nunca_bloqueia(self):
		corpo = ast.unparse(ast.parse(INTEGRACAO.read_text(encoding="utf-8")))

		self.assertIn("frappe.msgprint", corpo)
		self.assertNotIn("frappe.throw", corpo)

	def test_so_avisa_em_instalacao_brasileira(self):
		self.assertIn("pais_e_brasil()", INTEGRACAO.read_text(encoding="utf-8"))

	def test_a_funcao_publica_de_pais_existe_em_party(self):
		fonte = (INTEGRACAO.parent / "party.py").read_text(encoding="utf-8")

		self.assertIn("pais_e_brasil = _pais_e_brasil", fonte)


if __name__ == "__main__":
	unittest.main()
