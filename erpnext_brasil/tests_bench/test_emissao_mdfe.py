# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) de `emitir_mdfe`: o desfecho da SEFAZ vira `Transmissao Fiscal` no banco.

Tarefa 5.2 de `fechar-laco-cte-mdfe`. O transporte é **falso** (nenhum byte sai para a SEFAZ) e o
certificado/assinatura são substituídos: o que se prova aqui é a costura Frappe — o registro gravado em
todo desfecho, a empresa vinda de `pickup_company`, a chave/protocolo no `Shipment` — e não o envelope,
coberto na suíte pura (`test_autorizacao_sefaz_mdfe.py`).

Teste-âncora: `test_a_rejeicao_deixa_o_registro_mesmo_apos_o_rollback`
--------------------------------------------------------------------------
`frappe.throw` desfaz a transação. Sem o `commit` antes dele, o `Transmissao Fiscal` da rejeição sumiria
junto — e o teste só vê isso se der `rollback` e reler por `frappe.get_all`, outro caminho que não o objeto
que a função devolveu.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_emissao_mdfe
"""

from datetime import datetime
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.integracao.emissao_mdfe import emitir_mdfe
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel
from erpnext_brasil.tests_bench.test_cfop_sugestao import MATRIZ
from erpnext_brasil.tests_bench.test_mdfe_documento import CONTADOR, TestMdfeDocumento

MODULOS_COBERTOS = ("emissao_mdfe", "guarda_de_relogio")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

PROTOCOLO = "311260000000001"


class TransporteFalso:
	"""Responde o que o teste mandar e conta as chamadas. Ignora os argumentos de construção."""

	resposta = None
	chamadas = 0
	eventos = 0

	def __init__(self, *args, **kwargs):
		pass

	def __enter__(self):
		return self

	def __exit__(self, *_exc):
		return None

	def transmitir_mdfe(self, documento, id_lote):
		type(self).chamadas += 1
		chave = documento["MDFe"]["infMDFe"]["@Id"].removeprefix("MDFe")
		modelo = type(self).resposta

		if modelo == "autorizado":
			return RespostaTransmissao(
				codigo="100",
				mensagem="Autorizado o uso do MDF-e",
				autorizacao=Autorizacao(
					protocolo=PROTOCOLO, recebido_em=datetime.now().astimezone(), chave_acesso=chave
				),
				bruto={"cStat": "100", "nProt": PROTOCOLO},
			)

		if modelo == "pendente":
			raise TransporteIndisponivel("Lote 1 (recibo 351) continuou em processamento")

		return RespostaTransmissao(codigo="539", mensagem="Rejeição: duplicidade", bruto={"cStat": "539"})

	def transmitir_evento_mdfe(self, evento, chave_acesso):
		type(self).eventos += 1

		if type(self).resposta == "evento_recusado":
			return RespostaTransmissao(codigo="573", mensagem="Rejeição: evento", bruto={"cStat": "573"})

		return RespostaTransmissao(
			codigo="135",
			mensagem="Evento registrado e vinculado ao MDF-e",
			autorizacao=Autorizacao(
				protocolo="135260000000099",
				recebido_em=datetime.now().astimezone(),
				chave_acesso=chave_acesso,
			),
			bruto={"cStat": "135", "nProt": "135260000000099"},
		)


def substituir_envio(teste, modulo: str) -> None:
	"""Troca, em `modulo`, o transporte, o certificado e a assinatura por duplos — desfeito ao fim do teste."""
	for alvo, substituto in (
		("TransporteSefaz", TransporteFalso),
		("carregar_certificado_da_empresa", lambda company: (b"", "")),
		("AssinadorLocal", lambda pfx, senha: None),
		("assinar_mdfe", lambda arvore, assinador: arvore),
	):
		try:
			patcher = mock.patch(f"erpnext_brasil.integracao.{modulo}.{alvo}", substituto)
			patcher.start()
		except AttributeError:
			continue  # o módulo não usa esse símbolo (os eventos não assinam o documento)

		teste.addCleanup(patcher.stop)


class TestEmissaoMdfe(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestMdfeDocumento.setUpClass()

	def setUp(self):
		TransporteFalso.chamadas = 0
		self._criados: list[tuple[str, str]] = []
		self._shipments: list[str] = []
		substituir_envio(self, "emissao_mdfe")

	def tearDown(self):
		# O código sob teste faz `commit`; a limpeza também tem de ser explícita.
		for shipment in self._shipments:
			frappe.db.delete("Transmissao Fiscal", {"documento": shipment})

		for doctype, nome in reversed(self._criados):
			frappe.delete_doc(doctype, nome, force=True, ignore_permissions=True)

		frappe.db.commit()

	def _shipment(self, **extras):
		shipment = TestMdfeDocumento._shipment(self, **extras)
		self._shipments.append(shipment.name)

		return shipment

	def _nota(self, chave="usar-padrao"):
		return (
			TestMdfeDocumento._nota(self) if chave == "usar-padrao" else TestMdfeDocumento._nota(self, chave)
		)

	def _registros(self, shipment: str) -> list[dict]:
		return frappe.get_all(
			"Transmissao Fiscal",
			filters={"documento_tipo": "Shipment", "documento": shipment},
			fields=[
				"situacao",
				"codigo_status",
				"chave_acesso",
				"protocolo",
				"tipo",
				"company",
				"xml_retorno",
			],
		)

	def test_autorizado_grava_registro_e_chave_e_protocolo_no_shipment(self):
		shipment = self._shipment()
		TransporteFalso.resposta = "autorizado"

		resultado = emitir_mdfe("Shipment", shipment.name)

		registros = self._registros(shipment.name)
		self.assertEqual(len(registros), 1)
		self.assertEqual(registros[0].situacao, "Autorizado")
		self.assertEqual(registros[0].protocolo, PROTOCOLO)
		self.assertEqual(registros[0].tipo, "Autorização")
		self.assertEqual(registros[0].company, MATRIZ, "o Shipment não tem company: vem de pickup_company")
		self.assertIn("100", registros[0].xml_retorno)

		# Releitura por outro caminho: o `db_set` que não persistiu só aparece aqui.
		chave, protocolo = frappe.db.get_value(
			"Shipment", shipment.name, ["br_chave_acesso", "br_protocolo_autorizacao"]
		)
		self.assertEqual(chave, resultado["chave_acesso"])
		self.assertEqual(chave, registros[0].chave_acesso)
		self.assertEqual(len(chave), 44)
		self.assertEqual(protocolo, PROTOCOLO)

	def test_a_rejeicao_deixa_o_registro_mesmo_apos_o_rollback(self):
		shipment = self._shipment()
		TransporteFalso.resposta = "rejeitado"

		with self.assertRaises(frappe.ValidationError):
			emitir_mdfe("Shipment", shipment.name)

		frappe.db.rollback()

		registros = self._registros(shipment.name)
		self.assertEqual([r.situacao for r in registros], ["Rejeitado"])
		self.assertEqual(registros[0].codigo_status, "539")

		# A chave de um manifesto recusado não identifica documento nenhum: o Shipment não a recebe.
		self.assertFalse(frappe.db.get_value("Shipment", shipment.name, "br_chave_acesso"))
		self.assertFalse(frappe.db.get_value("Shipment", shipment.name, "br_protocolo_autorizacao"))

	def test_lote_em_processamento_nao_vira_rejeicao_e_guarda_o_numero(self):
		shipment = self._shipment()
		TransporteFalso.resposta = "pendente"

		with self.assertRaises(frappe.ValidationError):
			emitir_mdfe("Shipment", shipment.name)

		frappe.db.rollback()

		self.assertEqual(self._registros(shipment.name), [], "gravou desfecho que a SEFAZ não deu")
		numero = frappe.db.get_value("Shipment", shipment.name, "br_numero_mdfe")
		self.assertTrue(numero, "o número alocado se perdeu: a reemissão consumiria outro")

	def test_nao_reenvia_o_que_ja_foi_autorizado(self):
		shipment = self._shipment()
		TransporteFalso.resposta = "autorizado"

		emitir_mdfe("Shipment", shipment.name)
		ultimo = frappe.db.get_value("Numeracao Fiscal", CONTADOR, "ultimo_numero")

		with self.assertRaises(frappe.ValidationError):
			emitir_mdfe("Shipment", shipment.name)

		self.assertEqual(TransporteFalso.chamadas, 1, "reenviou um manifesto autorizado")
		self.assertEqual(frappe.db.get_value("Numeracao Fiscal", CONTADOR, "ultimo_numero"), ultimo)
		self.assertEqual(len(self._registros(shipment.name)), 1)

	def test_recusa_de_cadastro_nao_chama_a_sefaz_nem_grava_registro(self):
		shipment = self._shipment(br_placa_mdfe="")
		TransporteFalso.resposta = "autorizado"

		with self.assertRaises(frappe.ValidationError):
			emitir_mdfe("Shipment", shipment.name)

		self.assertEqual(TransporteFalso.chamadas, 0)
		self.assertEqual(self._registros(shipment.name), [])
		self.assertFalse(frappe.db.get_value("Shipment", shipment.name, "br_numero_mdfe"), "consumiu número")
