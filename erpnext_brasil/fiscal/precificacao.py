# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Preço de venda a partir do custo e da margem, com imposto brasileiro.

A armadilha que este módulo existe para evitar
------------------------------------------------------
O erro de precificação mais caro do Brasil cabe numa linha: **somar a alíquota ao custo
em vez de dividir**.

Um produto que custa R$ 100 e tem 18% de ICMS não é vendido a R$ 118. A R$ 118, o ICMS
— que é calculado **por dentro**, sobre o próprio preço — é R$ 21,24, e sobra R$ 96,76:
prejuízo de R$ 3,24 numa venda que parecia estar no custo. O preço correto é
R$ 100 ÷ (1 − 0,18) = R$ 121,95, onde o ICMS é R$ 21,95 e sobram exatamente R$ 100.

`icms.base_por_dentro` já fazia esse *gross-up* para **um** imposto. Este módulo resolve
o problema completo: vários impostos por dentro somados, mais a margem desejada, mais os
impostos **por fora** que a reforma tributária introduz.

Por dentro e por fora não se misturam na mesma conta
------------------------------------------------------------
Distinção que `ibs_cbs.py` já registrava e que aqui vira aritmética:

- **Por dentro** (ICMS, PIS, COFINS, ISS): integram a própria base. Entram no
  denominador — dividem.
- **Por fora** (IBS e CBS, a partir da reforma): não integram a própria base nem a um do
  outro. Entram depois — multiplicam.

Isso muda a fórmula do preço, não só o valor do imposto. Um sistema que trate os dois
igual acerta hoje e erra em 2027, ou vice-versa.

Margem sobre o preço, não sobre o custo
-----------------------------------------------
Duas coisas diferentes que a mesma palavra nomeia, e confundi-las é o segundo erro mais
comum:

- **margem** (aqui): percentual **do preço de venda** que sobra. Margem de 30% num preço
  de R$ 100 significa R$ 30 de sobra.
- **markup**: percentual **sobre o custo**. Markup de 30% sobre custo de R$ 100 dá preço
  de R$ 130 — cuja margem é 23%, não 30%.

Este módulo trabalha com **margem sobre o preço**, que é o que "margem de contribuição"
significa em análise de resultado, e oferece `markup_para_margem` para converter quando
a entrada vier no outro formato.

A pré-condição que impede o resultado absurdo
-----------------------------------------------------
Se impostos por dentro + margem somarem 100% ou mais, **não existe preço** que satisfaça:
o denominador vai a zero ou fica negativo. Uma implementação ingênua devolveria um número
enorme ou negativo e o usuário o cadastraria. Aqui falha alto, dizendo o que não fecha.

Funções puras: nenhuma dependência do Frappe. `Decimal` sempre, nunca `float` —
arredondamento de centavo em preço é diferença que aparece na nota.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = [
	"PrecificacaoInvalida",
	"ResultadoPreco",
	"margem_efetiva",
	"markup_para_margem",
	"preco_de_venda",
]

ZERO = Decimal("0.00")
UM = Decimal(1)


class PrecificacaoInvalida(ValueError):
	"""Combinação de custo, margem e impostos para a qual não existe preço."""


