# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) de `emitir_cte`: o desfecho da SEFAZ vira `Transmissao Fiscal` no banco.

Tarefa 3.2 de `fechar-laco-cte-mdfe`. O transporte é **falso** (nenhum byte sai para a SEFAZ) e o
certificado/assinatura são substituídos: o que se prova aqui é a costura Frappe — o registro
gravado em todo desfecho, a chave/protocolo na fatura — e não o envelope, coberto na suíte pura.

Teste-âncora: `test_a_rejeicao_deixa_o_registro_mesmo_apos_o_rollback`
--------------------------------------------------------------------------
`frappe.throw` desfaz a transação. Sem o `commit` antes dele, o `Transmissao Fiscal` da rejeição
sumiria junto — e o teste só vê isso se der `rollback` e reler por `frappe.get_all`, outro caminho
que não o objeto que a função devolveu.

Como rodar
-----------------
    bench --site v16.localhost run-tests \
        --module erpnext_brasil.tests_bench.test_emissao_cte
"""

from datetime import datetime
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.integracao.emissao_cte import emitir_cte
from erpnext_brasil.tests_bench.test_cte_documento import TestCteDocumento

MODULOS_COBERTOS = ("emissao_cte",)
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

PROTOCOLO = "311260000000001"


class TransporteFalso:
	"""Responde o que o teste mandar e conta as chamadas. Ignora os argumentos de construção."""

	resposta = None
	chamadas = 0

	def __init__(self, *args, **kwargs):
		pass

	def transmitir_cte(self, documento):
		type(self).chamadas += 1
		chave = documento["CTe"]["infCte"]["@Id"].removeprefix("CTe")
		modelo = type(self).resposta

		if modelo == "autorizado":
			return RespostaTransmissao(
				codigo="100",
				mensagem="Autorizado o uso do CT-e",
				autorizacao=Autorizacao(
					protocolo=PROTOCOLO, recebido_em=datetime.now().astimezone(), chave_acesso=chave
				),
				bruto={"cStat": "100", "nProt": PROTOCOLO},
			)

		if modelo == "denegado":
			return RespostaTransmissao(
				codigo="110", mensagem="Uso Denegado", denegado=True, bruto={"cStat": "110"}
			)

		return RespostaTransmissao(codigo="539", mensagem="Rejeição: duplicidade", bruto={"cStat": "539"})


class TestEmissaoCte(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestCteDocumento.setUpClass()

	def setUp(self):
		TransporteFalso.chamadas = 0
		self._faturas = []

		for alvo, substituto in (
			("TransporteSefaz", TransporteFalso),
			("carregar_certificado_da_empresa", lambda company: (b"", "")),
			("AssinadorLocal", lambda pfx, senha: None),
			("assinar_cte", lambda arvore, assinador: arvore),
		):
			patcher = mock.patch(f"erpnext_brasil.integracao.emissao_cte.{alvo}", substituto)
			patcher.start()
			self.addCleanup(patcher.stop)

	def tearDown(self):
		# O código sob teste faz `commit`; a limpeza também tem de ser explícita.
		for fatura in self._faturas:
			frappe.db.delete("Transmissao Fiscal", {"documento": fatura})

		frappe.db.commit()

	def _fatura(self):
		fatura = TestCteDocumento._fatura(self)
		self._faturas.append(fatura.name)

		return fatura

	def _registros(self, fatura: str) -> list[dict]:
		return frappe.get_all(
			"Transmissao Fiscal",
			filters={"documento_tipo": "Sales Invoice", "documento": fatura},
			fields=["situacao", "codigo_status", "chave_acesso", "protocolo", "tipo", "xml_retorno"],
		)

	def test_autorizado_grava_registro_e_chave_e_protocolo_na_fatura(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "autorizado"

		resultado = emitir_cte("Sales Invoice", fatura.name)

		registros = self._registros(fatura.name)
		self.assertEqual(len(registros), 1)
		self.assertEqual(registros[0].situacao, "Autorizado")
		self.assertEqual(registros[0].protocolo, PROTOCOLO)
		self.assertEqual(registros[0].tipo, "Autorização")
		self.assertIn("100", registros[0].xml_retorno)

		# Releitura por outro caminho: o `db_set` que não persistiu só aparece aqui.
		chave, protocolo = frappe.db.get_value(
			"Sales Invoice", fatura.name, ["br_chave_acesso", "br_protocolo_autorizacao"]
		)
		self.assertEqual(chave, resultado["chave_acesso"])
		self.assertEqual(chave, registros[0].chave_acesso)
		self.assertEqual(len(chave), 44)
		self.assertEqual(protocolo, PROTOCOLO)

	def test_a_rejeicao_deixa_o_registro_mesmo_apos_o_rollback(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "rejeitado"

		with self.assertRaises(frappe.ValidationError):
			emitir_cte("Sales Invoice", fatura.name)

		frappe.db.rollback()

		registros = self._registros(fatura.name)
		self.assertEqual([r.situacao for r in registros], ["Rejeitado"])
		self.assertEqual(registros[0].codigo_status, "539")
		self.assertFalse(frappe.db.get_value("Sales Invoice", fatura.name, "br_chave_acesso"))

	def test_denegado_e_registrado_como_denegado_e_nao_como_rejeitado(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "denegado"

		with self.assertRaises(frappe.ValidationError):
			emitir_cte("Sales Invoice", fatura.name)

		frappe.db.rollback()

		self.assertEqual([r.situacao for r in self._registros(fatura.name)], ["Denegado"])

	def test_nao_reenvia_o_que_ja_foi_autorizado(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "autorizado"
		emitir_cte("Sales Invoice", fatura.name)

		with self.assertRaises(frappe.ValidationError):
			emitir_cte("Sales Invoice", fatura.name)

		self.assertEqual(TransporteFalso.chamadas, 1)
		self.assertEqual(len(self._registros(fatura.name)), 1)

	def test_dado_ausente_recusa_sem_chamar_a_sefaz_e_sem_registro(self):
		fatura = self._fatura()
		frappe.db.set_value("Sales Invoice", fatura.name, "br_remetente_cte", None)
		TransporteFalso.resposta = "autorizado"

		with self.assertRaises(frappe.ValidationError) as contexto:
			emitir_cte("Sales Invoice", fatura.name)

		self.assertIn("[1206]", str(contexto.exception))
		self.assertEqual(TransporteFalso.chamadas, 0)
		self.assertEqual(self._registros(fatura.name), [])
