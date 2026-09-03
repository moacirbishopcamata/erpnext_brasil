# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `integracao/transmissao_esocial.py` com sessão HTTP falsa — sem rede.

Mesma disciplina de `test_transporte_sefaz.py`: `SessaoFalsa` satisfaz só `.post`,
devolve respostas pré-programadas em ordem. `TestPolling` prova o polling por
`cdResposta=203`, com `dormir` falso.
"""

import unittest
from unittest.mock import Mock

from erpnext_brasil.folha.esocial_lote import AMBIENTE_PRODUCAO_RESTRITA
from erpnext_brasil.integracao.contexto_esocial import ContextoEsocial
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel
from erpnext_brasil.integracao.transmissao_esocial import consultar_lote, enviar_lote


def _resposta_soap(operacao: str, corpo_interno: str) -> Mock:
	resposta = Mock()
	resposta.content = (
		'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
		f"<soap:Body><{operacao}Response>{corpo_interno}</{operacao}Response></soap:Body>"
		"</soap:Envelope>"
	).encode("utf-8")
	resposta.raise_for_status = Mock()

	return resposta


def _retorno_envio(cd_resposta=201, desc="Lote recebido com sucesso", protocolo="1.1.0000000000000000001"):
	dados_recepcao = (
		f"<dadosRecepcaoLote><protocoloEnvio>{protocolo}</protocoloEnvio></dadosRecepcaoLote>"
		if protocolo
		else ""
	)

	return (
		"<retornoEnvioLoteEventos>"
		f"<status><cdResposta>{cd_resposta}</cdResposta><descResposta>{desc}</descResposta></status>"
		f"{dados_recepcao}"
		"</retornoEnvioLoteEventos>"
	)


def _retorno_processamento(cd_resposta=201, desc="Processado", eventos_xml=""):
	return (
		"<retornoProcessamentoLoteEventos>"
		f"<status><cdResposta>{cd_resposta}</cdResposta><descResposta>{desc}</descResposta></status>"
		"<dadosRecepcaoLote><protocoloEnvio>1.1.0000000000000000001</protocoloEnvio></dadosRecepcaoLote>"
		f"<retornoEventos>{eventos_xml}</retornoEventos>"
		"</retornoProcessamentoLoteEventos>"
	)


_EVENTO_OK = (
	'<evento Id="ID1"><retornoEvento><eSocial xmlns="y"><evtRecibo>ok</evtRecibo></eSocial></retornoEvento></evento>'
)


class SessaoFalsa:
	def __init__(self, respostas: list[Mock]):
		self._respostas = list(respostas)
		self.chamadas: list[dict] = []

	def post(self, url, data, headers, cert, timeout):
		self.chamadas.append({"url": url, "data": data, "headers": headers, "cert": cert})

		return self._respostas.pop(0)


def _contexto(sessao) -> ContextoEsocial:
	return ContextoEsocial(
		ambiente=AMBIENTE_PRODUCAO_RESTRITA,
		sessao_http=sessao,
		arquivo_cert="cert.pem",
		arquivo_chave="chave.pem",
	)


class TestEnviarLote(unittest.TestCase):
	def test_sucesso_sem_pendencia(self):
		sessao = SessaoFalsa(
			[
				_resposta_soap("EnviarLoteEventos", _retorno_envio()),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento(eventos_xml=_EVENTO_OK)),
			]
		)

		resultado = enviar_lote("<eSocial>...</eSocial>", _contexto(sessao), dormir=lambda _: None)

		self.assertTrue(resultado.status.sucesso)
		self.assertEqual(len(resultado.eventos), 1)
		self.assertEqual(len(sessao.chamadas), 2)

	def test_usa_cabecalhos_soap_11(self):
		sessao = SessaoFalsa(
			[
				_resposta_soap("EnviarLoteEventos", _retorno_envio()),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento()),
			]
		)

		enviar_lote("<eSocial>...</eSocial>", _contexto(sessao), dormir=lambda _: None)

		primeira = sessao.chamadas[0]["headers"]
		self.assertEqual(primeira["Content-Type"], "text/xml; charset=utf-8")
		self.assertIn("SOAPAction", primeira)

	def test_usa_endpoint_de_producao_restrita(self):
		sessao = SessaoFalsa(
			[
				_resposta_soap("EnviarLoteEventos", _retorno_envio()),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento()),
			]
		)

		enviar_lote("<eSocial>...</eSocial>", _contexto(sessao), dormir=lambda _: None)

		self.assertIn("producaorestrita.esocial.gov.br", sessao.chamadas[0]["url"])

	def test_lote_recusado_e_erro(self):
		sessao = SessaoFalsa(
			[_resposta_soap("EnviarLoteEventos", _retorno_envio(cd_resposta=401, desc="Erro de preenchimento", protocolo=""))]
		)

		with self.assertRaises(TransporteIndisponivel):
			enviar_lote("<eSocial>...</eSocial>", _contexto(sessao), dormir=lambda _: None)

	def test_aceito_sem_protocolo_e_erro(self):
		sessao = SessaoFalsa([_resposta_soap("EnviarLoteEventos", _retorno_envio(protocolo=""))])

		with self.assertRaises(TransporteIndisponivel):
			enviar_lote("<eSocial>...</eSocial>", _contexto(sessao), dormir=lambda _: None)


class TestPolling(unittest.TestCase):
	def test_consulta_de_novo_quando_pendente(self):
		sessao = SessaoFalsa(
			[
				_resposta_soap("EnviarLoteEventos", _retorno_envio()),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento(cd_resposta=203, desc="Em fila")),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento(eventos_xml=_EVENTO_OK)),
			]
		)

		chamadas_dormir = []
		resultado = enviar_lote(
			"<eSocial>...</eSocial>", _contexto(sessao), dormir=chamadas_dormir.append, tentativas_consulta=5
		)

		self.assertTrue(resultado.status.sucesso)
		self.assertEqual(len(sessao.chamadas), 3)
		self.assertEqual(len(chamadas_dormir), 1)

	def test_desiste_apos_esgotar_tentativas(self):
		sessao = SessaoFalsa(
			[
				_resposta_soap("EnviarLoteEventos", _retorno_envio()),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento(cd_resposta=203)),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento(cd_resposta=203)),
				_resposta_soap("ConsultarLoteEventos", _retorno_processamento(cd_resposta=203)),
			]
		)

		with self.assertRaises(TransporteIndisponivel):
			enviar_lote(
				"<eSocial>...</eSocial>", _contexto(sessao), dormir=lambda _: None, tentativas_consulta=2
			)


class TestConsultarLote(unittest.TestCase):
	def test_consulta_sem_reenviar(self):
		sessao = SessaoFalsa([_resposta_soap("ConsultarLoteEventos", _retorno_processamento(eventos_xml=_EVENTO_OK))])

		resultado = consultar_lote("1.1.0000000000000000001", _contexto(sessao))

		self.assertTrue(resultado.status.sucesso)
		self.assertEqual(len(sessao.chamadas), 1)


if __name__ == "__main__":
	unittest.main()
