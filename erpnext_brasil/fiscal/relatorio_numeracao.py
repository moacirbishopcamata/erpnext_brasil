# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta pura do relatório "Lacunas de Numeracao" (`proposta-de-relatorios.md`).

A numeração fiscal é sequencial; cada número consumido precisa terminar em autorização, denegação, cancelamento ou
inutilização de faixa (`fiscal/documento/inutilizacao.py`). O contador de `Numeracao Fiscal` diz até onde se
consumiu; as `Transmissao Fiscal` dizem o que aconteceu com cada número. Esta função cruza os dois.

⚠️ Limite declarado: o app **ainda não grava a faixa inutilizada** em `Transmissao Fiscal`, então um número
inutilizado na SEFAZ continua aparecendo aqui como "sem desfecho". O relatório lista **candidatos** à inutilização, não
lacunas já justificadas — e é por isso que ele existe: o que aparece é o que precisa ser conferido.
"""

__all__ = ["DESFECHOS_QUE_FECHAM", "faixas_sem_desfecho"]

DESFECHOS_QUE_FECHAM = frozenset({"Autorizado", "Denegado", "Cancelado"})
"""Situações que encerram o número: ele existe na SEFAZ e não precisa de inutilização."""

SEM_REGISTRO = "Sem registro"
SO_REJEITADO = "Só rejeitado"
PENDENTE = "Pendente"


def _motivo(situacoes: set[str]) -> str | None:
	if situacoes & DESFECHOS_QUE_FECHAM:
		return None

	if not situacoes:
		return SEM_REGISTRO

	if "Pendente" in situacoes:
		return PENDENTE

	return SO_REJEITADO


def faixas_sem_desfecho(
	ultimo_numero: int, situacoes_por_numero: dict[int, set[str]], primeiro: int = 1
) -> list[dict]:
	"""Faixas consecutivas de números `primeiro..ultimo_numero` que não terminaram em desfecho que feche.

	`situacoes_por_numero`: `{número: {situações das transmissões com esse número}}`. Números fora do intervalo
	consumido são ignorados. Números consecutivos com o **mesmo motivo** viram uma faixa só (é como a inutilização
	é pedida: `nNFIni`–`nNFFin`).
	"""
	faixas: list[dict] = []

	for numero in range(primeiro, ultimo_numero + 1):
		motivo = _motivo(situacoes_por_numero.get(numero, set()))

		if motivo is None:
			continue

		if faixas and faixas[-1]["motivo"] == motivo and faixas[-1]["fim"] == numero - 1:
			faixas[-1]["fim"] = numero
		else:
			faixas.append({"inicio": numero, "fim": numero, "motivo": motivo})

	for faixa in faixas:
		faixa["quantidade"] = faixa["fim"] - faixa["inicio"] + 1

	return faixas
