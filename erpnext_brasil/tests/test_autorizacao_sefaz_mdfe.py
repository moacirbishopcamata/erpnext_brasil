# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio do MDF-e por lote e recibo (`integracao/autorizacao_sefaz_mdfe.py`) com sessão HTTP falsa.

Tarefa 5.1. O que se trava aqui é a **orquestração**, sem rede: primeiro o lote (`MDFeRecepcao`), depois
a consulta do recibo (`MDFeRetRecepcao`), sempre no autorizador nacional do MDF-e — nunca no da NF-e nem
no do CT-e.

Teste-âncora: `test_a_chave_autorizada_e_a_da_camada_pura`. A chave que a SEFAZ devolve em
`infProt/chMDFe` precisa ser a do `Id` do documento enviado; se divergir, gravar a autorização associaria
o protocolo de **outro** manifesto a este.
"""

import inspect
import unittest
from pathlib import Path
from unittest.mock import Mock

from erpnext_brasil.fiscal.documento.autorizadores_mdfe import endpoint
from erpnext_brasil.fiscal.documento.resposta_mdfe import RespostaMdfeInvalida
from erpnext_brasil.integracao import autorizacao_sefaz_mdfe
from erpnext_brasil.integracao.autorizacao_sefaz_mdfe import enviar_autorizacao_mdfe
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel
from erpnext_brasil.tests.test_soap_resposta_mdfe import CHAVE, NS, _lote, _recibo

DOCUMENTO = {
	"MDFe": {"@xmlns": NS, "infMDFe": {"@versao": "3.00", "@Id": f"MDFe{CHAVE}", "ide": {"cUF": "35"}}}
}
OUTRA_CHAVE = "5" + "4" * 43


class SessaoFalsa:
	"""Duplo de `requests.Session` que guarda tudo o que o adaptador enviou."""

	def __init__(self, *respostas: str):
		self._respostas = list(respostas)
		self.chamadas: list[dict] = []

	def post(self, url, data, headers, cert, timeout):
		self.chamadas.append({"url": url, "data": data, "headers": headers, "cert": cert, "timeout": timeout})
		resposta = Mock()
		resposta.content = (
			'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"><soap:Body>'
			f"{self._respostas.pop(0)}</soap:Body></soap:Envelope>"
		).encode()
		resposta.raise_for_status = Mock()

		return resposta


def _contexto(sessao, uf="SP", ambiente="homologacao") -> ContextoSefaz:
	return ContextoSefaz(
		uf=uf,
		ambiente=ambiente,
		sessao_http=sessao,
		arquivo_cert=Path("/tmp/cert.pem"),
		arquivo_chave=Path("/tmp/chave.pem"),
	)


def _enviar(sessao, dormir=None, tentativas=3, **contexto):
	return enviar_autorizacao_mdfe(
		DOCUMENTO,
		_contexto(sessao, **contexto),
		id_lote="1",
		dormir=dormir or Mock(),
		tentativas_consulta_recibo=tentativas,
		intervalo_consulta_recibo=2.0,
	)


def _autorizado(chave=CHAVE):
	return _lote(prot=("100", "135000000000001")).replace(CHAVE, chave)


class TestRequisicoes(unittest.TestCase):
	def test_primeiro_o_lote_depois_o_recibo_no_autorizador_nacional(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		_enviar(sessao)

		self.assertEqual(
			[c["url"] for c in sessao.chamadas],
			[
				endpoint("SP", "MDFeRecepcao", "homologacao"),
				endpoint("SP", "MDFeRetRecepcao", "homologacao"),
			],
		)

	def test_a_producao_usa_o_endereco_de_producao(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		_enviar(sessao, ambiente="producao")

		self.assertTrue(all("homologacao" not in c["url"] for c in sessao.chamadas))

	def test_o_lote_leva_cabecalho_idlote_e_o_mdfe_sem_compressao(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		_enviar(sessao)
		corpo = sessao.chamadas[0]["data"].decode()

		self.assertIn("<mdfeCabecMsg", corpo)
		self.assertIn("<cUF>35</cUF>", corpo)
		self.assertIn("<enviMDFe", corpo)
		self.assertIn("<idLote>1</idLote>", corpo)
		self.assertIn(f'Id="MDFe{CHAVE}"', corpo)

	def test_a_acao_soap_de_cada_chamada_vai_no_content_type(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		_enviar(sessao)

		self.assertIn("mdfeRecepcaoLote", sessao.chamadas[0]["headers"]["Content-Type"])
		self.assertIn("mdfeRetRecepcao", sessao.chamadas[1]["headers"]["Content-Type"])

	def test_a_consulta_do_recibo_leva_o_numero_e_o_ambiente(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		_enviar(sessao)
		corpo = sessao.chamadas[1]["data"].decode()

		self.assertIn("<tpAmb>2</tpAmb><nRec>351000000123456</nRec>", corpo)

	def test_usa_o_certificado_do_contexto_e_prazo(self):
		sessao = SessaoFalsa(_recibo(), _autorizado())

		_enviar(sessao)

		for chamada in sessao.chamadas:
			self.assertEqual(chamada["cert"], (str(Path("/tmp/cert.pem")), str(Path("/tmp/chave.pem"))))
			self.assertEqual(chamada["timeout"], 30)


class TestDesfechos(unittest.TestCase):
	def test_a_chave_autorizada_e_a_da_camada_pura(self):
		"""Teste-âncora. Protocolo de outro manifesto nunca vira o deste."""
		with self.assertRaises(RespostaMdfeInvalida):
			_enviar(SessaoFalsa(_recibo(), _autorizado(OUTRA_CHAVE)))

	def test_autorizado_devolve_protocolo_e_chave(self):
		r = _enviar(SessaoFalsa(_recibo(), _autorizado()))

		self.assertTrue(r.autorizada)
		self.assertEqual(
			(r.codigo, r.autorizacao.protocolo, r.autorizacao.chave_acesso), ("100", "135000000000001", CHAVE)
		)
		self.assertEqual(r.bruto["chMDFe"], CHAVE)

	def test_rejeitado_nao_tem_autorizacao_e_guarda_o_motivo(self):
		r = _enviar(SessaoFalsa(_recibo(), _lote(prot=("539", None))))

		self.assertFalse(r.autorizada)
		self.assertEqual(r.codigo, "539")
		self.assertEqual(r.bruto["cStat"], "539")

	def test_lote_recusado_nem_consulta_o_recibo(self):
		sessao = SessaoFalsa(_recibo("225", "Falha no Schema XML", rec=""))

		r = _enviar(sessao)

		self.assertEqual((r.codigo, r.mensagem, r.autorizada), ("225", "Falha no Schema XML", False))
		self.assertEqual(len(sessao.chamadas), 1)

	def test_em_processamento_espera_e_consulta_de_novo(self):
		dormir = Mock()
		sessao = SessaoFalsa(_recibo(), _lote("105"), _autorizado())

		r = _enviar(sessao, dormir=dormir)

		self.assertTrue(r.autorizada)
		self.assertEqual(len(sessao.chamadas), 3)
		self.assertEqual(dormir.call_count, 2)
		dormir.assert_called_with(2.0)

	def test_pendente_apos_as_tentativas_nao_e_rejeicao_e_diz_o_recibo(self):
		sessao = SessaoFalsa(_recibo(), _lote("105"), _lote("105"))

		with self.assertRaises(TransporteIndisponivel) as erro:
			_enviar(sessao, tentativas=2)

		self.assertIn("351000000123456", str(erro.exception))


class TestContrato(unittest.TestCase):
	def test_dormir_e_obrigatorio_e_injetado(self):
		parametros = inspect.signature(enviar_autorizacao_mdfe).parameters

		self.assertIn("dormir", parametros)
		self.assertIs(parametros["dormir"].default, inspect.Parameter.empty)

	def test_o_modulo_nao_importa_frappe_nem_fala_com_outro_documento(self):
		fonte = Path(autorizacao_sefaz_mdfe.__file__).read_text(encoding="utf-8")
		codigo = "\n".join(linha for linha in fonte.splitlines() if not linha.lstrip().startswith("#"))

		self.assertNotIn("import frappe", codigo)
		self.assertNotIn("autorizadores_cte", codigo)
		self.assertNotIn("autorizadores_sefaz", codigo)


if __name__ == "__main__":
	unittest.main()
