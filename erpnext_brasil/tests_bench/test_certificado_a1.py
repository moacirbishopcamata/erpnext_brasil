# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) de `integracao/certificado_a1.py` — primeira cobertura de
verdade para um módulo de `integracao/` desde que o bench WSL2 foi reconfirmado
(ver docstring de `tests_bench/__init__.py`).

Dois achados reais deste incremento, só possíveis com bench de verdade
------------------------------------------------------------------------------------------
1. **`File.content` precisa de `"decode": 1`** para gravar bytes a partir de uma
   string base64 — sem essa flag, o Frappe grava a própria string base64 como
   conteúdo literal do arquivo (não decodifica), e `get_content()` devolve a string,
   não os bytes originais. A primeira versão deste teste não passava `decode`, e
   `pfx == conteudo_original` falhava comparando bytes com a string base64.
2. **Estado de `Company` não volta sozinho entre métodos de teste** — `db_set`
   grava direto no banco, e o rollback automático de `FrappeTestCase` não desfez
   isso de forma confiável entre um método e o seguinte na mesma classe (dois
   testes que esperavam "sem certificado" passaram a falhar depois que um teste
   anterior, na mesma classe, gravava o campo). Corrigido com `setUp`/`tearDown`
   explícitos que capturam e restauram os campos tocados, em vez de confiar
   silenciosamente no rollback entre métodos.
"""

import base64

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao.certificado_a1 import (
	CertificadoA1Ausente,
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)

_CAMPOS_TOCADOS = ("br_certificado_a1", "br_senha_certificado_a1", "br_ambiente_sefaz")


def _primeira_company() -> str:
	return frappe.get_all("Company", limit=1, pluck="name")[0]


def _anexar_arquivo(company: str, conteudo: bytes) -> str:
	"""Cria um `File` privado com `conteudo` de verdade — `decode: 1` é o que faz o
	Frappe decodificar o base64 antes de gravar em disco (ver docstring do módulo,
	achado 1)."""
	arquivo = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": "certificado_teste.pfx",
			"attached_to_doctype": "Company",
			"attached_to_name": company,
			"content": base64.b64encode(conteudo).decode(),
			"decode": 1,
			"is_private": 1,
		}
	).insert()

	return arquivo.file_url


class _LimpaCamposDaCompanyMixin:
	"""Restaura `_CAMPOS_TOCADOS` da primeira `Company` depois de cada teste — não
	confia no rollback automático de `FrappeTestCase` para escritas via `db_set`
	(achado 2, ver docstring do módulo)."""

	def setUp(self):
		self.company = _primeira_company()
		self._originais = frappe.db.get_value("Company", self.company, list(_CAMPOS_TOCADOS), as_dict=True)
		self._arquivos_criados: list[str] = []

	def tearDown(self):
		frappe.db.set_value("Company", self.company, self._originais)

		for nome_arquivo in self._arquivos_criados:
			frappe.delete_doc("File", nome_arquivo, force=True, ignore_permissions=True)


class TestCarregarCertificadoDaEmpresa(_LimpaCamposDaCompanyMixin, FrappeTestCase):
	def test_sem_certificado_nem_senha_levanta_erro(self):
		with self.assertRaises(CertificadoA1Ausente):
			carregar_certificado_da_empresa(self.company)

	def test_com_arquivo_mas_sem_senha_levanta_erro(self):
		file_url = _anexar_arquivo(self.company, b"conteudo-fake")
		self._arquivos_criados.append(frappe.db.get_value("File", {"file_url": file_url}))

		frappe.db.set_value("Company", self.company, "br_certificado_a1", file_url)

		with self.assertRaises(CertificadoA1Ausente):
			carregar_certificado_da_empresa(self.company)

	def test_certificado_completo_devolve_bytes_e_senha_reais(self):
		"""O teste que mais importa: prova que o `Attach`/`Password` de verdade,
		gravados via `frappe.get_doc`/`db_set`, voltam intactos por
		`carregar_certificado_da_empresa` -- não um mock do que *deveria*
		acontecer."""
		conteudo_original = b"\x00\x01conteudo-binario-fake-do-pfx\xff"
		file_url = _anexar_arquivo(self.company, conteudo_original)
		self._arquivos_criados.append(frappe.db.get_value("File", {"file_url": file_url}))

		frappe.db.set_value(
			"Company",
			self.company,
			{"br_certificado_a1": file_url, "br_senha_certificado_a1": "senha-de-teste-123"},
		)

		pfx, senha = carregar_certificado_da_empresa(self.company)

		self.assertEqual(pfx, conteudo_original)
		self.assertEqual(senha, "senha-de-teste-123")


class TestAmbienteSefazDaEmpresa(_LimpaCamposDaCompanyMixin, FrappeTestCase):
	def test_sem_valor_configurado_resolve_homologacao(self):
		self.assertEqual(ambiente_sefaz_da_empresa(self.company), "homologacao")

	def test_producao_explicito(self):
		frappe.db.set_value("Company", self.company, "br_ambiente_sefaz", "Produção")

		self.assertEqual(ambiente_sefaz_da_empresa(self.company), "producao")

	def test_qualquer_outro_valor_resolve_homologacao(self):
		"""Achado real do próprio módulo, verificado aqui contra o banco de
		verdade: só a string exata "Produção" ativa produção -- qualquer outra
		coisa (incluindo erro de digitação) cai em homologação, o lado seguro."""
		frappe.db.set_value("Company", self.company, "br_ambiente_sefaz", "producao")  # sem acento

		self.assertEqual(ambiente_sefaz_da_empresa(self.company), "homologacao")
