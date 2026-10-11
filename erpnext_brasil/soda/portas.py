# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Alocação de portas para as instâncias: sem repetir, livre no sistema e fora das portas do ambiente.

Regras (spec `identidade-e-portas`)
-----------------------------------
- A porta alocada **não repete** a de outra instância do registro e **está livre no sistema** no momento da
  alocação, verificada por tentativa de abri-la (função `livre` injetável; a real é `sistema.rede.porta_livre`).
- **Portas reservadas do ambiente** nunca são alocadas, nem escolhidas pelo usuário: servidores de banco de dados,
  Redis, e as portas padrão do bench (`webserver_port` 8001, `socketio_port` 9001, `file_watcher_port` 6788,
  e as faixas de Redis do bench de desenvolvimento, 11000 a 13999).
- O usuário pode **escolher** a porta. Se ela estiver reservada, registrada ou ocupada, a alocação é recusada
  com o motivo (e quem a ocupa, quando se sabe) e uma **sugestão** da próxima livre.

A função é pura: o que toca o sistema (abrir a porta, descobrir quem a ocupa) entra por parâmetro.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

__all__ = [
	"FAIXA_PADRAO",
	"RESERVADAS",
	"FaixaDePortas",
	"FaixaEsgotada",
	"PortaRecusada",
	"alocar",
]


@dataclass(frozen=True)
class FaixaDePortas:
	inicio: int = 8100
	fim: int = 8999

	def __post_init__(self):
		if not (1024 <= self.inicio <= self.fim <= 65535):
			raise ValueError(f"faixa de portas inválida: {self.inicio} a {self.fim} (use de 1024 a 65535)")

	def __contains__(self, porta: object) -> bool:
		return isinstance(porta, int) and self.inicio <= porta <= self.fim

	def __iter__(self):
		return iter(range(self.inicio, self.fim + 1))


FAIXA_PADRAO = FaixaDePortas()

RESERVADAS: frozenset[int] = frozenset(
	{
		22,  # SSH
		80,
		443,
		3306,  # MariaDB
		3307,  # MariaDB em contêiner do ambiente de desenvolvimento
		5432,  # PostgreSQL
		6379,  # Redis padrão
		6788,  # file watcher do bench
		8000,  # servidor padrão do `bench serve`
		8001,  # webserver_port do bench de desenvolvimento
		8080,  # proxy do Docker (docker/compose.yaml)
		9000,
		9001,  # socketio_port do bench de desenvolvimento
	}
	| set(range(11000, 14000))  # Redis do bench de desenvolvimento
)


class PortaRecusada(ValueError):
	"""A porta escolhida não pode ser usada. `motivo` diz por quê; `sugestao` é a próxima livre, se houver."""

	def __init__(self, porta: int, motivo: str, *, sugestao: int | None = None):
		partes = [f"a porta {porta} não pode ser usada: {motivo}"]

		if sugestao is not None:
			partes.append(f"a próxima livre é a {sugestao}")

		super().__init__("; ".join(partes))
		self.porta = porta
		self.motivo = motivo
		self.sugestao = sugestao


class FaixaEsgotada(RuntimeError):
	"""Não há porta livre na faixa configurada."""


def _proxima(
	faixa: FaixaDePortas,
	registradas: Mapping[int, str],
	livre: Callable[[int], bool],
	reservadas: frozenset[int],
	depois_de: int | None = None,
) -> int | None:
	for porta in faixa:
		if depois_de is not None and porta <= depois_de:
			continue

		if porta in reservadas or porta in registradas:
			continue

		if livre(porta):
			return porta

	return None


def alocar(
	faixa: FaixaDePortas,
	registradas: Mapping[int, str],
	livre: Callable[[int], bool],
	*,
	escolhida: int | None = None,
	reservadas: frozenset[int] = RESERVADAS,
	quem_ocupa: Callable[[int], str | None] = lambda porta: None,
) -> int:
	"""A porta para uma instância nova.

	`registradas` mapeia a porta ao descritivo da instância que a tem (para nomear quem a usa na recusa).
	Sem `escolhida`, devolve a menor porta livre da faixa; com ela, valida e devolve a mesma, ou recusa.
	"""
	if escolhida is None:
		porta = _proxima(faixa, registradas, livre, reservadas)

		if porta is None:
			raise FaixaEsgotada(
				f"não há porta livre entre {faixa.inicio} e {faixa.fim}; amplie a faixa ou remova instâncias"
			)

		return porta

	if isinstance(escolhida, bool) or not isinstance(escolhida, int) or not 1024 <= escolhida <= 65535:
		raise PortaRecusada(escolhida, "use um número de 1024 a 65535")

	sugestao = _proxima(faixa, registradas, livre, reservadas, depois_de=escolhida) or _proxima(
		faixa, registradas, livre, reservadas
	)

	if escolhida in reservadas:
		raise PortaRecusada(
			escolhida,
			"é reservada do ambiente (banco de dados, Redis ou porta padrão do bench)",
			sugestao=sugestao,
		)

	if escolhida in registradas:
		raise PortaRecusada(escolhida, f'já é da instância "{registradas[escolhida]}"', sugestao=sugestao)

	if not livre(escolhida):
		ocupante = quem_ocupa(escolhida)
		detalhe = f"está ocupada por {ocupante}" if ocupante else "está ocupada por outro programa"
		raise PortaRecusada(escolhida, detalhe, sugestao=sugestao)

	return escolhida
