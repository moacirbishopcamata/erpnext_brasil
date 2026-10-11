# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A porta de persistência das ferramentas de operação: documentos em coleções, JSON ou SQLite.

Por que existe
--------------
O Cherry, o Soda e o Chantilly guardam estado (preferências, registro de instâncias, configuração).
Cada um escolheria o seu arquivo e a sua atomicidade. Esta porta dá a todos a mesma interface e
deixa a escolha do formato para a configuração: JSON, legível e simples de inspecionar, ou SQLite,
transacional e com trava entre processos pelo próprio banco (mudança `persistencia-sqlite-opcional`).

O modelo é deliberadamente pequeno: **coleções** de **documentos** (dicionários serializáveis em JSON)
identificados por uma **chave**. O que cada ferramenta tem de próprio (UUID, descritivo, portas) é
regra dela e mora no repositório tipado que ela constrói por cima desta porta.

Contratos (Design by Contract)
------------------------------
- **Pré-condição:** nomes de coleção e de chave só têm letras, dígitos e `. _ -`; documento é um
  dicionário de chaves de texto, serializável em JSON e **sem chave de segredo** (senha, token...).
  Violação levanta `PersistenciaInvalida` antes de tocar em qualquer arquivo.
- **Pós-condição:** o que se grava é o que se lê, por qualquer instância; uma transação é tudo ou nada.
- **Invariante:** quem lê recebe **cópia**: mudar o documento devolvido não muda o que está guardado.
  (É a classe de bug "duas leituras devolvendo a mesma instância por referência".)

Estado de verificação: coberto por uma suíte de contrato que roda a mesma bateria contra os três
adaptadores (memória, JSON e SQLite) — `tests/test_persistencia_contrato.py`.
"""

import json
import re
from contextlib import AbstractContextManager
from typing import Any, Protocol

__all__ = [
	"ArquivoIlegivel",
	"Documento",
	"EsquemaMaisNovo",
	"MigracaoDivergente",
	"PersistenciaInvalida",
	"RepositorioDeDocumentos",
	"TravaOcupada",
	"listar_tudo",
	"migrar",
	"sao_iguais",
	"validar_documento",
	"validar_nome",
]

Documento = dict[str, Any]

_NOME = re.compile(r"[A-Za-z0-9_.\-]{1,200}")
_SEGREDO = re.compile(r"senha|password|passwd|secret|segredo|token|api[_-]?key|chave_privada", re.IGNORECASE)


class PersistenciaInvalida(ValueError):
	"""Pré-condição violada: o pedido é recusado antes de tocar em qualquer arquivo."""


class EsquemaMaisNovo(RuntimeError):
	"""O arquivo foi gravado por uma versão mais nova da ferramenta; esta não grava nele."""


class ArquivoIlegivel(RuntimeError):
	"""O arquivo existe e não pode ser lido. Nunca é sobrescrito: o usuário decide a quarentena."""

	def __init__(self, caminho, motivo: str):
		super().__init__(f"{caminho} não pôde ser lido: {motivo}")
		self.caminho = caminho
		self.motivo = motivo


class TravaOcupada(RuntimeError):
	"""Outro processo está gravando e a espera esgotou."""


class MigracaoDivergente(RuntimeError):
	"""Depois de migrar, o destino não ficou igual à origem."""


class RepositorioDeDocumentos(Protocol):
	"""O que uma ferramenta pede à persistência, sem saber o formato."""

	formato: str

	def obter(self, colecao: str, chave: str) -> Documento | None: ...

	def listar(self, colecao: str) -> list[tuple[str, Documento]]: ...

	def colecoes(self) -> list[str]: ...

	def gravar(self, colecao: str, chave: str, documento: Documento) -> None: ...

	def remover(self, colecao: str, chave: str) -> bool: ...

	def transacao(self) -> AbstractContextManager[None]: ...

	def versao_do_esquema(self) -> int: ...


def validar_nome(valor: str, o_que: str) -> str:
	"""Coleção e chave são nomes seguros, iguais em qualquer formato e em qualquer sistema de arquivos."""
	if not isinstance(valor, str) or not _NOME.fullmatch(valor):
		raise PersistenciaInvalida(
			f"{o_que} só pode ter de 1 a 200 letras, dígitos e os caracteres . _ - — recebido {valor!r}"
		)

	return valor


def _sem_segredo(valor: Any, caminho: str) -> None:
	if isinstance(valor, dict):
		for chave, interno in valor.items():
			if not isinstance(chave, str):
				raise PersistenciaInvalida(
					f"chave de documento precisa ser texto em {caminho or 'raiz'}: {chave!r}"
				)

			if _SEGREDO.search(chave):
				raise PersistenciaInvalida(
					f"a chave {chave!r} parece guardar um segredo; nenhuma ferramenta persiste senha ou token"
				)

			_sem_segredo(interno, f"{caminho}.{chave}" if caminho else chave)
	elif isinstance(valor, list | tuple):
		for indice, interno in enumerate(valor):
			_sem_segredo(interno, f"{caminho}[{indice}]")


def validar_documento(documento: Any) -> Documento:
	"""Devolve uma **cópia** normalizada (via JSON) ou recusa. É aqui que o segredo é barrado."""
	if not isinstance(documento, dict):
		raise PersistenciaInvalida(
			f"documento precisa ser um dicionário, recebido {type(documento).__name__}"
		)

	_sem_segredo(documento, "")

	try:
		return json.loads(json.dumps(documento, allow_nan=False, sort_keys=True))
	except (TypeError, ValueError) as erro:
		raise PersistenciaInvalida(f"documento não é serializável em JSON: {erro}") from erro


def listar_tudo(repositorio: RepositorioDeDocumentos) -> dict[str, dict[str, Documento]]:
	"""Todo o conteúdo, por coleção e chave. Usado pela migração e pela comparação."""
	return {
		colecao: {chave: documento for chave, documento in repositorio.listar(colecao)}
		for colecao in repositorio.colecoes()
	}


def sao_iguais(a: RepositorioDeDocumentos, b: RepositorioDeDocumentos) -> bool:
	return listar_tudo(a) == listar_tudo(b)


def migrar(origem: RepositorioDeDocumentos, destino: RepositorioDeDocumentos) -> int:
	"""Copia tudo da origem para o destino, numa transação, e confere por releitura. Devolve o total.

	Pré-condição: o destino é vazio ou um subconjunto da origem (assim a migração é **idempotente**: repetir
	não duplica nem altera nada). Um destino com conteúdo próprio é recusado, nunca misturado.
	A origem nunca é tocada.
	"""
	dados = listar_tudo(origem)
	existente = listar_tudo(destino)

	for colecao, documentos in existente.items():
		for chave, documento in documentos.items():
			if dados.get(colecao, {}).get(chave) != documento:
				raise PersistenciaInvalida(
					f"o destino já tem {colecao}/{chave} diferente da origem; migre para um destino vazio"
				)

	total = 0

	with destino.transacao():
		for colecao, documentos in dados.items():
			for chave, documento in documentos.items():
				destino.gravar(colecao, chave, documento)
				total += 1

	if not sao_iguais(origem, destino):
		raise MigracaoDivergente("o destino não ficou igual à origem depois de migrar")

	return total
