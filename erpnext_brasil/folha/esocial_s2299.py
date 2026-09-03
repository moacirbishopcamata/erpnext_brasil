# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial S-2299 (evtDeslig): Desligamento de Trabalhador.

Par natural do S-2200 (`esocial_s2200.py`) — o evento que fecha o vínculo aberto lá.

`verbasResc.dmDev` reaproveita de verdade a estrutura do S-1200 — não por parecer,
por ser a mesma
------------------------------------------------------------------------------------------
Diferente de toda pegadinha "parece igual mas não é" já registrada neste bloco
eSocial (`tpInsc` do envelope, hash da assinatura, `procEmi` do S-2200), aqui é o
oposto: as verbas rescisórias (`verbasResc/dmDev`) usam **o mesmo complexType**
`dmDev` já modelado em `esocial_s1200.DmDev` (confirmado pela fonte: "Inclui
estabelecimentos (`infoPerApur`/`infoPerAnt`) e detalhamento de rubricas" — a mesma
árvore `InfoPerApur`/`IdeEstabLot`/`RemunPerApur`/`ItemRemuneracao`). Por isso
`VerbasResc` deste módulo importa e reaproveita `esocial_s1200.DmDev` diretamente,
em vez de duplicar a árvore inteira de novo.

`ideEvento` é, de novo, um tipo próprio — e `procEmi` diverge de um jeito novo
------------------------------------------------------------------------------------------
`T_ideEvento_trab_indGuia` (lido em `tipos.xsd`): `indRetif`, `nrRecibo`, `indGuia`
(campo novo, não visto nos outros dois eventos — indicador relacionado à guia de
recolhimento rescisório, domínio de `TS_indGuia` não localizado nesta rodada, aceito
por formato), `tpAmb`, `procEmi`, `verProc`. Note que `procEmi` aqui usa o tipo
genérico `TS_procEmi` (dígito 0-9 livre) — **não** `TS_procEmi_sem_8` como no
S-2200. Três eventos, três variações diferentes de `procEmi` já confirmadas neste
projeto (S-1200: livre; S-2200: exclui 8; S-2299: livre de novo) — nenhuma
suposição, cada uma lida na fonte.

`mtvDeslig`: Tabela 19, genuinamente não localizada
------------------------------------------------------------
O motivo do desligamento é um código de 2 dígitos que referencia a "Tabela 19" do
eSocial — confirmado que **não** está embutida em nenhum dos XSDs consultados
(`evtDeslig.xsd` nem `tipos.xsd`), diferente das quatro tabelas de incidência do
S-1010, que estavam. `mtv_deslig` é aceito só por formato (2 dígitos), sem validar
contra a tabela real. Isso limita, por ora, qualquer ponte automática com
`folha/fgts.calcular_multa_rescisoria` (que usa chaves semânticas como
`"sem_justa_causa"`/`"acordo"`, não os códigos numéricos da Tabela 19) — uma função
de tradução entre os dois exigiria a tabela real, que não foi trazida para este
projeto.

O que fica de fora, deliberadamente
------------------------------------------
- **`pensAlim`/`percAliment`** (pensão alimentícia sobre a rescisão) — os tipos
  `TS_pensAlim`/`TS_percAliment` não foram localizados nesta rodada (a busca
  truncou antes de alcançá-los); niche o bastante para não valer inventar o formato.
- **`procJudTrab`/`infoMV`/`procCS`** dentro de `verbasResc` — mesma decisão de
  excluir esses grupos raros já tomada em `esocial_s1200.IdeTrabalhador`.
- **Serialização XML/assinatura/envio** — mesmo padrão dos outros eventos.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date

from erpnext_brasil.folha.esocial_s1200 import DmDev

__all__ = ["EsocialS2299Invalido", "IdeEvento", "InfoDeslig", "VerbasResc"]


class EsocialS2299Invalido(ValueError):
	"""Dado que impede a montagem do evento — campo fora do padrão do XSD."""


def _validar_digito_unico(valor: int, campo: str) -> None:
	if not (0 <= valor <= 9):
		raise EsocialS2299Invalido(f"{campo} deve ser um dígito único (0-9), recebido {valor}")


@dataclass(frozen=True)
class IdeEvento:
	"""`ideEvento` do S-2299 (`T_ideEvento_trab_indGuia`) — `proc_emi` aqui é livre
	(0-9), diferente do `TS_procEmi_sem_8` do S-2200; `ind_guia` é campo novo deste
	evento, domínio não localizado, aceito por presença/formato apenas."""

	ind_retif: int
	proc_emi: int
	ver_proc: str
	tp_amb: int
	nr_recibo: str | None = None
	ind_guia: str | None = None

	def __post_init__(self):
		if self.ind_retif not in (1, 2):
			raise EsocialS2299Invalido(
				f"indRetif deve ser 1 (original) ou 2 (retificação), recebido {self.ind_retif}"
			)

		if self.ind_retif == 2 and not self.nr_recibo:
			raise EsocialS2299Invalido("nrRecibo é obrigatório quando indRetif=2 (retificação)")

		if self.tp_amb not in (1, 2):
			raise EsocialS2299Invalido(
				f"tpAmb deve ser 1 (Produção) ou 2 (Produção Restrita), recebido {self.tp_amb}"
			)

		_validar_digito_unico(self.proc_emi, "procEmi")

		if not (1 <= len(self.ver_proc) <= 20):
			raise EsocialS2299Invalido(
				f"verProc deve ter entre 1 e 20 caracteres, recebido {self.ver_proc!r}"
			)


@dataclass(frozen=True)
class InfoDeslig:
	"""`infoDeslig` — `mtv_deslig` é só formato (Tabela 19 não localizada, ver
	docstring do módulo); `dt_deslig` é o último dia trabalhado."""

	mtv_deslig: str
	dt_deslig: date
	ind_pagto_api: str
	dt_proj_fim_api: date | None = None

	def __post_init__(self):
		if not self.mtv_deslig.isdigit() or len(self.mtv_deslig) != 2:
			raise EsocialS2299Invalido(
				f"mtvDeslig deve ter exatamente 2 dígitos numéricos, recebido {self.mtv_deslig!r}"
			)

		if self.ind_pagto_api not in ("S", "N"):
			raise EsocialS2299Invalido(f"indPagtoAPI deve ser 'S' ou 'N', recebido {self.ind_pagto_api!r}")


@dataclass(frozen=True)
class VerbasResc:
	"""`verbasResc` — as verbas rescisórias, reaproveitando `esocial_s1200.DmDev`
	de verdade (mesmo complexType `dmDev` do XSD, não uma cópia). Até 50 `DmDev`
	(mesmo limite do `dmDev` do S-1200, `maxOccurs="99"` no XSD original — 50 aqui
	é o valor citado pela fonte para este evento especificamente, não reconferido
	dígito a dígito contra o XSD nesta rodada)."""

	dm_dev: tuple[DmDev, ...]

	def __post_init__(self):
		if len(self.dm_dev) > 50:
			raise EsocialS2299Invalido(
				f"dmDev aceita no máximo 50 ocorrências aqui, recebido {len(self.dm_dev)}"
			)
