# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envelope SOAP dos webservices do eSocial — SOAP 1.1, não 1.2 como a NF-e.

Mais uma peça que não é a da NF-e com o nome trocado
------------------------------------------------------------
`fiscal/documento/soap.py` (NF-e) monta `soap12:Envelope`
(`http://www.w3.org/2003/05/soap-envelope`). O WSDL do eSocial
(`nfephp-org/sped-esocial`, `WsEnviarLoteEventos-v1_1_0.wsdl`/
`WsConsultarLoteEventos-v1_1_0.wsdl`) declara `soap:binding
transport="http://schemas.xmlsoap.org/soap/http"` — **SOAP 1.1**
(`http://schemas.xmlsoap.org/soap/envelope/`), um namespace diferente, não uma
variação do mesmo. Confirma o padrão já visto duas vezes neste bloco eSocial
(`ideEmpregador` do envelope de lote, o hash da assinatura): parecer com a NF-e não
é motivo para reaproveitar sem conferir.

O corpo da mensagem: elemento wrapper distinto por serviço
------------------------------------------------------------------
Cada operação tem seu próprio elemento raiz e wrapper interno, confirmados
diretamente nos WSDLs:

- `EnviarLoteEventos` (operação) → `<loteEventos>` (wrapper interno, carrega o XML de
  `esocial_lote.LoteEventos` já assinado/serializado).
- `ConsultarLoteEventos` (operação) → `<consulta>` (wrapper interno; a estrutura XML
  exata do conteúdo, `ConsultaLoteEventos-v1_0_0.xsd`, não foi verificada nesta
  rodada — só o nome do elemento wrapper, não o schema por dentro dele).

`xs:any` nos dois: o WSDL aceita qualquer XML dentro do wrapper — este módulo não
valida o conteúdo, só monta o envelope em volta dele (mesmo "caller entrega XML
pronto" já usado em `esocial_montagem.py`).

Autenticação por certificado é na camada de transporte, não aqui
------------------------------------------------------------------------------
Os WSDLs declaram `RequireClientCertificate="true"` — o eSocial autentica por TLS
mútuo (o mesmo certificado A1 usado para assinar o XML, apresentado também como
certificado de cliente HTTPS). Isso é responsabilidade de quem faz a chamada HTTP de
verdade (ainda não implementado, ver `docs/rh-estado-esocial.md`), não deste módulo,
que só monta o envelope XML.

Funções puras: nenhuma dependência do Frappe, `lxml` só na extração da resposta
(import tardio, mesmo motivo de `fiscal/documento/soap.py`).
"""

__all__ = [
	"NAMESPACE_SOAP11",
	"EsocialSoapInvalido",
	"extrair_resultado",
	"montar_envelope",
	"soap_action",
]

NAMESPACE_SOAP11 = "http://schemas.xmlsoap.org/soap/envelope/"

# servico -> (operação, elemento wrapper interno, namespace do serviço, soapAction).
# Confirmados diretamente nos WSDLs de nfephp-org/sped-esocial (v1_5_0).
_SERVICOS = {
	"enviarLoteEventos": (
		"EnviarLoteEventos",
		"loteEventos",
		"http://www.esocial.gov.br/servicos/empregador/lote/eventos/envio/v1_1_0",
	),
	"consultarLoteEventos": (
		"ConsultarLoteEventos",
		"consulta",
		"http://www.esocial.gov.br/servicos/empregador/lote/eventos/envio/"
		"consulta/retornoProcessamento/v1_1_0",
	),
}


class EsocialSoapInvalido(ValueError):
	"""Dado que impede a montagem do envelope, ou resposta que não pôde ser lida."""


def _dados_do_servico(servico: str) -> tuple[str, str, str]:
	if servico not in _SERVICOS:
		raise EsocialSoapInvalido(
			f"Serviço {servico!r} não tem envelope SOAP confirmado — serviços conhecidos: "
			f"{sorted(_SERVICOS)}"
		)

	return _SERVICOS[servico]


def soap_action(servico: str) -> str:
	"""O cabeçalho HTTP `SOAPAction` exigido pelo WSDL — namespace do serviço mais
	`/Servico<Operação>/<Operação>`, padrão confirmado nos dois WSDLs."""
	operacao, _, namespace = _dados_do_servico(servico)

	return f"{namespace}/Servico{operacao}/{operacao}"


def montar_envelope(servico: str, xml_interno: str) -> str:
	"""Envolve `xml_interno` (já pronto — o `LoteEventos` assinado, ou a consulta)
	no envelope SOAP 1.1 e no wrapper específico do serviço."""
	if not (xml_interno or "").strip():
		raise EsocialSoapInvalido("XML interno vazio: nada para enviar ao eSocial")

	operacao, wrapper, namespace = _dados_do_servico(servico)

	return (
		f'<soap:Envelope xmlns:soap="{NAMESPACE_SOAP11}">'
		"<soap:Body>"
		f'<{operacao} xmlns="{namespace}">'
		f"<{wrapper}>{xml_interno}</{wrapper}>"
		f"</{operacao}>"
		"</soap:Body>"
		"</soap:Envelope>"
	)


def extrair_resultado(resposta_soap: bytes | str) -> str:
	"""Extrai o conteúdo do primeiro (e único) filho de `soap:Body` — mesma
	estratégia de `fiscal/documento/soap.extrair_resultado`, adaptada ao namespace
	SOAP 1.1: em vez de fixar o nome do elemento de resposta (que muda por
	operação), pega o que sempre está lá."""
	import copy

	from lxml import etree

	bruto = resposta_soap.encode("utf-8") if isinstance(resposta_soap, str) else resposta_soap

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise EsocialSoapInvalido(f"Resposta SOAP não é XML válido: {e}") from e

	corpo = raiz.find(f".//{{{NAMESPACE_SOAP11}}}Body")

	if corpo is None:
		raise EsocialSoapInvalido("Resposta SOAP sem elemento Body reconhecível")

	filhos = list(corpo)

	if not filhos:
		raise EsocialSoapInvalido("O Body da resposta SOAP está vazio")

	netos = list(filhos[0])

	if not netos:
		return (filhos[0].text or "").strip()

	resultado = copy.deepcopy(netos[0])
	etree.cleanup_namespaces(resultado)

	return etree.tostring(resultado, encoding="unicode")
