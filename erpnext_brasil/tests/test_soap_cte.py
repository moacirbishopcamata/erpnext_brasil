# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envelope SOAP da autorização síncrona do CT-e (`fiscal/documento/soap_cte.py`).

Tarefa 3.1 de `fechar-laco-cte-mdfe`. O envelope do CT-e **não é o da NF-e com outro nome**, e
cada diferença abaixo foi lida do `sped-cte` e do `sped-common` (código de produção que fala com
a SEFAZ), não suposta:

- o cabeçalho `cteCabecMsg` (`cUF` + `versaoDados`) **existe** no CT-e 4.00 — o `soap.py` da NF-e
  documenta que ele é obsoleto lá, e copiá-lo para cá omitiria um cabeçalho que o CT-e manda;
- o corpo é `cteDadosMsg` com o `CTe` **compactado em GZip e codificado em Base64**, não o XML
  em texto;
- a ação SOAP vai no `Content-Type` (`action="<namespace>/<método>"`).

Fonte secundária (a biblioteca), não o MOC — declarado como tal na docstring do módulo.
"""

import base64
import gzip
import unittest

from erpnext_brasil.fiscal.documento import soap_cte
from erpnext_brasil.fiscal.documento.soap import EnvelopeSoapInvalido

NS = "http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoSincV4"
XML = '<CTe xmlns="http://www.portalfiscal.inf.br/cte"><infCte Id="CTe1">Prestação</infCte></CTe>'


def _parse(envelope: str):
	from lxml import etree

	return etree.fromstring(envelope.encode("utf-8"))


def _tag(ns: str, nome: str) -> str:
	return f"{{{ns}}}{nome}"


SOAP12 = "http://www.w3.org/2003/05/soap-envelope"


class TestConstantesDoServico(unittest.TestCase):
	def test_o_namespace_segue_a_operacao_confirmada(self):
		self.assertEqual(soap_cte.NAMESPACE_AUTORIZACAO, NS)

	def test_a_acao_leva_o_metodo_e_vem_entre_aspas(self):
		self.assertEqual(soap_cte.ACAO_AUTORIZACAO, f'"{NS}/cteRecepcao"')

	def test_o_content_type_carrega_a_acao(self):
		self.assertEqual(
			soap_cte.content_type_autorizacao(),
			f'application/soap+xml; charset=utf-8; action="{NS}/cteRecepcao"',
		)

	def test_o_servico_e_a_chave_da_tabela_de_endpoints(self):
		"""`CteRecepcao` é o nome em `autorizadores_cte.ENDPOINTS`; a operação SOAP é outro nome."""
		from erpnext_brasil.fiscal.documento.autorizadores_cte import ENDPOINTS

		self.assertIn(soap_cte.SERVICO_AUTORIZACAO, ENDPOINTS["SVRS"])
		self.assertIn("CTeRecepcaoSincV4", ENDPOINTS["SVRS"][soap_cte.SERVICO_AUTORIZACAO])


class TestCompactacao(unittest.TestCase):
	def test_ida_e_volta_preserva_o_xml_com_acentos(self):
		compactado = soap_cte.compactar(XML)

		self.assertEqual(gzip.decompress(base64.b64decode(compactado)).decode("utf-8"), XML)

	def test_e_deterministica(self):
		"""`gzip` grava a hora no cabeçalho; sem fixá-la, o mesmo documento geraria corpos
		diferentes a cada chamada — ruim para teste e para diagnóstico."""
		self.assertEqual(soap_cte.compactar(XML), soap_cte.compactar(XML))

	def test_o_resultado_e_base64_puro_sem_quebra_de_linha(self):
		self.assertNotIn("\n", soap_cte.compactar(XML * 50))


class TestEnvelope(unittest.TestCase):
	def setUp(self):
		self.envelope = soap_cte.montar_envelope_autorizacao(XML, "11")
		self.raiz = _parse(self.envelope)

	def test_e_soap_1_2(self):
		self.assertEqual(self.raiz.tag, _tag(SOAP12, "Envelope"))

	def test_o_cabecalho_cte_cabec_msg_existe_com_cuf_e_versao(self):
		cabecalho = self.raiz.find(_tag(SOAP12, "Header")).find(_tag(NS, "cteCabecMsg"))

		self.assertIsNotNone(cabecalho, "o CT-e 4.00 manda cteCabecMsg — a NF-e não")
		self.assertEqual(cabecalho.find(_tag(NS, "cUF")).text, "11")
		self.assertEqual(cabecalho.find(_tag(NS, "versaoDados")).text, "4.00")

	def test_o_cabecalho_vem_antes_do_corpo(self):
		filhos = [f.tag for f in self.raiz]

		self.assertEqual(filhos, [_tag(SOAP12, "Header"), _tag(SOAP12, "Body")])

	def test_o_corpo_e_cte_dados_msg_no_namespace_da_operacao(self):
		dados = self.raiz.find(_tag(SOAP12, "Body")).find(_tag(NS, "cteDadosMsg"))

		self.assertIsNotNone(dados)
		self.assertEqual(gzip.decompress(base64.b64decode(dados.text)).decode("utf-8"), XML)

	def test_nao_usa_nada_do_envelope_da_nfe(self):
		for proibido in ("nfeDadosMsg", "nfeCabecMsg", "enviCTe", "indSinc"):
			with self.subTest(proibido=proibido):
				self.assertNotIn(proibido, self.envelope)

	def test_o_xml_nao_aparece_em_texto_no_corpo(self):
		"""Compactado de verdade: o XML cru no envelope seria o formato da NF-e."""
		self.assertNotIn("<infCte", self.envelope)


class TestRecusas(unittest.TestCase):
	def test_xml_vazio_recusa(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			soap_cte.montar_envelope_autorizacao("   ", "11")

	def test_cuf_precisa_ter_dois_digitos(self):
		for cuf in ("", "1", "RO", "111", "1 "):
			with self.subTest(cuf=cuf), self.assertRaises(EnvelopeSoapInvalido):
				soap_cte.montar_envelope_autorizacao(XML, cuf)


if __name__ == "__main__":
	unittest.main()
