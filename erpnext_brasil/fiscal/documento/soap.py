# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envelope SOAP 1.2 dos webservices da NF-e.

Sem `nfeCabecMsg`, e é proposital
----------------------------------
Muita referência em blog e fórum ainda mostra um `soap12:Header` com `nfeCabecMsg`
(`cUF` + `versaoDados`). Isso é do layout **anterior a novembro de 2017**. A própria
biblioteca de referência que documenta esse header a marca como obsoleta no código-fonte:
*"will no longer exist in version 4.0 of the SEFAZ layout (...) valid only until
11/2017 after that date becomes OBSOLETE and if it is used it will cause communication
failure."* (`nfephp-org/sped-nfe`, `Factories/Header.php`).

O leiaute 4.00 — o que este app usa — **não leva header**. Só `soap12:Body >
nfeDadosMsg`. Foi preciso cruzar duas fontes independentes (uma dizia que precisava do
header, outra não) e achar o comentário datado no código-fonte para resolver o conflito
— por isso ele está registrado aqui, e não escondido.

O namespace de `nfeDadosMsg`
------------------------------
Segue o padrão `http://www.portalfiscal.inf.br/nfe/wsdl/<operacao>`, onde `<operacao>`
é o valor confirmado em `autorizadores_sefaz.OPERACAO_SOAP` — não o nome "bonito" do
serviço (`NfeConsultaProtocolo` na tabela vira `NFeConsultaProtocolo4` na operação,
maiúsculas e sufixo incluídos).

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.fiscal.documento.autorizadores_sefaz import OPERACAO_SOAP

__all__ = [
	"NAMESPACE_SOAP12",
	"EnvelopeSoapInvalido",
	"extrair_resultado",
	"montar_envelope",
	"namespace_operacao",
]

NAMESPACE_SOAP12 = "http://www.w3.org/2003/05/soap-envelope"
_NAMESPACE_WSDL_BASE = "http://www.portalfiscal.inf.br/nfe/wsdl"


class EnvelopeSoapInvalido(ValueError):
	pass


def namespace_operacao(servico: str) -> str:
	"""Namespace de `nfeDadosMsg` para o serviço, a partir da operação confirmada."""
	operacao = OPERACAO_SOAP.get(servico)

	if not operacao:
		raise EnvelopeSoapInvalido(f"Serviço {servico!r} não tem operação SOAP confirmada em OPERACAO_SOAP")

	return f"{_NAMESPACE_WSDL_BASE}/{operacao}"


def montar_envelope(servico: str, xml_interno: str) -> str:
	"""Envolve o XML (já serializado e, quando aplicável, assinado) no envelope SOAP 1.2.

	`xml_interno` entra como está — string já pronta, não árvore de dicionário. Isso
	porque o que se envelopa aqui já passou por `serializacao.para_xml` (e por
	`assinar_nfe`, quando o serviço exige assinatura); remontar a árvore aqui duplicaria
	trabalho e arriscaria produzir um XML byte a byte diferente do que foi assinado.
	"""
	if not (xml_interno or "").strip():
		raise EnvelopeSoapInvalido("XML interno vazio: nada para enviar à SEFAZ")

	namespace = namespace_operacao(servico)

	return (
		'<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
		'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
		f'xmlns:soap12="{NAMESPACE_SOAP12}">'
		"<soap12:Body>"
		f'<nfeDadosMsg xmlns="{namespace}">{xml_interno}</nfeDadosMsg>'
		"</soap12:Body>"
		"</soap12:Envelope>"
	)


def extrair_resultado(resposta_soap: bytes | str) -> str:
	"""Extrai o conteúdo de `nfeResultMsg` (ou equivalente) da resposta SOAP.

	A resposta não usa o mesmo elemento em todos os serviços — a maioria devolve
	`nfeResultMsg`, mas o nome muda com o serviço (`nfeStatusServicoNFResult`,
	`nfeAutorizacaoLoteResult`, e por aí vai, no padrão `<method>Result`). Em vez de
	fixar um nome só, a extração pega o **primeiro elemento filho de `soap12:Body`**
	— é sempre o único, seja qual for o nome — e devolve seu conteúdo interno cru.

	Faz o parsing com `lxml`, não com regex: regex sobre XML quebra silenciosamente
	diante de elemento aninhado com o mesmo nome do wrapper, ou de atributo contendo
	`>` — e a mensagem de erro nunca aponta pra causa real. `lxml` já é dependência de
	`integracao/assinador_local.py`; o import fica dentro da função pelo mesmo motivo:
	a suíte precisa continuar rodando num ambiente sem a biblioteca instalada.

	Devolve string, não árvore: quem chama decide se precisa fazer parsing (o corpo é
	tipicamente um XML de resposta da SEFAZ, não um formato deste app).
	"""
	import copy

	from lxml import etree

	bruto = resposta_soap.encode("utf-8") if isinstance(resposta_soap, str) else resposta_soap

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise EnvelopeSoapInvalido(f"Resposta SOAP não é XML válido: {e}") from e

	corpo = raiz.find(".//{http://www.w3.org/2003/05/soap-envelope}Body")

	if corpo is None:
		raise EnvelopeSoapInvalido("Resposta SOAP sem elemento Body reconhecível")

	filhos = list(corpo)

	if not filhos:
		raise EnvelopeSoapInvalido("O Body da resposta SOAP está vazio")

	# O elemento *Result (nfeResultMsg, nfeStatusServicoNFResult, ...) embrulha o XML de
	# resposta de verdade da SEFAZ como filho único — é esse filho que interessa a quem
	# chama, não o wrapper nem seu texto solto.
	netos = list(filhos[0])

	if not netos:
		return (filhos[0].text or "").strip()

	# lxml propaga para o elemento extraído as declarações de namespace dos ancestrais
	# que estão no escopo (aqui, o xmlns:soap do envelope), mesmo quando não usadas no
	# subelemento — sem a limpeza, o XML devolvido sairia poluído com um `xmlns:soap`
	# que não pertence a ele. `cleanup_namespaces` remove o que não é referenciado.
	resultado = copy.deepcopy(netos[0])
	etree.cleanup_namespaces(resultado)

	return etree.tostring(resultado, encoding="unicode")
