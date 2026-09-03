# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_lote.py` — envelope de lote de eventos e endpoints."""

import unittest

from erpnext_brasil.folha.esocial_lote import (
	AMBIENTE_PRODUCAO,
	AMBIENTE_PRODUCAO_RESTRITA,
	LIMITE_MAXIMO_EVENTOS_POR_LOTE,
	EsocialLoteInvalido,
	EventoLote,
	IdeEmpregadorLote,
	IdeTransmissorLote,
	LoteEventos,
	endpoint,
	montar_xml_lote,
)


class TestEndpoint(unittest.TestCase):
	def test_enviar_producao(self):
		url = endpoint("enviarLoteEventos", AMBIENTE_PRODUCAO)

		self.assertTrue(url.startswith("https://webservices.envio.esocial.gov.br"))

	def test_enviar_producao_restrita(self):
		url = endpoint("enviarLoteEventos", AMBIENTE_PRODUCAO_RESTRITA)

		self.assertTrue(url.startswith("https://webservices.producaorestrita.esocial.gov.br"))

	def test_consultar_producao(self):
		url = endpoint("consultarLoteEventos", AMBIENTE_PRODUCAO)

		self.assertTrue(url.startswith("https://webservices.consulta.esocial.gov.br"))

	def test_consultar_producao_restrita(self):
		url = endpoint("consultarLoteEventos", AMBIENTE_PRODUCAO_RESTRITA)

		self.assertTrue(url.startswith("https://webservices.producaorestrita.esocial.gov.br"))

	def test_servico_desconhecido_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			endpoint("servicoInventado", AMBIENTE_PRODUCAO)

	def test_producao_e_producao_restrita_sao_urls_diferentes(self):
		for servico in ("enviarLoteEventos", "consultarLoteEventos"):
			with self.subTest(servico=servico):
				self.assertNotEqual(
					endpoint(servico, AMBIENTE_PRODUCAO), endpoint(servico, AMBIENTE_PRODUCAO_RESTRITA)
				)


class TestIdeEmpregadorLote(unittest.TestCase):
	def test_cnpj_valido(self):
		IdeEmpregadorLote(tp_insc=1, nr_insc="12345678000199")

	def test_cpf_valido(self):
		IdeEmpregadorLote(tp_insc=2, nr_insc="12345678901")

	def test_tp_insc_fora_do_enum_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			IdeEmpregadorLote(tp_insc=3, nr_insc="12345678000199")

	def test_nr_insc_invalido_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			IdeEmpregadorLote(tp_insc=1, nr_insc="123")


class TestIdeTransmissorLote(unittest.TestCase):
	def test_valido(self):
		IdeTransmissorLote(tp_insc=1, nr_insc="12345678000199")

	def test_tp_insc_fora_do_enum_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			IdeTransmissorLote(tp_insc=0, nr_insc="12345678000199")


class TestEventoLote(unittest.TestCase):
	def test_valido(self):
		EventoLote(id_evento="ID1234567890", xml_assinado="<evtRemun>...</evtRemun>")

	def test_id_vazio_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			EventoLote(id_evento="", xml_assinado="<evtRemun>...</evtRemun>")

	def test_xml_vazio_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			EventoLote(id_evento="ID1234567890", xml_assinado="")


class TestLoteEventos(unittest.TestCase):
	def _empregador(self):
		return IdeEmpregadorLote(tp_insc=1, nr_insc="12345678000199")

	def _transmissor(self):
		return IdeTransmissorLote(tp_insc=1, nr_insc="12345678000199")

	def _evento(self, n=1):
		return EventoLote(id_evento=f"ID{n}", xml_assinado=f"<evt>{n}</evt>")

	def test_lote_valido(self):
		LoteEventos(
			grupo=1,
			ide_empregador=self._empregador(),
			ide_transmissor=self._transmissor(),
			eventos=(self._evento(),),
		)

	def test_lote_sem_eventos_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			LoteEventos(
				grupo=1, ide_empregador=self._empregador(), ide_transmissor=self._transmissor(), eventos=()
			)

	def test_lote_com_mais_de_50_eventos_e_erro(self):
		eventos = tuple(self._evento(n) for n in range(LIMITE_MAXIMO_EVENTOS_POR_LOTE + 1))

		with self.assertRaises(EsocialLoteInvalido):
			LoteEventos(
				grupo=1,
				ide_empregador=self._empregador(),
				ide_transmissor=self._transmissor(),
				eventos=eventos,
			)

	def test_lote_com_exatamente_50_eventos_e_valido(self):
		eventos = tuple(self._evento(n) for n in range(LIMITE_MAXIMO_EVENTOS_POR_LOTE))

		LoteEventos(
			grupo=1, ide_empregador=self._empregador(), ide_transmissor=self._transmissor(), eventos=eventos
		)

	def test_grupo_negativo_e_erro(self):
		with self.assertRaises(EsocialLoteInvalido):
			LoteEventos(
				grupo=-1,
				ide_empregador=self._empregador(),
				ide_transmissor=self._transmissor(),
				eventos=(self._evento(),),
			)


class TestMontarXmlLote(unittest.TestCase):
	def _empregador(self):
		return IdeEmpregadorLote(tp_insc=1, nr_insc="12345678000199")

	def _transmissor(self):
		return IdeTransmissorLote(tp_insc=1, nr_insc="12345678000199")

	def test_estrutura_do_envelope(self):
		lote = LoteEventos(
			grupo=1,
			ide_empregador=self._empregador(),
			ide_transmissor=self._transmissor(),
			eventos=(EventoLote(id_evento="ID1", xml_assinado="<evtRemun>x</evtRemun>"),),
		)

		xml = montar_xml_lote(lote)

		self.assertIn('<envioLoteEventos grupo="1">', xml)
		self.assertIn("<ideEmpregador><tpInsc>1</tpInsc><nrInsc>12345678000199</nrInsc></ideEmpregador>", xml)
		self.assertIn('<evento Id="ID1"><evtRemun>x</evtRemun></evento>', xml)

	def test_varios_eventos_viram_irmaos(self):
		lote = LoteEventos(
			grupo=1,
			ide_empregador=self._empregador(),
			ide_transmissor=self._transmissor(),
			eventos=(
				EventoLote(id_evento="ID1", xml_assinado="<a/>"),
				EventoLote(id_evento="ID2", xml_assinado="<b/>"),
			),
		)

		xml = montar_xml_lote(lote)

		self.assertIn('<evento Id="ID1"><a/></evento><evento Id="ID2"><b/></evento>', xml)


if __name__ == "__main__":
	unittest.main()
