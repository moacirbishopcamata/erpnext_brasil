# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Portas (`Protocol`) do módulo avulso: tudo o que é de fora entra por aqui.

O módulo opera sozinho, com implementação própria mínima de cada porta (cadastro próprio, digitação conferida,
relógio do sistema). Healthcare, analisador, RNDS e GAL são adaptadores **opcionais** que implementam as mesmas
interfaces; nenhuma regra importa um adaptador. Mesma inversão de dependência de `integracao/repositorio_frappe.py`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

__all__ = [
	"CadastroDeReferencia",
	"EntradaDeResultado",
	"EnvioARnds",
	"EnvioAoGal",
	"Impressora",
	"Relogio",
	"ResultadoRecebido",
]


@dataclass(frozen=True)
class ResultadoRecebido:
	"""Um resultado como chega por qualquer entrada, antes do casamento por identificador exato."""

	identificador_do_tubo: str
	exame: str
	valor: str
	unidade: str
	origem: str
	"""`digitacao`, `arquivo`, `analisador`, `gal`..."""
	conferido_por: str | None = None


class CadastroDeReferencia(Protocol):
	def paciente(self, identificador: str) -> dict | None: ...
	def unidade(self, cnes: str) -> dict | None: ...
	def profissional(self, registro: str) -> dict | None: ...


class EntradaDeResultado(Protocol):
	def pendentes(self) -> Sequence[ResultadoRecebido]: ...


class Impressora(Protocol):
	def imprimir(self, conteudo: str, estacao: str) -> bool:
		"""`True` só quando a impressão foi confirmada; falha não confirma a coleta."""
		...


class Relogio(Protocol):
	def agora(self) -> datetime: ...
	def desvio_segundos(self) -> float | None:
		"""Desvio contra a fonte de tempo, ou `None` quando não foi possível medir."""
		...


class EnvioARnds(Protocol):
	def enviar(self, recurso: dict, chave_de_idempotencia: str) -> bool: ...


class EnvioAoGal(Protocol):
	def numero_da_requisicao(self, tubo: str) -> str | None: ...
