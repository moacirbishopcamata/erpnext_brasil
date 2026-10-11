# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""`TransporteSefaz.transmitir_mdfe` e `transmitir_evento_mdfe`: mesma guarda e mesmo registrador do CT-e.

Tarefas 5.1 (os métodos existem e delegam) e 5.3 (a guarda de consumo indevido recusa o envio do MDF-e
**antes** de qualquer chamada à SEFAZ). O `cStat 656` vale para os três documentos e a porta é uma só;
repetir a guarda num caminho próprio do MDF-e seria uma chance a mais de esquecê-la, e ela fica em
`_contexto`.

Teste-âncora: `test_a_guarda_recusa_antes_de_chamar_a_sefaz` conta as chamadas à sessão HTTP: zero — no
lote **e** no evento.
"""

import unittest

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.evento_mdfe import montar_evento_encerramento_mdfe
from erpnext_brasil.tests.test_autorizacao_sefaz_mdfe import CHAVE, DOCUMENTO, SessaoFalsa, _autorizado
from erpnext_brasil.tests.test_soap_resposta_mdfe import _evento, _lote, _recibo
from erpnext_brasil.tests.test_transporte_sefaz import TEM_DEPENDENCIAS, _gerar_pfx

CNPJ = "11222333000181"
CHAVE_REAL = montar_chave(
	uf="35",
	ano_mes="2610",
	cnpj=CNPJ,
	modelo="58",
	serie="001",
	numero="000000001",
	tipo_emissao="1",
	codigo_numerico="12345678",
)


class Bloqueado(Exception):
	pass


def _encerramento():
	return montar_evento_encerramento_mdfe(
		chave_acesso=CHAVE_REAL,
		protocolo="935260000000001",
		data_encerramento="2026-10-10",
		codigo_uf="35",
		codigo_municipio="3550308",
		cnpj_autor=CNPJ,
		data_evento="2026-10-10T12:00:00-03:00",
		ambiente="2",
	)


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography, disponível no bench")
class TestTransmitirMdfe(unittest.TestCase):
	def _transporte(self, sessao, **extras):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		return TransporteSefaz(
			_gerar_pfx(),
			"teste123",
			"SP",
			CNPJ,
			ambiente="homologacao",
			sessao=sessao,
			dormir=lambda _s: None,
			**extras,
		)

	def test_lote_e_recibo_devolvem_a_autorizacao(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		with self._transporte(sessao) as transporte:
			resposta = transporte.transmitir_mdfe(DOCUMENTO, "1")

		self.assertEqual(len(sessao.chamadas), 2)
		self.assertTrue(resposta.autorizada)
		self.assertEqual(resposta.autorizacao.chave_acesso, CHAVE)

	def test_vai_ao_servico_do_mdfe_e_nao_ao_da_nfe_nem_do_cte(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		with self._transporte(sessao) as transporte:
			transporte.transmitir_mdfe(DOCUMENTO, "1")

		for chamada in sessao.chamadas:
			self.assertIn("mdfe", chamada["url"])
			self.assertNotIn("NFeAutorizacao", chamada["url"])
			self.assertNotIn("CTeRecepcao", chamada["url"])

	def test_a_guarda_recusa_antes_de_chamar_a_sefaz(self):
		"""Teste-âncora da 5.3: bloqueado, a requisição **não sai** — a que sair na janela reinicia a
		contagem de uma hora."""
		sessao = SessaoFalsa(_recibo(), _autorizado())
		consultas = []

		def guarda(cnpj, ambiente):
			consultas.append((cnpj, ambiente))
			raise Bloqueado("janela aberta")

		with self.assertRaises(Bloqueado), self._transporte(sessao, guarda=guarda) as transporte:
			transporte.transmitir_mdfe(DOCUMENTO, "1")

		self.assertEqual(consultas, [(CNPJ, "homologacao")])
		self.assertEqual(sessao.chamadas, [], "a guarda não impediu a requisição")

	def test_a_guarda_tambem_recusa_o_evento(self):
		sessao = SessaoFalsa(_evento())

		def guarda(_cnpj, _ambiente):
			raise Bloqueado("janela aberta")

		with self.assertRaises(Bloqueado), self._transporte(sessao, guarda=guarda) as transporte:
			transporte.transmitir_evento_mdfe(_encerramento(), CHAVE_REAL)

		self.assertEqual(sessao.chamadas, [])

	def test_o_registrador_recebe_o_656_do_lote(self):
		"""É assim que o `656` do MDF-e abre a janela de bloqueio, igual ao da NF-e e ao do CT-e."""
		anotado = []
		sessao = SessaoFalsa(_recibo("656", "Consumo Indevido", rec=""))

		with self._transporte(sessao, registrador=lambda *args: anotado.append(args)) as transporte:
			resposta = transporte.transmitir_mdfe(DOCUMENTO, "1")

		self.assertEqual(resposta.codigo, "656")
		self.assertEqual(anotado, [(CNPJ, "homologacao", "656", "Consumo Indevido")])

	def test_o_registrador_tambem_ve_a_autorizacao(self):
		anotado = []

		with self._transporte(
			SessaoFalsa(_recibo(), _lote(prot=("100", "135000000000001"))),
			registrador=lambda *args: anotado.append(args),
		) as transporte:
			transporte.transmitir_mdfe(DOCUMENTO, "1")

		self.assertEqual([a[2] for a in anotado], ["100"])

	def test_evento_registrado_devolve_o_protocolo_e_assina_o_evento_mdfe(self):
		sessao = SessaoFalsa(_evento().replace(CHAVE, CHAVE_REAL))

		with self._transporte(sessao) as transporte:
			resposta = transporte.transmitir_evento_mdfe(_encerramento(), CHAVE_REAL)

		corpo = sessao.chamadas[0]["data"].decode()

		self.assertTrue(resposta.autorizada)
		self.assertIn("<eventoMDFe", corpo)
		self.assertIn("<Signature", corpo)
		self.assertIn("<evEncMDFe>", corpo)
		self.assertIn("mdfeRecepcaoEvento", sessao.chamadas[0]["headers"]["Content-Type"])

	def test_evento_de_outra_chave_nao_e_gravado(self):
		from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel

		with (
			self.assertRaises(TransporteIndisponivel),
			self._transporte(SessaoFalsa(_evento())) as transporte,
		):
			transporte.transmitir_evento_mdfe(_encerramento(), CHAVE_REAL)

	def test_evento_recusado_nao_tem_autorizacao(self):
		sessao = SessaoFalsa(_evento("573", prot=None).replace(CHAVE, CHAVE_REAL))

		with self._transporte(sessao) as transporte:
			resposta = transporte.transmitir_evento_mdfe(_encerramento(), CHAVE_REAL)

		self.assertFalse(resposta.autorizada)
		self.assertEqual(resposta.codigo, "573")


if __name__ == "__main__":
	unittest.main()
