# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) de `inutilizar_faixa`: a resposta da SEFAZ vira `Transmissao Fiscal` e o relatório a enxerga.

O transporte é falso (nenhum byte vai à SEFAZ); o que se prova é a costura Frappe — a faixa gravada e relida pelo
relatório `Lacunas de Numeracao`, a recusa antes de chamar, e a rejeição que sobrevive ao `throw`.

Teste-âncora: `test_faixa_inutilizada_sai_do_relatorio_de_lacunas`. Era o gap: o app enviava a inutilização mas
nenhum registro dizia que a faixa tinha sido inutilizada.

Como rodar
-----------------
    bench --site v16.localhost run-tests --skip-before-tests --app erpnext_brasil \
        --module erpnext_brasil.tests_bench.test_inutilizacao_fiscal
"""

from contextlib import contextmanager
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.porta import ResultadoInutilizacao
from erpnext_brasil.integracao import inutilizacao_fiscal
from erpnext_brasil.integracao.inutilizacao_fiscal import inutilizar_faixa
from erpnext_brasil.registros_fiscais.report.lacunas_de_numeracao.lacunas_de_numeracao import execute

MODULOS_COBERTOS = ("inutilizacao_fiscal", "serie_fiscal")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

SERIE = "986"
CNPJ = "11222333000181"
JUSTIFICATIVA = "Numeracao pulada por falha na contingencia"


class _TransporteFalso:
	def __init__(self, resultado):
		self.resultado = resultado
		self.chamadas = []

	def inutilizar(self, **kwargs):
		self.chamadas.append(kwargs)

		return self.resultado


class TestInutilizacaoFiscalNoBench(FrappeTestCase):
	def setUp(self):
		self.empresa = frappe.db.get_value("Company", {}, "name")

		if not self.empresa:
			self.skipTest("o site não tem nenhuma Company")

		frappe.reload_doc("registros_fiscais", "doctype", "transmissao_fiscal")
		self._limpar()
		self.serie = frappe.get_doc(
			{
				"doctype": "Numeracao Fiscal",
				"company": self.empresa,
				"modelo": "55",
				"serie": SERIE,
				"ultimo_numero": 5,
			}
		).insert(ignore_permissions=True)
		self._autorizar(1)
		self._autorizar(5)

	def tearDown(self):
		self._limpar()

	def _limpar(self):
		nome = f"{self.empresa}-55-{SERIE}"
		frappe.db.delete("Transmissao Fiscal", {"documento": ["in", [nome, "_TESTE-INUTILIZACAO"]]})
		frappe.db.delete("Numeracao Fiscal", {"serie": SERIE, "company": self.empresa})
		frappe.db.commit()

	def _autorizar(self, numero):
		frappe.get_doc(
			{
				"doctype": "Transmissao Fiscal",
				"documento_tipo": "Sales Invoice",
				"documento": "_TESTE-INUTILIZACAO",
				"tipo": "Autorização",
				"ambiente": "Homologação",
				"company": self.empresa,
				"situacao": "Autorizado",
				"chave_acesso": montar_chave(
					"35", "2610", CNPJ, "55", SERIE, str(numero), "1", f"{numero:08d}"
				),
				"protocolo": "135260000000001",
			}
		).insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)

	@contextmanager
	def _sefaz(self, resultado):
		transporte = _TransporteFalso(resultado)

		@contextmanager
		def fabrica(*_args, **_kwargs):
			yield transporte

		with (
			mock.patch.object(inutilizacao_fiscal, "_emissor", return_value=(CNPJ, "SP")),
			mock.patch.object(inutilizacao_fiscal, "_transporte", fabrica),
		):
			yield transporte

	def _lacunas(self):
		_, linhas, _ = execute({"company": self.empresa})

		return [(r["inicio"], r["fim"]) for r in linhas if r["serie"] == SERIE]

	def _aceita(self):
		return ResultadoInutilizacao(
			codigo="102",
			mensagem="Inutilização de número homologada",
			homologada=True,
			protocolo="135260000000099",
		)

	def test_faixa_inutilizada_sai_do_relatorio_de_lacunas(self):
		self.assertEqual(self._lacunas(), [(2, 4)])

		with self._sefaz(self._aceita()) as transporte:
			resultado = inutilizar_faixa(self.serie.name, 2, 4, JUSTIFICATIVA)

		self.assertEqual(self._lacunas(), [])
		self.assertEqual(resultado["situacao"], "Autorizado")
		self.assertEqual(
			(transporte.chamadas[0]["numero_inicial"], transporte.chamadas[0]["numero_final"]), ("2", "4")
		)

	def test_o_registro_guarda_faixa_justificativa_e_protocolo(self):
		with self._sefaz(self._aceita()):
			resultado = inutilizar_faixa(self.serie.name, 2, 3, JUSTIFICATIVA)

		registro = frappe.db.get_value(
			"Transmissao Fiscal",
			resultado["registro"],
			[
				"tipo",
				"documento_tipo",
				"documento",
				"numero_inicial",
				"numero_final",
				"justificativa",
				"protocolo",
			],
			as_dict=True,
		)

		self.assertEqual(
			registro,
			{
				"tipo": "Inutilização",
				"documento_tipo": "Numeracao Fiscal",
				"documento": self.serie.name,
				"numero_inicial": 2,
				"numero_final": 3,
				"justificativa": JUSTIFICATIVA,
				"protocolo": "135260000000099",
			},
		)
		self.assertEqual(self._lacunas(), [(4, 4)])

	def test_numero_com_desfecho_e_recusado_sem_chamar_a_sefaz(self):
		with self._sefaz(self._aceita()) as transporte, self.assertRaises(frappe.ValidationError):
			inutilizar_faixa(self.serie.name, 1, 3, JUSTIFICATIVA)

		self.assertEqual(transporte.chamadas, [])

	def test_numero_ainda_nao_alocado_e_recusado_sem_chamar_a_sefaz(self):
		with self._sefaz(self._aceita()) as transporte, self.assertRaises(frappe.ValidationError):
			inutilizar_faixa(self.serie.name, 4, 9, JUSTIFICATIVA)

		self.assertEqual(transporte.chamadas, [])

	def test_rejeicao_da_sefaz_fica_registrada_e_a_faixa_continua_candidata(self):
		recusa = ResultadoInutilizacao(codigo="563", mensagem="Rejeição: já existe pedido", homologada=False)

		with self._sefaz(recusa), self.assertRaises(frappe.ValidationError):
			inutilizar_faixa(self.serie.name, 2, 4, JUSTIFICATIVA)

		rejeitados = frappe.get_all(
			"Transmissao Fiscal",
			filters={"documento": self.serie.name, "tipo": "Inutilização", "situacao": "Rejeitado"},
			fields=["codigo_status", "numero_inicial", "numero_final"],
		)

		self.assertEqual(
			[(r.codigo_status, r.numero_inicial, r.numero_final) for r in rejeitados], [("563", 2, 4)]
		)
		self.assertEqual(self._lacunas(), [(2, 4)])

	def test_segunda_inutilizacao_da_mesma_faixa_e_recusada(self):
		with self._sefaz(self._aceita()):
			inutilizar_faixa(self.serie.name, 2, 4, JUSTIFICATIVA)

		with self._sefaz(self._aceita()) as transporte, self.assertRaises(frappe.ValidationError):
			inutilizar_faixa(self.serie.name, 3, 3, JUSTIFICATIVA)

		self.assertEqual(transporte.chamadas, [])
