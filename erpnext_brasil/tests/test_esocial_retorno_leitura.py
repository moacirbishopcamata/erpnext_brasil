# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_retorno_leitura.py` — XML de verdade → tipos de `esocial_retorno.py`."""

import unittest

from erpnext_brasil.folha.esocial_retorno import EsocialRetornoInvalido
from erpnext_brasil.folha.esocial_retorno_leitura import (
	ler_retorno_envio_lote,
	ler_retorno_processamento_lote,
)


def _retorno_envio(cd_resposta=201, desc="Lote recebido com sucesso", protocolo="1.1.0000000000000000001"):
	return (
		'<eSocial xmlns="http://www.esocial.gov.br/schema/lote/eventos/envio/retornoEnvio/v1_1_0">'
		"<retornoEnvioLoteEventos>"
		f"<status><cdResposta>{cd_resposta}</cdResposta><descResposta>{desc}</descResposta></status>"
		"<dadosRecepcaoLote>"
		"<dhRecepcao>2026-09-02T10:00:00-03:00</dhRecepcao>"
		"<versaoAplicativoRecepcao>1.0</versaoAplicativoRecepcao>"
		f"<protocoloEnvio>{protocolo}</protocoloEnvio>"
		"</dadosRecepcaoLote>"
		"</retornoEnvioLoteEventos>"
		"</eSocial>"
	)


class TestLerRetornoEnvioLote(unittest.TestCase):
	def test_sucesso_com_dados_de_recepcao(self):
		resultado = ler_retorno_envio_lote(_retorno_envio())

		self.assertTrue(resultado.status.sucesso)
		self.assertEqual(resultado.dados_recepcao.protocolo_envio, "1.1.0000000000000000001")

	def test_pendente_cd_resposta_203(self):
		resultado = ler_retorno_envio_lote(_retorno_envio(cd_resposta=203, desc="Lote em processamento"))

		self.assertTrue(resultado.status.pendente)

	def test_com_ocorrencias(self):
		xml = (
			'<eSocial xmlns="x"><retornoEnvioLoteEventos>'
			"<status><cdResposta>401</cdResposta><descResposta>Erro de preenchimento</descResposta>"
			"<ocorrencias><ocorrencia><codigo>10</codigo><descricao>Campo inválido</descricao>"
			"<tipo>1</tipo><localizacao>/evtRemun/ideEvento</localizacao></ocorrencia></ocorrencias>"
			"</status></retornoEnvioLoteEventos></eSocial>"
		)

		resultado = ler_retorno_envio_lote(xml)

		self.assertEqual(len(resultado.status.ocorrencias), 1)
		self.assertTrue(resultado.status.tem_erro)
		self.assertEqual(resultado.status.ocorrencias[0].localizacao, "/evtRemun/ideEvento")

	def test_sem_dados_recepcao_quando_ausente(self):
		xml = (
			'<eSocial xmlns="x"><retornoEnvioLoteEventos>'
			"<status><cdResposta>401</cdResposta><descResposta>Erro</descResposta></status>"
			"</retornoEnvioLoteEventos></eSocial>"
		)

		resultado = ler_retorno_envio_lote(xml)

		self.assertIsNone(resultado.dados_recepcao)

	def test_xml_invalido_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			ler_retorno_envio_lote("não é xml")

	def test_sem_status_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			ler_retorno_envio_lote('<eSocial xmlns="x"><retornoEnvioLoteEventos/></eSocial>')


class TestLerRetornoProcessamentoLote(unittest.TestCase):
	def _xml(self, cd_resposta=201, eventos_xml=""):
		return (
			'<eSocial xmlns="x"><retornoProcessamentoLoteEventos>'
			f"<status><cdResposta>{cd_resposta}</cdResposta><descResposta>Processado</descResposta></status>"
			"<dadosRecepcaoLote><protocoloEnvio>1.1.0000000000000000001</protocoloEnvio></dadosRecepcaoLote>"
			f"<retornoEventos>{eventos_xml}</retornoEventos>"
			"</retornoProcessamentoLoteEventos></eSocial>"
		)

	def test_sem_eventos(self):
		resultado = ler_retorno_processamento_lote(self._xml())

		self.assertEqual(resultado.eventos, ())
		self.assertTrue(resultado.status.sucesso)

	def test_um_evento_processado_com_sucesso(self):
		evento_xml = (
			'<evento Id="ID1234567890"><retornoEvento>'
			'<eSocial xmlns="y"><evtRecibo><reciboEvento>x</reciboEvento></evtRecibo></eSocial>'
			"</retornoEvento></evento>"
		)

		resultado = ler_retorno_processamento_lote(self._xml(eventos_xml=evento_xml))

		self.assertEqual(len(resultado.eventos), 1)
		self.assertEqual(resultado.eventos[0].id_evento, "ID1234567890")
		self.assertFalse(resultado.eventos[0].evento_duplicado)
		self.assertIn("evtRecibo", resultado.eventos[0].xml_retorno)

	def test_evento_duplicado(self):
		evento_xml = (
			'<evento Id="ID1" evtDupl="true"><retornoEvento>'
			'<eSocial xmlns="y"><ok/></eSocial>'
			"</retornoEvento></evento>"
		)

		resultado = ler_retorno_processamento_lote(self._xml(eventos_xml=evento_xml))

		self.assertTrue(resultado.eventos[0].evento_duplicado)

	def test_sem_status_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			ler_retorno_processamento_lote('<eSocial xmlns="x"><retornoProcessamentoLoteEventos/></eSocial>')


if __name__ == "__main__":
	unittest.main()
