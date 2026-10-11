# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) de `encerrar_mdfe` e `cancelar_mdfe`: um teste por evento, no banco.

Tarefa 5.4 de `fechar-laco-cte-mdfe`. O transporte é **falso**: o que se prova é a costura Frappe — o
registro de cada evento com a empresa de `pickup_company`, o "não reenvia o que já foi aceito" e a ordem
(encerrado não se cancela). Nenhum byte sai para a SEFAZ; o envelope e a assinatura do evento estão na
suíte pura (`test_transporte_mdfe.py`).

Teste-âncora: `test_cancelar_um_mdfe_ja_encerrado_recusa_antes_de_chamar_a_sefaz` — conta as chamadas ao
transporte: zero.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_eventos_mdfe
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao.emissao_mdfe import emitir_mdfe
from erpnext_brasil.integracao.eventos_mdfe import cancelar_mdfe, encerrar_mdfe, estado_do_mdfe
from erpnext_brasil.tests_bench.test_cfop_sugestao import MATRIZ
from erpnext_brasil.tests_bench.test_emissao_mdfe import TransporteFalso, substituir_envio
from erpnext_brasil.tests_bench.test_mdfe_documento import TestMdfeDocumento

MODULOS_COBERTOS = ("eventos_mdfe", "situacao_fiscal")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

JUSTIFICATIVA = "Veículo não saiu do pátio por falha mecânica"


