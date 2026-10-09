# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) do aviso de valoração LIFO: o Frappe grava, a mensagem aparece, nada é bloqueado.

Teste-âncora: `test_item_com_lifo_e_gravado_e_o_aviso_aparece`. Avisar sem deixar gravar seria a regra não
comprovada (UEPS) virando bloqueio por baixo dos panos.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_valoracao_estoque
"""

from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao import valoracao_estoque
from erpnext_brasil.integracao.valoracao_estoque import avisar_valoracao_lifo

MODULOS_COBERTOS = ("valoracao_estoque",)
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""


class TestAvisoDeValoracaoNoBench(FrappeTestCase):
	def _mensagens(self, doc, brasil: bool = True) -> list[str]:
		with (
			mock.patch.object(valoracao_estoque, "pais_e_brasil", return_value=brasil),
			mock.patch.object(valoracao_estoque.frappe, "msgprint") as msgprint,
		):
			avisar_valoracao_lifo(doc)

		return [str(chamada.args[0]) for chamada in msgprint.call_args_list]

	def test_lifo_no_item_avisa(self):
		mensagens = self._mensagens(frappe._dict(valuation_method="LIFO"))

		self.assertEqual(len(mensagens), 1)
		self.assertIn("LIFO", mensagens[0])
		self.assertIn("pendente", mensagens[0])

	def test_lifo_no_stock_settings_avisa(self):
		settings = frappe.get_doc("Stock Settings")
		settings.valuation_method = "LIFO"

		self.assertEqual(len(self._mensagens(settings)), 1)

	def test_metodos_admitidos_nao_avisam(self):
		for metodo in ("FIFO", "Moving Average", "", None):
			with self.subTest(metodo=metodo):
				self.assertEqual(self._mensagens(frappe._dict(valuation_method=metodo)), [])

	def test_fora_do_brasil_nao_avisa(self):
		self.assertEqual(self._mensagens(frappe._dict(valuation_method="LIFO"), brasil=False), [])

	def test_item_com_lifo_e_gravado_e_o_aviso_aparece(self):
		frappe.local.message_log = []
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_Teste LIFO",
				"item_name": "Teste LIFO",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"valuation_method": "LIFO",
			}
		)

		with mock.patch.object(valoracao_estoque, "pais_e_brasil", return_value=True):
			item.insert(ignore_permissions=True, ignore_mandatory=True)

		self.assertEqual(
			frappe.db.get_value("Item", item.name, "valuation_method"), "LIFO", "o aviso bloqueou"
		)
		self.assertTrue(any("LIFO" in str(m) for m in frappe.local.message_log))
