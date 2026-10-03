# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura da resposta da autorização síncrona do CT-e (`retCTe`).

Um nível só, ao contrário da NF-e
------------------------------------
A resposta da NF-e tem dois `cStat` em níveis diferentes (lote e nota) por causa do recibo —
ver `resposta_sefaz.py`. O CT-e 4.00 é síncrono e unitário: **não há lote nem recibo**. O
`retCTe` (`TRetCTe`, `cteTiposBasico_v4.00.xsd`) traz `tpAmb`, `cUF`, `verAplic`, `cStat`,
`xMotivo` e um `protCTe` **opcional** (`TProtCTe`: `infProt` com `chCTe`, `dhRecbto`, `nProt`
opcional, `cStat`, `xMotivo`).

Quem decide é um `cStat` só: o de `infProt`, quando há `protCTe` (é o do documento); o do
`retCTe` quando não há — rejeição antes do processamento, e também o `656` de consumo indevido.

`cStat` de autorizado e denegado
----------------------------------
`100` autorizado e `150` autorizado fora do prazo; `110` uso denegado, `205` CT-e denegado e
`301` uso denegado por irregularidade fiscal do emitente. Vêm do `sped-cte` (`Complements.php`,
o conjunto de `cStat` com que ele aceita anexar o protocolo), fonte **secundária**: o MOC não foi
lido. Não são os da NF-e (`DENEGADO` lá inclui `302` e `303`), e por isso não se reaproveita aquele
conjunto.

Autorizado sem `nProt` é recusado: um `cStat` 100 sem protocolo não é prova de autorização, e
gravá-lo deixaria o documento "autorizado" sem o número que o prova.

O `retCTe` é procurado em qualquer profundidade: o nome do elemento que o embrulha na resposta SOAP
muda por serviço (`cteRecepcaoResult`, `cteResultMsg`…), o `retCTe` não. Sem o WSDL oficial à mão,
fixar o embrulho seria apostar.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import datetime

__all__ = [
	"AUTORIZADOS",
	"DENEGADOS",
	"RetornoCte",
	"RetornoCteInvalido",
	"interpretar_retorno_cte",
]

AUTORIZADOS = {"100", "150"}
DENEGADOS = {"110", "205", "301"}


class RetornoCteInvalido(ValueError):
	"""A resposta não é um `retCTe` utilizável, ou diz algo que não se pode gravar."""


@dataclass(frozen=True)
class RetornoCte:
	"""O que a SEFAZ respondeu à autorização — dado, não decisão da integração."""

	codigo: str
	"""O `cStat` que decide: o de `infProt` quando há `protCTe`, senão o do `retCTe`."""
	motivo: str
	protocolo: str = ""
	chave: str = ""
	recebido_em: datetime | None = None

	@property
	def autorizado(self) -> bool:
		return self.codigo in AUTORIZADOS

	@property
	def denegado(self) -> bool:
		return self.codigo in DENEGADOS


def _local(no) -> str:
	return no.tag.rsplit("}", 1)[-1] if isinstance(no.tag, str) else ""


def _filho(no, nome: str):
	return next((f for f in no if _local(f) == nome), None)


def _texto(no, nome: str) -> str:
	filho = _filho(no, nome)

	return (filho.text or "").strip() if filho is not None else ""


def interpretar_retorno_cte(xml: str | bytes) -> RetornoCte:
	"""Lê o `retCTe` da resposta SOAP (já sem o envelope, ou ainda embrulhado)."""
	from lxml import etree

	bruto = xml.encode("utf-8") if isinstance(xml, str) else xml

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise RetornoCteInvalido(f"Resposta do CT-e não é XML válido: {e}") from e

	ret = raiz if _local(raiz) == "retCTe" else next((n for n in raiz.iter() if _local(n) == "retCTe"), None)

	if ret is None:
		raise RetornoCteInvalido("Resposta sem retCTe — não é o retorno da autorização do CT-e")

	cstat_ret = _texto(ret, "cStat")

	if not cstat_ret:
		raise RetornoCteInvalido("retCTe sem cStat")

	prot = _filho(ret, "protCTe")
	inf = _filho(prot, "infProt") if prot is not None else None

	if inf is None:
		return RetornoCte(codigo=cstat_ret, motivo=_texto(ret, "xMotivo"))

	codigo = _texto(inf, "cStat") or cstat_ret
	protocolo = _texto(inf, "nProt")
	recebimento = _texto(inf, "dhRecbto")

	if codigo in AUTORIZADOS and not protocolo:
		raise RetornoCteInvalido(f"cStat {codigo} (autorizado) sem nProt — sem protocolo não há autorização")

	try:
		recebido_em = datetime.fromisoformat(recebimento) if recebimento else None
	except ValueError as e:
		raise RetornoCteInvalido(f"dhRecbto inválido: {recebimento!r}") from e

	return RetornoCte(
		codigo=codigo,
		motivo=_texto(inf, "xMotivo") or _texto(ret, "xMotivo"),
		protocolo=protocolo,
		chave=_texto(inf, "chCTe"),
		recebido_em=recebido_em,
	)
