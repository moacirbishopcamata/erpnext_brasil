# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Eventos da NF-e: cancelamento (tpEvento 110111) e carta de correção (tpEvento 110110).

Por que este módulo existia como `NotImplementedError` até agora
--------------------------------------------------------------------
A ordem completa de `infEvento` não vinha no pacote de leiaute principal (o esquema de
eventos é distribuído à parte). Adivinhar a ordem de um `xs:sequence` é exatamente o
tipo de erro que produz rejeição silenciosa — por isso `transporte_sefaz.cancelar`
recusava a operação em vez de arriscar.

O pacote de cancelamento foi baixado do Portal Nacional da NF-e ("Esquemas XML
NF-e/NFC-e - Evento Cancelamento", atualizado em 21/12/2018) e a estrutura abaixo vem
de `leiauteEventoCancNFe_v1.00.xsd`, lida diretamente — não de memória nem de blog. O
esquema da carta de correção (`leiauteCCe_v1.00.xsd`) foi confirmado à parte, pela
mesma via — o corpo de `infEvento` é idêntico entre os dois eventos; só `detEvento`
muda.

A ordem confirmada de `infEvento` (comum aos dois eventos)
------------------------------------------------------------
`cOrgao, tpAmb, (CNPJ|CPF), chNFe, dhEvento, tpEvento, nSeqEvento, verEvento, detEvento`

`tpEvento` é fixo por evento (`"110111"` cancelamento, `"110110"` carta de correção) e
`verEvento` fixo em `"1.00"` — não são escolha de quem chama.

`detEvento` do cancelamento tem `@versao="1.00"` e, em ordem, `descEvento` (texto fixo
"Cancelamento"), `nProt` (protocolo da autorização que está sendo cancelada) e `xJust`
(a justificativa — mesmo limite de 15 a 256 caracteres já usado em
`estado.DocumentoFiscal.cancelar`).

`detEvento` da carta de correção tem `@versao="1.00"` e, em ordem, `descEvento` (texto
fixo, o XSD aceita tanto "Carta de Correção" quanto "Carta de Correcao" — a variante sem
cedilha é a usada pela maioria das implementações de referência, mas este módulo usa a
acentuada, também válida), `xCorrecao` (o texto da correção, 15 a 1000 caracteres — não
15 a 256 como a justificativa de cancelamento, limite diferente confirmado no XSD) e
`xCondUso` (texto fixo obrigatório, o XSD restringe a exatamente duas variantes —
acentuada e não-acentuada — do mesmo aviso legal; não é campo livre, é enumeração).
**Uma CC-e nunca substitui a anterior** — cada nova carta deve reunir o texto de todas
as correções já feitas, não só a mais recente (regra de negócio da SEFAZ, não imposta
por este módulo, que só monta uma carta por vez).

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

Por que `cStat` de sucesso não é um único conjunto para todo evento
----------------------------------------------------------------------
`135` ("Evento registrado e vinculado a NF-e") é o código genérico de homologação de
**qualquer** evento recebido via `NFeRecepcaoEvento4` — confirmado num exemplo real de
carta de correção homologada. Mas o cancelamento tem códigos próprios adicionais (`101`
"Cancelamento de NF-e homologado", `155` "Cancelamento homologado fora de prazo") que
não fazem sentido para nenhum outro evento — usá-los para julgar sucesso de uma CC-e
seria aceitar como homologado um `cStat` que nunca vai aparecer nesse contexto, mas o
erro oposto (usar só `135` para tudo) rejeitaria cancelamentos genuinamente homologados
com um desses códigos específicos. Por isso o sucesso é resolvido por `tpEvento`, lido
da própria resposta — não por um conjunto único.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.estado import JUSTIFICATIVA_MAXIMA, JUSTIFICATIVA_MINIMA
from erpnext_brasil.fiscal.documento.nfe import NAMESPACE_NFE
from erpnext_brasil.fiscal.documento.resposta_sefaz import RespostaSefazInvalida
from erpnext_brasil.fiscal.validators import validar_cnpj

__all__ = [
	"CODIGOS_SUCESSO_CANCELAMENTO",
	"CODIGOS_SUCESSO_CORRECAO",
	"CORRECAO_MAXIMA",
	"CORRECAO_MINIMA",
	"TIPO_EVENTO_CANCELAMENTO",
	"TIPO_EVENTO_CORRECAO",
	"XCONDUSO_CCE",
	"EventoInvalido",
	"RetornoEvento",
	"interpretar_retorno_evento",
	"montar_env_evento",
	"montar_evento_cancelamento",
	"montar_evento_correcao",
]

TIPO_EVENTO_CANCELAMENTO = "110111"
TIPO_EVENTO_CORRECAO = "110110"
_VERSAO_EVENTO = "1.00"

# 135 é o código genérico de qualquer evento; 101 e 155 só existem para cancelamento
# (ver docstring do módulo — por que não há um único conjunto para todo evento).
CODIGOS_SUCESSO_CANCELAMENTO = frozenset({"101", "135", "155"})
CODIGOS_SUCESSO_CORRECAO = frozenset({"135"})
_CODIGOS_SUCESSO_POR_EVENTO = {
	TIPO_EVENTO_CANCELAMENTO: CODIGOS_SUCESSO_CANCELAMENTO,
	TIPO_EVENTO_CORRECAO: CODIGOS_SUCESSO_CORRECAO,
}
# Fallback para um tpEvento não mapeado aqui: só o código genérico, nunca os específicos
# de cancelamento — ver a mesma nota.
_CODIGO_SUCESSO_GENERICO = frozenset({"135"})

CORRECAO_MINIMA = 15
CORRECAO_MAXIMA = 1000

# Texto fixo de `xCondUso`, confirmado caractere a caractere em `leiauteCCe_v1.00.xsd`
# (o XSD restringe o campo a uma enumeração de duas variantes — esta e uma sem
# acentuação — não é texto livre).
XCONDUSO_CCE = (
	"A Carta de Correção é disciplinada pelo § 1º-A do art. 7º do Convênio S/N, "
	"de 15 de dezembro de 1970 e pode ser utilizada para regularização de erro "
	"ocorrido na emissão de documento fiscal, desde que o erro não esteja "
	"relacionado com: I - as variáveis que determinam o valor do imposto tais "
	"como: base de cálculo, alíquota, diferença de preço, quantidade, valor da "
	"operação ou da prestação; II - a correção de dados cadastrais que implique "
	"mudança do remetente ou do destinatário; III - a data de emissão ou de saída."
)


class EventoInvalido(ValueError):
	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _formatar_id(chave: str, tipo_evento: str, numero_sequencia: int) -> str:
	"""`"ID" + tpEvento + chave(44) + nSeqEvento(2, com zero à esquerda)`.

	O zero à esquerda só existe aqui — o elemento `nSeqEvento` do corpo do evento não o
	leva.
	"""
	return f"ID{tipo_evento}{chave}{numero_sequencia:02d}"


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
		"@Id": _formatar_id(chave, TIPO_EVENTO_CANCELAMENTO, numero_sequencia),
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


def montar_evento_correcao(
	chave_acesso: str,
	texto_correcao: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da carta de correção (110110).

	`texto_correcao` é só o texto desta carta — quem chama é responsável por já incluir
	nele as correções de cartas anteriores, se houver (regra de negócio da SEFAZ: uma
	CC-e nova substitui a anterior para exibição, mas precisa reunir todo o histórico).
	`xCondUso` é sempre o texto fixo `XCONDUSO_CCE`, não um parâmetro — o XSD não permite
	outro valor.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_limpo = (texto_correcao or "").strip()

	if not (CORRECAO_MINIMA <= len(texto_limpo) <= CORRECAO_MAXIMA):
		raise EventoInvalido(
			f"O texto da correção deve ter de {CORRECAO_MINIMA} a {CORRECAO_MAXIMA} "
			f"caracteres, recebidos {len(texto_limpo)}",
			"texto_correcao",
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id(chave, TIPO_EVENTO_CORRECAO, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chNFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CORRECAO,
		"nSeqEvento": str(numero_sequencia),
		"verEvento": _VERSAO_EVENTO,
		"detEvento": {
			"@versao": _VERSAO_EVENTO,
			"descEvento": "Carta de Correção",
			"xCorrecao": texto_limpo,
			"xCondUso": XCONDUSO_CCE,
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
	pedido, o de `retEvento/infEvento` é se a SEFAZ de fato homologou o evento."""

	cstat_lote: str
	motivo_lote: str
	cstat_evento: str | None = None
	motivo_evento: str | None = None
	protocolo: str | None = None
	chave_conferida: str | None = None
	data_registro: str | None = None
	tipo_evento: str | None = None

	@property
	def homologado(self) -> bool:
		"""Sucesso depende de qual evento é — ver a nota no topo do módulo sobre por que
		não existe um único conjunto de `cStat` de sucesso para todo tipo de evento."""
		codigos = _CODIGOS_SUCESSO_POR_EVENTO.get(self.tipo_evento, _CODIGO_SUCESSO_GENERICO)

		return self.cstat_evento in codigos


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
		tipo_evento=filho_direto(inf_evento, "tpEvento"),
	)
