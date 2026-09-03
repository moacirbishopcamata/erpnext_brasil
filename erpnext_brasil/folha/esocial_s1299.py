# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial S-1299 (evtFechaEvPer): Fechamento dos Eventos Periódicos.

Por que existe — a peça real por trás do que "DCTFWeb" significa neste projeto
------------------------------------------------------------------------------
Investigado a pedido de "continuar" o backlog de obrigações acessórias (DCTFWeb, item
registrado desde 2026-08-31). Achado que reformula o escopo: **a DCTFWeb não é um arquivo que
o contribuinte constrói**. Confirmado por busca agregada — o sistema é ativado automaticamente
pela Receita Federal depois que os eventos de fechamento do eSocial (S-1299, este módulo) e do
EFD-Reinf (R-2099, não implementado ainda) são transmitidos com sucesso; não há layout de
arquivo para "montar uma DCTFWeb", há um evento de fechamento que a **dispara**. O campo
`transDCTFWeb` deste evento (linha abaixo) é a confirmação direta disso: "Solicitação de
transmissão imediata da DCTFWeb" — é literalmente o gatilho.

O que este módulo cobre
------------------------------
O evento inteiro, verificado contra o XSD literal (`evtFechaEvPer.xsd`, `nfephp-org/
sped-esocial`, 112 linhas — pequeno o suficiente para ler inteiro): `ideEvento` (tipo próprio
`T_ideEvento_folha_sem_retificacao`, **não** reaproveitado de `esocial_s1200.IdeEvento` — ver
seção própria abaixo), `ideEmpregador` (reaproveitado de `esocial_s1200`, mesmo tipo
`TEmpregador` confirmado idêntico) e `infoFech` (os indicadores de quais eventos periódicos
existiram no período, mais os três campos de controle: `indExcApur1250`, `transDCTFWeb`,
`naoValid`).

`ideEvento` do S-1299 não é o mesmo tipo do S-1200 — não reaproveitar por analogia
------------------------------------------------------------------------------------------
Confirmado por leitura direta de `tipos.xsd`: o `ideEvento` do S-1299 usa
`T_ideEvento_folha_sem_retificacao` — **sem** `indRetif`/`nrRecibo` (o evento de fechamento não
tem retificação no mesmo sentido dos eventos de folha) — e **com** um campo que o S-1200 não
tem, `indGuia` (opcional). Reaproveitar `esocial_s1200.IdeEvento` aqui produziria um objeto com
campos que o XSD do S-1299 nem tem (`indRetif`/`nrRecibo`) e sem um que ele tem (`indGuia`) —
mesma categoria de erro já evitada ao não reaproveitar o `modal` do CT-e no MDF-e
(`docs/mdfe-estado.md`). Por isso `IdeEventoFechamento` é uma dataclass nova, não um alias.

`indGuia`: campo quase vazio de propósito, não esquecido
------------------------------------------------------------------------------
Confirmado em fonte secundária (documentação técnica de ERP, mesmo padrão de confiança já usado
para DeSTDA): `indGuia` só tem um valor definido hoje (`1` = DAE, Documento de Arrecadação do
eSocial) e a própria documentação do campo diz "será tratado em versões futuras" — não é uma
enumeração incompleta por falta de investigação, é o próprio leiaute ainda não ter mais opções.

Reuso: `IdeEmpregador` de `esocial_s1200.py`, sem alteração
------------------------------------------------------------------------------
Mesmo tipo `TEmpregador` — confirmado, não suposto — reaproveitado diretamente, mesmo padrão de
`esocial_s2299.py` reaproveitar `DmDev` do S-1200.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

from erpnext_brasil.folha.esocial_s1200 import (
	AMBIENTE_PRODUCAO,
	AMBIENTE_PRODUCAO_RESTRITA,
	INDICADOR_APURACAO_DECIMO_TERCEIRO,
	INDICADOR_APURACAO_MENSAL,
	EsocialInvalido,
	IdeEmpregador,
	validar_digito_unico,
)

__all__ = [
	"INDICADOR_GUIA_DAE",
	"IdeEmpregador",
	"IdeEventoFechamento",
	"InfoFechamento",
	"montar_info_fech",
]

# `indGuia` — só um valor definido no leiaute hoje, ver docstring do módulo.
INDICADOR_GUIA_DAE = 1


def _sim_nao(valor: bool) -> str:
	return "S" if valor else "N"


