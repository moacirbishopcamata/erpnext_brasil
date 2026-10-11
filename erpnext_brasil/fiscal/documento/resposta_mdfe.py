# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura das respostas do MDF-e: recibo do lote, resultado do lote e evento.

Dois níveis, como a NF-e — e ao contrário do CT-e
---------------------------------------------------
O MDF-e usa lote e recibo (`MDFeRecepcao` / `MDFeRetRecepcao`), então há **dois** `cStat` em níveis
diferentes: o do lote e o do documento. Lidos dos XSD (`retEnviMDFe`, `retConsReciMDFe` e `TProtMDFe`,
`PL_MDFe_300b` do `sped-mdfe`):

- `retEnviMDFe`: `tpAmb`, `cUF`, `verAplic`, `cStat`, `xMotivo` e `infRec` **opcional** (`nRec`,
  `dhRecbto`, `tMed`). O recibo só existe quando o lote foi recebido (`cStat` 103).
- `retConsReciMDFe`: `tpAmb`, `verAplic`, `nRec`, `cStat`, `xMotivo`, `cUF` e `protMDFe` **opcional**
  (`infProt`: `chMDFe`, `dhRecbto`, `nProt` opcional, `cStat`, `xMotivo`).

Quem decide é o `cStat` do `infProt`, quando há `protMDFe` (é o do documento); sem protocolo, o do lote:
**105 (em processamento) é pendência**, e qualquer outro é recusa do lote.

⚠️ Estado de verificação: a **estrutura** vem do XSD; os **códigos** (103 recebido, 105 em processamento,
100 autorizado, 135 evento registrado) vêm do `sped-mdfe` e da tabela de status que o ecossistema usa
para os três documentos, não do MOC lido. Por isso a leitura é conservadora:

- só o `100` é autorizado — sem tabela de "autorizado fora do prazo" nem de uso denegado do MDF-e, que
  não foram confirmados para este documento (a leitura do CT-e não é copiada);
- evento só é registrado com `135`; o `136` ("registrado, mas não vinculado") e o `155` do CT-e **não**
  contam, para uma inconsistência aparecer como recusa e não como registro falso.

Autorizado sem `nProt` é recusado: um `cStat` 100 sem protocolo não é prova de autorização.

O `retEnviMDFe`, o `retConsReciMDFe` e o `retEventoMDFe` são procurados em qualquer profundidade: o
elemento que os embrulha na resposta SOAP muda por serviço, e fixá-lo seria apostar sem o WSDL oficial.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import datetime

__all__ = [
	"AUTORIZADO",
	"EM_PROCESSAMENTO",
	"EVENTO_REGISTRADO",
	"LOTE_RECEBIDO",
	"ReciboLote",
	"RespostaMdfeInvalida",
	"RetornoEventoMdfe",
	"RetornoLote",
	"interpretar_recibo_lote",
	"interpretar_retorno_evento_mdfe",
	"interpretar_retorno_lote",
]

LOTE_RECEBIDO = "103"
EM_PROCESSAMENTO = "105"
AUTORIZADO = "100"
EVENTO_REGISTRADO = "135"


class RespostaMdfeInvalida(ValueError):
	"""A resposta não é a esperada, ou diz algo que não se pode gravar."""


@dataclass(frozen=True)
class ReciboLote:
	"""O que a SEFAZ respondeu ao envio do lote."""

	codigo: str
	motivo: str
	recibo: str = ""
	tempo_medio_s: int | None = None

	@property
	def recebido(self) -> bool:
		return self.codigo == LOTE_RECEBIDO


@dataclass(frozen=True)
class RetornoLote:
	"""O resultado do processamento do lote — dado, não decisão da integração."""

	codigo: str
	"""O `cStat` que decide: o de `infProt` quando há `protMDFe`, senão o do lote."""
	motivo: str
	protocolo: str = ""
	chave: str = ""
	recebido_em: datetime | None = None

	@property
	def autorizado(self) -> bool:
		return self.codigo == AUTORIZADO

	@property
	def pendente(self) -> bool:
		return self.codigo == EM_PROCESSAMENTO


@dataclass(frozen=True)
class RetornoEventoMdfe:
	"""O que a SEFAZ respondeu a um evento."""

	codigo: str
	motivo: str
	tipo_evento: str = ""
	protocolo: str = ""
	chave: str = ""
	registrado_em: datetime | None = None

	@property
	def registrado(self) -> bool:
		return self.codigo == EVENTO_REGISTRADO


def _local(no) -> str:
	return no.tag.rsplit("}", 1)[-1] if isinstance(no.tag, str) else ""