class TestEventosMdfe(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestMdfeDocumento.setUpClass()

	def setUp(self):
		TransporteFalso.chamadas = 0
		TransporteFalso.eventos = 0
		self._criados: list[tuple[str, str]] = []
		self._shipments: list[str] = []
		substituir_envio(self, "emissao_mdfe")
		substituir_envio(self, "eventos_mdfe")

	def tearDown(self):
		for shipment in self._shipments:
			frappe.db.delete("Transmissao Fiscal", {"documento": shipment})

		for doctype, nome in reversed(self._criados):
			frappe.delete_doc(doctype, nome, force=True, ignore_permissions=True)

		frappe.db.commit()

	def _nota(self, chave="usar-padrao"):
		"""A nota (com chave) que o `Shipment` manifesta — emprestada do teste do mapeador."""
		return (
			TestMdfeDocumento._nota(self) if chave == "usar-padrao" else TestMdfeDocumento._nota(self, chave)
		)

	def _autorizado(self) -> str:
		"""Um `Shipment` com MDF-e autorizado — o ponto de partida de todo evento."""
		shipment = TestMdfeDocumento._shipment(self)
		self._shipments.append(shipment.name)
		TransporteFalso.resposta = "autorizado"
		emitir_mdfe("Shipment", shipment.name)

		return shipment.name

	def _registros(self, shipment: str, tipo: str) -> list[dict]:
		return frappe.get_all(
			"Transmissao Fiscal",
			filters={"documento_tipo": "Shipment", "documento": shipment, "tipo": tipo},
			fields=["situacao", "codigo_status", "protocolo", "company", "chave_acesso"],
		)

	# ------------------------------------------------------------------ encerramento

	def test_encerrar_grava_o_evento_e_o_estado_passa_a_encerrado(self):
		shipment = self._autorizado()

		resultado = encerrar_mdfe(shipment)

		registros = self._registros(shipment, "Encerramento")
		self.assertEqual([r.situacao for r in registros], ["Autorizado"])
		self.assertEqual(registros[0].company, MATRIZ)
		self.assertEqual(registros[0].protocolo, resultado["protocolo"])
		self.assertEqual(TransporteFalso.eventos, 1)

		estado = estado_do_mdfe(shipment)
		self.assertTrue(estado["encerrado"])
		self.assertEqual(estado["situacao"], "Autorizado", "encerrar não cancela: o manifesto segue válido")

	def test_encerrar_duas_vezes_recusa_sem_reenviar(self):
		shipment = self._autorizado()
		encerrar_mdfe(shipment)

		with self.assertRaises(frappe.ValidationError):
			encerrar_mdfe(shipment)

		self.assertEqual(TransporteFalso.eventos, 1, "reenviou um evento já aceito")
		self.assertEqual(len(self._registros(shipment, "Encerramento")), 1)

	def test_encerrar_sem_autorizacao_recusa(self):
		shipment = TestMdfeDocumento._shipment(self)
		self._shipments.append(shipment.name)

		with self.assertRaises(frappe.ValidationError):
			encerrar_mdfe(shipment.name)

		self.assertEqual(TransporteFalso.eventos, 0)

	def test_encerramento_recusado_fica_registrado_apos_o_rollback(self):
		shipment = self._autorizado()
		TransporteFalso.resposta = "evento_recusado"

		with self.assertRaises(frappe.ValidationError):
			encerrar_mdfe(shipment)

		frappe.db.rollback()

		registros = self._registros(shipment, "Encerramento")
		self.assertEqual([(r.situacao, r.codigo_status) for r in registros], [("Rejeitado", "573")])
		self.assertFalse(estado_do_mdfe(shipment)["encerrado"], "recusa não encerra")

	# ------------------------------------------------------------------ cancelamento

	def test_cancelar_grava_o_evento_e_o_manifesto_passa_a_cancelado(self):
		shipment = self._autorizado()

		cancelar_mdfe(shipment, JUSTIFICATIVA)

		registros = self._registros(shipment, "Cancelamento")
		self.assertEqual([r.situacao for r in registros], ["Cancelado"])
		self.assertEqual(registros[0].company, MATRIZ)

		estado = estado_do_mdfe(shipment)
		self.assertEqual(estado["situacao"], "Cancelado")
		self.assertFalse(estado["encerrado"])

	def test_cancelar_um_mdfe_ja_cancelado_recusa_sem_reenviar(self):
		shipment = self._autorizado()
		cancelar_mdfe(shipment, JUSTIFICATIVA)

		with self.assertRaises(frappe.ValidationError):
			cancelar_mdfe(shipment, JUSTIFICATIVA)

		self.assertEqual(TransporteFalso.eventos, 1)

	def test_cancelar_um_mdfe_ja_encerrado_recusa_antes_de_chamar_a_sefaz(self):
		"""Teste-âncora. Encerrado não se cancela — e a recusa não gasta uma chamada à SEFAZ."""
		shipment = self._autorizado()
		encerrar_mdfe(shipment)
		antes = TransporteFalso.eventos

		with self.assertRaises(frappe.ValidationError):
			cancelar_mdfe(shipment, JUSTIFICATIVA)

		self.assertEqual(TransporteFalso.eventos, antes, "chamou a SEFAZ para cancelar um encerrado")
		self.assertEqual(self._registros(shipment, "Cancelamento"), [])

	def test_encerrar_um_mdfe_cancelado_recusa(self):
		shipment = self._autorizado()
		cancelar_mdfe(shipment, JUSTIFICATIVA)

		with self.assertRaises(frappe.ValidationError):
			encerrar_mdfe(shipment)

		self.assertEqual(TransporteFalso.eventos, 1)

	def test_justificativa_curta_e_recusada_antes_de_chamar_a_sefaz(self):
		shipment = self._autorizado()

		with self.assertRaises(frappe.ValidationError):
			cancelar_mdfe(shipment, "curta")

		self.assertEqual(TransporteFalso.eventos, 0)
		self.assertEqual(self._registros(shipment, "Cancelamento"), [])

	def test_cancelamento_recusado_fica_registrado_e_o_manifesto_segue_valido(self):
		shipment = self._autorizado()
		TransporteFalso.resposta = "evento_recusado"

		with self.assertRaises(frappe.ValidationError):
			cancelar_mdfe(shipment, JUSTIFICATIVA)

		frappe.db.rollback()

		self.assertEqual([r.situacao for r in self._registros(shipment, "Cancelamento")], ["Rejeitado"])
		self.assertEqual(estado_do_mdfe(shipment)["situacao"], "Autorizado")
