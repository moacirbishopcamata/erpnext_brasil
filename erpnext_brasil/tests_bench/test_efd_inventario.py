# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) do saldo de inventário do Bloco H — a única consulta SQL crua do app.

Por que este arquivo existe
------------------------------------
`integracao/efd_inventario.saldos_na_data` é a única função do app com `frappe.db.sql` de
verdade, e a suíte pura só consegue inspecionar o **texto** da consulta
(`tests/test_efd_inventario.py`). Aqui ela roda contra o razão de estoque real — e, desde
a troca do banco, roda igual em MariaDB e em PostgreSQL (`docs/postgresql.md`).

Teste-âncora: `test_o_saldo_e_o_da_data_e_nao_o_de_hoje`. Duas entradas submetidas em
datas diferentes; o saldo lido **na data intermediária** tem de ser o daquela data. A
versão anterior da consulta escolhia o lançamento "mais recente" ordenando texto
(`MAX(CONCAT(posting_date, posting_time, name))`), o que no PostgreSQL dependia do
`DateStyle` da sessão; a atual usa `ROW_NUMBER()` sobre os tipos de verdade. Este teste é
o que prova que a troca não mudou o resultado.

Como rodar
-----------------
    bench --site v16.localhost   run-tests --module erpnext_brasil.tests_bench.test_efd_inventario
    bench --site v16pg.localhost run-tests --module erpnext_brasil.tests_bench.test_efd_inventario
"""

from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao.efd_inventario import saldos_na_data

MODULOS_COBERTOS = ("efd_inventario",)
"""Os módulos de `integracao/` que este arquivo exercita — declarados, lidos por
`scripts/cobertura_de_bench.py`."""

CNPJ = "11.222.333/0001-81"
EMPRESA = "_Teste Consumo Indevido"
"""A mesma empresa dos outros testes de bench: um plano de contas a mais não provaria nada."""

ITEM = "_Teste Inventario H"
ARMAZEM = "Stores - _TCI"


class TestSaldoNaData(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# Os mesmos sete cadastros que um site sem assistente não tem — ver
		# `docs/ambiente-dev-bench.md`, "Site sem assistente de configuração".
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Company", EMPRESA):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": EMPRESA,
					"abbr": "_TCI",
					"default_currency": "BRL",
					"country": "Brazil",
					"tax_id": CNPJ,
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("UOM", "Unidade"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Unidade"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Item Group", "Teste GS1"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Teste GS1", "is_group": 0}).insert(
				ignore_permissions=True
			)

		if not frappe.db.exists("Stock Entry Type", "Material Receipt"):
			frappe.get_doc(
				{"doctype": "Stock Entry Type", "name": "Material Receipt", "purpose": "Material Receipt"}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Item", ITEM):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": ITEM,
					"item_name": "Item de teste do inventário",
					"item_group": "Teste GS1",
					"stock_uom": "Unidade",
					"is_stock_item": 1,
					"valuation_rate": 10,
				}
			).insert(ignore_permissions=True)

		frappe.db.set_value("Item", ITEM, "valuation_rate", 10, update_modified=False)

		# Duas entradas em datas distintas do ano corrente; o ano fiscal cobre as duas.
		ano = str(frappe.utils.now_datetime().year)

		if not frappe.db.exists("Fiscal Year", ano):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": ano,
					"year_start_date": f"{ano}-01-01",
					"year_end_date": f"{ano}-12-31",
				}
			).insert(ignore_permissions=True)

		cls.ano = ano
		frappe.db.commit()

	def _entrada(self, quantidade: int, data: str, hora: str) -> None:
		doc = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"purpose": "Material Receipt",
				"company": EMPRESA,
				"set_posting_time": 1,
				"posting_date": data,
				"posting_time": hora,
				"items": [
					{
						"item_code": ITEM,
						"qty": quantidade,
						"uom": "Unidade",
						"basic_rate": 10,
						"t_warehouse": ARMAZEM,
					}
				],
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.submit()

	def _saldo(self, data: str) -> Decimal | None:
		for item in saldos_na_data(EMPRESA, data):
			if item.codigo_item == ITEM:
				return item.quantidade

		return None

	def test_o_saldo_e_o_da_data_e_nao_o_de_hoje(self):
		"""Teste-âncora. `Bin` diria o saldo de hoje; o inventário é de uma data."""
		self._entrada(10, f"{self.ano}-01-10", "09:00:00")
		self._entrada(5, f"{self.ano}-01-20", "09:00:00")

		self.assertEqual(Decimal("10"), self._saldo(f"{self.ano}-01-15"), "entre as duas entradas")
		self.assertEqual(Decimal("15"), self._saldo(f"{self.ano}-01-31"), "depois das duas")
		self.assertIsNone(self._saldo(f"{self.ano}-01-05"), "antes de qualquer entrada")

	def test_dois_lancamentos_no_mesmo_dia_usam_o_mais_tarde(self):
		"""A ordem é por `posting_time` de verdade, não por texto: 09:00 < 15:00."""
		self._entrada(3, f"{self.ano}-02-10", "15:00:00")
		self._entrada(4, f"{self.ano}-02-10", "09:00:00")

		self.assertEqual(Decimal("7"), self._saldo(f"{self.ano}-02-10"))

	def test_o_valor_acompanha_a_quantidade(self):
		"""`stock_value` é o acumulado do mesmo lançamento que dá a quantidade."""
		self._entrada(2, f"{self.ano}-03-01", "09:00:00")

		for item in saldos_na_data(EMPRESA, f"{self.ano}-03-01"):
			if item.codigo_item == ITEM:
				self.assertEqual(Decimal("20.00"), item.valor_item)
				self.assertEqual(Decimal("10.000000"), item.valor_unitario)
				return

		self.fail("o item não apareceu no inventário")
