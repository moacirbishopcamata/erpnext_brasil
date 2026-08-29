# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Interpretação da resposta de autorização — os dois níveis de `cStat`.

A armadilha que este módulo existe para evitar
------------------------------------------------
A resposta de `NFeAutorizacao4` (ou de `NFeRetAutorizacao4`, para lote processado de
forma assíncrona) tem **dois `cStat` em níveis diferentes**, e confundi-los é o erro
mais fácil de cometer aqui:

- `retEnviNFe/cStat` — status do **lote**. `104` significa "Lote processado", que **não
  quer dizer que a nota foi autorizada** — só que o lote terminou de ser processado.
- `retEnviNFe/protNFe/infProt/cStat` — status **da NF-e em si**. `100` é "Autorizado o
  uso da NF-e"; qualquer outro valor é rejeição.

Um código que só olhasse o `cStat` do lote relataria rejeição como sucesso sempre que o
lote tivesse sido processado (o caso comum) — o documento pareceria autorizado sem ter
sido.

Quando `protNFe` não vem
--------------------------
Lote em fila (`cStat` de lote diferente de 104, ex. `105` "Lote em processamento") não
tem `protNFe` — a nota ainda não foi julgada, e é aí que entra o polling via
`NFeConsultaProtocolo4`/`NFeRetAutorizacao4`. Este módulo modela essa ausência como
`protocolo=None` no resultado, nunca como erro: é estado válido do fluxo, não falha.

Funções puras: nenhuma dependência do Frappe. Usa `lxml` para o parsing (mesma
justificativa de `soap.py`: regex sobre XML esconde bug em vez de acusar).
"""

from dataclasses import dataclass

__all__ = ["RespostaSefazInvalida", "RetornoAutorizacao", "interpretar_autorizacao"]

# Status do lote que indicam processamento concluído — só a partir daqui faz sentido
# procurar `protNFe`. Os demais (105 "Lote em processamento", etc.) exigem novo poll.
_LOTE_PROCESSADO = {"104"}

AUTORIZADO = "100"
DENEGADO = {"110", "301", "302", "303"}


class RespostaSefazInvalida(ValueError):
	pass


@dataclass(frozen=True)
class RetornoAutorizacao:
	"""Leitura estruturada de uma resposta de autorização.

	`protocolo` é `None` enquanto o lote não foi julgado — nunca confundir com erro de
	parsing: é o estado "ainda não decidido", que quem chama trata pedindo nova consulta.
	"""

	cstat_lote: str
	motivo_lote: str
	lote_processado: bool
	cstat_nfe: str | None = None
	motivo_nfe: str | None = None
	protocolo: str | None = None
	data_recebimento: str | None = None
	chave_conferida: str | None = None
	numero_recibo: str | None = None
	"""Presente quando o lote foi enfileirado para processamento assíncrono — é o que se
	usa para consultar depois via NFeRetAutorizacao4."""

	@property
	def autorizado(self) -> bool:
		return self.cstat_nfe == AUTORIZADO

	@property
	def denegado(self) -> bool:
		return self.cstat_nfe in DENEGADO

	@property
	def pendente(self) -> bool:
		"""Lote ainda não julgado: nem autorizado, nem rejeitado — precisa nova consulta."""
		return not self.lote_processado


def interpretar_autorizacao(xml_resposta: str | bytes) -> RetornoAutorizacao:
	"""Interpreta o `retEnviNFe` (ou equivalente de `NFeRetAutorizacao4`).

	Recebe o XML já isolado do envelope SOAP — é o que `soap.extrair_resultado`
	devolve, não a resposta HTTP crua.
	"""
	from lxml import etree

	bruto = xml_resposta.encode("utf-8") if isinstance(xml_resposta, str) else xml_resposta

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise RespostaSefazInvalida(f"Resposta da SEFAZ não é XML válido: {e}") from e

	# `local-name()` — via `.xpath()`, não `.find()` — porque o namespace do documento
	# (`portalfiscal.inf.br/nfe`) é declarado sem prefixo, e `.find()` só entende o
	# subconjunto simplificado de caminho do ElementTree, sem predicados de função.
	def filho_direto(no, nome: str):
		encontrados = no.xpath(f"*[local-name()='{nome}']")

		return encontrados[0] if encontrados else None

	def texto_em_qualquer_nivel(no, nome: str) -> str | None:
		encontrados = no.xpath(f".//*[local-name()='{nome}']")

		return encontrados[0].text.strip() if encontrados and encontrados[0].text else None

	def texto_filho(no, nome: str) -> str | None:
		elemento = filho_direto(no, nome)

		return elemento.text.strip() if elemento is not None and elemento.text else None

	# cStat/xMotivo aparecem em mais de um nível (lote e, dentro de infProt, a nota); os
	# do lote são os primeiros do documento, por isso a busca aqui é restrita à raiz.
	cstat_lote = texto_filho(raiz, "cStat")
	motivo_lote = texto_filho(raiz, "xMotivo")

	if cstat_lote is None:
		raise RespostaSefazInvalida("Resposta sem cStat do lote — não é um retEnviNFe reconhecível")

	inf_prot = None
	for candidato in raiz.xpath(".//*[local-name()='infProt']"):
		inf_prot = candidato
		break

	if inf_prot is None:
		return RetornoAutorizacao(
			cstat_lote=cstat_lote,
			motivo_lote=motivo_lote or "",
			lote_processado=cstat_lote in _LOTE_PROCESSADO,
			numero_recibo=texto_em_qualquer_nivel(raiz, "nRec"),
		)

	return RetornoAutorizacao(
		cstat_lote=cstat_lote,
		motivo_lote=motivo_lote or "",
		lote_processado=cstat_lote in _LOTE_PROCESSADO,
		cstat_nfe=texto_filho(inf_prot, "cStat"),
		motivo_nfe=texto_filho(inf_prot, "xMotivo"),
		protocolo=texto_filho(inf_prot, "nProt"),
		data_recebimento=texto_filho(inf_prot, "dhRecbto"),
		chave_conferida=texto_filho(inf_prot, "chNFe"),
	)