def _fracao(valor: Decimal, nome: str) -> None:
	"""Alíquota e margem são fração (`0.18`), nunca percentual (`18`) — mesma convenção
	de todo o app, e aqui o erro seria de ordem de grandeza."""
	if not isinstance(valor, Decimal):
		raise PrecificacaoInvalida(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

	if valor < ZERO or valor >= UM:
		raise PrecificacaoInvalida(
			f"{nome} deve ser uma fração entre 0 e 1 (0.18 para 18%), recebido {valor}"
		)


@dataclass(frozen=True)
class ResultadoPreco:
	"""O preço e a decomposição que o justifica.

	Devolver só o preço esconderia a conta: quem precifica quer ver quanto do preço é
	imposto e quanto sobra, para decidir se aceita a margem que restou.
	"""

	preco: Decimal
	"""Preço de venda antes dos impostos por fora — a base sobre a qual eles incidem."""

	preco_final: Decimal
	"""O que o cliente paga, já com os impostos por fora."""

	custo: Decimal
	impostos_por_dentro: Decimal
	impostos_por_fora: Decimal
	margem: Decimal
	"""Valor absoluto que sobra depois do custo e dos impostos por dentro."""

	@property
	def margem_percentual(self) -> Decimal:
		"""A margem como fração do preço — o mesmo número que entrou, confirmado pela
		conta de volta. Serve de pós-condição verificável por quem chama."""
		if self.preco == ZERO:
			return ZERO

		return self.margem / self.preco


def preco_de_venda(
	custo: Decimal,
	margem: Decimal = ZERO,
	aliquotas_por_dentro: list[Decimal] | None = None,
	aliquotas_por_fora: list[Decimal] | None = None,
) -> ResultadoPreco:
	"""Preço que entrega a `margem` desejada sobre o custo, com os impostos informados.

	`aliquotas_por_dentro` (ICMS, PIS, COFINS, ISS) entram no **denominador**;
	`aliquotas_por_fora` (IBS, CBS) multiplicam o resultado. Passar uma no lugar da outra
	produz preço errado nos dois sentidos — ver docstring do módulo.

	A fórmula:

	    preço = custo ÷ (1 − Σ alíquotas por dentro − margem)
	    preço final = preço × (1 + Σ alíquotas por fora)
	"""
	if not isinstance(custo, Decimal):
		raise PrecificacaoInvalida(f"custo deve ser Decimal, recebido {type(custo).__name__}")

	if custo < ZERO:
		raise PrecificacaoInvalida(f"custo não pode ser negativo, recebido {custo}")

	_fracao(margem, "margem")

	por_dentro = _somar_aliquotas(aliquotas_por_dentro, "aliquotas_por_dentro")
	por_fora = _somar_aliquotas(aliquotas_por_fora, "aliquotas_por_fora")

	denominador = UM - por_dentro - margem

	if denominador <= ZERO:
		raise PrecificacaoInvalida(
			f"impostos por dentro ({por_dentro}) mais margem ({margem}) consomem o preço "
			"inteiro: não existe preço que satisfaça. Reduza a margem ou reveja a "
			"tributação — somar as duas coisas e esperar que caiba é o erro que esta "
			"verificação impede"
		)

	preco = arredondar(custo / denominador)
	valor_por_dentro = arredondar(preco * por_dentro)
	preco_final = arredondar(preco * (UM + por_fora))

	return ResultadoPreco(
		preco=preco,
		preco_final=preco_final,
		custo=custo,
		impostos_por_dentro=valor_por_dentro,
		impostos_por_fora=arredondar(preco * por_fora),
		margem=arredondar(preco - custo - valor_por_dentro),
	)


def margem_efetiva(
	preco: Decimal,
	custo: Decimal,
	aliquotas_por_dentro: list[Decimal] | None = None,
) -> Decimal:
	"""A margem que um preço **já praticado** realmente entrega.

	O caminho inverso de `preco_de_venda`, e o mais útil na prática: descobrir que a
	tabela de preços herdada entrega 4% onde se acreditava entregar 20%. Devolve fração
	do preço, e pode ser **negativa** — prejuízo é resultado legítimo desta conta, não
	erro a esconder.
	"""
	if preco <= ZERO:
		raise PrecificacaoInvalida(f"preço deve ser positivo, recebido {preco}")

	por_dentro = _somar_aliquotas(aliquotas_por_dentro, "aliquotas_por_dentro")

	sobra = preco - custo - (preco * por_dentro)

	return sobra / preco


def markup_para_margem(markup: Decimal) -> Decimal:
	"""Converte markup (sobre o **custo**) em margem (sobre o **preço**).

	Markup de 30% não é margem de 30%: custo 100 vira preço 130, e 30 sobre 130 é 23,08%.
	A conversão existe porque a entrada costuma vir no formato errado — de planilha, de
	fornecedor, de hábito.
	"""
	if markup < ZERO:
		raise PrecificacaoInvalida(f"markup não pode ser negativo, recebido {markup}")

	return markup / (UM + markup)


def _somar_aliquotas(aliquotas: list[Decimal] | None, nome: str) -> Decimal:
	total = ZERO

	for indice, aliquota in enumerate(aliquotas or []):
		_fracao(aliquota, f"{nome}[{indice}]")
		total += aliquota

	if total >= UM:
		raise PrecificacaoInvalida(f"a soma de {nome} ({total}) atinge ou passa de 100%")

	return total
