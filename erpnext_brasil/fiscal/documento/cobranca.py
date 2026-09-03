# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Grupo `cobr` da NF-e — fatura e duplicatas da venda a prazo.

O elo que faltava entre venda, documento fiscal e boleto
----------------------------------------------------------------
Auditoria do fluxo de Compras e Vendas: `pag` (formas de pagamento) já estava modelado,
`cobr` não. É uma lacuna com consequência prática, porque `cobr` é onde três coisas se
encontram:

1. a **venda parcelada** (no ERPNext, o `Payment Schedule` da fatura);
2. o **documento fiscal**, que precisa declarar cada duplicata;
3. o **boleto**, que é emitido por parcela — mesmo vencimento, mesmo valor.

Sem `cobr`, uma NF-e de venda a prazo sai declarando só a forma de pagamento, sem dizer
quais são as parcelas. E a duplicata não é detalhe de layout: é título de crédito
(Lei 5.474/68), base do que vira "contas a receber" e do que se leva a protesto.

`pag` e `cobr` respondem perguntas diferentes — e por isso são grupos separados
------------------------------------------------------------------------------------------
Fácil confundir, e o XSD os separa de propósito: `pag` diz **como** se paga (dinheiro,
cartão, Pix, prazo); `cobr` diz **quando e quanto** de cada parcela. Uma venda em 3x no
boleto tem um `pag` (com `tPag` de duplicata mercantil) e três `dup`.

O que o layout permite, e o que este módulo exige a mais
----------------------------------------------------------------
Confirmado no `leiauteNFe_v4.00.xsd`: **todos** os campos de `fat` e `dup` são
`minOccurs="0"` — o XSD aceita uma duplicata sem número, sem vencimento e sem valor.
Aceitar isso aqui seria produzir um documento tecnicamente válido e inútil: uma parcela
sem valor não cobra nada, e sem vencimento não vence. Este módulo exige valor e
vencimento em cada duplicata — **divergência deliberada e mais restritiva que o XSD**,
registrada como tal (mesma disciplina de `esocial_lote_registro`, que exige protocolo
onde o schema não exigiria).

O limite de 120 duplicatas é do XSD (`maxOccurs="120"`), não invenção.

Pós-condição da fatura
------------------------------
Quando `fat` é informada, `vLiq` tem de bater com `vOrig - vDesc` — o XSD não verifica,
mas uma fatura cujo líquido não fecha com a conta é erro de montagem, não escolha. É
pós-condição no sentido de Design by Contract: a função não devolve um resultado que
contradiz o que ela mesma recebeu.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

__all__ = [
	"LIMITE_DE_DUPLICATAS",
	"CobrancaInvalida",
	"Duplicata",
	"Fatura",
	"montar_cobr",
]

LIMITE_DE_DUPLICATAS = 120
"""`maxOccurs="120"` no `leiauteNFe_v4.00.xsd`."""

ZERO = Decimal("0.00")

_TAMANHO_MAXIMO_NUMERO = 60


class CobrancaInvalida(ValueError):
	"""Dado que produziria uma cobrança tecnicamente válida e inútil."""


@dataclass(frozen=True)
class Duplicata:
	"""Uma parcela — `dup` no XSD, duplicata mercantil na Lei 5.474/68.

	`numero` e `vencimento` são opcionais no XSD; aqui `vencimento` e `valor` são
	obrigatórios, porque parcela sem vencimento não vence e sem valor não cobra nada
	(ver docstring do módulo).
	"""

	vencimento: date
	valor: Decimal
	numero: str = ""

	def __post_init__(self) -> None:
		if self.valor <= ZERO:
			raise CobrancaInvalida(
				f"duplicata precisa de valor positivo, recebido {self.valor} — "
				"uma parcela sem valor não cobra nada"
			)

		if len(self.numero) > _TAMANHO_MAXIMO_NUMERO:
			raise CobrancaInvalida(
				f"nDup aceita até {_TAMANHO_MAXIMO_NUMERO} caracteres, recebido {len(self.numero)}"
			)


@dataclass(frozen=True)
class Fatura:
	"""`fat` — o total que as duplicatas parcelam.

	`liquido` é derivado, não recebido: `original - desconto`. Aceitá-lo por fora
	permitiria informar um líquido que não fecha com a conta, e é justamente o tipo de
	incoerência que ninguém percebe até o Fisco recusar.
	"""

	original: Decimal
	desconto: Decimal = ZERO
	numero: str = ""

	def __post_init__(self) -> None:
		if self.original <= ZERO:
			raise CobrancaInvalida(f"valor original da fatura deve ser positivo, recebido {self.original}")

		if self.desconto < ZERO:
			raise CobrancaInvalida(f"desconto não pode ser negativo, recebido {self.desconto}")

		if self.desconto > self.original:
			raise CobrancaInvalida(f"desconto ({self.desconto}) maior que o valor original ({self.original})")

		if len(self.numero) > _TAMANHO_MAXIMO_NUMERO:
			raise CobrancaInvalida(
				f"nFat aceita até {_TAMANHO_MAXIMO_NUMERO} caracteres, recebido {len(self.numero)}"
			)

	@property
	def liquido(self) -> Decimal:
		return self.original - self.desconto


def montar_cobr(fatura: Fatura | None = None, duplicatas: list[Duplicata] | None = None) -> dict:
	"""Monta o grupo `cobr`, na ordem do XSD: `fat` antes de `dup`.

	Pós-condição verificada: quando há fatura **e** duplicatas, a soma das parcelas tem
	de bater com o líquido da fatura. Parcelar R$ 1.000 em três de R$ 300 é erro de
	montagem que o XSD aceitaria em silêncio — e que só apareceria na conciliação do
	contas a receber, muito depois.
	"""
	duplicatas = list(duplicatas or [])

	if len(duplicatas) > LIMITE_DE_DUPLICATAS:
		raise CobrancaInvalida(
			f"a NF-e aceita no máximo {LIMITE_DE_DUPLICATAS} duplicatas, recebido {len(duplicatas)}"
		)

	if fatura is None and not duplicatas:
		raise CobrancaInvalida("cobrança vazia: informe a fatura, as duplicatas, ou ambas")

	if fatura is not None and duplicatas:
		soma = sum((d.valor for d in duplicatas), ZERO)

		if soma != fatura.liquido:
			raise CobrancaInvalida(
				f"a soma das duplicatas ({soma}) não fecha com o líquido da fatura "
				f"({fatura.liquido}) — parcelar um valor diferente do faturado é erro de "
				"montagem, e só apareceria na conciliação do contas a receber"
			)

	grupo: dict = {}

	if fatura is not None:
		grupo["fat"] = _montar_fat(fatura)

	if duplicatas:
		grupo["dup"] = [_montar_dup(d) for d in duplicatas]

	return {"cobr": grupo}


def _montar_fat(fatura: Fatura) -> dict:
	campos: dict = {}

	if fatura.numero:
		campos["nFat"] = fatura.numero

	campos["vOrig"] = fatura.original

	if fatura.desconto:
		campos["vDesc"] = fatura.desconto

	campos["vLiq"] = fatura.liquido

	return campos


def _montar_dup(duplicata: Duplicata) -> dict:
	campos: dict = {}

	if duplicata.numero:
		campos["nDup"] = duplicata.numero

	# `TData` no XSD: AAAA-MM-DD, que é o `isoformat()` de `date`.
	campos["dVenc"] = duplicata.vencimento.isoformat()
	campos["vDup"] = duplicata.valor

	return campos
