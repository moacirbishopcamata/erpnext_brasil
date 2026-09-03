# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""EFD-Reinf R-2099 (evtFechamento): Fechamento dos Eventos Periódicos.

Por que existe — a outra metade do gatilho da DCTFWeb
------------------------------------------------------------------------------
Continuação direta de `folha/esocial_s1299.py`: a DCTFWeb é disparada pelos eventos de
fechamento do eSocial **e** do EFD-Reinf, não por um arquivo próprio (ver docstring daquele
módulo). Este é o segundo gatilho — o evento de fechamento do EFD-Reinf, `evtFechamento`
(código R-2099).

O evento, verificado contra o XSD literal
------------------------------------------------------------------------------
`R-2099-evtFechamento-v2_01_02_B.xsd` (`nfephp-org/sped-efdreinf`, 244 linhas — lido inteiro).
Quatro grupos: `ideEvento`, `ideContri`, `ideRespInf` (opcional) e `infoFech`.

**Achado real**: diferente do S-1299, o R-2099 **não tem** nenhum campo equivalente a
`transDCTFWeb` — o gatilho explícito de "solicitar transmissão imediata da DCTFWeb" existe só
do lado do eSocial. Não suposto por analogia (o R-2099 tem sua própria versão de `infoFech`,
com sete indicadores `S`/`N`, todos obrigatórios — nenhum opcional como no S-1299) — confirmado
por leitura direta do XSD, sem esse campo em lugar nenhum do evento.

`ideEvento` do R-2099 não é o mesmo tipo do R-4020 — mesma lição do S-1299/S-1200
------------------------------------------------------------------------------------------
`reinf_r4020.IdeEvento` tem `ind_retif`/`nr_recibo` (evento de folha, sujeito a retificação);
`ideEvento` do R-2099 **não tem** nenhum dos dois — só `perApur`, `tpAmb`, `procEmi`, `verProc`.
Mesma categoria de erro já evitada duas vezes neste projeto (`modal` do CT-e/MDF-e,
`ideEvento` do S-1299/S-1200): tipos com o mesmo nome de grupo em documentos irmãos não são
garantidamente o mesmo tipo — cada um verificado individualmente. `perApur` aqui também tem um
padrão de validação mais explícito no próprio XSD (`xs:gYearMonth` com `pattern
"20([1-9][0-9])-(0[1-9]|1[0-2])"`) do que o `len() == 7` usado nos outros eventos — mesma regra
de fundo (formato AAAA-MM), verificação mais direta.

Reuso: `IdeContri` de `reinf_r4020.py`, sem alteração
------------------------------------------------------------------------------
Mesmo `tpInsc` (`1|2`) e `nrInsc` (8/11/14 dígitos) confirmados idênticos entre os dois eventos
— reaproveitado diretamente, mesmo padrão de `esocial_s1299.py` reaproveitar `IdeEmpregador` do
S-1200.

Funções puras: nenhuma dependência do Frappe.
"""

import re
from dataclasses import dataclass

from erpnext_brasil.contabil.reinf_r4020 import (
	AMBIENTE_PRODUCAO,
	AMBIENTE_PRODUCAO_RESTRITA,
	IdeContri,
	ReinfInvalido,
)

__all__ = [
	"AMBIENTE_PRODUCAO",
	"AMBIENTE_PRODUCAO_RESTRITA",
	"IdeContri",
	"IdeEventoFechamento",
	"IdeRespInf",
	"InfoFechamentoReinf",
	"ReinfInvalido",
	"montar_info_fech_reinf",
]

_PADRAO_PER_APUR = re.compile(r"^20[1-9][0-9]-(0[1-9]|1[0-2])$")


def _sim_nao(valor: bool) -> str:
	return "S" if valor else "N"


@dataclass(frozen=True)
class IdeEventoFechamento:
	"""`ideEvento` do R-2099 — sem `indRetif`/`nrRecibo`, diferente de
	`reinf_r4020.IdeEvento` (que tem os dois)."""

	per_apur: str
	tp_amb: int
	proc_emi: int
	ver_proc: str

	def __post_init__(self):
		if not _PADRAO_PER_APUR.match(self.per_apur):
			raise ReinfInvalido(
				f"perApur deve seguir o padrão AAAA-MM, entre 2010-01 e 2099-12, recebido {self.per_apur!r}"
			)

		if self.tp_amb not in (AMBIENTE_PRODUCAO, AMBIENTE_PRODUCAO_RESTRITA):
			raise ReinfInvalido(
				f"tpAmb deve ser 1 (Produção) ou 2 (Produção Restrita), recebido {self.tp_amb}"
			)

		if self.proc_emi not in (1, 2):
			raise ReinfInvalido(f"procEmi deve ser 1 ou 2 neste evento, recebido {self.proc_emi}")

		if not (1 <= len(self.ver_proc) <= 20):
			raise ReinfInvalido(f"verProc deve ter entre 1 e 20 caracteres, recebido {self.ver_proc!r}")


@dataclass(frozen=True)
class IdeRespInf:
	"""`ideRespInf` — responsável pelas informações prestadas, grupo opcional."""

	nome: str
	cpf: str
	telefone: str = ""
	email: str = ""

	def __post_init__(self):
		if not (1 <= len(self.nome) <= 70):
			raise ReinfInvalido(f"nmResp deve ter entre 1 e 70 caracteres, recebido {self.nome!r}")

		if not (self.cpf.isdigit() and len(self.cpf) == 11):
			raise ReinfInvalido(f"cpfResp deve ter 11 dígitos numéricos, recebido {self.cpf!r}")


@dataclass(frozen=True)
class InfoFechamentoReinf:
	"""`infoFech` do R-2099 — sete indicadores, **todos obrigatórios** (diferente do
	S-1299, onde `indExcApur1250`/`transDCTFWeb`/`naoValid` eram opcionais — aqui o
	XSD não tem nenhum campo opcional dentro de `infoFech`)."""

	servicos_tomados: bool
	servicos_prestados: bool
	recebimento_assoc_desportiva: bool
	repasse_assoc_desportiva: bool
	comercializacao_producao_rural: bool
	cprb: bool
	aquisicao_producao_rural: bool


def montar_info_fech_reinf(info: InfoFechamentoReinf) -> dict:
	"""Monta o grupo `infoFech` do R-2099."""
	return {
		"evtServTm": _sim_nao(info.servicos_tomados),
		"evtServPr": _sim_nao(info.servicos_prestados),
		"evtAssDespRec": _sim_nao(info.recebimento_assoc_desportiva),
		"evtAssDespRep": _sim_nao(info.repasse_assoc_desportiva),
		"evtComProd": _sim_nao(info.comercializacao_producao_rural),
		"evtCPRB": _sim_nao(info.cprb),
		"evtAquis": _sim_nao(info.aquisicao_producao_rural),
	}
