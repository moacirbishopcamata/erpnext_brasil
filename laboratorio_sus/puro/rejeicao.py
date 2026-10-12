# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Motivos enumerados de rejeição de amostra e de quarentena de resultado, e a avaliação de estabilidade.

Rejeição só por motivo da lista (spec `sus-coleta-e-recepcao`); quarentena só por motivo da lista (spec
`sus-analise-e-liberacao`). Texto livre não é motivo: entra como observação junto de um motivo da lista.

Os prazos e faixas de temperatura **não são regra deste módulo**: vêm do cadastro do exame (parâmetro). O
levantamento deles por exame e a norma de transporte (RDC 504/2021, ANVISA) são a tarefa 1.5 do change.
"""

import enum
from dataclasses import dataclass
from datetime import datetime, timedelta

__all__ = [
	"CondicaoDeTransporte",
	"EstabilidadeDoExame",
	"MotivoDeQuarentena",
	"MotivoDeRejeicao",
	"avaliar_estabilidade",
]


class MotivoDeRejeicao(str, enum.Enum):
	ROTULO_ILEGIVEL_OU_AUSENTE = "rotulo_ilegivel_ou_ausente"
	DIVERGENCIA_DE_IDENTIFICACAO = "divergencia_de_identificacao"
	VOLUME_INSUFICIENTE = "volume_insuficiente"
	HEMOLISE = "hemolise"
	TUBO_INADEQUADO = "tubo_inadequado"
	AMOSTRA_COAGULADA = "amostra_coagulada"
	ESTABILIDADE_VENCIDA = "estabilidade_vencida"
	TEMPERATURA_FORA_DA_FAIXA = "temperatura_fora_da_faixa"
	MATERIAL_DERRAMADO = "material_derramado"


class MotivoDeQuarentena(str, enum.Enum):
	IDENTIFICADOR_DESCONHECIDO = "identificador_desconhecido"
	IDENTIFICADOR_AMBIGUO = "identificador_ambiguo"
	DIGITADO_SEM_CONFERENCIA = "digitado_sem_conferencia"
	DADOS_DO_PACIENTE_DIVERGENTES = "dados_do_paciente_divergentes"
	UNIDADE_DIFERENTE = "unidade_diferente"
	CONTROLE_REPROVADO = "controle_reprovado"
	LACUNA_NA_CADEIA = "lacuna_na_cadeia"
	DIVERGENCIA_ENTRE_SISTEMAS = "divergencia_entre_sistemas"
	COLISAO_DE_IDENTIFICADOR = "colisao_de_identificador"
	SEM_VINCULO_DO_LABORATORIO_DE_REFERENCIA = "sem_vinculo_do_laboratorio_de_referencia"


@dataclass(frozen=True)
class EstabilidadeDoExame:
	"""O que o cadastro do exame diz sobre quanto a amostra aguenta."""

	prazo: timedelta
	"""Tempo máximo entre a coleta e o recebimento."""
	temperatura_minima: float | None = None
	temperatura_maxima: float | None = None


@dataclass(frozen=True)
class CondicaoDeTransporte:
	coleta: datetime
	recebimento: datetime
	temperatura: float | None = None
	"""Temperatura registrada; `None` quando o exame exige e não houve registro conta como fora da faixa."""


def avaliar_estabilidade(
	exame: EstabilidadeDoExame, condicao: CondicaoDeTransporte
) -> MotivoDeRejeicao | None:
	"""O motivo de rejeição, ou `None` se a amostra está dentro dos limites. Nunca aceita por omissão."""
	if condicao.recebimento < condicao.coleta:
		raise ValueError("recebimento anterior à coleta: relógio incoerente")

	if condicao.recebimento - condicao.coleta > exame.prazo:
		return MotivoDeRejeicao.ESTABILIDADE_VENCIDA

	exige_temperatura = exame.temperatura_minima is not None or exame.temperatura_maxima is not None

	if exige_temperatura:
		t = condicao.temperatura

		if t is None:
			return MotivoDeRejeicao.TEMPERATURA_FORA_DA_FAIXA

		if exame.temperatura_minima is not None and t < exame.temperatura_minima:
			return MotivoDeRejeicao.TEMPERATURA_FORA_DA_FAIXA

		if exame.temperatura_maxima is not None and t > exame.temperatura_maxima:
			return MotivoDeRejeicao.TEMPERATURA_FORA_DA_FAIXA

	return None
