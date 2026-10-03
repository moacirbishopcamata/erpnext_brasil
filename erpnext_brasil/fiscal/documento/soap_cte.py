# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envelope SOAP 1.2 da autorização **síncrona** do CT-e (`CTeRecepcaoSincV4`).

Por que não reaproveita `soap.py`
-----------------------------------
O envelope do CT-e não é o da NF-e com outro nome. Três diferenças, lidas de código de produção
(`nfephp-org/sped-cte`, `src/Tools.php` e `src/Common/Tools.php`, e `nfephp-org/sped-common`,
`Soap/SoapBase.php` e `SoapCurl.php`), não supostas:

1. **Há cabeçalho.** `soap.py` registra que o `nfeCabecMsg` é do layout anterior a nov/2017 e
   não existe na NF-e 4.00. No CT-e 4.00 o `sped-cte` ainda monta
   `<soap12:Header><cteCabecMsg xmlns="…"><cUF/><versaoDados/></cteCabecMsg></soap12:Header>`.
   Copiar o envelope da NF-e omitiria um cabeçalho que o CT-e manda.
2. **O corpo vai compactado.** `cteDadosMsg` carrega o `CTe` em **GZip e Base64**
   (`base64_encode(gzencode($request, 9))`), e não o XML em texto. É a **árvore `CTe` direta**,
   sem o `enviCTe` de lote — o serviço é unitário.
3. **A ação SOAP vai no `Content-Type`**: `application/soap+xml;…;action="<ns>/<método>"`.

Os nomes (`CteRecepcao` → operação `CTeRecepcaoSincV4`, método `cteRecepcao`, versão `4.00`) são os
do `storage/wscte_4.00_mod57.xml` do mesmo repositório, idênticos em todos os grupos de
autorizador. O `cUF` do cabeçalho é o da UF do **emitente** (nos grupos compartilhados, SVRS/SVSP,
a biblioteca troca o código do grupo pelo da UF de origem).

⚠️ Estado de verificação: fonte **secundária** — a biblioteca que assina CT-e em produção —, e
não o MOC nem o WSDL oficial. Nenhuma requisição foi feita a uma SEFAZ real; a validação em
homologação é critério da tarefa 3.1 e depende do certificado A1.

Funções puras: nenhuma dependência do Frappe.
"""

import base64
import gzip

from erpnext_brasil.fiscal.documento.soap import NAMESPACE_SOAP12, EnvelopeSoapInvalido

__all__ = [
	"ACAO_AUTORIZACAO",
	"NAMESPACE_AUTORIZACAO",
	"OPERACAO_AUTORIZACAO",
	"SERVICO_AUTORIZACAO",
	"VERSAO_DADOS",
	"compactar",
	"content_type_autorizacao",
	"montar_envelope_autorizacao",
]

_NAMESPACE_WSDL_BASE = "http://www.portalfiscal.inf.br/cte/wsdl"

SERVICO_AUTORIZACAO = "CteRecepcao"
"""A chave do serviço em `autorizadores_cte.ENDPOINTS` — não é o nome da operação SOAP."""

OPERACAO_AUTORIZACAO = "CTeRecepcaoSincV4"
METODO_AUTORIZACAO = "cteRecepcao"
VERSAO_DADOS = "4.00"

NAMESPACE_AUTORIZACAO = f"{_NAMESPACE_WSDL_BASE}/{OPERACAO_AUTORIZACAO}"
ACAO_AUTORIZACAO = f'"{NAMESPACE_AUTORIZACAO}/{METODO_AUTORIZACAO}"'


def content_type_autorizacao() -> str:
	"""O `Content-Type` do POST, com a ação SOAP — é onde o SOAP 1.2 a leva."""
	return f"application/soap+xml; charset=utf-8; action={ACAO_AUTORIZACAO}"


def compactar(xml: str) -> str:
	"""GZip + Base64 do XML, em uma linha.

	`mtime=0` de propósito: o `gzip` grava a hora da compactação no cabeçalho, e sem fixá-la o
	mesmo documento gera corpos diferentes a cada chamada — ruim para teste e para diagnóstico.
	"""
	return base64.b64encode(gzip.compress(xml.encode("utf-8"), compresslevel=9, mtime=0)).decode("ascii")


def montar_envelope_autorizacao(xml_cte: str, codigo_uf: str) -> str:
	"""Envolve o `CTe` (já serializado e assinado) no envelope SOAP 1.2 do serviço síncrono.

	`xml_cte` entra como está, só compactado — remontar a árvore aqui produziria um XML diferente
	do que foi assinado. `codigo_uf` é o `cUF` IBGE de dois dígitos da UF do emitente.
	"""
	if not (xml_cte or "").strip():
		raise EnvelopeSoapInvalido("XML do CT-e vazio: nada para enviar à SEFAZ")

	if not (len(codigo_uf or "") == 2 and codigo_uf.isdigit()):
		raise EnvelopeSoapInvalido(f"cUF do cabeçalho deve ter dois dígitos, recebido {codigo_uf!r}")

	return (
		'<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
		'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
		f'xmlns:soap12="{NAMESPACE_SOAP12}">'
		"<soap12:Header>"
		f'<cteCabecMsg xmlns="{NAMESPACE_AUTORIZACAO}">'
		f"<cUF>{codigo_uf}</cUF><versaoDados>{VERSAO_DADOS}</versaoDados>"
		"</cteCabecMsg>"
		"</soap12:Header>"
		"<soap12:Body>"
		f'<cteDadosMsg xmlns="{NAMESPACE_AUTORIZACAO}">{compactar(xml_cte)}</cteDadosMsg>'
		"</soap12:Body>"
		"</soap12:Envelope>"
	)