@dataclass(frozen=True)
class IdeEventoFechamento:
	"""Grupo `ideEvento` do S-1299 (`T_ideEvento_folha_sem_retificacao`) — sem
	`indRetif`/`nrRecibo`, com `indGuia` (que `esocial_s1200.IdeEvento` não tem)."""

	ind_apuracao: int
	per_apur: str
	tp_amb: int
	proc_emi: int
	ver_proc: str
	ind_guia: int | None = None

	def __post_init__(self):
		if self.ind_apuracao not in (INDICADOR_APURACAO_MENSAL, INDICADOR_APURACAO_DECIMO_TERCEIRO):
			raise EsocialInvalido(
				f"indApuracao deve ser 1 (mensal) ou 2 (décimo terceiro), recebido {self.ind_apuracao}"
			)

		if self.ind_apuracao == INDICADOR_APURACAO_MENSAL and len(self.per_apur) != 7:
			raise EsocialInvalido(
				f"perApur deve ter 7 caracteres (formato AAAA-MM) quando indApuracao=1, "
				f"recebido {self.per_apur!r}"
			)

		if self.ind_apuracao == INDICADOR_APURACAO_DECIMO_TERCEIRO and len(self.per_apur) != 4:
			raise EsocialInvalido(
				f"perApur deve ter 4 caracteres (formato AAAA) quando indApuracao=2, "
				f"recebido {self.per_apur!r}"
			)

		if self.tp_amb not in (AMBIENTE_PRODUCAO, AMBIENTE_PRODUCAO_RESTRITA):
			raise EsocialInvalido(
				f"tpAmb deve ser 1 (Produção) ou 2 (Produção Restrita), recebido {self.tp_amb}"
			)

		validar_digito_unico(self.proc_emi, "procEmi")

		if not (1 <= len(self.ver_proc) <= 20):
			raise EsocialInvalido(f"verProc deve ter entre 1 e 20 caracteres, recebido {self.ver_proc!r}")

		if self.ind_guia is not None and self.ind_guia != INDICADOR_GUIA_DAE:
			raise EsocialInvalido(
				f"indGuia só tem o valor {INDICADOR_GUIA_DAE} (DAE) definido no leiaute atual, "
				f"recebido {self.ind_guia}"
			)


@dataclass(frozen=True)
class InfoFechamento:
	"""Grupo `infoFech` — indicadores de quais eventos periódicos existiram no período,
	mais os três campos de controle opcionais.

	Cada indicador `evt_*` é a confirmação de que o evento correspondente foi (ou não)
	enviado para o período — o XSD documenta a regra de consistência (ex.: `evt_remun`
	em `True` exige que exista S-1200/S-1202/S-1207/S-2299/S-2399 para o período), mas
	**este módulo não verifica isso** — checar contra os eventos de fato enviados é
	responsabilidade de quem monta o fechamento (teria acesso ao lote inteiro), não
	deste grupo isolado.
	"""

	evt_remun: bool
	evt_pgtos: bool
	evt_com_prod: bool
	evt_contrat_av_np: bool
	evt_info_compl_per: bool
	ind_exc_apur_1250: bool = False
	trans_dctfweb: bool = False
	"""Solicitação de transmissão imediata da DCTFWeb — o campo que efetivamente
	dispara a geração da declaração, não um arquivo separado (ver docstring do
	módulo)."""
	nao_valid: bool | None = None
	"""`None` (campo não informado) e `True` têm o mesmo efeito no XSD — "não executa
	REGRA_VALIDA_FECHAMENTO_FOPAG". Só `False` (`"N"`) executa a regra de verdade.
	Modelado como `bool | None` em vez de só `bool` para não forçar quem monta o
	fechamento a escolher entre as duas formas equivalentes de "não informado"."""


def montar_info_fech(info: InfoFechamento) -> dict:
	"""Monta o grupo `infoFech`."""
	grupo: dict = {
		"evtRemun": _sim_nao(info.evt_remun),
		"evtPgtos": _sim_nao(info.evt_pgtos),
		"evtComProd": _sim_nao(info.evt_com_prod),
		"evtContratAvNP": _sim_nao(info.evt_contrat_av_np),
		"evtInfoComplPer": _sim_nao(info.evt_info_compl_per),
	}

	if info.ind_exc_apur_1250:
		grupo["indExcApur1250"] = "S"

	if info.trans_dctfweb:
		grupo["transDCTFWeb"] = "S"

	if info.nao_valid is not None:
		grupo["naoValid"] = _sim_nao(info.nao_valid)

	return grupo
