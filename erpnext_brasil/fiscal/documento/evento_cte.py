# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Evento de cancelamento do CT-e (`tpEvento` 110111) — `evCancCTe`.

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

Reuso: `assinar_evento` e `EventoInvalido` de `evento.py`, sem alteração
------------------------------------------------------------------------------
`assinar_evento` já era genérica (não hardcoda `NAMESPACE_NFE`, só lê o que o dicionário
`evento` já tem) — reaproveitada direto. `EventoInvalido` também: mensagem + campo, nenhuma
lógica específica de NF-e embutida.

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.fiscal.cte import NAMESPACE_CTE
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.evento import EventoInvalido, assinar_evento
from erpnext_brasil.fiscal.validators import validar_cnpj

__all__ = [
	"JUSTIFICATIVA_MAXIMA_CTE",
	"JUSTIFICATIVA_MINIMA_CTE",
	"TIPO_EVENTO_CANCELAMENTO_CTE",
	"EventoInvalido",
	"assinar_evento",
	"montar_env_evento_cte",
	"montar_evento_cancelamento_cte",
]

TIPO_EVENTO_CANCELAMENTO_CTE = "110111"
_VERSAO_LEIAUTE_CTE = "4.00"

# `TJust` do CT-e — diverge do máximo de 256 da NF-e (`estado.JUSTIFICATIVA_MAXIMA`).
JUSTIFICATIVA_MINIMA_CTE = 15
JUSTIFICATIVA_MAXIMA_CTE = 255


def _formatar_id_cte(chave: str, tipo_evento: str, numero_sequencia: int) -> str:
	"""`"ID" + tpEvento + chave(44) + nSeqEvento(3, com zero à esquerda)` — 3 dígitos,
	não 2 como na NF-e (`evento._formatar_id`); confirmado pelo padrão `ID[0-9]{53}`."""
	return f"ID{tipo_evento}{chave}{numero_sequencia:03d}"


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
