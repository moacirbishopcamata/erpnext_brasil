# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Código de município do IBGE: formato, UF e dígito verificador — sem `frappe`.

Por que existe
--------------
Até aqui o `Address` só recusava um código de município que não tivesse 7 dígitos numéricos. Um dígito
trocado passava, e um município de outra UF também — e o erro só apareceria como rejeição da SEFAZ (ou
pior, como documento autorizado com o município errado).

A regra, e de onde ela vem
---------------------------
O código tem 7 dígitos: os dois primeiros são o código da UF, os quatro seguintes identificam o município
na UF, e o sétimo é o **dígito verificador** dos seis primeiros — módulo 10, pesos 1 e 2 alternados
começando pelo 1, somando os algarismos de cada produto de dois dígitos. Dígito = `(10 − soma mod 10) mod 10`.

**Conferida contra a lista oficial completa**, não contra exemplos: em 2026-10-09 a API de localidades do IBGE
(`servicodados.ibge.gov.br/api/v1/localidades/municipios`) devolveu 5.571 municípios. **5.562 obedecem à regra e 9
não** — municípios criados depois, cujo código o IBGE atribuiu fora dela. Os 27 prefixos de UF correspondem
cada um a uma só sigla. Uma regra que parecia certa em sete códigos conhecidos teria recusado endereços válidos;
por isso as 9 exceções estão abaixo, com a fonte, e o administrador pode acrescentar outras por configuração.

⚠️ O algoritmo é de conhecimento corrente em bibliotecas fiscais, mas **a documentação oficial dele não foi
localizada** nesta pesquisa; o que o sustenta aqui é a conferência contra os 5.571 códigos.

Funções puras: nenhuma dependência do Frappe.
"""

import re

from erpnext_brasil.fiscal.codigos.uf import UfDesconhecida, sigla_da_uf
from erpnext_brasil.fiscal.ufs import resolver_uf

__all__ = [
	"EXCECOES_DO_DIGITO",
	"ExcecoesInvalidas",
	"MunicipioInvalido",
	"digito_verificador",
	"ler_excecoes",
	"validar_municipio",
]

EXCECOES_DO_DIGITO: dict[str, tuple[str, str]] = {
	"2201919": ("Bom Princípio do Piauí", "PI"),
	"2201988": ("Brejo do Piauí", "PI"),
	"2202251": ("Canavieira", "PI"),
	"2611533": ("Quixaba", "PE"),
	"3117836": ("Cônego Marinho", "MG"),
	"3152131": ("Ponto Chique", "MG"),
	"4305871": ("Coronel Barros", "RS"),
	"5203939": ("Buriti de Goiás", "GO"),
	"5203962": ("Buritinópolis", "GO"),
}
"""Municípios reais cujo código não obedece à regra do dígito verificador. Fonte: lista de municípios do IBGE,
conferida em 2026-10-09 (5.571 municípios; 9 exceções)."""

_SETE_DIGITOS = re.compile(r"\d{7}")


class MunicipioInvalido(ValueError):
	"""O código de município não passa. `motivo` é `"formato"`, `"uf"` ou `"digito"`."""

	def __init__(self, motivo: str, mensagem: str):
		super().__init__(mensagem)
		self.motivo = motivo


class ExcecoesInvalidas(ValueError):
	"""A lista de exceções configurada não é uma lista de códigos de sete dígitos."""


def digito_verificador(seis_primeiros: str) -> int:
	"""O dígito verificador dos seis primeiros algarismos (ver o módulo)."""
	if not re.fullmatch(r"\d{6}", seis_primeiros):
		raise ValueError(f"esperados 6 algarismos, recebido {seis_primeiros!r}")

	soma = 0

	for posicao, algarismo in enumerate(seis_primeiros):
		produto = int(algarismo) * (1 if posicao % 2 == 0 else 2)
		soma += produto - 9 if produto > 9 else produto

	return (10 - soma % 10) % 10


def ler_excecoes(valor) -> frozenset[str]:
	"""A lista de exceções adicionais do administrador; `None` ou vazia dá conjunto vazio.

	Recusa o que não for lista de códigos de sete dígitos, em vez de ignorar em silêncio: uma exceção digitada
	errada não liberaria o município que o administrador queria liberar.
	"""
	if valor is None:
		return frozenset()

	if not isinstance(valor, list | tuple) or not all(
		isinstance(item, str) and _SETE_DIGITOS.fullmatch(item.strip()) for item in valor
	):
		raise ExcecoesInvalidas(
			f"deve ser uma lista de códigos de município de 7 dígitos, recebido {valor!r}"
		)

	return frozenset(item.strip() for item in valor)


def validar_municipio(codigo: str, uf: str | None = None, excecoes_extras=frozenset()) -> None:
	"""Levanta `MunicipioInvalido` se o código não passa; devolve `None` se passa.

	`uf` é o texto do estado do endereço (sigla ou nome por extenso). Se não resolver para uma UF, a coerência
	com o prefixo **não se aplica** — adivinhar rejeitaria endereço válido —, mas o formato e o dígito continuam
	valendo. As exceções (as 9 conhecidas e as extras) dispensam só o dígito verificador, nunca a UF.
	"""
	if not _SETE_DIGITOS.fullmatch(codigo or ""):
		raise MunicipioInvalido(
			"formato", f"Código do Município (IBGE) deve ter 7 dígitos numéricos, recebido {codigo}"
		)

	try:
		uf_do_codigo = sigla_da_uf(codigo[:2])
	except UfDesconhecida as erro:
		raise MunicipioInvalido(
			"uf", f"O código de município {codigo} começa por {codigo[:2]}, que não é código de UF"
		) from erro

	uf_do_endereco = resolver_uf(uf)

	if uf_do_endereco and uf_do_endereco != uf_do_codigo:
		raise MunicipioInvalido(
			"uf",
			f"O código de município {codigo} é de {uf_do_codigo}, mas o endereço informa {uf_do_endereco}",
		)

	if codigo in EXCECOES_DO_DIGITO or codigo in excecoes_extras:
		return

	esperado = digito_verificador(codigo[:6])

	if int(codigo[6]) != esperado:
		raise MunicipioInvalido(
			"digito",
			f"Dígito verificador do código de município {codigo} incorreto: o último dígito deveria ser "
			f"{esperado}. Confira o código na tabela do IBGE.",
		)
