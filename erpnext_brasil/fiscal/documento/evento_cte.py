# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Eventos do CT-e: cancelamento (`tpEvento` 110111, `evCancCTe`) e carta de correção
(`tpEvento` 110110, `evCCeCTe`).

Por que existe
--------------
Fecha mais uma peça de infraestrutura do CT-e, no mesmo espírito de `fiscal/documento/
evento.py` (NF-e). Verificado campo a campo contra o XSD literal (`evCancCTe_v4.00.xsd`,
36 linhas — lido inteiro — e `eventoCTeTiposBasico_v4.00.xsd`, `nfephp-org/sped-cte`), não
suposto por analogia com a NF-e — que, como os incrementos anteriores do CT-e já mostraram
repetidas vezes (`modal`, `procEmi`, `ideEvento`), às vezes bate e às vezes diverge.

`tpEvento` idêntico, `detEvento` idêntico — mas dois pontos genuinamente divergentes
------------------------------------------------------------------------------------------
O código do evento (`"110111"`) e o corpo de `detEvento` (`descEvento`="Cancelamento",
`nProt`, `xJust`) são **idênticos** aos da NF-e — confirmado, não copiado às cegas. Dois
pontos, porém, divergem de verdade:

1. **Limite da justificativa**: `TJust` do CT-e é `minLength=15, maxLength=255` — a NF-e usa
   `256` (`estado.JUSTIFICATIVA_MAXIMA`). Um caractere de diferença que reaproveitar a
   constante da NF-e teria deixado passar despercebido até uma justificativa de exatamente
   256 caracteres ser rejeitada pela SEFAZ.
2. **Onde a versão do evento mora**: a NF-e tem um elemento `verEvento` dentro de
   `infEvento`, fixo em `"1.00"` — independente da versão do próprio leiaute da NF-e. O CT-e
   **não tem** esse elemento; a versão vive só como atributo `detEvento/@versaoEvento`
   (confirmado, padrão `"4.NN"`) e, no nível do `evento` inteiro, `@versao` (tipo
   `TVerEvento`, valor fixo `"4.00"`) — a mesma versão do leiaute do CT-e, não uma numeração
   de evento independente como a NF-e usa.

`@Id` tem 53 dígitos, não 52 — `nSeqEvento` entra com 3 dígitos, não 2
------------------------------------------------------------------------------------------
Confirmado por leitura direta: o padrão é `ID[0-9]{53}` (contra `ID[0-9]{52}` da NF-e). A
composição é a mesma (`"ID" + tpEvento(6) + chave(44) + nSeqEvento`), mas o `nSeqEvento`
dentro do `@Id` do CT-e usa **3** dígitos com zero à esquerda (`"001"`), não 2 (`"01"`) — a
diferença de um dígito no padrão do `@Id` bate exatamente com essa mudança de largura.

A carta de correção do CT-e não é texto livre — é uma lista estruturada de alterações
------------------------------------------------------------------------------------------
Achado real, verificado em `evCCeCTe_v4.00.xsd` (98 linhas, lido inteiro): diferente da NF-e
(`xCorrecao`, texto livre de 15 a 1000 caracteres), a CC-e do CT-e é `infCorrecao`, uma lista
repetível (`maxOccurs="unbounded"`) de correções campo a campo — cada item tem `grupoAlterado`
(o grupo do XSD, ex. `"ide"`, 1-20 caracteres), `campoAlterado` (o nome do campo, 1-20
caracteres), `valorAlterado` (o novo valor, 1-500 caracteres) e `nroItemAlterado` (opcional, o
índice quando o campo corrigido está numa lista — "o índice inicia sempre em 1"). Modelar isso
como texto livre (copiando a forma da NF-e) perderia a estrutura que o schema exige.

