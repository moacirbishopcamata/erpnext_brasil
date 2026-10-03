# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio síncrono do CT-e (`integracao/autorizacao_sefaz_cte.py`) com sessão HTTP falsa.

Tarefa 3.1. O que se trava aqui é a **orquestração**, sem rede: uma única requisição (o CT-e 4.00
não tem lote nem recibo), ao serviço certo da UF, com o envelope do CT-e — e nunca ao
`NFeAutorizacao4`, que é o engano que o `design.md` (decisão 3) descreve como "o pior resultado
possível: mandar um CT-e para o serviço da NF-e".

Teste-âncora: `test_a_chave_autorizada_e_a_da_camada_pura`. A chave que a SEFAZ devolve em
`infProt/chCTe` precisa ser a do `Id` do documento enviado; se divergir, gravar a autorização
associaria o protocolo de **outro** CT-e a este.
"""

import base64
import gzip
import inspect
import unittest
from pathlib import Path
from unittest.mock import Mock

from erpnext_brasil.fiscal.cte_montagem import montar_cte_de_dados
from erpnext_brasil.fiscal.documento.autorizadores_cte import AutorizadorDesconhecido, endpoint
from erpnext_brasil.fiscal.documento.resposta_cte import RetornoCteInvalido
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.integracao import autorizacao_sefaz_cte
from erpnext_brasil.integracao.autorizacao_sefaz_cte import enviar_autorizacao_cte
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.tests.test_cte_montagem import _dados, _sorteio_fixo
from erpnext_brasil.tests.test_resposta_cte import NS, _prot, _ret

CTE, CHAVE = montar_cte_de_dados(_dados(), "42", sortear=_sorteio_fixo)


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


def _contexto(sessao, uf="RO", ambiente="homologacao") -> ContextoSefaz:
	return ContextoSefaz(
		uf=uf,
		ambiente=ambiente,
		sessao_http=sessao,
		arquivo_cert=Path("/tmp/cert.pem"),
		arquivo_chave=Path("/tmp/chave.pem"),
	)


def _autorizado(**mudancas) -> str:
	return _ret(**{"prot": _prot(chave=CHAVE), **mudancas})


class TestRequisicao(unittest.TestCase):
	def setUp(self):
		self.sessao = SessaoFalsa(_autorizado())
		enviar_autorizacao_cte(CTE, _contexto(self.sessao))
		self.chamada = self.sessao.chamadas[0]

	def test_uma_unica_requisicao_sem_lote_nem_recibo(self):
		self.assertEqual(len(self.sessao.chamadas), 1)

	def test_vai_ao_servico_de_recepcao_do_cte_da_uf(self):
		self.assertEqual(self.chamada["url"], endpoint("RO", "CteRecepcao", "homologacao"))
		self.assertIn("CTeRecepcaoSincV4", self.chamada["url"])

	def test_o_content_type_carrega_a_acao_soap(self):
		self.assertIn(
			'action="http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoSincV4/cteRecepcao"',
			self.chamada["headers"]["Content-Type"],
		)
		self.assertTrue(self.chamada["headers"]["Content-Type"].startswith("application/soap+xml"))

	def test_o_corpo_e_o_cte_compactado_com_cabecalho_do_cte(self):
		from lxml import etree

		raiz = etree.fromstring(self.chamada["data"])
		soap12 = "http://www.w3.org/2003/05/soap-envelope"
		wsdl = "http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoSincV4"
		dados = raiz.find(f"{{{soap12}}}Body/{{{wsdl}}}cteDadosMsg")
		cuf = raiz.find(f"{{{soap12}}}Header/{{{wsdl}}}cteCabecMsg/{{{wsdl}}}cUF")

		self.assertEqual(gzip.decompress(base64.b64decode(dados.text)).decode("utf-8"), para_xml(CTE))
		self.assertEqual(cuf.text, "11", "o cUF do cabeçalho é o da UF do emitente (RO = 11)")

	def test_nunca_usa_o_servico_da_nfe(self):
		corpo = self.chamada["data"].decode("utf-8")

		for proibido in ("NFeAutorizacao", "nfeDadosMsg", "NFeRetAutorizacao"):
			with self.subTest(proibido=proibido):
				self.assertNotIn(proibido, corpo + self.chamada["url"])

	def test_usa_o_certificado_do_contexto_e_um_prazo(self):
		self.assertEqual(self.chamada["cert"], (str(Path("/tmp/cert.pem")), str(Path("/tmp/chave.pem"))))
		self.assertGreater(self.chamada["timeout"], 0)

	def test_o_grupo_do_emitente_ro_e_o_svrs_e_o_url_e_o_dele(self):
		"""RO não tem webservice próprio de CT-e: cai no SVRS (ver `autorizadores_cte`)."""
		self.assertIn("svrs", self.chamada["url"].lower())


class TestRespostas(unittest.TestCase):
	def _enviar(self, resposta: str):
		return enviar_autorizacao_cte(CTE, _contexto(SessaoFalsa(resposta)))

	def test_a_chave_autorizada_e_a_da_camada_pura(self):
		"""Teste-âncora. A autorização devolve a chave do `Id` enviado, não outra qualquer."""
		resposta = self._enviar(_autorizado())

		self.assertTrue(resposta.autorizada)
		self.assertEqual(resposta.autorizacao.chave_acesso, CHAVE)
		self.assertEqual(CTE["CTe"]["infCte"]["@Id"], f"CTe{resposta.autorizacao.chave_acesso}")

	def test_autorizado_traz_protocolo_e_recebimento_com_fuso(self):
		autorizacao = self._enviar(_autorizado()).autorizacao

		self.assertEqual(autorizacao.protocolo, "311260000012345")
		self.assertIsNotNone(autorizacao.recebido_em.tzinfo)

	def test_150_autorizado_fora_do_prazo_autoriza(self):
		self.assertTrue(
			self._enviar(_ret("150", "fora do prazo", _prot("150", "fora do prazo", chave=CHAVE))).autorizada
		)

	def test_denegado_nao_e_autorizado(self):
		resposta = self._enviar(
			_ret("110", "Uso Denegado", _prot("110", "Uso Denegado", chave=CHAVE, protocolo=""))
		)

		self.assertTrue(resposta.denegado)
		self.assertFalse(resposta.autorizada)
		self.assertEqual(resposta.codigo, "110")

	def test_rejeicao_devolve_codigo_e_motivo_sem_autorizacao(self):
		resposta = self._enviar(_ret("539", "Rejeição: Duplicidade de CT-e"))

		self.assertFalse(resposta.autorizada)
		self.assertFalse(resposta.denegado)
		self.assertEqual((resposta.codigo, resposta.mensagem), ("539", "Rejeição: Duplicidade de CT-e"))

	def test_o_consumo_indevido_chega_como_codigo_656(self):
		"""É o que o registrador de `TransporteSefaz` lê para abrir a janela de bloqueio."""
		self.assertEqual(self._enviar(_ret("656", "Consumo Indevido")).codigo, "656")

	def test_chave_divergente_na_autorizacao_recusa(self):
		outra = _ret(prot=_prot(chave=CHAVE[:-1] + ("0" if CHAVE[-1] != "0" else "1")))

		with self.assertRaises(RetornoCteInvalido):
			self._enviar(outra)

	def test_resposta_que_nao_e_retcte_recusa(self):
		with self.assertRaises(RetornoCteInvalido):
			self._enviar("<qualquerCoisa/>")


class TestFalhas(unittest.TestCase):
	def test_erro_http_sobe_sem_virar_resposta(self):
		sessao = SessaoFalsa(_autorizado())
		resposta = Mock()
		resposta.raise_for_status = Mock(side_effect=RuntimeError("HTTP 500"))
		sessao.post = Mock(return_value=resposta)

		with self.assertRaises(RuntimeError):
			enviar_autorizacao_cte(CTE, _contexto(sessao))

	def test_uf_desconhecida_levanta_antes_de_qualquer_requisicao(self):
		sessao = SessaoFalsa(_autorizado())

		with self.assertRaises(AutorizadorDesconhecido):
			enviar_autorizacao_cte(CTE, _contexto(sessao, uf="XX"))

		self.assertEqual(sessao.chamadas, [])


class TestForma(unittest.TestCase):
	def test_nao_ha_polling_nem_dormir_porque_o_cte_e_sincrono(self):
		"""A tarefa 3.1 fala em `dormir` injetado; num serviço **síncrono** não há o que esperar, e
		um parâmetro que nunca é usado seria inventar uma espera que o leiaute não tem."""
		assinatura = inspect.signature(enviar_autorizacao_cte)

		self.assertEqual(list(assinatura.parameters), ["documento", "contexto"])

	def test_o_modulo_nao_importa_frappe(self):
		fonte = Path(autorizacao_sefaz_cte.__file__).read_text(encoding="utf-8")

		self.assertNotIn("import frappe", fonte)

	def test_o_namespace_do_retorno_e_o_do_cte(self):
		self.assertEqual(NS, "http://www.portalfiscal.inf.br/cte")


if __name__ == "__main__":
	unittest.main()
