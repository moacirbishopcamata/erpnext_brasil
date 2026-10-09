# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) dos Script Reports "Lacunas de Numeracao" e "Bloqueios SEFAZ".

Teste-âncora: `test_a_lacuna_aparece_pela_chave_de_acesso`. O número de uma transmissão só existe dentro da chave de
acesso: se o relatório lesse o campo errado, a série pareceria sem lacuna.

Como rodar
-----------------
    bench --site v16.localhost run-tests --skip-before-tests --app erpnext_brasil \
        --module erpnext_brasil.tests_bench.test_relatorios_fiscais
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.registros_fiscais.report.bloqueios_sefaz.bloqueios_sefaz import (
	execute as bloqueios,
)
from erpnext_brasil.registros_fiscais.report.lacunas_de_numeracao.lacunas_de_numeracao import (
	execute as lacunas,
)

MODULOS_COBERTOS = ("relatorio_numeracao", "relatorio_bloqueios")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

DOCUMENTO = "_TESTE-RELATORIOS-FISCAIS"
SERIE = "987"
CNPJ = "11222333000181"


def _chave(numero: int) -> str:
	return montar_chave("35", "2610", CNPJ, "55", SERIE, str(numero), "1", f"{numero:08d}")


class TestRelatoriosFiscaisNoBench(FrappeTestCase):
	def setUp(self):
		self.empresa = frappe.db.get_value("Company", {}, "name")

		if not self.empresa:
			self.skipTest("o site não tem nenhuma Company")

		self._limpar()

	def tearDown(self):
		self._limpar()

	def _limpar(self):
		frappe.db.delete("Transmissao Fiscal", {"documento": DOCUMENTO})
		frappe.db.delete("Numeracao Fiscal", {"serie": SERIE, "company": self.empresa})
		frappe.db.delete("Bloqueio Sefaz", {"cnpj": CNPJ})
		frappe.db.commit()

	def _numeracao(self, ultimo: int):
		frappe.get_doc(
			{
				"doctype": "Numeracao Fiscal",
				"company": self.empresa,
				"modelo": "55",
				"serie": SERIE,
				"ultimo_numero": ultimo,
			}
		).insert(ignore_permissions=True)

	def _transmissao(self, numero: int, situacao: str):
		return frappe.get_doc(
			{
				"doctype": "Transmissao Fiscal",
				"documento_tipo": "Sales Invoice",
				"documento": DOCUMENTO,
				"tipo": "Autorização",
				"ambiente": "Homologação",
				"company": self.empresa,
				"situacao": situacao,
				"chave_acesso": _chave(numero),
				"protocolo": "135260000000001" if situacao == "Autorizado" else "",
				"mensagem": "Rejeição de teste" if situacao == "Rejeitado" else "",
			}
		).insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)

	def _faixas(self):
		_, linhas, _ = lacunas({"company": self.empresa})

		return [(r["inicio"], r["fim"], r["motivo"]) for r in linhas if r["serie"] == SERIE]

	def test_a_lacuna_aparece_pela_chave_de_acesso(self):
		self._numeracao(4)
		self._transmissao(1, "Autorizado")
		self._transmissao(4, "Autorizado")

		self.assertEqual(self._faixas(), [(2, 3, "Sem registro")])

	def test_numero_so_rejeitado_e_apontado(self):
		self._numeracao(2)
		self._transmissao(1, "Autorizado")
		self._transmissao(2, "Rejeitado")

		self.assertEqual(self._faixas(), [(2, 2, "Só rejeitado")])

	def test_serie_completa_nao_tem_lacuna(self):
		self._numeracao(2)
		self._transmissao(1, "Autorizado")
		self._transmissao(2, "Autorizado")

		self.assertEqual(self._faixas(), [])

	def test_lacunas_exige_empresa(self):
		with self.assertRaises(frappe.ValidationError):
			lacunas({})

	def _bloqueio(self, ambiente, ha_minutos):
		return frappe.get_doc(
			{
				"doctype": "Bloqueio Sefaz",
				"chave": f"{CNPJ}-{ambiente}",
				"cnpj": CNPJ,
				"ambiente": ambiente,
				"company": self.empresa,
				"bloqueado_em": add_to_date(now_datetime(), minutes=-ha_minutos),
				"codigo_status": "656",
				"mensagem": "Consumo indevido",
			}
		).insert(ignore_permissions=True, ignore_links=True)

	def _meus_bloqueios(self, **filtros):
		_, linhas = bloqueios({"company": self.empresa, **filtros})

		return {r["ambiente"]: r for r in linhas if r["cnpj"] == CNPJ}

	def test_bloqueio_recente_esta_ativo_e_o_antigo_liberado(self):
		self._bloqueio("Produção", 10)
		self._bloqueio("Homologação", 180)

		meus = self._meus_bloqueios()

		self.assertEqual(meus["Produção"]["situacao"], "Ativo")
		self.assertTrue(0 < meus["Produção"]["restante_min"] <= 50)
		self.assertEqual(meus["Homologação"]["situacao"], "Liberado")

	def test_somente_ativos_recorta(self):
		self._bloqueio("Produção", 10)
		self._bloqueio("Homologação", 180)

		self.assertEqual(list(self._meus_bloqueios(somente_ativos=1)), ["Produção"])

	def test_bloqueios_exige_empresa(self):
		with self.assertRaises(frappe.ValidationError):
			bloqueios({})

	def test_os_relatorios_estao_registrados_com_o_papel_fiscal(self):
		for pasta, nome in (
			("lacunas_de_numeracao", "Lacunas de Numeracao"),
			("bloqueios_sefaz", "Bloqueios SEFAZ"),
		):
			frappe.reload_doc("registros_fiscais", "report", pasta)

			papeis = {p.role for p in frappe.get_doc("Report", nome).roles}

			self.assertEqual(papeis, {"Accounts Manager", "Accounts User"}, nome)
