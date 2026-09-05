# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Conversão entre a sigla da UF e o código IBGE (`cUF` do leiaute).

O resto do app trabalha com a **sigla** (`"RO"`) — é o que `autorizadores_sefaz` e
`TransporteSefaz` usam para escolher o endpoint, e o que o `Address` do ERPNext guarda.
Mas o campo `cUF` do leiaute exige o **código IBGE** (`"11"`), e ele aparece em mais de um
lugar: no `inutNFe`, no `ide` da NF-e e do CT-e, e no primeiro par de dígitos da chave de
acesso.

A tabela morava em `fiscal/documento/inutilizacao.py` com um comentário dizendo que a
conversão "só é necessária aqui, porque só a inutilização carrega esse campo no corpo do
documento". Isso deixou de ser verdade quando a montagem passou a precisar do `cUF` do
`ide` — extraída aqui para não haver duas tabelas divergindo, que é como a UF de um
documento passa a discordar da UF da chave que o acompanha.

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = ["CODIGO_UF_POR_SIGLA", "SIGLA_POR_CODIGO_UF", "UfDesconhecida", "codigo_da_uf", "sigla_da_uf"]

CODIGO_UF_POR_SIGLA = {
	"RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
	"MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
	"SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
	"SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}  # fmt: skip

SIGLA_POR_CODIGO_UF = {codigo: sigla for sigla, codigo in CODIGO_UF_POR_SIGLA.items()}


class UfDesconhecida(ValueError):
	"""Sigla ou código que não corresponde a nenhuma das 27 unidades da Federação."""


def codigo_da_uf(sigla: str) -> str:
	"""`"SP"` → `"35"`. Sigla desconhecida falha alto.

	Devolver vazio produziria um `cUF` vazio no documento, e a rejeição viria da SEFAZ sem
	dizer qual campo estava errado.
	"""
	codigo = CODIGO_UF_POR_SIGLA.get((sigla or "").strip().upper())

	if not codigo:
		raise UfDesconhecida(
			f"UF {sigla!r} não é uma das 27 unidades da Federação — o cUF do leiaute não admite outro valor"
		)

	return codigo


def sigla_da_uf(codigo: str) -> str:
	"""`"35"` → `"SP"`. O caminho inverso, usado ao ler chave de acesso recebida."""
	sigla = SIGLA_POR_CODIGO_UF.get((codigo or "").strip())

	if not sigla:
		raise UfDesconhecida(f"código de UF {codigo!r} não corresponde a nenhuma unidade da Federação")

	return sigla
