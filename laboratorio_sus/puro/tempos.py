# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Tempo de resposta por etapa e atraso por prioridade (spec `sus-resultado-e-entrega`).

Etapas: solicitação→coleta, coleta→chegada ao laboratório, chegada→liberação, liberação→ciência. Os prazos
por prioridade são parâmetro do serviço, não regra fixa. Os carimbos vêm de relógio sincronizado; um carimbo
fora de ordem é erro de dado (relógio incoerente), nunca tempo negativo silencioso.
"""

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

__all__ = ["Etapa", "Prioridade", "TempoDeEtapa", "etapas_atrasadas", "tempos_por_etapa"]


class Prioridade(str, enum.Enum):
	ROTINA = "rotina"
	URGENCIA = "urgencia"


class Etapa(str, enum.Enum):
	SOLICITACAO_ATE_COLETA = "solicitacao_ate_coleta"
	COLETA_ATE_CHEGADA = "coleta_ate_chegada"
	CHEGADA_ATE_LIBERACAO = "chegada_ate_liberacao"
	LIBERACAO_ATE_CIENCIA = "liberacao_ate_ciencia"


_PARES = (
	(Etapa.SOLICITACAO_ATE_COLETA, "solicitacao", "coleta"),
	(Etapa.COLETA_ATE_CHEGADA, "coleta", "chegada"),
	(Etapa.CHEGADA_ATE_LIBERACAO, "chegada", "liberacao"),
	(Etapa.LIBERACAO_ATE_CIENCIA, "liberacao", "ciencia"),
)


@dataclass(frozen=True)
class TempoDeEtapa:
	etapa: Etapa
	duracao: timedelta


def tempos_por_etapa(carimbos: Mapping[str, datetime]) -> list[TempoDeEtapa]:
	"""A duração de cada etapa cujos dois carimbos existem. Etapa com carimbo faltando é omitida."""
	tempos = []

	for etapa, de, ate in _PARES:
		if de in carimbos and ate in carimbos:
			duracao = carimbos[ate] - carimbos[de]

			if duracao < timedelta(0):
				raise ValueError(f"{ate} anterior a {de}: relógio incoerente")

			tempos.append(TempoDeEtapa(etapa, duracao))

	return tempos


def etapas_atrasadas(
	tempos: list[TempoDeEtapa],
	prioridade: Prioridade,
	prazos: Mapping[Prioridade, Mapping[Etapa, timedelta]],
) -> list[Etapa]:
	"""As etapas cuja duração **excedeu** o prazo da prioridade (exatamente no prazo não é atraso)."""
	limites = prazos.get(prioridade, {})

	return [t.etapa for t in tempos if t.etapa in limites and t.duracao > limites[t.etapa]]
