# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Quem usa um perfil de banco: as instâncias do Soda que apontam para ele.

Liga os perfis (Cherry) ao registro de instâncias (Soda) pelo leitor somente leitura do contrato de identidade,
sem que um pacote escreva no outro. O resultado alimenta a recusa de remover ou mudar um perfil em uso.
"""

from collections.abc import Callable, Sequence

from erpnext_brasil.bancos.modelo import chave_do_nome
from erpnext_brasil.bancos.repositorio import Uso
from erpnext_brasil.soda.leitura import LeitorDeInstancias

__all__ = ["usos_pelas_instancias"]


def usos_pelas_instancias(leitor: LeitorDeInstancias) -> Callable[[str], Sequence[Uso]]:
	"""A função `usos(nome_do_perfil)` que o `PerfisDeBanco` espera, lida do registro do Soda a cada chamada."""

	def usos(nome: str) -> Sequence[Uso]:
		chave = chave_do_nome(nome)
		leitura = leitor.ler()

		return tuple(
			Uso(instancia.descritivo, instancia.abreviado)
			for instancia in leitura.instancias
			if instancia.perfil_de_banco.casefold() == chave
		)

	return usos
