# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envelope SOAP 1.2 do MDF-e: autorização por **lote e recibo**, consulta do recibo e evento.

Por que não reaproveita `soap.py` nem `soap_cte.py`
-----------------------------------------------------
Três envelopes diferentes, lidos de código de produção (`nfephp-org/sped-mdfe`, `Tools.php` e
`Common/Tools.php`), não supostos:

1. **Há cabeçalho** `mdfeCabecMsg` com `cUF` e `versaoDados` (como o CT-e, ao contrário da NF-e 4.00).
2. **O corpo se chama `mdfeDadosMsg`** e o namespace é `…/mdfe/wsdl/<operação>`, com a ação SOAP
   `"<namespace>/<método>"` no `Content-Type` (SOAP 1.2).
3. **O lote do MDF-e vai em texto, sem compressão.** `enviMDFe` (com `idLote`) entra como está em
   `mdfeDadosMsg`. O GZip+Base64 só existe no serviço **síncrono** (`MDFeRecepcaoSinc`), que este módulo
   não usa — a tarefa 5.1 pede lote e recibo. O evento também vai em texto e **sem lote**: o
   `eventoMDFe` assinado entra direto.

Os nomes de método vêm do `storage/wsmdfe_3.00.xml` do mesmo repositório (`mdfeRecepcaoLote`,
`mdfeRetRecepcao`, `mdfeRecepcaoEvento`; versão `3.00`). O `cUF` do cabeçalho é o da UF do emitente,
como no CT-e.

⚠️ Estado de verificação: fonte **secundária** — a biblioteca que emite MDF-e em produção, e o pacote de
esquemas `PL_MDFe_300b` que ela distribui —, e não o MOC nem o WSDL oficial. O `cUF` do cabeçalho
(emitente, e não "91" nacional) é herdado do CT-e por analogia: **confirmar em homologação**. Nenhuma
requisição foi feita a uma SEFAZ real; a prova depende do certificado A1.

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.fiscal.documento.soap import NAMESPACE_SOAP12, EnvelopeSoapInvalido

__all__ = [
	"SERVICO_EVENTO",
	"SERVICO_LOTE",
	"SERVICO_RECIBO",
	"VERSAO_DADOS",
	"content_type",
	"montar_consulta_recibo",
	"montar_envelope",
	"montar_lote",
]

_PORTAL = "http://www.portalfiscal.inf.br/mdfe"
VERSAO_DADOS = "3.00"

SERVICO_LOTE = "MDFeRecepcao"
SERVICO_RECIBO = "MDFeRetRecepcao"
SERVICO_EVENTO = "MDFeRecepcaoEvento"
"""As chaves de `autorizadores_mdfe.ENDPOINTS` — que são também os nomes da operação SOAP."""

_METODO = {
	SERVICO_LOTE: "mdfeRecepcaoLote",
	SERVICO_RECIBO: "mdfeRetRecepcao",
	SERVICO_EVENTO: "mdfeRecepcaoEvento",
}


def _namespace(servico: str) -> str:
	if servico not in _METODO:
		raise EnvelopeSoapInvalido(f"Serviço {servico!r} do MDF-e não tem método SOAP confirmado")

	return f"{_PORTAL}/wsdl/{servico}"


def content_type(servico: str) -> str:
	"""O `Content-Type` do POST, com a ação SOAP — é onde o SOAP 1.2 a leva."""
	return f'application/soap+xml; charset=utf-8; action="{_namespace(servico)}/{_METODO[servico]}"'


def _sem_declaracao(xml: str) -> str:
	"""Tira a declaração `<?xml …?>` — não pode aparecer dentro de `enviMDFe`."""
	texto = xml.strip()

	if texto.startswith("<?xml"):
		texto = texto[texto.index("?>") + 2 :].lstrip()

	return texto


def montar_lote(xml_mdfe: str, id_lote: str) -> str:
	"""O `enviMDFe` com um MDF-e já serializado e assinado. `xml_mdfe` entra como está.

	Um MDF-e por lote: é o que o app envia, e dispensa decidir o que fazer com um lote parcialmente
	autorizado.
	"""
	if not (xml_mdfe or "").strip():
		raise EnvelopeSoapInvalido("XML do MDF-e vazio: nada para enviar à SEFAZ")

	if not (id_lote or "").isdigit() or not 1 <= len(id_lote) <= 15:
		raise EnvelopeSoapInvalido(f"idLote deve ter de 1 a 15 dígitos, recebido {id_lote!r}")

	return (
		f'<enviMDFe xmlns="{_PORTAL}" versao="{VERSAO_DADOS}">'
		f"<idLote>{id_lote}</idLote>{_sem_declaracao(xml_mdfe)}</enviMDFe>"
	)


def montar_consulta_recibo(recibo: str, ambiente: str) -> str:
	"""O `consReciMDFe` (`tpAmb` e `nRec`, nessa ordem — `consReciMDFeTiposBasico_v3.00.xsd`)."""
	if not (recibo or "").isdigit():
		raise EnvelopeSoapInvalido(f"nRec deve ser numérico, recebido {recibo!r}")

	if ambiente not in ("1", "2"):
		raise EnvelopeSoapInvalido(f"tpAmb deve ser '1' ou '2', recebido {ambiente!r}")

	return (
		f'<consReciMDFe xmlns="{_PORTAL}" versao="{VERSAO_DADOS}">'
		f"<tpAmb>{ambiente}</tpAmb><nRec>{recibo}</nRec></consReciMDFe>"
	)


def montar_envelope(servico: str, xml_interno: str, codigo_uf: str) -> str:
	"""Envolve o XML (já serializado) no envelope SOAP 1.2 do serviço, com o cabeçalho `mdfeCabecMsg`."""
	namespace = _namespace(servico)

	if not (xml_interno or "").strip():
		raise EnvelopeSoapInvalido("XML interno vazio: nada para enviar à SEFAZ")

	if not (len(codigo_uf or "") == 2 and codigo_uf.isdigit()):
		raise EnvelopeSoapInvalido(f"cUF do cabeçalho deve ter dois dígitos, recebido {codigo_uf!r}")

	return (
		'<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
		'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
		f'xmlns:soap12="{NAMESPACE_SOAP12}">'
		"<soap12:Header>"
		f'<mdfeCabecMsg xmlns="{namespace}">'
		f"<cUF>{codigo_uf}</cUF><versaoDados>{VERSAO_DADOS}</versaoDados>"
		"</mdfeCabecMsg>"
		"</soap12:Header>"
		"<soap12:Body>"
		f'<mdfeDadosMsg xmlns="{namespace}">{_sem_declaracao(xml_interno)}</mdfeDadosMsg>'
		"</soap12:Body>"
		"</soap12:Envelope>"
	)
