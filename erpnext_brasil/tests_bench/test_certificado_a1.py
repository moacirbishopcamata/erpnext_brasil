# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) de `integracao/certificado_a1.py` — primeira cobertura de
verdade para um módulo de `integracao/` desde que o bench WSL2 foi reconfirmado
(ver docstring de `tests_bench/__init__.py`)."""

import base64

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao.certificado_a1 import (
	CertificadoA1Ausente,
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)


def _primeira_company() -> str:
	return frappe.get_all("Company", limit=1, pluck="name")[0]


class TestCarregarCertificadoDaEmpresa(FrappeTestCase):
	def test_sem_certificado_nem_senha_levanta_erro(self):
		company = _primeira_company()

		with self.assertRaises(CertificadoA1Ausente):
			carregar_certificado_da_empresa(company)

	def test_com_arquivo_mas_sem_senha_levanta_erro(self):
		company = frappe.get_doc("Company", _primeira_company())

		arquivo = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "certificado_teste.pfx",
				"attached_to_doctype": "Company",
				"attached_to_name": company.name,
				"content": base64.b64encode(b"conteudo-fake").decode(),
				"is_private": 1,
			}
		).insert()

		company.db_set("br_certificado_a1", arquivo.file_url)

		with self.assertRaises(CertificadoA1Ausente):
			carregar_certificado_da_empresa(company.name)

	def test_certificado_completo_devolve_bytes_e_senha_reais(self):
		"""O teste que mais importa: prova que o `Attach`/`Password` de verdade,
		gravados via `frappe.get_doc`/`db_set`, voltam intactos por
		`carregar_certificado_da_empresa` -- não um mock do que *deveria*
		acontecer."""
		company = frappe.get_doc("Company", _primeira_company())
		conteudo_original = b"\x00\x01conteudo-binario-fake-do-pfx\xff"

		arquivo = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "certificado_teste.pfx",
				"attached_to_doctype": "Company",
				"attached_to_name": company.name,
				"content": base64.b64encode(conteudo_original).decode(),
				"is_private": 1,
			}
		).insert()

		company.db_set("br_certificado_a1", arquivo.file_url)
		company.reload()
		company.br_senha_certificado_a1 = "senha-de-teste-123"
		company.save()

		pfx, senha = carregar_certificado_da_empresa(company.name)

		self.assertEqual(pfx, conteudo_original)
		self.assertEqual(senha, "senha-de-teste-123")


class TestAmbienteSefazDaEmpresa(FrappeTestCase):
	def test_sem_valor_configurado_resolve_homologacao(self):
		company = _primeira_company()

		self.assertEqual(ambiente_sefaz_da_empresa(company), "homologacao")

	def test_producao_explicito(self):
		company = frappe.get_doc("Company", _primeira_company())
		company.db_set("br_ambiente_sefaz", "Produção")

		self.assertEqual(ambiente_sefaz_da_empresa(company.name), "producao")

	def test_qualquer_outro_valor_resolve_homologacao(self):
		"""Achado real do próprio módulo, verificado aqui contra o banco de
		verdade: só a string exata "Produção" ativa produção -- qualquer outra
		coisa (incluindo erro de digitação) cai em homologação, o lado seguro."""
		company = frappe.get_doc("Company", _primeira_company())
		company.db_set("br_ambiente_sefaz", "producao")  # sem acento, minúsculo

		self.assertEqual(ambiente_sefaz_da_empresa(company.name), "homologacao")