`xCondUso` cita uma base legal diferente da NF-e — não é o mesmo texto com nome trocado
------------------------------------------------------------------------------------------
A NF-e cita o § 1º-A do art. 7º do Convênio S/N de 15/12/1970. O CT-e cita o **Art. 58-B do
Convênio SINIEF 06/89** — uma norma diferente, com texto integralmente diferente (a lista de
restrições também muda: a NF-e fala em "remetente ou destinatário", o CT-e em "emitente,
tomador, remetente ou destinatário" — mais uma parte porque o CT-e tem mais papéis
envolvidos). `XCONDUSO_CCE_CTE` é uma constante nova, não um reaproveitamento com o nome
trocado.

Reuso: `assinar_evento` e `EventoInvalido` de `evento.py`, sem alteração
------------------------------------------------------------------------------
`assinar_evento` já era genérica (não hardcoda `NAMESPACE_NFE`, só lê o que o dicionário
`evento` já tem) — reaproveitada direto. `EventoInvalido` também: mensagem + campo, nenhuma
lógica específica de NF-e embutida.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

from erpnext_brasil.fiscal.cte import NAMESPACE_CTE
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.evento import EventoInvalido, assinar_evento
from erpnext_brasil.fiscal.validators import validar_cnpj

__all__ = [
	"JUSTIFICATIVA_MAXIMA_CTE",
	"JUSTIFICATIVA_MINIMA_CTE",
	"TIPO_EVENTO_CANCELAMENTO_CTE",
	"TIPO_EVENTO_CORRECAO_CTE",
	"XCONDUSO_CCE_CTE",
	"CorrecaoCte",
	"EventoInvalido",
	"assinar_evento",
	"montar_env_evento_cte",
	"montar_evento_cancelamento_cte",
	"montar_evento_correcao_cte",
]

TIPO_EVENTO_CANCELAMENTO_CTE = "110111"
TIPO_EVENTO_CORRECAO_CTE = "110110"
_VERSAO_LEIAUTE_CTE = "4.00"

# `TJust` do CT-e — diverge do máximo de 256 da NF-e (`estado.JUSTIFICATIVA_MAXIMA`).
JUSTIFICATIVA_MINIMA_CTE = 15
JUSTIFICATIVA_MAXIMA_CTE = 255

# Texto fixo de `xCondUso` da CC-e do CT-e — confirmado caractere a caractere em
# `evCCeCTe_v4.00.xsd`. Base legal diferente da NF-e (Art. 58-B do Convênio SINIEF 06/89,
# não o Art. 7º do Convênio S/N de 1970) — não é o mesmo texto com o nome do documento
# trocado, ver docstring do módulo.
XCONDUSO_CCE_CTE = (
	"A Carta de Correção é disciplinada pelo Art. 58-B do CONVÊNIO/SINIEF 06/89: Fica "
	"permitida a utilização de carta de correção, para regularização de erro ocorrido na "
	"emissão de documentos fiscais relativos à prestação de serviço de transporte, desde "
	"que o erro não esteja relacionado com: I - as variáveis que determinam o valor do "
	"imposto tais como: base de cálculo, alíquota, diferença de preço, quantidade, valor "
	"da prestação;II - a correção de dados cadastrais que implique mudança do emitente, "
	"tomador, remetente ou do destinatário;III - a data de emissão ou de saída."
)


def _formatar_id_cte(chave: str, tipo_evento: str, numero_sequencia: int) -> str:
	"""`"ID" + tpEvento + chave(44) + nSeqEvento(3, com zero à esquerda)` — 3 dígitos,
	não 2 como na NF-e (`evento._formatar_id`); confirmado pelo padrão `ID[0-9]{53}`."""
	return f"ID{tipo_evento}{chave}{numero_sequencia:03d}"


