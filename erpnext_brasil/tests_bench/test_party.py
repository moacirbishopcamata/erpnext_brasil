# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) de `integracao/party.py` — segunda cobertura de verdade
para um módulo de `integracao/`, depois de `test_certificado_a1.py`.

Achado real deste incremento, só possível com bench de verdade
------------------------------------------------------------------------------
`_pais_e_brasil()` decide pelo país da `Company` em `frappe.local.flags.company`
ou pelo *default de Company do usuário* (`frappe.defaults.get_user_default`) —
**não** pelo país das `System Settings` quando qualquer uma dessas duas existir.
Neste bench, o default de Company do usuário é `Wind Power LLC` (país Estados
Unidos) mesmo com `System Settings.country = "Brazil"` — checado direto no
console antes de escrever este teste. Isso significa que, num site com uma
Company padrão não-brasileira configurada, `validar_tax_id`/`validar_ie` fazem
*nada* para qualquer Customer/Supplier novo, mesmo o sistema como um todo sendo
brasileiro — silenciosamente, sem erro. Por isso todo teste aqui cria sua
própria `Company` com `country="Brazil"` e ajusta `frappe.local.flags.company`
explicitamente, em vez de confiar no default do site (que pode ser qualquer
país, dependendo de como o site foi inicializado).

Teste de costura, não só de unidade
------------------------------------------
`test_tax_id_normalizado_sobrevive_ao_insert` cria um `Customer` de verdade,
`.insert()` (dispara o `doc_events` real do hooks.py, não uma chamada direta à
função), e relê por `frappe.db.get_value` — caminho independente do objeto que
o `insert()` devolveu — mesma disciplina que achou os dois bugs de
`certificado_a1.py`.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao.party import validar_codigo_municipio, validar_ncm, validar_tax_id


class _EmpresaBrasileiraMixin:
	"""Cria uma `Company` com `country="Brazil"` e força `frappe.local.flags.company`
	para ela — ver achado no docstring do módulo sobre por que não dá para confiar
	no default do site. Limpeza explícita no `tearDown`, mesma disciplina de
	`test_certificado_a1._LimpaCamposDaCompanyMixin`: não confiar no rollback
	automático de `FrappeTestCase` sozinho para estado que passa por cache
	(`frappe.get_cached_value`, que `_pais_e_brasil()` usa)."""

	def setUp(self):
		self._flag_anterior = frappe.local.flags.company

		self.empresa = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test Empresa BR (erpnext_brasil)",
				"abbr": "TEBREB",
				"default_currency": "BRL",
				"country": "Brazil",
			}
		).insert(ignore_permissions=True)

		frappe.local.flags.company = self.empresa.name
		self._docs_criados: list[tuple[str, str]] = []

	def tearDown(self):
		frappe.local.flags.company = self._flag_anterior

		for doctype, nome in reversed(self._docs_criados):
			frappe.delete_doc(doctype, nome, force=True, ignore_permissions=True)

		frappe.delete_doc("Company", self.empresa.name, force=True, ignore_permissions=True)


class TestValidarTaxId(_EmpresaBrasileiraMixin, FrappeTestCase):
	def test_tax_id_normalizado_sobrevive_ao_insert(self):
		"""CNPJ sem máscara, gravado via `Customer.insert()` de verdade (dispara o
		hook real do `hooks.py`), relido por um caminho independente."""
		cliente = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Cliente Teste CNPJ",
				"customer_group": "Individual",
				"tax_id": "11222333000181",
			}
		).insert(ignore_permissions=True)
		self._docs_criados.append(("Customer", cliente.name))

		tax_id_relido = frappe.db.get_value("Customer", cliente.name, "tax_id")

		self.assertEqual(tax_id_relido, "11.222.333/0001-81")

	def test_cnpj_invalido_impede_o_insert(self):
		"""`11222333000180` — mesmo CNPJ-base válido de `11222333000181` (usado no
		teste de sucesso), só com o último dígito verificador trocado. Achado ao
		escrever este teste: `11111111000191` (sequência repetida) **não** serve
		como CNPJ inválido aqui — os dígitos verificadores dele conferem de
		verdade; este validador só rejeita sequência repetida para CPF, não CNPJ."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "Cliente Teste CNPJ Invalido",
					"customer_group": "Individual",
					"tax_id": "11222333000180",
				}
			).insert(ignore_permissions=True)

	def test_campo_vazio_nao_impede_o_insert(self):
		cliente = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "Cliente Sem Tax Id", "customer_group": "Individual"}
		).insert(ignore_permissions=True)
		self._docs_criados.append(("Customer", cliente.name))

		self.assertFalse(frappe.db.get_value("Customer", cliente.name, "tax_id"))

	def test_funcao_chamada_direto_fora_do_contexto_brasil_nao_normaliza(self):
		"""Fora do contexto Brasil (sem `flags.company` apontando para país
		Brasil), a função não faz nada — mesmo com CNPJ sem máscara."""
		frappe.local.flags.company = None
		doc = frappe.new_doc("Customer")
		doc.tax_id = "11222333000181"

		validar_tax_id(doc)

		self.assertEqual(doc.tax_id, "11222333000181")


class TestValidarCodigoMunicipio(_EmpresaBrasileiraMixin, FrappeTestCase):
	def test_codigo_valido_e_aceito_direto(self):
		doc = frappe.new_doc("Address")
		doc.codigo_municipio_ibge = "3550308"

		validar_codigo_municipio(doc)

		self.assertEqual(doc.codigo_municipio_ibge, "3550308")

	def test_codigo_fora_do_formato_levanta_erro(self):
		doc = frappe.new_doc("Address")
		doc.codigo_municipio_ibge = "123"

		with self.assertRaises(frappe.ValidationError):
			validar_codigo_municipio(doc)


class TestValidarNcm(_EmpresaBrasileiraMixin, FrappeTestCase):
	def test_ncm_normalizado_sobrevive_ao_insert(self):
		"""Mesma disciplina de costura de `test_tax_id_normalizado_sobrevive_ao_insert`,
		para o `Item.validate` real."""
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "_Test Item NCM (erpnext_brasil)",
				"item_group": "All Item Groups",
				"ncm": "8471.30.19",
			}
		).insert(ignore_permissions=True)
		self._docs_criados.append(("Item", item.name))

		ncm_relido = frappe.db.get_value("Item", item.name, "ncm")

		self.assertEqual(ncm_relido, "84713019")

	def test_ncm_fora_do_formato_impede_o_insert(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "_Test Item NCM Invalido (erpnext_brasil)",
					"item_group": "All Item Groups",
					"ncm": "123",
				}
			).insert(ignore_permissions=True)
