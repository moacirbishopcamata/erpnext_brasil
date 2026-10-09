# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta pura do relatório "Bloqueios SEFAZ" (cStat 656, consumo indevido — `fiscal/consumo_indevido.py`)."""

import math
from datetime import datetime

__all__ = ["classificar"]


def classificar(bloqueios: list[dict], agora: datetime) -> list[dict]:
	"""Acrescenta `situacao` ("Ativo"/"Liberado") e `restante_min` a cada bloqueio.

	Mesma fronteira da regra: exatamente em `liberado_em` já está liberado. Bloqueio sem `liberado_em` é tratado como
	**ativo** — na dúvida, o relatório não declara liberado o que não sabe. Ativos primeiro, depois o mais recente.
	"""
	saida = []

	for b in bloqueios:
		liberado = b.get("liberado_em")
		ativo = liberado is None or agora < liberado
		restante = math.ceil((liberado - agora).total_seconds() / 60) if ativo and liberado else 0
		saida.append({**b, "situacao": "Ativo" if ativo else "Liberado", "restante_min": max(restante, 0)})

	return sorted(
		saida,
		key=lambda x: (
			x["situacao"] != "Ativo",
			-(x["bloqueado_em"].timestamp() if x.get("bloqueado_em") else 0),
		),
	)
