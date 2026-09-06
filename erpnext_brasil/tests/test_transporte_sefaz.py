# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `TransporteSefaz` com sessão HTTP falsa — sem rede.

`SessaoFalsa` satisfaz só o que o adaptador usa (`.post`), e devolve respostas
pré-programadas por chamada — a mesma disciplina de duplo usada em toda a sessão para
portas (`RepositorioClassificacao`, `Assinador`).

O teste mais importante é `TestPolling`: prova que o adaptador de fato consulta de novo
quando o lote vem `pendente`, usando `dormir` falso para não esperar de verdade, e que
desiste depois do número de tentativas configurado em vez de entrar em loop infinito.
"""

import unittest
from unittest.mock import Mock

try:
	from cryptography import x509
	from cryptography.hazmat.primitives import hashes
	from cryptography.hazmat.primitives.asymmetric import rsa
	from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
	from cryptography.x509.oid import NameOID

	TEM_DEPENDENCIAS = True
except ImportError:
	TEM_DEPENDENCIAS = False

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.porta import RespostaTransmissao, ResultadoConsulta, TransporteFiscal

CHAVE_VALIDA = montar_chave("35", "2608", "11222333000181", "55", "1", "1", "1", "12345678")


def _gerar_pfx(senha: str = "teste123") -> bytes:
	from datetime import datetime, timedelta, timezone

	chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Teste")])
	agora = datetime.now(timezone.utc)

	certificado = (
		x509.CertificateBuilder()
		.subject_name(nome)
		.issuer_name(nome)
		.public_key(chave.public_key())
		.serial_number(x509.random_serial_number())
		.not_valid_before(agora - timedelta(days=1))
		.not_valid_after(agora + timedelta(days=365))
		.sign(chave, hashes.SHA256())
	)

	return pkcs12.serialize_key_and_certificates(
		b"t", chave, certificado, None, BestAvailableEncryption(senha.encode())
	)


def _resposta_soap(elemento_result: str, corpo_ret_envi: str) -> Mock:
	resposta = Mock()
	resposta.content = (
		'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
		f"<soap:Body><{elemento_result}>{corpo_ret_envi}</{elemento_result}></soap:Body>"
		"</soap:Envelope>"
	).encode()
	resposta.raise_for_status = Mock()

	return resposta


def _ret_envi_nfe(cstat="104", motivo="Lote processado", inf_prot="", nrec=""):
	extra = f"<nRec>{nrec}</nRec>" if nrec else ""

	return (
		'<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
		f"<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>{extra}{inf_prot}"
		"</retEnviNFe>"
	)


def _prot_nfe(cstat="100", motivo="Autorizado o uso da NF-e"):
	return (
		"<protNFe><infProt>"
		f"<chNFe>{'3' * 44}</chNFe><dhRecbto>2026-08-24T10:00:01-04:00</dhRecbto>"
		f"<nProt>135260000123456</nProt><cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>"
		"</infProt></protNFe>"
	)


DOCUMENTO_MINIMO = {"NFe": {"@xmlns": "x", "infNFe": {"@Id": "NFe1", "ide": {"mod": "55"}, "a": "1"}}}


class SessaoFalsa:
	"""Duplo de `requests.Session`: devolve as respostas programadas, em ordem."""

	def __init__(self, respostas: list[Mock]):
		self._respostas = list(respostas)
		self.chamadas: list[dict] = []

	def post(self, url, data, headers, cert, timeout):
		self.chamadas.append({"url": url, "data": data, "cert": cert, "timeout": timeout})

		return self._respostas.pop(0)


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography, disponível no bench")
class TestContratoDaPorta(unittest.TestCase):
	def test_satisfaz_transportefiscal(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([])
		) as transporte:
			self.assertIsInstance(transporte, TransporteFiscal)


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography, disponível no bench")
class TestArquivosTLS(unittest.TestCase):
	def test_escreve_e_remove_os_arquivos_temporarios(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([])
		) as transporte:
			self.assertTrue(transporte._tls.cert.exists())
			self.assertTrue(transporte._tls.chave.exists())
			caminho_cert = transporte._tls.cert

		self.assertFalse(caminho_cert.exists())

	def test_a_chave_e_o_certificado_somem_juntos(self):
		"""Estão no mesmo diretório temporário de propósito: dois `NamedTemporaryFile`
		soltos poderiam sobreviver um ao outro, e o que sobra é a chave privada."""
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([])
		) as transporte:
			cert, chave = transporte._tls.cert, transporte._tls.chave

			self.assertEqual(cert.parent, chave.parent)

		self.assertFalse(cert.exists())
		self.assertFalse(chave.exists())

	def test_requisicao_usa_os_arquivos_de_certificado(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[_resposta_soap("nfeAutorizacaoLoteResult", _ret_envi_nfe(inf_prot=_prot_nfe()))]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.transmitir(DOCUMENTO_MINIMO)

		cert_usado = sessao.chamadas[0]["cert"]
		self.assertTrue(cert_usado[0].endswith("cert.pem"))
		self.assertTrue(cert_usado[1].endswith("chave.pem"))


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography, disponível no bench")
class TestTransmitirAutorizado(unittest.TestCase):
	def test_lote_processado_e_nota_autorizada(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[_resposta_soap("nfeAutorizacaoLoteResult", _ret_envi_nfe(inf_prot=_prot_nfe()))]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			resultado = transporte.transmitir(DOCUMENTO_MINIMO)

		self.assertIsInstance(resultado, RespostaTransmissao)
		self.assertTrue(resultado.autorizada)
		self.assertEqual(resultado.autorizacao.protocolo, "135260000123456")

	def test_usa_o_endpoint_de_ro_svrs(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[_resposta_soap("nfeAutorizacaoLoteResult", _ret_envi_nfe(inf_prot=_prot_nfe()))]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.transmitir(DOCUMENTO_MINIMO)

		self.assertIn("svrs.rs.gov.br", sessao.chamadas[0]["url"])

	def test_uma_unica_chamada_quando_ja_vem_decidido(self):
		"""Sem pendência, não há por que consultar de novo."""
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[_resposta_soap("nfeAutorizacaoLoteResult", _ret_envi_nfe(inf_prot=_prot_nfe()))]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.transmitir(DOCUMENTO_MINIMO)

		self.assertEqual(len(sessao.chamadas), 1)


class TestTransmitirRejeitadoEDenegado(unittest.TestCase):
	@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography")
	def test_rejeitado(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[
				_resposta_soap(
					"nfeAutorizacaoLoteResult",
					_ret_envi_nfe(inf_prot=_prot_nfe(cstat="225", motivo="Falha no schema")),
				)
			]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			resultado = transporte.transmitir(DOCUMENTO_MINIMO)

		self.assertFalse(resultado.autorizada)
		self.assertFalse(resultado.denegado)
		self.assertEqual(resultado.mensagem, "Falha no schema")

	@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography")
	def test_denegado(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[
				_resposta_soap(
					"nfeAutorizacaoLoteResult",
					_ret_envi_nfe(inf_prot=_prot_nfe(cstat="110", motivo="Uso Denegado")),
				)
			]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			resultado = transporte.transmitir(DOCUMENTO_MINIMO)

		self.assertTrue(resultado.denegado)
		self.assertFalse(resultado.autorizada)


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography, disponível no bench")
class TestPolling(unittest.TestCase):
	"""Prova que o adaptador de fato consulta de novo — não só reconhece o estado pendente."""

	def test_consulta_de_novo_ate_decidir(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[
				_resposta_soap(
					"nfeAutorizacaoLoteResult",
					_ret_envi_nfe(cstat="103", motivo="Lote recebido", nrec="351000000000001"),
				),
				_resposta_soap(
					"nfeRetAutorizacaoLoteResult",
					_ret_envi_nfe(cstat="105", motivo="Lote em processamento", nrec="351000000000001"),
				),
				_resposta_soap("nfeRetAutorizacaoLoteResult", _ret_envi_nfe(inf_prot=_prot_nfe())),
			]
		)
		dormidas = []

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao, dormir=dormidas.append
		) as transporte:
			resultado = transporte.transmitir(DOCUMENTO_MINIMO)

		self.assertTrue(resultado.autorizada)
		self.assertEqual(len(sessao.chamadas), 3)
		self.assertEqual(len(dormidas), 2)

	def test_segunda_chamada_usa_o_numero_de_recibo(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[
				_resposta_soap(
					"nfeAutorizacaoLoteResult", _ret_envi_nfe(cstat="103", motivo="x", nrec="999")
				),
				_resposta_soap("nfeRetAutorizacaoLoteResult", _ret_envi_nfe(inf_prot=_prot_nfe())),
			]
		)

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao, dormir=lambda s: None
		) as transporte:
			transporte.transmitir(DOCUMENTO_MINIMO)

		self.assertIn("<nRec>999</nRec>", sessao.chamadas[1]["data"].decode("utf-8"))

	def test_desiste_apos_o_limite_de_tentativas(self):
		"""Nunca entra em loop infinito — desiste e avisa que não decidiu."""
		from erpnext_brasil.integracao.transporte_sefaz import TransporteIndisponivel, TransporteSefaz

		sempre_pendente = [
			_resposta_soap("x", _ret_envi_nfe(cstat="105", motivo="Lote em processamento", nrec="1"))
			for _ in range(4)
		]

		with TransporteSefaz(
			_gerar_pfx(),
			"teste123",
			"RO",
			"11222333000181",
			sessao=SessaoFalsa(sempre_pendente),
			dormir=lambda s: None,
			tentativas_consulta_recibo=3,
		) as transporte:
			with self.assertRaises(TransporteIndisponivel):
				transporte.transmitir(DOCUMENTO_MINIMO)


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography, disponível no bench")
class TestConsultar(unittest.TestCase):
	def test_devolve_resultado_consulta(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa([_resposta_soap("nfeConsultaNFResult", _ret_envi_nfe(inf_prot=_prot_nfe()))])

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			resultado = transporte.consultar(CHAVE_VALIDA)

		self.assertIsInstance(resultado, ResultadoConsulta)
		self.assertEqual(resultado.codigo, "100")


def _ret_env_evento(cstat_lote="128", motivo_lote="Lote de evento processado", inf_evento=""):
	return (
		'<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe">'
		f"<cStat>{cstat_lote}</cStat><xMotivo>{motivo_lote}</xMotivo>{inf_evento}"
		"</retEnvEvento>"
	)


def _inf_evento(
	cstat="135",
	motivo="Evento homologado fora de prazo",
	chave=CHAVE_VALIDA,
	nprot="135260000123456",
	tipo_evento="110111",
):
	return (
		"<retEvento><infEvento>"
		f"<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>"
		f"<chNFe>{chave}</chNFe><tpEvento>{tipo_evento}</tpEvento><nProt>{nprot}</nProt>"
		"<dhRegEvento>2026-08-24T10:05:00-04:00</dhRegEvento>"
		"</infEvento></retEvento>"
	)


JUSTIFICATIVA_TESTE = "justificativa de teste com mais de 15 caracteres"


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography")
class TestCancelar(unittest.TestCase):
	def test_homologado_devolve_autorizacao_com_protocolo_do_cancelamento(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		resposta = _resposta_soap("retEnvEventoResult", _ret_env_evento(inf_evento=_inf_evento()))

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([resposta])
		) as transporte:
			resultado = transporte.cancelar(CHAVE_VALIDA, "135260000000001", JUSTIFICATIVA_TESTE)

		self.assertTrue(resultado.autorizada)
		self.assertEqual(resultado.autorizacao.protocolo, "135260000123456")
		self.assertEqual(resultado.autorizacao.chave_acesso, CHAVE_VALIDA)

	def test_xml_enviado_esta_assinado(self):
		"""Regressão: a primeira versão de `cancelar` mandava o evento sem `Signature` —
		nenhum teste anterior pegava isso porque todos simulam a resposta, nenhum
		inspecionava o corpo da requisição. Este inspeciona."""
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[_resposta_soap("retEnvEventoResult", _ret_env_evento(inf_evento=_inf_evento()))]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.cancelar(CHAVE_VALIDA, "135260000000001", JUSTIFICATIVA_TESTE)

		corpo = sessao.chamadas[0]["data"].decode("utf-8")

		self.assertIn("<Signature", corpo)
		self.assertIn("<SignatureValue>", corpo)
		self.assertIn("<X509Certificate>", corpo)

	def test_nao_homologado_devolve_resposta_sem_autorizacao(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		resposta = _resposta_soap(
			"retEnvEventoResult",
			_ret_env_evento(inf_evento=_inf_evento(cstat="573", motivo="Duplicidade de evento")),
		)

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([resposta])
		) as transporte:
			resultado = transporte.cancelar(CHAVE_VALIDA, "135260000000001", JUSTIFICATIVA_TESTE)

		self.assertFalse(resultado.autorizada)
		self.assertEqual(resultado.codigo, "573")
		self.assertEqual(resultado.mensagem, "Duplicidade de evento")

	def test_sem_endpoint_de_recepcaoevento_levanta_transporteindisponivel(self):
		"""Nenhuma UF conhecida hoje deixa `RecepcaoEvento` sem endpoint — a guarda em
		`cancelar` é defensiva para se a tabela de autorizadores um dia tiver uma lacuna
		aqui, como já acontece com `NfeConsultaCadastro`. Testado forçando `endpoint` a
		devolver `None`, não por UF real.

		O `endpoint` que importa é o de `eventos_sefaz` (onde `enviar_evento` de fato
		roda), não o de `transporte_sefaz` — são módulos diferentes desde a extração por
		tamanho de arquivo."""
		from erpnext_brasil.integracao import eventos_sefaz as modulo
		from erpnext_brasil.integracao.transporte_sefaz import TransporteIndisponivel, TransporteSefaz

		with unittest.mock.patch.object(modulo, "endpoint", return_value=None):
			with TransporteSefaz(
				_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([])
			) as transporte:
				with self.assertRaises(TransporteIndisponivel):
					transporte.cancelar(CHAVE_VALIDA, "135260000000001", JUSTIFICATIVA_TESTE)


TEXTO_CORRECAO_TESTE = "Corrigir o descritivo do item onde se le X leia-se Y, conforme combinado"


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography")
class TestCorrigir(unittest.TestCase):
	def test_homologado_devolve_autorizacao_com_protocolo_ecoado(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		resposta = _resposta_soap(
			"retEnvEventoResult",
			_ret_env_evento(inf_evento=_inf_evento(cstat="135", tipo_evento="110110")),
		)

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([resposta])
		) as transporte:
			resultado = transporte.corrigir(CHAVE_VALIDA, TEXTO_CORRECAO_TESTE)

		self.assertTrue(resultado.autorizada)
		self.assertEqual(resultado.autorizacao.protocolo, "135260000123456")
		self.assertEqual(resultado.autorizacao.chave_acesso, CHAVE_VALIDA)

	def test_101_nao_homologa_correcao_mesmo_sendo_sucesso_de_cancelamento(self):
		"""101 é específico de cancelamento (ver `evento.py`) — uma CC-e com esse `cStat`
		não é sucesso, é um retorno inesperado que a resposta deve refletir como tal."""
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		resposta = _resposta_soap(
			"retEnvEventoResult",
			_ret_env_evento(inf_evento=_inf_evento(cstat="101", motivo="x", tipo_evento="110110")),
		)

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([resposta])
		) as transporte:
			resultado = transporte.corrigir(CHAVE_VALIDA, TEXTO_CORRECAO_TESTE)

		self.assertFalse(resultado.autorizada)
		self.assertEqual(resultado.codigo, "101")

	def test_usa_o_mesmo_endpoint_de_recepcaoevento_do_cancelamento(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa(
			[
				_resposta_soap(
					"retEnvEventoResult", _ret_env_evento(inf_evento=_inf_evento(tipo_evento="110110"))
				)
			]
		)

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.corrigir(CHAVE_VALIDA, TEXTO_CORRECAO_TESTE)

		self.assertIn("recepcaoevento", sessao.chamadas[0]["url"].lower())


def _ret_inut(cstat="102", motivo="Inutilizacao de numero homologado", protocolo="111260000012345"):
	return (
		'<retInutNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
		f"<infInut><cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>"
		f"<nProt>{protocolo}</nProt><dhRecbto>2026-08-28T10:00:00-04:00</dhRecbto>"
		"</infInut></retInutNFe>"
	)


JUSTIFICATIVA_INUTILIZACAO = "Faixa pulada por erro de configuracao do emissor fiscal"


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography")
class TestInutilizar(unittest.TestCase):
	def test_homologada_devolve_protocolo(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		resposta = _resposta_soap("retInutNFeResult", _ret_inut())

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([resposta])
		) as transporte:
			resultado = transporte.inutilizar(
				"26", "11222333000181", "55", "1", "100", "105", JUSTIFICATIVA_INUTILIZACAO
			)

		self.assertTrue(resultado.homologada)
		self.assertEqual(resultado.protocolo, "111260000012345")

	def test_rejeitada_nao_e_homologada(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		resposta = _resposta_soap("retInutNFeResult", _ret_inut(cstat="563", motivo="Rejeicao: outro motivo"))

		with TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=SessaoFalsa([resposta])
		) as transporte:
			resultado = transporte.inutilizar(
				"26", "11222333000181", "55", "1", "100", "105", JUSTIFICATIVA_INUTILIZACAO
			)

		self.assertFalse(resultado.homologada)
		self.assertEqual(resultado.codigo, "563")

	def test_usa_o_endpoint_de_nfeinutilizacao(self):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa([_resposta_soap("retInutNFeResult", _ret_inut())])

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.inutilizar("26", "11222333000181", "55", "1", "100", "105", JUSTIFICATIVA_INUTILIZACAO)

		self.assertIn("nfeinutilizacao", sessao.chamadas[0]["url"].lower())

	def test_xml_enviado_esta_assinado(self):
		"""Mesma checagem de regressão de `TestCancelar` — `TInutNFe` também exige
		`Signature` com cardinalidade 1-1."""
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa([_resposta_soap("retInutNFeResult", _ret_inut())])

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.inutilizar("26", "11222333000181", "55", "1", "100", "105", JUSTIFICATIVA_INUTILIZACAO)

		corpo = sessao.chamadas[0]["data"].decode("utf-8")

		self.assertIn("<Signature", corpo)
		self.assertIn("<SignatureValue>", corpo)

	def test_converte_sigla_da_uf_para_codigo_ibge_no_corpo(self):
		"""`self._uf` é "RO" (sigla); `cUF` no XML precisa ser "11" (código IBGE) — a
		conversão que `CODIGO_UF_POR_SIGLA` existe para fazer."""
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		sessao = SessaoFalsa([_resposta_soap("retInutNFeResult", _ret_inut())])

		with TransporteSefaz(_gerar_pfx(), "teste123", "RO", "11222333000181", sessao=sessao) as transporte:
			transporte.inutilizar("26", "11222333000181", "55", "1", "100", "105", JUSTIFICATIVA_INUTILIZACAO)

		corpo = sessao.chamadas[0]["data"].decode("utf-8")

		self.assertIn("<cUF>11</cUF>", corpo)


if __name__ == "__main__":
	unittest.main()
