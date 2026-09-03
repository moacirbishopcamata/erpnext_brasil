# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Resolução da unidade federativa a partir do campo livre `state` do Address.

O ERPNext trata `state` como texto livre, então o mesmo estado chega como "SP",
"São Paulo", "sao paulo" ou "S. Paulo" conforme quem digitou. A validação de
Inscrição Estadual precisa da sigla, e adivinhar errado rejeitaria cadastro válido —
por isso a resolução é conservadora: o que não casar com segurança devolve None, e
quem chama trata None como "sem regra a aplicar".

Funções puras, sem dependência do Frappe.
"""

import unicodedata

__all__ = ["SIGLAS", "resolver_uf"]

SIGLAS = frozenset(
	[
		"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
		"MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
		"RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
	]
)  # fmt: skip

_NOMES = {
	"acre": "AC",
	"alagoas": "AL",
	"amazonas": "AM",
	"amapa": "AP",
	"bahia": "BA",
	"ceara": "CE",
	"distrito federal": "DF",
	"espirito santo": "ES",
	"goias": "GO",
	"maranhao": "MA",
	"minas gerais": "MG",
	"mato grosso do sul": "MS",
	"mato grosso": "MT",
	"para": "PA",
	"paraiba": "PB",
	"pernambuco": "PE",
	"piaui": "PI",
	"parana": "PR",
	"rio de janeiro": "RJ",
	"rio grande do norte": "RN",
	"rondonia": "RO",
	"roraima": "RR",
	"rio grande do sul": "RS",
	"santa catarina": "SC",
	"sergipe": "SE",
	"sao paulo": "SP",
	"tocantins": "TO",
}


def _normalizar(texto: str) -> str:
	"""Remove acentos, colapsa espaços e caixa — "São Paulo" e "sao  paulo" convergem."""
	sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")

	return " ".join(sem_acento.lower().split())


def resolver_uf(estado: str | None) -> str | None:
	"""Devolve a sigla da UF, ou None quando não dá para afirmar com segurança.

	None não é erro: significa "não há regra aplicável", e quem chama deve deixar
	o valor passar em vez de rejeitá-lo.
	"""
	if not estado:
		return None

	bruto = str(estado).strip()

	if bruto.upper() in SIGLAS:
		return bruto.upper()

	return _NOMES.get(_normalizar(bruto))
