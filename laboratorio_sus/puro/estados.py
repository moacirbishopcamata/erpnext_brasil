# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Ciclo de estados do exame: tabela de transições permitidas, sem salto.

Estados (spec `sus-coleta-e-recepcao`): solicitado, coletado, em remessa, recebido, em análise, resultado
disponível, liberado, entregue; terminais cancelado, rejeitado e descartado. Toda transição fora da tabela é
recusada. Gerar o evento de custódia de cada transição é do repositório; a tabela é a única fonte de verdade.
"""

import enum

__all__ = ["TRANSICOES", "Estado", "TransicaoInvalida", "e_terminal", "permitidas", "transicionar"]


class Estado(str, enum.Enum):
	SOLICITADO = "solicitado"
	COLETADO = "coletado"
	EM_REMESSA = "em_remessa"
	RECEBIDO = "recebido"
	EM_ANALISE = "em_analise"
	RESULTADO_DISPONIVEL = "resultado_disponivel"
	LIBERADO = "liberado"
	ENTREGUE = "entregue"
	CANCELADO = "cancelado"
	REJEITADO = "rejeitado"
	DESCARTADO = "descartado"


E = Estado

TRANSICOES: dict[Estado, frozenset[Estado]] = {
	E.SOLICITADO: frozenset({E.COLETADO, E.CANCELADO}),
	# coletado no próprio laboratório vai direto à recepção; nas demais unidades, em remessa
	E.COLETADO: frozenset({E.EM_REMESSA, E.RECEBIDO, E.REJEITADO, E.DESCARTADO}),
	E.EM_REMESSA: frozenset({E.RECEBIDO, E.REJEITADO, E.DESCARTADO}),
	E.RECEBIDO: frozenset({E.EM_ANALISE, E.REJEITADO, E.DESCARTADO}),
	E.EM_ANALISE: frozenset({E.RESULTADO_DISPONIVEL, E.REJEITADO, E.DESCARTADO}),
	# repetição do exame volta à análise; o resultado anterior vira versão, nunca é sobrescrito
	E.RESULTADO_DISPONIVEL: frozenset({E.LIBERADO, E.EM_ANALISE, E.DESCARTADO}),
	E.LIBERADO: frozenset({E.ENTREGUE, E.DESCARTADO}),
	E.ENTREGUE: frozenset({E.DESCARTADO}),
	E.CANCELADO: frozenset(),
	E.REJEITADO: frozenset(),
	E.DESCARTADO: frozenset(),
}


class TransicaoInvalida(ValueError):
	"""Mudança de estado fora da ordem permitida."""


def permitidas(atual: Estado) -> frozenset[Estado]:
	return TRANSICOES[atual]


def e_terminal(estado: Estado) -> bool:
	return not TRANSICOES[estado]


def transicionar(atual: Estado, novo: Estado) -> Estado:
	"""O `novo` estado, se a transição é permitida; senão `TransicaoInvalida`, sem efeito."""
	if novo not in TRANSICOES[atual]:
		raise TransicaoInvalida(f"o exame está {atual.value} e não pode ir para {novo.value}")

	return novo
