# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) de `cancelar_cte` e `corrigir_cte`: o evento vira `Transmissao Fiscal` no banco.

Tarefa 3.4 de `fechar-laco-cte-mdfe`. A autorização é feita por `emitir_cte` com transporte falso, e
o evento também sai por um transporte falso (nenhum byte vai à SEFAZ): o que se prova é a costura
Frappe — protocolo lido do registro da autorização, `nSeqEvento` que avança, rejeição que sobrevive
ao `rollback`, evento que não é reenviado.

Teste-âncora: `test_a_segunda_carta_usa_a_sequencia_2`. Sem contar as cartas já aceitas, a segunda
repetiria o `@Id` da primeira e a SEFAZ a recusaria por duplicidade.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_eventos_cte
"""

from datetime import datetime
from typing import ClassVar
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.integracao.eventos_cte import cancelar_cte, corrigir_cte
from erpnext_brasil.tests_bench.test_emissao_cte import TestEmissaoCte, TransporteFalso

MODULOS_COBERTOS = ("eventos_cte",)
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

PROTOCOLO_EVENTO = "311260000077777"
JUSTIFICATIVA = "Erro de digitação no valor da prestação de serviço."
CORRECAO = [{"grupo_alterado": "ide", "campo_alterado": "natOp", "valor_alterado": "Frete"}]


class TransporteDeEventoFalso:
	"""Responde o que o teste mandar, guarda os eventos recebidos e funciona como `with`."""

	modo = "registrado"
	eventos: ClassVar[list] = []

	def __init__(self, *args, **kwargs):
		pass

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def transmitir_evento_cte(self, evento, chave):
		type(self).eventos.append(evento)

		if type(self).modo == "registrado":
			return RespostaTransmissao(
				codigo="135",
				mensagem="Evento registrado e vinculado a CT-e",
				autorizacao=Autorizacao(
					protocolo=PROTOCOLO_EVENTO, recebido_em=datetime.now().astimezone(), chave_acesso=chave
				),
				bruto={"cStat": "135"},
			)

		return RespostaTransmissao(
			codigo="494", mensagem="Rejeição: chave inexistente", bruto={"cStat": "494"}
		)


class TestEventosCte(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestEmissaoCte.setUpClass()

	def setUp(self):
		TransporteFalso.chamadas = 0
		TransporteFalso.resposta = "autorizado"
		TransporteDeEventoFalso.modo = "registrado"
		TransporteDeEventoFalso.eventos = []
		self._faturas = []

		emissao = "erpnext_brasil.integracao.emissao_cte"
		eventos = "erpnext_brasil.integracao.eventos_cte"
		alvos = {
			f"{emissao}.TransporteSefaz": TransporteFalso,
			f"{emissao}.carregar_certificado_da_empresa": lambda company: (b"", ""),
			f"{emissao}.AssinadorLocal": lambda pfx, senha: None,
			f"{emissao}.assinar_cte": lambda arvore, assinador: arvore,
			f"{eventos}.TransporteSefaz": TransporteDeEventoFalso,
			f"{eventos}.carregar_certificado_da_empresa": lambda company: (b"", ""),
		}

		for alvo, substituto in alvos.items():
			patcher = mock.patch(alvo, substituto)
			patcher.start()
			self.addCleanup(patcher.stop)

	def tearDown(self):
		for fatura in self._faturas:
			frappe.db.delete("Transmissao Fiscal", {"documento": fatura})

		frappe.db.commit()

	def _fatura(self):
		from erpnext_brasil.tests_bench.test_cte_documento import TestCteDocumento

		fatura = TestCteDocumento._fatura(self)
		self._faturas.append(fatura.name)

		return fatura

	def _fatura_autorizada(self):
		from erpnext_brasil.integracao.emissao_cte import emitir_cte

		fatura = self._fatura()
		emitir_cte("Sales Invoice", fatura.name)

		return fatura

	def _registros(self, fatura: str, tipo: str) -> list[dict]:
		return frappe.get_all(
			"Transmissao Fiscal",
			filters={"documento_tipo": "Sales Invoice", "documento": fatura, "tipo": tipo},
			fields=["situacao", "codigo_status", "protocolo", "chave_acesso"],
			order_by="creation asc",
		)

	def test_cancelar_usa_o_protocolo_da_autorizacao_e_grava_cancelado(self):
		fatura = self._fatura_autorizada()
		protocolo_autorizacao = frappe.db.get_value("Sales Invoice", fatura.name, "br_protocolo_autorizacao")

		resultado = cancelar_cte("Sales Invoice", fatura.name, JUSTIFICATIVA)

		evento = TransporteDeEventoFalso.eventos[0]["eventoCTe"]["infEvento"]
		self.assertEqual(evento["detEvento"]["evCancCTe"]["nProt"], protocolo_autorizacao)
		self.assertEqual(evento["nSeqEvento"], "1")

		registros = self._registros(fatura.name, "Cancelamento")
		self.assertEqual([r.situacao for r in registros], ["Cancelado"])
		self.assertEqual(registros[0].protocolo, PROTOCOLO_EVENTO)
		self.assertEqual(registros[0].chave_acesso, resultado["chave_acesso"])

	def test_nao_cancela_duas_vezes(self):
		fatura = self._fatura_autorizada()
		cancelar_cte("Sales Invoice", fatura.name, JUSTIFICATIVA)

		with self.assertRaises(frappe.ValidationError):
			cancelar_cte("Sales Invoice", fatura.name, JUSTIFICATIVA)

		self.assertEqual(len(TransporteDeEventoFalso.eventos), 1)
		self.assertEqual(len(self._registros(fatura.name, "Cancelamento")), 1)

	def test_cancelamento_rejeitado_deixa_o_registro_apos_o_rollback(self):
		fatura = self._fatura_autorizada()
		TransporteDeEventoFalso.modo = "rejeitado"

		with self.assertRaises(frappe.ValidationError):
			cancelar_cte("Sales Invoice", fatura.name, JUSTIFICATIVA)

		frappe.db.rollback()

		registros = self._registros(fatura.name, "Cancelamento")
		self.assertEqual([r.situacao for r in registros], ["Rejeitado"])
		self.assertEqual(registros[0].codigo_status, "494")

	def test_rejeitado_nao_impede_cancelar_depois(self):
		fatura = self._fatura_autorizada()
		TransporteDeEventoFalso.modo = "rejeitado"

		with self.assertRaises(frappe.ValidationError):
			cancelar_cte("Sales Invoice", fatura.name, JUSTIFICATIVA)

		TransporteDeEventoFalso.modo = "registrado"
		cancelar_cte("Sales Invoice", fatura.name, JUSTIFICATIVA)

		self.assertEqual(
			[r.situacao for r in self._registros(fatura.name, "Cancelamento")], ["Rejeitado", "Cancelado"]
		)

	def test_sem_autorizacao_nao_ha_o_que_cancelar_nem_corrigir(self):
		fatura = self._fatura()

		with self.assertRaises(frappe.ValidationError):
			cancelar_cte("Sales Invoice", fatura.name, JUSTIFICATIVA)

		with self.assertRaises(frappe.ValidationError):
			corrigir_cte("Sales Invoice", fatura.name, CORRECAO)

		self.assertEqual(TransporteDeEventoFalso.eventos, [])

	def test_justificativa_curta_recusa_sem_chamar_a_sefaz(self):
		fatura = self._fatura_autorizada()

		with self.assertRaises(frappe.ValidationError):
			cancelar_cte("Sales Invoice", fatura.name, "curta")

		self.assertEqual(TransporteDeEventoFalso.eventos, [])
		self.assertEqual(self._registros(fatura.name, "Cancelamento"), [])

	def test_a_segunda_carta_usa_a_sequencia_2(self):
		fatura = self._fatura_autorizada()

		corrigir_cte("Sales Invoice", fatura.name, CORRECAO)
		corrigir_cte("Sales Invoice", fatura.name, frappe.as_json(CORRECAO))

		ids = [e["eventoCTe"]["infEvento"]["@Id"] for e in TransporteDeEventoFalso.eventos]
		self.assertTrue(ids[0].endswith("001"), ids[0])
		self.assertTrue(ids[1].endswith("002"), ids[1])
		self.assertNotEqual(ids[0], ids[1])

		registros = self._registros(fatura.name, "Carta de Correção")
		self.assertEqual([r.situacao for r in registros], ["Autorizado", "Autorizado"])

	def test_carta_rejeitada_nao_consome_a_sequencia(self):
		fatura = self._fatura_autorizada()
		TransporteDeEventoFalso.modo = "rejeitado"

		with self.assertRaises(frappe.ValidationError):
			corrigir_cte("Sales Invoice", fatura.name, CORRECAO)

		TransporteDeEventoFalso.modo = "registrado"
		corrigir_cte("Sales Invoice", fatura.name, CORRECAO)

		ids = [e["eventoCTe"]["infEvento"]["@Id"] for e in TransporteDeEventoFalso.eventos]
		self.assertTrue(ids[0].endswith("001") and ids[1].endswith("001"), ids)

	def test_carta_sem_correcoes_ou_malformada_recusa_sem_chamar_a_sefaz(self):
		fatura = self._fatura_autorizada()

		for ruim in ([], [{"campo": "x"}]):
			with self.subTest(ruim=ruim), self.assertRaises(frappe.ValidationError):
				corrigir_cte("Sales Invoice", fatura.name, ruim)

		self.assertEqual(TransporteDeEventoFalso.eventos, [])