def _filho(no, nome: str):
	return next((f for f in no if _local(f) == nome), None)


def _texto(no, nome: str) -> str:
	filho = _filho(no, nome)

	return (filho.text or "").strip() if filho is not None else ""


def _data(valor: str, campo: str) -> datetime | None:
	try:
		return datetime.fromisoformat(valor) if valor else None
	except ValueError as e:
		raise RespostaMdfeInvalida(f"{campo} inválido: {valor!r}") from e


def _raiz(xml: str | bytes, nome: str, o_que: str):
	"""A raiz `nome`, onde estiver na resposta — com mensagem que diz **o que** se esperava."""
	from lxml import etree

	bruto = xml.encode("utf-8") if isinstance(xml, str) else xml

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise RespostaMdfeInvalida(f"Resposta do MDF-e não é XML válido: {e}") from e

	achado = raiz if _local(raiz) == nome else next((n for n in raiz.iter() if _local(n) == nome), None)

	if achado is None:
		raise RespostaMdfeInvalida(f"Resposta sem {nome} — não é {o_que}")

	return achado


def interpretar_recibo_lote(xml: str | bytes) -> ReciboLote:
	"""Lê o `retEnviMDFe` do envio do lote. Lote recebido (103) sem `nRec` é recusado."""
	ret = _raiz(xml, "retEnviMDFe", "o retorno do envio do lote do MDF-e")
	codigo = _texto(ret, "cStat")

	if not codigo:
		raise RespostaMdfeInvalida("retEnviMDFe sem cStat")

	inf = _filho(ret, "infRec")
	recibo = _texto(inf, "nRec") if inf is not None else ""
	medio = _texto(inf, "tMed") if inf is not None else ""

	if codigo == LOTE_RECEBIDO and not recibo:
		raise RespostaMdfeInvalida("Lote recebido (103) sem nRec — sem recibo não há como consultar")

	return ReciboLote(
		codigo=codigo,
		motivo=_texto(ret, "xMotivo"),
		recibo=recibo,
		tempo_medio_s=int(medio) if medio.isdigit() else None,
	)


def interpretar_retorno_lote(xml: str | bytes) -> RetornoLote:
	"""Lê o `retConsReciMDFe` da consulta do recibo."""
	ret = _raiz(xml, "retConsReciMDFe", "o retorno da consulta do recibo do MDF-e")
	codigo_lote = _texto(ret, "cStat")

	if not codigo_lote:
		raise RespostaMdfeInvalida("retConsReciMDFe sem cStat")

	prot = _filho(ret, "protMDFe")
	inf = _filho(prot, "infProt") if prot is not None else None

	if inf is None:
		return RetornoLote(codigo=codigo_lote, motivo=_texto(ret, "xMotivo"))

	codigo = _texto(inf, "cStat") or codigo_lote
	protocolo = _texto(inf, "nProt")

	if codigo == AUTORIZADO and not protocolo:
		raise RespostaMdfeInvalida("cStat 100 (autorizado) sem nProt — sem protocolo não há autorização")

	return RetornoLote(
		codigo=codigo,
		motivo=_texto(inf, "xMotivo") or _texto(ret, "xMotivo"),
		protocolo=protocolo,
		chave=_texto(inf, "chMDFe"),
		recebido_em=_data(_texto(inf, "dhRecbto"), "dhRecbto"),
	)


def interpretar_retorno_evento_mdfe(xml: str | bytes) -> RetornoEventoMdfe:
	"""Lê o `retEventoMDFe`: sem lote, o `cStat` que decide é o de `infEvento`."""
	ret = _raiz(xml, "retEventoMDFe", "o retorno de um evento do MDF-e")
	inf = _filho(ret, "infEvento")

	if inf is None:
		raise RespostaMdfeInvalida("retEventoMDFe sem infEvento")

	codigo = _texto(inf, "cStat")

	if not codigo:
		raise RespostaMdfeInvalida("infEvento sem cStat")

	retorno = RetornoEventoMdfe(
		codigo=codigo,
		motivo=_texto(inf, "xMotivo"),
		tipo_evento=_texto(inf, "tpEvento"),
		protocolo=_texto(inf, "nProt"),
		chave=_texto(inf, "chMDFe"),
		registrado_em=_data(_texto(inf, "dhRegEvento"), "dhRegEvento"),
	)

	if retorno.registrado and not retorno.protocolo:
		raise RespostaMdfeInvalida(f"cStat {codigo} (registrado) sem nProt — sem protocolo não há registro")

	return retorno
