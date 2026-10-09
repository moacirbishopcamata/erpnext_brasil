# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Evento do CT-e (cancelamento e CC-e) de ponta a ponta, sem rede — tarefa 3.4.

Três camadas, todas puras: o envelope SOAP (`soap_cte.montar_envelope_evento`), a leitura do
`retEventoCTe` (`resposta_cte.interpretar_retorno_evento_cte`) e o envio com sessão falsa
(`integracao/eventos_sefaz_cte.py`). A estrutura da resposta vem de `TRetEvento`
(`eventoCTeTiposBasico_v4.00.xsd`); os `cStat` de registro (135/136, e 155 no cancelamento) vêm de
`sped-cte` (`Complements::addEventoCTeProtocol`) — fonte secundária, não o MOC.

Teste-âncora: `test_a_chave_devolvida_precisa_ser_a_do_evento` — o protocolo de um evento ligado a
**outro** CT-e nunca pode ser gravado neste.
"""

import unittest

from erpnext_brasil.fiscal.documento.autorizadores_cte import AutorizadorDesconhecido
from erpnext_brasil.fiscal.documento.evento_cte import (
	CorrecaoCte,
	montar_evento_cancelamento_cte,
	montar_evento_correcao_cte,
)
from erpnext_brasil.fiscal.documento.resposta_cte import (
	REGISTRADOS,
	REGISTRADOS_CANCELAMENTO,
	RetornoCteInvalido,
	interpretar_retorno_evento_cte,
)
from erpnext_brasil.fiscal.documento.soap import EnvelopeSoapInvalido
from erpnext_brasil.fiscal.documento.soap_cte import content_type_evento, montar_envelope_evento
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel
from erpnext_brasil.integracao.eventos_sefaz_cte import enviar_evento_cte
from erpnext_brasil.tests.test_autorizacao_sefaz_cte import CHAVE, SessaoFalsa, _contexto
from erpnext_brasil.tests.test_evento_cte import AssinadorFalso
from erpnext_brasil.tests.test_resposta_cte import NS

CNPJ = "11222333000181"
PROTOCOLO = "311260000099999"


def _ret_evento(cstat="135", motivo="Evento registrado e vinculado a CT-e", tipo="110111", chave=CHAVE):
	return (
		f'<retEventoCTe xmlns="{NS}" versao="4.00"><infEvento Id="ID123456789012345">'
		"<tpAmb>2</tpAmb><verAplic>RS20260101</verAplic><cOrgao>11</cOrgao>"
		f"<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo><chCTe>{chave}</chCTe>"
		f"<tpEvento>{tipo}</tpEvento><xEvento>Cancelamento</xEvento><nSeqEvento>1</nSeqEvento>"
		f"<dhRegEvento>2026-10-09T10:00:00-04:00</dhRegEvento><nProt>{PROTOCOLO}</nProt>"
		"</infEvento></retEventoCTe>"
	)


def _cancelamento(chave=CHAVE):
	return montar_evento_cancelamento_cte(
		chave_acesso=chave,
		protocolo="311260000012345",
		justificativa="Erro de digitação no valor da prestação de serviço.",
		cnpj_autor=CNPJ,
		data_evento="2026-10-09T10:00:00-04:00",
	)


def _enviar(sessao, evento=None, uf="RO"):
	return enviar_evento_cte(
		evento or _cancelamento(), _contexto(sessao, uf=uf), chave_acesso=CHAVE, assinador=AssinadorFalso()
	)


class TestEnvelope(unittest.TestCase):
	def test_o_corpo_vai_em_texto_sem_compactar(self):
		envelope = montar_envelope_evento("<eventoCTe>x</eventoCTe>", "11")

		self.assertIn("<eventoCTe>x</eventoCTe>", envelope)

	def test_vai_ao_namespace_do_evento_e_nao_ao_da_autorizacao(self):
		envelope = montar_envelope_evento("<eventoCTe/>", "11")

		self.assertIn("CTeRecepcaoEventoV4", envelope)
		self.assertNotIn("CTeRecepcaoSincV4", envelope)
		self.assertIn("<cUF>11</cUF>", envelope)

	def test_a_acao_soap_vai_no_content_type(self):
		self.assertIn(
			'action="http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEventoV4/cteRecepcaoEvento"',
			content_type_evento(),
		)

	def test_recusa_xml_vazio_e_cuf_invalido(self):
		with self.assertRaises(EnvelopeSoapInvalido):
			montar_envelope_evento("  ", "11")

		with self.assertRaises(EnvelopeSoapInvalido):
			montar_envelope_evento("<eventoCTe/>", "RO")


class TestRetorno(unittest.TestCase):
	def test_135_e_136_registram_qualquer_evento(self):
		self.assertEqual(REGISTRADOS, {"135", "136"})

		for cstat in ("135", "136"):
			with self.subTest(cstat=cstat):
				self.assertTrue(interpretar_retorno_evento_cte(_ret_evento(cstat, tipo="110110")).registrado)

	def test_155_so_vale_para_o_cancelamento(self):
		self.assertIn("155", REGISTRADOS_CANCELAMENTO)
		self.assertTrue(interpretar_retorno_evento_cte(_ret_evento("155", tipo="110111")).registrado)
		self.assertFalse(interpretar_retorno_evento_cte(_ret_evento("155", tipo="110110")).registrado)

	def test_rejeicao_nao_e_registro(self):
		retorno = interpretar_retorno_evento_cte(_ret_evento("494", "Rejeição: chave inexistente"))

		self.assertFalse(retorno.registrado)
		self.assertEqual(retorno.codigo, "494")

	def test_registrado_sem_protocolo_e_recusado(self):
		sem_protocolo = _ret_evento().replace(f"<nProt>{PROTOCOLO}</nProt>", "")

		with self.assertRaises(RetornoCteInvalido):
			interpretar_retorno_evento_cte(sem_protocolo)

	def test_resposta_que_nao_e_retEventoCTe_e_recusada(self):
		for lixo in ("<naoeum/>", "isto não é xml", f'<retCTe xmlns="{NS}"><cStat>100</cStat></retCTe>'):
			with self.subTest(lixo=lixo[:20]), self.assertRaises(RetornoCteInvalido):
				interpretar_retorno_evento_cte(lixo)

	def test_le_dentro_do_envelope_soap(self):
		envolvido = (
			'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"><soap:Body>'
			f"{_ret_evento()}</soap:Body></soap:Envelope>"
		)

		self.assertEqual(interpretar_retorno_evento_cte(envolvido).protocolo, PROTOCOLO)


class TestEnvio(unittest.TestCase):
	def test_registrado_devolve_a_autorizacao_com_o_protocolo_do_evento(self):
		resposta = _enviar(SessaoFalsa(_ret_evento()))

		self.assertTrue(resposta.autorizada)
		self.assertEqual(resposta.autorizacao.protocolo, PROTOCOLO)
		self.assertEqual(resposta.autorizacao.chave_acesso, CHAVE)
		self.assertEqual(resposta.bruto["cStat"], "135")

	def test_uma_requisicao_ao_servico_de_evento_e_nao_ao_de_autorizacao(self):
		sessao = SessaoFalsa(_ret_evento())

		_enviar(sessao)

		self.assertEqual(len(sessao.chamadas), 1)
		self.assertIn("CTeRecepcaoEventoV4", sessao.chamadas[0]["url"])
		corpo = sessao.chamadas[0]["data"].decode("utf-8")
		self.assertIn("eventoCTe", corpo)
		self.assertIn("Signature", corpo, "o evento tem de ir assinado")

	def test_rejeitado_nao_tem_autorizacao_e_guarda_o_motivo(self):
		resposta = _enviar(SessaoFalsa(_ret_evento("494", "Rejeição: chave inexistente")))

		self.assertFalse(resposta.autorizada)
		self.assertEqual((resposta.codigo, resposta.mensagem), ("494", "Rejeição: chave inexistente"))

	def test_a_chave_devolvida_precisa_ser_a_do_evento(self):
		outra = CHAVE[:-1] + ("0" if CHAVE[-1] != "0" else "1")

		with self.assertRaises(TransporteIndisponivel):
			_enviar(SessaoFalsa(_ret_evento(chave=outra)))

	def test_uf_sem_endpoint_falha_alto(self):
		with self.assertRaises((TransporteIndisponivel, AutorizadorDesconhecido)):
			_enviar(SessaoFalsa(), uf="XX")

	def test_a_carta_de_correcao_passa_pelo_mesmo_caminho(self):
		carta = montar_evento_correcao_cte(
			chave_acesso=CHAVE,
			correcoes=[CorrecaoCte(grupo_alterado="ide", campo_alterado="natOp", valor_alterado="Frete")],
			cnpj_autor=CNPJ,
			data_evento="2026-10-09T10:00:00-04:00",
		)
		sessao = SessaoFalsa(_ret_evento("135", tipo="110110"))

		resposta = _enviar(sessao, carta)

		self.assertTrue(resposta.autorizada)
		self.assertIn("evCCeCTe", sessao.chamadas[0]["data"].decode("utf-8"))
