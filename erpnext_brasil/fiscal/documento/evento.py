# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Evento de cancelamento da NF-e (tpEvento 110111).

Por que este módulo existia como `NotImplementedError` até agora
--------------------------------------------------------------------
A ordem completa de `infEvento` não vinha no pacote de leiaute principal (o esquema de
eventos é distribuído à parte). Adivinhar a ordem de um `xs:sequence` é exatamente o
tipo de erro que produz rejeição silenciosa — por isso `transporte_sefaz.cancelar`
recusava a operação em vez de arriscar.

O pacote foi baixado do Portal Nacional da NF-e ("Esquemas XML NF-e/NFC-e - Evento
Cancelamento", atualizado em 21/12/2018) e a estrutura abaixo vem de
`leiauteEventoCancNFe_v1.00.xsd`, lida diretamente — não de memória nem de blog.

A ordem confirmada de `infEvento`
------------------------------------
`cOrgao, tpAmb, (CNPJ|CPF), chNFe, dhEvento, tpEvento, nSeqEvento, verEvento, detEvento`

`tpEvento` é fixo em `"110111"` e `verEvento` fixo em `"1.00"` neste schema — não são
escolha de quem chama, são constantes do próprio evento de cancelamento.

`detEvento` tem `@versao="1.00"` e, em ordem, `descEvento` (texto fixo "Cancelamento"),
`nProt` (protocolo da autorização que está sendo cancelada) e `xJust` (a justificativa —
mesmo limite de 15 a 256 caracteres já usado em `estado.DocumentoFiscal.cancelar`).

A pegadinha do `@Id`
----------------------
O padrão confirmado no XSD é `ID[0-9]{52}`, e a regra é *"ID" + tpEvento + chave da NF-e
+ nSeqEvento*. Decompondo um `Id` real de exemplo (52 dígitos após "ID"): 6 do
`tpEvento`, 44 da chave, e **2** do `nSeqEvento` — só que o **elemento** `nSeqEvento`
segue o padrão `[1-9]|[1][0-9]{0,1}|20` (sem zero à esquerda, ex. `"1"`). O valor dentro
do `@Id` é o mesmo número **preenchido com zero à esquerda até 2 dígitos** (`"01"`). São
duas representações do mesmo número, e usar uma no lugar da outra produz `Id` que não
bate com o padrão — exatamente o tipo de detalhe que só aparece decompondo um exemplo
real, não lendo a documentação em prosa.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.estado import JUSTIFICATIVA_MAXIMA, JUSTIFICATIVA_MINIMA
from erpnext_brasil.fiscal.documento.nfe import NAMESPACE_NFE
from erpnext_brasil.fiscal.documento.resposta_sefaz import RespostaSefazInvalida
from erpnext_brasil.fiscal.validators import validar_cnpj

__all__ = [
	"CODIGOS_SUCESSO_EVENTO",
	"TIPO_EVENTO_CANCELAMENTO",
	"EventoInvalido",
	"RetornoEvento",
	"interpretar_retorno_evento",
	"montar_env_evento",
	"montar_evento_cancelamento",
]

# Diferente da autorização (onde 100 é o único sucesso), o evento de cancelamento tem
# três códigos de sucesso possíveis, confirmados em fonte técnica: 101 (homologado),
# 135 (homologado fora de prazo) e 155 (homologado com data de evento divergente).
CODIGOS_SUCESSO_EVENTO = frozenset({"101", "135", "155"})

TIPO_EVENTO_CANCELAMENTO = "110111"
_VERSAO_EVENTO = "1.00"


class EventoInvalido(ValueError):
	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _formatar_id(chave: str, numero_sequencia: int) -> str:
	"""`"ID" + tpEvento + chave(44) + nSeqEvento(2, com zero à esquerda)`.

	O zero à esquerda só existe aqui — o elemento `nSeqEvento` do corpo do evento não o
	leva.
	"""
	return f"ID{TIPO_EVENTO_CANCELAMENTO}{chave}{numero_sequencia:02d}"


def montar_evento_cancelamento(
	chave_acesso: str,
	protocolo: str,
	justificativa: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do cancelamento.

	`data_evento` já vem formatada (ISO 8601 com fuso, `TDateTimeUTC`) — este módulo não
	decide fuso horário, que é responsabilidade de quem monta o documento.

	`numero_sequencia` só é maior que 1 quando o mesmo evento precisou ser retransmitido
	— não é um contador de tentativa livre, é o campo `nSeqEvento` do próprio schema.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_justificativa = (justificativa or "").strip()

	if not (JUSTIFICATIVA_MINIMA <= len(texto_justificativa) <= JUSTIFICATIVA_MAXIMA):
		raise EventoInvalido(
			f"A justificativa deve ter de {JUSTIFICATIVA_MINIMA} a {JUSTIFICATIVA_MAXIMA} "
			f"caracteres, recebidos {len(texto_justificativa)}",
			"justificativa",
		)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório para cancelar", "protocolo")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id(chave, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chNFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CANCELAMENTO,
		"nSeqEvento": str(numero_sequencia),
		"verEvento": _VERSAO_EVENTO,
		"detEvento": {
			"@versao": _VERSAO_EVENTO,
			"descEvento": "Cancelamento",
			"nProt": protocolo_limpo,
			"xJust": texto_justificativa,
		},
	}

	return {"evento": {"@versao": _VERSAO_EVENTO, "infEvento": inf_evento}}


def montar_env_evento(eventos: list[dict], id_lote: str) -> dict:
	"""Monta `envEvento`, o envelope de lote — até 20 eventos por lote, confirmado no
	XSD (`maxOccurs="20"`)."""
	if not eventos:
		raise EventoInvalido("O lote de eventos precisa de ao menos um evento", "eventos")

	if len(eventos) > 20:
		raise EventoInvalido(
			f"Um lote de eventos admite no máximo 20, recebidos {len(eventos)}", "eventos"
		)

	if not (id_lote or "").strip():
		raise EventoInvalido("idLote é obrigatório", "id_lote")

	return {
		"envEvento": {
			"@xmlns": NAMESPACE_NFE,
			"@versao": _VERSAO_EVENTO,
			"idLote": id_lote.strip(),
			"evento": [e["evento"] for e in eventos],
		}
	}


@dataclass(frozen=True)
class RetornoEvento:
	"""Leitura estruturada de `retEnvEvento` — o `cStat` do lote é de recepção do
	pedido, o de `retEvento/infEvento` é se a SEFAZ de fato homologou o cancelamento."""

	cstat_lote: str
	motivo_lote: str
	cstat_evento: str | None = None
	motivo_evento: str | None = None
	protocolo: str | None = None
	chave_conferida: str | None = None
	data_registro: str | None = None

	@property
	def homologado(self) -> bool:
		return self.cstat_evento in CODIGOS_SUCESSO_EVENTO


def interpretar_retorno_evento(xml_resposta: str | bytes) -> RetornoEvento:
	"""Interpreta `retEnvEvento` (a resposta de `NFeRecepcaoEvento4`).

	Mesma disciplina de `resposta_sefaz.interpretar_autorizacao`: `lxml` com
	`local-name()` via `.xpath()`, nunca `.find()` (que não entende predicado de
	função) nem regex sobre XML.
	"""
	from lxml import etree

	bruto = xml_resposta.encode("utf-8") if isinstance(xml_resposta, str) else xml_resposta

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise RespostaSefazInvalida(f"Resposta da SEFAZ não é XML válido: {e}") from e

	def filho_direto(no, nome: str) -> str | None:
		encontrados = no.xpath(f"*[local-name()='{nome}']")

		return encontrados[0].text.strip() if encontrados and encontrados[0].text else None

	cstat_lote = filho_direto(raiz, "cStat")
	motivo_lote = filho_direto(raiz, "xMotivo")

	if cstat_lote is None:
		raise RespostaSefazInvalida("Resposta sem cStat do lote — não é um retEnvEvento reconhecível")

	inf_evento = None
	for candidato in raiz.xpath(".//*[local-name()='infEvento']"):
		inf_evento = candidato
		break

	if inf_evento is None:
		return RetornoEvento(cstat_lote=cstat_lote, motivo_lote=motivo_lote or "")

	return RetornoEvento(
		cstat_lote=cstat_lote,
		motivo_lote=motivo_lote or "",
		cstat_evento=filho_direto(inf_evento, "cStat"),
		motivo_evento=filho_direto(inf_evento, "xMotivo"),
		protocolo=filho_direto(inf_evento, "nProt"),
		chave_conferida=filho_direto(inf_evento, "chNFe"),
		data_registro=filho_direto(inf_evento, "dhRegEvento"),
	)
