# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Faixa de identificadores reservada a uma estação de coleta offline.

A estação recebe um bloco de números e os consome em sequência. Nada é impresso antes da coleta; só o
*número* é reservado. Na sincronização, `reconciliar` separa o que foi usado do que deve ir à quarentena
(fora da faixa ou repetido) e do que sobrou e precisa ser **anulado e registrado** — nunca reaproveitado.
"""

from collections.abc import Collection, Iterable
from dataclasses import dataclass

__all__ = ["FaixaEsgotada", "FaixaReservada", "Reconciliacao", "UsoDaFaixa", "reconciliar"]


class FaixaEsgotada(RuntimeError):
	"""A estação consumiu todos os números reservados e precisa sincronizar para receber outra faixa."""


@dataclass(frozen=True)
class FaixaReservada:
	estacao: str
	inicio: int
	fim: int  # inclusive

	def __post_init__(self):
		if self.inicio < 1 or self.fim < self.inicio:
			raise ValueError("faixa inválida")

	def __contains__(self, numero: object) -> bool:
		return isinstance(numero, int) and self.inicio <= numero <= self.fim

	@property
	def tamanho(self) -> int:
		return self.fim - self.inicio + 1


class UsoDaFaixa:
	"""O consumo em sequência da faixa pela estação: cada número sai uma só vez, em ordem crescente."""

	def __init__(self, faixa: FaixaReservada, proximo: int | None = None):
		self._faixa = faixa
		self._proximo = faixa.inicio if proximo is None else proximo

		if self._proximo not in faixa and self._proximo != faixa.fim + 1:
			raise ValueError("o próximo número está fora da faixa")

	@property
	def proximo(self) -> int:
		return self._proximo

	@property
	def restantes(self) -> int:
		return self._faixa.fim - self._proximo + 1

	def consumir(self) -> int:
		if self._proximo > self._faixa.fim:
			raise FaixaEsgotada(f"a estação {self._faixa.estacao} usou toda a faixa; sincronize")

		numero = self._proximo
		self._proximo += 1

		return numero


@dataclass(frozen=True)
class Reconciliacao:
	usados: tuple[int, ...]
	"""Números da faixa usados uma vez só, em ordem."""
	quarentena: tuple[tuple[int, str], ...]
	"""Números a reter, com o motivo: fora da faixa da estação, repetido na própria estação, ou já usado por outra."""
	anulados: tuple[int, ...]
	"""Números reservados e não usados: anular e registrar, nunca reaproveitar."""


def reconciliar(
	faixa: FaixaReservada, enviados: Iterable[int], ja_usados_por_outras: Collection[int] = ()
) -> Reconciliacao:
	usados: list[int] = []
	quarentena: list[tuple[int, str]] = []
	vistos: set[int] = set()
	outras = set(ja_usados_por_outras)

	for numero in enviados:
		if numero not in faixa:
			quarentena.append((numero, "fora da faixa da estação"))
		elif numero in outras:
			quarentena.append((numero, "já usado por outra estação"))
		elif numero in vistos:
			quarentena.append((numero, "repetido na própria estação"))
		else:
			vistos.add(numero)
			usados.append(numero)

	anulados = tuple(n for n in range(faixa.inicio, faixa.fim + 1) if n not in vistos and n not in outras)

	return Reconciliacao(tuple(sorted(usados)), tuple(quarentena), anulados)
