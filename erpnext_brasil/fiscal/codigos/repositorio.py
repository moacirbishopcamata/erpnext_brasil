# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Porta de leitura das tabelas de classificação (inversão de dependência).

Por que existe
--------------
A regra de compatibilidade precisa das tabelas oficiais, mas **não** precisa saber que
elas vieram de um Code List do Frappe — poderiam vir de um XLSX, de um cache ou de um
teste. Depender da interface em vez da origem é o que mantém a regra em `fiscal/` livre
de `frappe`, e testável sem bench.

Interface pequena de propósito: duas operações, não um repositório genérico que force
implementar métodos que ninguém usa.
"""

from typing import Protocol, runtime_checkable

from erpnext_brasil.fiscal.codigos.classificacao import ClassificacaoTributaria, CstIbsCbs

__all__ = ["RepositorioClassificacao", "RepositorioEmMemoria"]


@runtime_checkable
class RepositorioClassificacao(Protocol):
	"""Fonte das tabelas de CST e cClassTrib."""

	def cst(self) -> dict[str, CstIbsCbs]:
		"""CST do IBS/CBS indexados pelo código. Vazio quando não importados."""
		...

	def classificacoes(self) -> dict[str, ClassificacaoTributaria]:
		"""cClassTrib indexados pelo código. Vazio quando não importados."""
		...


class RepositorioEmMemoria:
	"""Implementação trivial, para testes e para uso a partir do XLSX lido.

	Existe no código de produção, e não só nos testes, porque a importação também
	precisa validar o que acabou de ler — antes de gravar.
	"""

	def __init__(
		self,
		cst: dict[str, CstIbsCbs] | None = None,
		classificacoes: dict[str, ClassificacaoTributaria] | None = None,
	):
		self._cst = dict(cst or {})
		self._classificacoes = dict(classificacoes or {})

	def cst(self) -> dict[str, CstIbsCbs]:
		# Cópia: quem lê não recebe referência para o estado interno.
		return dict(self._cst)

	def classificacoes(self) -> dict[str, ClassificacaoTributaria]:
		return dict(self._classificacoes)
