# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) de `integracao/folha.py`: o ponto de plugue do `hrms` e as linhas de INSS/IRRF.

Teste-âncora: `test_o_hook_do_hrms_dispara_a_folha_brasileira_pelo_metodo_do_proprio_hrms`. A costura que o módulo declarava
"ainda não exercitada contra um Salary Slip real" é esta: o `hrms` chama a função pelo nome em `regional_overrides`;
se um dos dois nomes mudar, a folha segue sem INSS e sem IRRF e nada acusa.

O que **não** é exercitado: um `Salary Slip` completo (estrutura salarial, funcionário, período) — o teste monta o
documento real do `hrms` em memória, sem gravar, e confere as linhas da tabela `deductions` (DocType filho real).

Como rodar
-----------------
    bench --site v16.localhost run-tests --skip-before-tests --app erpnext_brasil \\
        --module erpnext_brasil.tests_bench.test_folha
"""

import unittest
from decimal import Decimal
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil import hooks
from erpnext_brasil.folha.inss import calcular_inss
from erpnext_brasil.folha.irrf import calcular_irrf
from erpnext_brasil.integracao import folha
from erpnext_brasil.integracao.folha import apply_regional_deductions

MODULOS_COBERTOS = ("folha",)
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

BRUTO = 5000


class TestFolhaNoBench(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not frappe.db.exists("DocType", "Salary Slip"):
			raise unittest.SkipTest("hrms não está instalado neste site")

	def _holerite(self, bruto=BRUTO):
		holerite = frappe.new_doc("Salary Slip")
		holerite.company = "_Empresa Qualquer"
		holerite.gross_pay = bruto

		return holerite

	def _aplicar(self, holerite):
		with mock.patch.object(folha, "_pais_e_brasil", return_value=True):
			apply_regional_deductions(holerite)

	def test_o_hook_do_hrms_dispara_a_folha_brasileira_pelo_metodo_do_proprio_hrms(self):
		"""Caminho real: `SalarySlip.apply_regional_deductions` (decorado com `hrms.allow_regional`) monta o nome
		`módulo.função`, procura em `regional_overrides` do país do sistema e chama o nosso. Se a chave do `hooks.py` ou o
		nome no `hrms` mudar, o método original (no-op) roda e a folha sai sem INSS e IRRF."""
		holerite = self._holerite()
		pais_anterior = frappe.flags.country
		frappe.flags.country = "Brazil"

		try:
			with mock.patch.object(folha, "_pais_e_brasil", return_value=True):
				holerite.apply_regional_deductions()
		finally:
			frappe.flags.country = pais_anterior

		self.assertEqual(
			sorted(linha.salary_component for linha in holerite.deductions),
			["INSS", "IRRF"],
			"o hrms não chamou a folha brasileira (regional_overrides)",
		)

		self.assertIn(
			"erpnext_brasil.integracao.folha.apply_regional_deductions",
			hooks.regional_overrides["Brazil"].values().__iter__().__next__(),
		)

	def test_os_componentes_salariais_existem_apos_a_instalacao(self):
		for nome in folha.COMPONENTES_DESTE_MODULO:
			self.assertTrue(frappe.db.exists("Salary Component", nome), f"falta o Salary Component {nome}")
			self.assertEqual(frappe.db.get_value("Salary Component", nome, "type"), "Deduction")

	def test_inss_e_irrf_entram_nas_deducoes_com_o_valor_da_regra_pura(self):
		holerite = self._holerite()

		self._aplicar(holerite)

		valores = {linha.salary_component: linha.amount for linha in holerite.deductions}
		inss = calcular_inss(Decimal(BRUTO))
		irrf = calcular_irrf(Decimal(BRUTO), Decimal(BRUTO) - inss)

		self.assertEqual(valores, {"INSS": float(inss), "IRRF": float(irrf)})

	def test_recalcular_nao_duplica_as_linhas(self):
		holerite = self._holerite()

		self._aplicar(holerite)
		self._aplicar(holerite)

		self.assertEqual([linha.salary_component for linha in holerite.deductions].count("INSS"), 1)
		self.assertEqual([linha.salary_component for linha in holerite.deductions].count("IRRF"), 1)

	def test_recalcular_com_outro_bruto_substitui_o_valor(self):
		holerite = self._holerite(BRUTO)
		self._aplicar(holerite)

		holerite.gross_pay = 8000
		self._aplicar(holerite)

		inss = {linha.salary_component: linha.amount for linha in holerite.deductions}["INSS"]

		self.assertEqual(inss, float(calcular_inss(Decimal(8000))))

	def test_outras_deducoes_do_holerite_sao_preservadas(self):
		holerite = self._holerite()
		holerite.append("deductions", {"salary_component": "INSS", "amount": 1})  # sobra de execução anterior
		holerite.append("deductions", {"salary_component": "Vale Transporte", "amount": 120})

		self._aplicar(holerite)

		componentes = [linha.salary_component for linha in holerite.deductions]

		self.assertIn("Vale Transporte", componentes)
		self.assertEqual(componentes.count("INSS"), 1)
		self.assertNotIn(1, [linha.amount for linha in holerite.deductions])

	def test_fora_do_brasil_nao_mexe_na_tabela(self):
		holerite = self._holerite()

		with mock.patch.object(folha, "_pais_e_brasil", return_value=False):
			apply_regional_deductions(holerite)

		self.assertEqual(list(holerite.deductions), [])
