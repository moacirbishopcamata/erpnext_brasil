# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) do Script Report "Notas por Situacao": grava `Transmissao Fiscal` e relê pelo relatório.

Teste-âncora: `test_o_relatorio_soma_o_que_foi_gravado`. A costura é o relatório achar o DocType, o módulo e o
recorte (empresa, período, ambiente) — a regra de agrupamento já está na suíte pura.

Como rodar
-----------------
    bench --site v16.localhost run-tests --skip-before-tests --app erpnext_brasil \
        --module erpnext_brasil.tests_bench.test_relatorio_notas
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.documento.chave_acesso import calcular_dv
from erpnext_brasil.registros_fiscais.report.notas_por_situacao.notas_por_situacao import execute

MODULOS_COBERTOS = ("relatorio_notas",)
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

DOCUMENTO = "_TESTE-RELATORIO-NOTAS"

_BASE = "3" * 43
CHAVE_VALIDA = _BASE + calcular_dv(_BASE)
"""O DocType recusa chave com dígito verificador errado: o teste usa uma válida."""


class TestRelatorioNotasNoBench(FrappeTestCase):
	def setUp(self):
		self.empresa = frappe.db.get_value("Company", {}, "name")

		if not self.empresa:
			self.skipTest("o site não tem nenhuma Company")

	def tearDown(self):
		frappe.db.delete("Transmissao Fiscal", {"documento": DOCUMENTO})
		frappe.db.commit()

	def _gravar(self, situacao, codigo, ambiente="Homologação", chave="", tipo="Autorização"):
		return frappe.get_doc(
			{
				"doctype": "Transmissao Fiscal",
				"documento_tipo": "Sales Invoice",
				"documento": DOCUMENTO,
				"tipo": tipo,
				"ambiente": ambiente,
				"company": self.empresa,
				"situacao": situacao,
				"codigo_status": codigo,
				"chave_acesso": chave,
				"protocolo": "135260000000001" if situacao == "Autorizado" else "",
				"mensagem": "Rejeição de teste" if situacao == "Rejeitado" else "",
			}
		).insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)

	def _filtros(self, **extra):
		hoje = frappe.utils.today()

		return {"company": self.empresa, "from_date": hoje, "to_date": hoje, **extra}

	def _meus(self, linhas):
		return [r for r in linhas if r["codigo_status"] in ("100", "539", "999")]

	def test_o_relatorio_soma_o_que_foi_gravado(self):
		for _ in range(2):
			self._gravar("Autorizado", "100", chave=CHAVE_VALIDA)

		self._gravar("Rejeitado", "539")

		_, linhas, _ = execute(self._filtros())
		contagem = {(r["situacao"], r["codigo_status"]): r["quantidade"] for r in self._meus(linhas)}

		self.assertEqual(contagem, {("Autorizado", "100"): 2, ("Rejeitado", "539"): 1})

	def test_filtro_de_ambiente_recorta(self):
		self._gravar("Autorizado", "100", ambiente="Produção", chave=CHAVE_VALIDA)
		self._gravar("Autorizado", "100", ambiente="Homologação", chave=CHAVE_VALIDA)

		_, linhas, _ = execute(self._filtros(ambiente="Produção"))

		self.assertEqual(sum(r["quantidade"] for r in self._meus(linhas)), 1)

	def test_periodo_sem_dados_nao_traz_a_linha_de_hoje(self):
		self._gravar("Autorizado", "100", chave=CHAVE_VALIDA)

		_, linhas, _ = execute({"company": self.empresa, "from_date": "2000-01-01", "to_date": "2000-01-31"})

		self.assertEqual(self._meus(linhas), [])

	def test_autorizada_sem_chave_aparece_no_aviso(self):
		self._gravar("Autorizado", "100", chave="")

		_, _, aviso = execute(self._filtros())

		self.assertIn("sem chave de acesso", str(aviso))

	def test_sem_empresa_ou_periodo_recusa(self):
		for filtros in ({}, {"company": self.empresa}, {"from_date": "2026-01-01", "to_date": "2026-01-02"}):
			with self.subTest(filtros=filtros), self.assertRaises(frappe.ValidationError):
				execute(filtros)

	def test_o_relatorio_esta_registrado_com_o_papel_fiscal(self):
		frappe.reload_doc("registros_fiscais", "report", "notas_por_situacao")

		papeis = {p.role for p in frappe.get_doc("Report", "Notas por Situacao").roles}

		self.assertEqual(papeis, {"Accounts Manager", "Accounts User"})
