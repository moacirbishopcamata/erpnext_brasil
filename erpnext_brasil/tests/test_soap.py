# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do envelope SOAP 1.2 dos webservices da NF-e.

`test_sem_header_nfecabecmsg` guarda a decisão mais frágil deste módulo: duas fontes
divergiam sobre precisar de `nfeCabecMsg` no `soap12:Header`, e só o comentário datado
no código-fonte da biblioteca de referência resolveu (obsoleto desde 11/2017). Se
alguém reintroduzir o header lendo um blog desatualizado, este teste acusa.

Os testes de `extrair_resultado` dependem de `lxml` (não é dependência de `fiscal/`
diretamente, mas da função) — pulados quando a biblioteca não está instalada, como no
ambiente puro desta suíte fora do bench.
"""

import unittest

try:
	import lxml  # noqa: F401

	TEM_LXML = True
except ImportError:
	TEM_LXML = False

from erpnext_brasil.fiscal.documento.soap import (
	NAMESPACE_SOAP12,
	EnvelopeSoapInvalido,
	montar_envelope,
	namespace_operacao,
)


class TestNamespaceDaOperacao(unittest.TestCase):
	def test_autorizacao(self):
		self.assertEqual(
			namespace_operacao("NFeAutorizacao"),
			"http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4",
		)

	def test_usa_a_operacao_confirmada_nao_o_nome_da_tabela(self):
		"""Na tabela de endpoints o serviço é `NfeConsultaProtocolo` (f minúsculo); a
		operação SOAP é `NFeConsultaProtocolo4` — maiúscula e com sufixo."""
		self.assertEqual(
			namespace_operacao("NfeConsultaProtocolo"),
			"http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4",
		)

	def test_recepcao_evento(self):
		self.assertEqual(
			namespace_operacao("RecepcaoEvento"),
			"http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4",
		)

	def test_servico_desconhecido_e_erro(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			namespace_operacao("ServicoQueNaoExiste")


class TestMontarEnvelope(unittest.TestCase):
	def setUp(self):
		self.envelope = montar_envelope("NfeStatusServico", "<consStatServ>x</consStatServ>")

	def test_sem_header_nfecabecmsg(self):
		"""nfeCabecMsg é obsoleto desde 11/2017 (layout 4.00). Reintroduzi-lo quebra a
		comunicação, segundo a própria biblioteca que o documentava."""
		self.assertNotIn("nfeCabecMsg", self.envelope)
		self.assertNotIn("Header", self.envelope)

	def test_estrutura_soap12(self):
		self.assertIn("soap12:Envelope", self.envelope)
		self.assertIn("soap12:Body", self.envelope)
		self.assertIn(f'xmlns:soap12="{NAMESPACE_SOAP12}"', self.envelope)

	def test_nfedadosmsg_com_namespace_do_servico(self):
		self.assertIn(
			'<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4">',
			self.envelope,
		)

	def test_xml_interno_preservado_ao_pe_da_letra(self):
		"""O XML já assinado não pode ser remontado aqui — só envelopado como veio."""
		self.assertIn("<consStatServ>x</consStatServ>", self.envelope)

	def test_xml_vazio_e_erro(self):
		for vazio in ("", "   "):
			with self.subTest(valor=vazio):
				with self.assertRaises(EnvelopeSoapInvalido):
					montar_envelope("NfeStatusServico", vazio)

	def test_servico_sem_operacao_e_erro(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			montar_envelope("Inexistente", "<x/>")


@unittest.skipUnless(TEM_LXML, "requer lxml, disponível apenas no bench")
class TestExtrairResultado(unittest.TestCase):
	def setUp(self):
		from erpnext_brasil.fiscal.documento.soap import extrair_resultado

		self.extrair = extrair_resultado

	def _envelope_resposta(self, elemento_result: str, conteudo: str) -> str:
		return (
			'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
			f"<soap:Body><{elemento_result}>{conteudo}</{elemento_result}></soap:Body>"
			"</soap:Envelope>"
		)

	def test_extrai_o_xml_de_dentro_do_wrapper_result(self):
		resposta = self._envelope_resposta(
			"nfeStatusServicoNFResult", "<retConsStatServ><cStat>107</cStat></retConsStatServ>"
		)

		self.assertEqual(self.extrair(resposta), "<retConsStatServ><cStat>107</cStat></retConsStatServ>")

	def test_nome_do_wrapper_varia_por_servico_e_nao_importa(self):
		"""O elemento *Result muda de nome por serviço; a extração não fixa um nome."""
		resposta = self._envelope_resposta(
			"nfeAutorizacaoLoteResult", "<retEnviNFe><cStat>103</cStat></retEnviNFe>"
		)

		self.assertIn("<retEnviNFe>", self.extrair(resposta))

	def test_aceita_bytes(self):
		resposta = self._envelope_resposta("xResult", "<a>1</a>").encode("utf-8")

		self.assertEqual(self.extrair(resposta), "<a>1</a>")

	def test_elemento_aninhado_de_mesmo_nome_nao_confunde_a_extracao(self):
		"""O motivo real para não usar regex: <a><a>interno</a></a> quebraria um `\\1`."""
		resposta = self._envelope_resposta("aResult", "<a><a>interno</a></a>")

		self.assertEqual(self.extrair(resposta), "<a><a>interno</a></a>")

	def test_xml_invalido_e_erro_claro(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			self.extrair("isto nao e xml")

	def test_sem_body_e_erro(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			self.extrair('<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"/>')

	def test_body_vazio_e_erro(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			self.extrair(
				'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
				"<soap:Body/></soap:Envelope>"
			)

	def test_result_so_com_texto_devolve_o_texto(self):
		resposta = self._envelope_resposta("xResult", "apenas texto")

		self.assertEqual(self.extrair(resposta), "apenas texto")


if __name__ == "__main__":
	unittest.main()
