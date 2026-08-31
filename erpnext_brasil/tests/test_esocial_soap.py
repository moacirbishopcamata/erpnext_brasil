# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_soap.py` — envelope SOAP 1.1 do eSocial."""

import unittest

from erpnext_brasil.folha.esocial_soap import (
	NAMESPACE_SOAP11,
	EsocialSoapInvalido,
	extrair_resultado,
	montar_envelope,
	soap_action,
)

try:
	from lxml import etree

	TEM_LXML = True
except ImportError:
	TEM_LXML = False


class TestSoapAction(unittest.TestCase):
	def test_enviar_lote_eventos(self):
		acao = soap_action("enviarLoteEventos")

		self.assertEqual(
			acao,
			"http://www.esocial.gov.br/servicos/empregador/lote/eventos/envio/v1_1_0/"
			"ServicoEnviarLoteEventos/EnviarLoteEventos",
		)

	def test_consultar_lote_eventos(self):
		acao = soap_action("consultarLoteEventos")

		self.assertEqual(
			acao,
			"http://www.esocial.gov.br/servicos/empregador/lote/eventos/envio/consulta/"
			"retornoProcessamento/v1_1_0/ServicoConsultarLoteEventos/ConsultarLoteEventos",
		)

	def test_servico_desconhecido_e_erro(self):
		with self.assertRaises(EsocialSoapInvalido):
			soap_action("servicoInventado")


class TestMontarEnvelope(unittest.TestCase):
	def test_usa_soap_11_nao_soap_12(self):
		envelope = montar_envelope("enviarLoteEventos", "<eSocial>conteudo</eSocial>")

		self.assertIn(NAMESPACE_SOAP11, envelope)
		self.assertNotIn("http://www.w3.org/2003/05/soap-envelope", envelope)

	def test_envolve_no_wrapper_do_servico(self):
		envelope = montar_envelope("enviarLoteEventos", "<eSocial>conteudo</eSocial>")

		self.assertIn("<loteEventos><eSocial>conteudo</eSocial></loteEventos>", envelope)
		self.assertIn("<EnviarLoteEventos ", envelope)

	def test_consultar_usa_wrapper_diferente(self):
		envelope = montar_envelope("consultarLoteEventos", "<eSocial>consulta</eSocial>")

		self.assertIn("<consulta><eSocial>consulta</eSocial></consulta>", envelope)
		self.assertIn("<ConsultarLoteEventos ", envelope)

	def test_xml_interno_vazio_e_erro(self):
		with self.assertRaises(EsocialSoapInvalido):
			montar_envelope("enviarLoteEventos", "")

	def test_servico_desconhecido_e_erro(self):
		with self.assertRaises(EsocialSoapInvalido):
			montar_envelope("servicoInventado", "<a/>")

	@unittest.skipUnless(TEM_LXML, "requer lxml, disponível no bench")
	def test_envelope_e_xml_bem_formado(self):
		envelope = montar_envelope("enviarLoteEventos", "<eSocial>conteudo</eSocial>")

		etree.fromstring(envelope.encode("utf-8"))  # não deve lançar


@unittest.skipUnless(TEM_LXML, "requer lxml, disponível no bench")
class TestExtrairResultado(unittest.TestCase):
	def test_extrai_o_conteudo_do_elemento_de_resposta(self):
		resposta = (
			'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
			"<soap:Body>"
			'<EnviarLoteEventosResponse xmlns="http://www.esocial.gov.br/servicos/'
			'empregador/lote/eventos/envio/v1_1_0">'
			"<EnviarLoteEventosResult>"
			'<eSocial xmlns="http://www.esocial.gov.br/schema/lote/eventos/envio/retornoLote/v1_1_0">'
			"<retornoEnvioLoteEventos><status><cdResposta>201</cdResposta></status></retornoEnvioLoteEventos>"
			"</eSocial>"
			"</EnviarLoteEventosResult>"
			"</EnviarLoteEventosResponse>"
			"</soap:Body>"
			"</soap:Envelope>"
		)

		resultado = extrair_resultado(resposta)

		self.assertIn("<retornoEnvioLoteEventos>", resultado)
		self.assertIn("<cdResposta>201</cdResposta>", resultado)

	def test_body_vazio_e_erro(self):
		resposta = (
			'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
			"<soap:Body></soap:Body>"
			"</soap:Envelope>"
		)

		with self.assertRaises(EsocialSoapInvalido):
			extrair_resultado(resposta)

	def test_xml_invalido_e_erro(self):
		with self.assertRaises(EsocialSoapInvalido):
			extrair_resultado("isto não é XML")

	def test_sem_body_e_erro(self):
		resposta = '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"></soap:Envelope>'

		with self.assertRaises(EsocialSoapInvalido):
			extrair_resultado(resposta)


if __name__ == "__main__":
	unittest.main()
