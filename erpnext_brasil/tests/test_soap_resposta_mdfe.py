# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envelopes SOAP e leitura das respostas do MDF-e (lote, recibo e evento).

As respostas são montadas **na ordem dos XSD** (`retEnviMDFe`, `retConsReciMDFe`, `TProtMDFe`,
`retEventoMDFe`) — a estrutura vem do esquema; os códigos, de fonte secundária (ver
`fiscal/documento/resposta_mdfe.py`). Nada aqui foi enviado a uma SEFAZ.
"""

import unittest
from datetime import datetime

from lxml import etree

from erpnext_brasil.fiscal.documento.resposta_mdfe import (
	RespostaMdfeInvalida,
	interpretar_recibo_lote,
	interpretar_retorno_evento_mdfe,
	interpretar_retorno_lote,
)
from erpnext_brasil.fiscal.documento.soap import EnvelopeSoapInvalido
from erpnext_brasil.fiscal.documento.soap_mdfe import (
	SERVICO_EVENTO,
	SERVICO_LOTE,
	SERVICO_RECIBO,
	content_type,
	montar_consulta_recibo,
	montar_envelope,
	montar_lote,
)

NS = "http://www.portalfiscal.inf.br/mdfe"
CHAVE = "5" + "3" * 43
MDFE = f'<?xml version="1.0"?><MDFe xmlns="{NS}"><infMDFe Id="MDFe{CHAVE}"/></MDFe>'


def _envelopado(corpo: str) -> str:
	return (
		'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"><soap:Body>'
		f'<mdfeResultMsg xmlns="{NS}/wsdl/X">{corpo}</mdfeResultMsg></soap:Body></soap:Envelope>'
	)


def _recibo(cstat="103", motivo="Lote recebido com sucesso", rec="351000000123456"):
	inf = f"<infRec><nRec>{rec}</nRec><dhRecbto>2026-10-10T10:00:00-03:00</dhRecbto><tMed>1</tMed></infRec>"

	return (
		f'<retEnviMDFe xmlns="{NS}" versao="3.00"><tpAmb>2</tpAmb><cUF>35</cUF><verAplic>X</verAplic>'
		f"<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>{inf if rec else ''}</retEnviMDFe>"
	)


def _lote(cstat_lote="104", prot=None):
	corpo = (
		f'<retConsReciMDFe xmlns="{NS}" versao="3.00"><tpAmb>2</tpAmb><verAplic>X</verAplic>'
		f"<nRec>351000000123456</nRec><cStat>{cstat_lote}</cStat><xMotivo>Lote</xMotivo><cUF>35</cUF>"
	)

	if prot:
		cstat, nprot = prot
		corpo += (
			'<protMDFe versao="3.00"><infProt><tpAmb>2</tpAmb><verAplic>X</verAplic>'
			f"<chMDFe>{CHAVE}</chMDFe><dhRecbto>2026-10-10T10:00:05-03:00</dhRecbto>"
			f"{f'<nProt>{nprot}</nProt>' if nprot else ''}"
			f"<cStat>{cstat}</cStat><xMotivo>Autorizado o uso do MDF-e</xMotivo></infProt></protMDFe>"
		)

	return corpo + "</retConsReciMDFe>"


def _evento(cstat="135", prot="135000000000001"):
	return (
		f'<retEventoMDFe xmlns="{NS}" versao="3.00"><infEvento><tpAmb>2</tpAmb><verAplic>X</verAplic>'
		f"<cOrgao>35</cOrgao><cStat>{cstat}</cStat><xMotivo>Evento registrado</xMotivo>"
		f"<chMDFe>{CHAVE}</chMDFe><tpEvento>110112</tpEvento><xEvento>Encerramento</xEvento>"
		f"<nSeqEvento>1</nSeqEvento><dhRegEvento>2026-10-10T11:00:00-03:00</dhRegEvento>"
		f"{f'<nProt>{prot}</nProt>' if prot else ''}</infEvento></retEventoMDFe>"
	)


class TestEnvelope(unittest.TestCase):
	def test_o_envelope_tem_cabecalho_e_corpo_do_servico(self):
		xml = montar_envelope(SERVICO_LOTE, "<enviMDFe/>", "35")
		raiz = etree.fromstring(xml.encode())
		namespace = f"{NS}/wsdl/MDFeRecepcao"

		self.assertEqual(raiz.find(f".//{{{namespace}}}cUF").text, "35")
		self.assertEqual(raiz.find(f".//{{{namespace}}}versaoDados").text, "3.00")
		self.assertIsNotNone(raiz.find(f".//{{{namespace}}}mdfeDadosMsg"))

	def test_a_acao_soap_vai_no_content_type_com_o_metodo_de_cada_servico(self):
		self.assertIn(
			'action="http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeRecepcao/mdfeRecepcaoLote"',
			content_type(SERVICO_LOTE),
		)
		self.assertIn("/MDFeRetRecepcao/mdfeRetRecepcao", content_type(SERVICO_RECIBO))
		self.assertIn("/MDFeRecepcaoEvento/mdfeRecepcaoEvento", content_type(SERVICO_EVENTO))

	def test_servico_desconhecido_e_recusado(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			content_type("MDFeConsulta")

	def test_uf_e_xml_vazio_sao_recusados(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			montar_envelope(SERVICO_LOTE, "<x/>", "3")

		with self.assertRaises(EnvelopeSoapInvalido):
			montar_envelope(SERVICO_LOTE, "  ", "35")

	def test_o_corpo_do_evento_vai_em_texto_sem_compressao(self):
		xml = montar_envelope(SERVICO_EVENTO, "<eventoMDFe/>", "35")

		self.assertIn("<eventoMDFe/>", xml)


class TestLote(unittest.TestCase):
	def test_o_lote_leva_o_idlote_antes_do_mdfe_e_sem_declaracao_xml(self):
		lote = montar_lote(MDFE, "123")
		raiz = etree.fromstring(lote.encode())

		self.assertEqual([etree.QName(f).localname for f in raiz], ["idLote", "MDFe"])
		self.assertNotIn("<?xml", lote)

	def test_o_mdfe_assinado_entra_sem_ser_remontado(self):
		self.assertIn(f'<infMDFe Id="MDFe{CHAVE}"/>', montar_lote(MDFE, "1"))

	def test_idlote_invalido_e_recusado(self):
		for invalido in ("", "abc", "1" * 16):
			with self.subTest(id_lote=invalido), self.assertRaises(EnvelopeSoapInvalido):
				montar_lote(MDFE, invalido)

	def test_consulta_do_recibo_na_ordem_do_xsd(self):
		raiz = etree.fromstring(montar_consulta_recibo("351000000123456", "2").encode())

		self.assertEqual([etree.QName(f).localname for f in raiz], ["tpAmb", "nRec"])

	def test_consulta_recusa_recibo_nao_numerico_e_ambiente_invalido(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			montar_consulta_recibo("x", "2")

		with self.assertRaises(EnvelopeSoapInvalido):
			montar_consulta_recibo("1", "3")


class TestReciboDoLote(unittest.TestCase):
	def test_lote_recebido_traz_o_recibo(self):
		r = interpretar_recibo_lote(_envelopado(_recibo()))

		self.assertTrue(r.recebido)
		self.assertEqual((r.recibo, r.tempo_medio_s), ("351000000123456", 1))

	def test_lote_recusado_nao_tem_recibo(self):
		r = interpretar_recibo_lote(_recibo("225", "Falha no Schema XML", rec=""))

		self.assertFalse(r.recebido)
		self.assertEqual((r.codigo, r.recibo), ("225", ""))

	def test_lote_recebido_sem_recibo_e_recusado(self):
		with self.assertRaises(RespostaMdfeInvalida):
			interpretar_recibo_lote(_recibo("103", rec=""))

	def test_resposta_que_nao_e_o_retorno_do_lote(self):
		with self.assertRaises(RespostaMdfeInvalida):
			interpretar_recibo_lote(_lote())

		with self.assertRaises(RespostaMdfeInvalida):
			interpretar_recibo_lote("<html>502</html>")


class TestResultadoDoLote(unittest.TestCase):
	def test_autorizado_traz_protocolo_chave_e_data(self):
		r = interpretar_retorno_lote(_envelopado(_lote(prot=("100", "135000000000001"))))

		self.assertTrue(r.autorizado)
		self.assertEqual((r.protocolo, r.chave), ("135000000000001", CHAVE))
		self.assertEqual(r.recebido_em, datetime.fromisoformat("2026-10-10T10:00:05-03:00"))

	def test_em_processamento_e_pendencia(self):
		r = interpretar_retorno_lote(_lote("105"))

		self.assertTrue(r.pendente)
		self.assertFalse(r.autorizado)

	def test_o_cstat_do_documento_decide_sobre_o_do_lote(self):
		r = interpretar_retorno_lote(_lote("104", prot=("539", None)))

		self.assertEqual(r.codigo, "539")
		self.assertFalse(r.autorizado)
		self.assertFalse(r.pendente)

	def test_lote_nao_localizado_nao_e_autorizado_nem_pendente(self):
		r = interpretar_retorno_lote(_lote("106"))

		self.assertEqual(r.codigo, "106")
		self.assertFalse(r.autorizado or r.pendente)

	def test_autorizado_sem_protocolo_e_recusado(self):
		with self.assertRaises(RespostaMdfeInvalida):
			interpretar_retorno_lote(_lote(prot=("100", None)))

	def test_so_o_cstat_100_autoriza(self):
		"""Sem tabela confirmada de "autorizado fora do prazo" ou denegado do MDF-e, nada além do 100."""
		for codigo in ("101", "110", "150", "205", "301"):
			with self.subTest(cstat=codigo):
				self.assertFalse(interpretar_retorno_lote(_lote(prot=(codigo, "1"))).autorizado)

	def test_data_invalida_e_recusada(self):
		xml = _lote(prot=("100", "1")).replace("2026-10-10T10:00:05-03:00", "ontem")

		with self.assertRaises(RespostaMdfeInvalida):
			interpretar_retorno_lote(xml)


class TestRetornoDoEvento(unittest.TestCase):
	def test_evento_registrado(self):
		r = interpretar_retorno_evento_mdfe(_envelopado(_evento()))

		self.assertTrue(r.registrado)
		self.assertEqual((r.tipo_evento, r.chave, r.protocolo), ("110112", CHAVE, "135000000000001"))

	def test_so_o_135_registra(self):
		for codigo in ("136", "155", "573"):
			with self.subTest(cstat=codigo):
				self.assertFalse(interpretar_retorno_evento_mdfe(_evento(codigo)).registrado)

	def test_registrado_sem_protocolo_e_recusado(self):
		with self.assertRaises(RespostaMdfeInvalida):
			interpretar_retorno_evento_mdfe(_evento("135", prot=None))

	def test_resposta_que_nao_e_de_evento(self):
		with self.assertRaises(RespostaMdfeInvalida):
			interpretar_retorno_evento_mdfe(_lote())


if __name__ == "__main__":
	unittest.main()
