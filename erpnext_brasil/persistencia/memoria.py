# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Adaptador em memória: o repositório dos testes das regras que precisam de persistência.

Existe para que a regra de uma ferramenta (por exemplo, o registro de instâncias do Soda) seja testada
sem arquivo nenhum, e passa na mesma suíte de contrato dos adaptadores de arquivo. Não é usado em produção.
"""

import copy
from collections.abc import Iterator
from contextlib import contextmanager

from erpnext_brasil.persistencia.documentos import (
	Documento,
	PersistenciaInvalida,
	validar_documento,
	validar_nome,
)

__all__ = ["RepositorioEmMemoria"]


class RepositorioEmMemoria:
	formato = "memoria"

	def __init__(self):
		self._dados: dict[str, dict[str, Documento]] = {}
		self._em_transacao = False

	def obter(self, colecao: str, chave: str) -> Documento | None:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")
		documento = self._dados.get(colecao, {}).get(chave)

		return copy.deepcopy(documento) if documento is not None else None

	def listar(self, colecao: str) -> list[tuple[str, Documento]]:
		validar_nome(colecao, "a coleção")

		return [(chave, copy.deepcopy(doc)) for chave, doc in sorted(self._dados.get(colecao, {}).items())]

	def colecoes(self) -> list[str]:
		return sorted(nome for nome, documentos in self._dados.items() if documentos)

	def gravar(self, colecao: str, chave: str, documento: Documento) -> None:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")
		normalizado = validar_documento(documento)
		self._dados.setdefault(colecao, {})[chave] = normalizado

	def remover(self, colecao: str, chave: str) -> bool:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")
		documentos = self._dados.get(colecao, {})

		return documentos.pop(chave, None) is not None

	@contextmanager
	def transacao(self) -> Iterator[None]:
		if self._em_transacao:
			raise PersistenciaInvalida("transação aninhada não é permitida")

		antes = copy.deepcopy(self._dados)
		self._em_transacao = True

		try:
			yield
		except BaseException:
			self._dados = antes
			raise
		finally:
			self._em_transacao = False

	def versao_do_esquema(self) -> int:
		return 1