@dataclass(frozen=True)
class CorrecaoCte:
	"""Um item de `infCorrecao` — uma correção campo a campo (não texto livre, ver
	docstring do módulo)."""

	grupo_alterado: str
	campo_alterado: str
	valor_alterado: str
	numero_item_alterado: int | None = None

	def __post_init__(self):
		if not (1 <= len(self.grupo_alterado) <= 20):
			raise EventoInvalido(
				f"grupoAlterado deve ter de 1 a 20 caracteres, recebido {self.grupo_alterado!r}",
				"grupo_alterado",
			)

		if not (1 <= len(self.campo_alterado) <= 20):
			raise EventoInvalido(
				f"campoAlterado deve ter de 1 a 20 caracteres, recebido {self.campo_alterado!r}",
				"campo_alterado",
			)

		if not (1 <= len(self.valor_alterado) <= 500):
			raise EventoInvalido(
				f"valorAlterado deve ter de 1 a 500 caracteres, recebido {self.valor_alterado!r}",
				"valor_alterado",
			)

		if self.numero_item_alterado is not None and not (1 <= self.numero_item_alterado <= 99):
			raise EventoInvalido(
				f"nroItemAlterado deve estar entre 1 e 99 (o índice começa em 1), "
				f"recebido {self.numero_item_alterado}",
				"numero_item_alterado",
			)


def _montar_inf_correcao(correcao: CorrecaoCte) -> dict:
	item = {
		"grupoAlterado": correcao.grupo_alterado,
		"campoAlterado": correcao.campo_alterado,
		"valorAlterado": correcao.valor_alterado,
	}

	if correcao.numero_item_alterado is not None:
		item["nroItemAlterado"] = str(correcao.numero_item_alterado)

	return item


def montar_evento_cancelamento_cte(
	chave_acesso: str,
	protocolo: str,
	justificativa: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do cancelamento do CT-e.

	Mesma costura de `evento.montar_evento_cancelamento`, com as divergências
	confirmadas no XSD do CT-e: `chCTe` no lugar de `chNFe`, `versaoEvento` como
	atributo de `detEvento` no lugar do elemento `verEvento`, `@Id` de 53 dígitos, e
	limite de justificativa de 255 caracteres.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_justificativa = (justificativa or "").strip()

	if not (JUSTIFICATIVA_MINIMA_CTE <= len(texto_justificativa) <= JUSTIFICATIVA_MAXIMA_CTE):
		raise EventoInvalido(
			f"A justificativa deve ter de {JUSTIFICATIVA_MINIMA_CTE} a "
			f"{JUSTIFICATIVA_MAXIMA_CTE} caracteres, recebidos {len(texto_justificativa)}",
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
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_CANCELAMENTO_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CANCELAMENTO_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": "Cancelamento",
			"nProt": protocolo_limpo,
			"xJust": texto_justificativa,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_evento_correcao_cte(
	chave_acesso: str,
	correcoes: list[CorrecaoCte],
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da carta de correção do CT-e.

	`correcoes` é a lista de alterações campo a campo (`infCorrecao`) — não um texto
	livre como na NF-e (ver docstring do módulo). O XSD não impede repetir a mesma
	correção anterior numa carta nova (diferente da regra de negócio da NF-e, onde a
	CC-e nova precisa reunir o histórico inteiro em texto) — aqui cada carta é a lista
	completa de alterações que ela reporta, e é responsabilidade de quem chama decidir
	se isso inclui correções já reportadas antes.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	if not correcoes:
		raise EventoInvalido("A carta de correção precisa de ao menos uma correção", "correcoes")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_CORRECAO_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CORRECAO_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": "Carta de Correção",
			"infCorrecao": [_montar_inf_correcao(c) for c in correcoes],
			"xCondUso": XCONDUSO_CCE_CTE,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_env_evento_cte(eventos: list[dict], id_lote: str) -> dict:
	"""Monta `envEvento` do CT-e — mesma disciplina de `evento.montar_env_evento`
	(até 20 eventos por lote), com o namespace do CT-e."""
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
			"@xmlns": NAMESPACE_CTE,
			"@versao": _VERSAO_LEIAUTE_CTE,
			"idLote": id_lote.strip(),
			"evento": [e["evento"] for e in eventos],
		}
	}
