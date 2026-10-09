# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) do modelo de endereço brasileiro: o Jinja do Frappe renderiza, o banco guarda.

Teste-âncora: `test_o_endereco_formatado_pelo_frappe_traz_numero_e_bairro`. A pura confere o texto do modelo; só o
Frappe, com o `Address` de verdade, mostra que o endereço **impresso** passou a ter número e bairro.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_modelo_de_endereco
"""

import frappe
from frappe.contacts.doctype.address.address import get_address_display
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.setup.modelo_de_endereco import MODELO, PAIS, instalar_modelo_de_endereco

MODULOS_COBERTOS = ("modelo_de_endereco",)
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

ENDERECO = {
	"doctype": "Address",
	"address_title": "_Teste modelo",
	"address_type": "Billing",
	"address_line1": "Rua das Flores",
	"address_line2": "Sala 12",
	"br_numero_endereco": "123",
	"br_bairro": "Centro",
	"city": "Porto Velho",
	"state": "RO",
	"pincode": "76801-000",
	"country": PAIS,
	"br_codigo_municipio_ibge": "1100205",
}


class TestModeloDeEndereco(FrappeTestCase):
	def setUp(self):
		# Cada teste parte do mesmo ponto: sem modelo do Brasil e com um padrão existente.
		if not frappe.db.exists("Address Template", {"is_default": 1}):
			self.skipTest(
				"o site não tem modelo de endereço padrão (assistente de configuração não concluído)"
			)

		antigo = frappe.db.get_value("Address Template", {"country": PAIS}, "name")

		if antigo:
			# O Frappe recusa apagar o modelo padrão: passa o padrão para outro país antes (a transação do
			# teste é revertida, o site não muda).
			outro = frappe.db.get_value("Address Template", {"country": ("!=", PAIS)}, "name")

			if not outro:
				self.skipTest("o site só tem o modelo do Brasil; não há outro país para receber o padrão")

			if frappe.db.get_value("Address Template", antigo, "is_default"):
				frappe.db.set_value("Address Template", antigo, "is_default", 0)
				frappe.db.set_value("Address Template", outro, "is_default", 1)

			frappe.delete_doc("Address Template", antigo, force=True, ignore_permissions=True)

	def test_cria_o_modelo_do_brasil_e_nao_o_torna_padrao(self):
		self.assertEqual(instalar_modelo_de_endereco(), "criado")

		modelo = frappe.db.get_value(
			"Address Template", {"country": PAIS}, ["template", "is_default"], as_dict=True
		)

		self.assertEqual(modelo.template, MODELO)
		self.assertEqual(modelo.is_default, 0, "virou o padrão de todos os países")

	def test_o_padrao_dos_outros_paises_nao_muda(self):
		antes = frappe.db.get_value("Address Template", {"is_default": 1}, "name")

		instalar_modelo_de_endereco()

		self.assertEqual(frappe.db.get_value("Address Template", {"is_default": 1}, "name"), antes)

	def test_segunda_execucao_nao_duplica(self):
		instalar_modelo_de_endereco()

		self.assertEqual(instalar_modelo_de_endereco(), "ja_existia")
		self.assertEqual(frappe.db.count("Address Template", {"country": PAIS}), 1)

	def test_modelo_ajustado_pelo_administrador_e_preservado(self):
		instalar_modelo_de_endereco()
		nome = frappe.db.get_value("Address Template", {"country": PAIS}, "name")
		frappe.db.set_value("Address Template", nome, "template", "{{ address_line1 }} (ajustado)")

		self.assertEqual(instalar_modelo_de_endereco(), "ja_existia")
		self.assertEqual(
			frappe.db.get_value("Address Template", nome, "template"), "{{ address_line1 }} (ajustado)"
		)

	def test_o_endereco_formatado_pelo_frappe_traz_numero_e_bairro(self):
		instalar_modelo_de_endereco()
		endereco = frappe.get_doc(ENDERECO).insert(ignore_permissions=True)

		texto = get_address_display(endereco.name)

		self.assertIn("Rua das Flores, 123", texto)
		self.assertIn("Sala 12", texto)
		self.assertIn("Centro", texto)
		self.assertIn("Porto Velho - RO", texto)
		self.assertIn("CEP 76801-000", texto)

	def test_campos_opcionais_vazios_nao_deixam_linha_solta(self):
		instalar_modelo_de_endereco()
		sem_opcionais = {
			**ENDERECO,
			"address_line2": "",
			"br_numero_endereco": "",
			"br_bairro": "",
			"pincode": "",
		}
		endereco = frappe.get_doc(sem_opcionais).insert(ignore_permissions=True)

		texto = get_address_display(endereco.name)

		self.assertNotIn("CEP", texto)
		self.assertNotIn(", <br>", texto)
		self.assertNotIn("<br><br><br>", "".join(texto.split()))

	def test_endereco_de_outro_pais_continua_no_formato_padrao(self):
		instalar_modelo_de_endereco()
		estrangeiro = {**ENDERECO, "country": "United States", "state": "TX", "br_codigo_municipio_ibge": ""}
		endereco = frappe.get_doc(estrangeiro).insert(ignore_permissions=True)

		self.assertNotIn("CEP", get_address_display(endereco.name))
