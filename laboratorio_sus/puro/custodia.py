# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cadeia de custódia do tubo: eventos só de acréscimo, encadeados por hash (SHA-256).

Cada evento guarda o hash do evento anterior do mesmo tubo. Alterar, remover ou reordenar qualquer evento
quebra o encadeamento, e `verificar` aponta onde. O histórico nativo de um banco é editável por quem tem
acesso a ele e não serve de prova; o encadeamento torna a adulteração **detectável**, não impossível.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field

__all__ = ["GENESE", "Evento", "QuebraDeCadeia", "encadear", "verificar"]

GENESE = "0" * 64


@dataclass(frozen=True)
class Evento:
	tubo: str
	tipo: str
	usuario: str
	local: str
	instante: str
	dados: dict = field(default_factory=dict)
	hash_anterior: str = GENESE
	hash: str = ""


@dataclass(frozen=True)
class QuebraDeCadeia:
	posicao: int
	motivo: str


def _calcular(evento: Evento) -> str:
	corpo = {
		"tubo": evento.tubo,
		"tipo": evento.tipo,
		"usuario": evento.usuario,
		"local": evento.local,
		"instante": evento.instante,
		"dados": evento.dados,
		"hash_anterior": evento.hash_anterior,
	}
	canonico = json.dumps(corpo, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

	return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def encadear(
	cadeia: Sequence[Evento],
	*,
	tubo: str,
	tipo: str,
	usuario: str,
	local: str,
	instante: str,
	dados: dict | None = None,
) -> Evento:
	"""O próximo evento da cadeia (já com hash), ligado ao último. Não altera a cadeia recebida."""
	if cadeia and cadeia[-1].tubo != tubo:
		raise ValueError("o evento é de outro tubo")

	novo = Evento(
		tubo=tubo,
		tipo=tipo,
		usuario=usuario,
		local=local,
		instante=instante,
		dados=dict(dados or {}),
		hash_anterior=cadeia[-1].hash if cadeia else GENESE,
	)

	return Evento(**{**novo.__dict__, "hash": _calcular(novo)})


def verificar(cadeia: Sequence[Evento]) -> list[QuebraDeCadeia]:
	"""Recalcula a cadeia inteira; lista vazia significa íntegra."""
	quebras: list[QuebraDeCadeia] = []
	esperado_anterior = GENESE

	for posicao, evento in enumerate(cadeia):
		if evento.hash_anterior != esperado_anterior:
			quebras.append(
				QuebraDeCadeia(posicao, "hash anterior não confere (evento removido ou reordenado)")
			)

		if evento.hash != _calcular(evento):
			quebras.append(QuebraDeCadeia(posicao, "conteúdo do evento foi alterado"))

		if posicao and evento.tubo != cadeia[0].tubo:
			quebras.append(QuebraDeCadeia(posicao, "evento de outro tubo na cadeia"))

		esperado_anterior = evento.hash

	return quebras
