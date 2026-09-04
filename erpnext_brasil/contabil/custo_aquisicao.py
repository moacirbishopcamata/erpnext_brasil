# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Custo de aquisição: quanto da nota vira estoque e quanto vira crédito.

A regra que faz o mesmo produto ter custos diferentes
--------------------------------------------------------------
**RIR/2018, art. 301, §3º**: os impostos recuperáveis por meio de créditos na escrita
fiscal **não integram** o custo de aquisição. Eles vão para "Impostos a Recuperar" (conta
que `plano_de_contas.py` já tem), não para o estoque.

A consequência é contraintuitiva e cara: o **mesmo produto, na mesma nota, tem custo
diferente** dependendo de quem compra e para quê. Uma empresa do Lucro Real que compra
para revenda credita ICMS e PIS/COFINS — o custo é o valor da mercadoria sem esses
tributos. A mesma compra feita por optante do Simples, que não credita, tem custo maior.

Somar tudo ao estoque infla o custo, derruba a margem calculada e distorce o preço que
`fiscal/precificacao.py` produziria. É o erro que este módulo existe para evitar.

Atecnia registrada: o texto diz "impostos", mas PIS/COFINS são contribuições
------------------------------------------------------------------------------------------
O §3º fala em *impostos* recuperáveis. PIS e COFINS, tecnicamente, são **contribuições**,
não impostos — pela letra estrita, ficariam de fora da exclusão. A doutrina trata isso
como atecnia de redação: a interpretação sistemática inclui as contribuições, porque a
razão da regra (não capitalizar no estoque o que se recupera como crédito) vale
igualmente para elas.

Este módulo segue a interpretação sistemática — trata PIS/COFINS recuperáveis como não
integrantes do custo —, e registra aqui que a letra do dispositivo é mais estreita. É
divergência declarada, não interpretação silenciosa.

O que decide a recuperabilidade não é o tributo, é a situação
----------------------------------------------------------------------
Quem chama informa **quais** tributos são recuperáveis naquela aquisição, porque isso
depende de coisas que este módulo não conhece:

- o **regime** do comprador (Simples não credita ICMS/IPI da forma comum; o não
  cumulativo credita PIS/COFINS, o cumulativo não);
- a **destinação** do item (revenda e insumo creditam; uso e consumo não);
- se o comprador é **industrial ou equiparado** (só ele credita IPI).

O projeto já tem esses dados (`br_regime_pis_cofins`, `finalidade_compra`), mas cruzá-los
é decisão da camada de integração — aqui fica a aritmética, que é o que se pode testar
sem bench.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = ["CustoInvalido", "ResultadoCusto", "TributoDaAquisicao", "custo_de_aquisicao"]

ZERO = Decimal("0.00")


class CustoInvalido(ValueError):
	"""Composição de custo que não fecha."""


@dataclass(frozen=True)
class TributoDaAquisicao:
	"""Um tributo destacado na nota de compra, e se ele é recuperável **nesta** compra.

	`recuperavel` é informado, não deduzido do nome: o mesmo ICMS é recuperável para uma
	empresa e não para outra (ver docstring do módulo). Deduzir aqui exigiria conhecer
	regime e destinação, que este módulo deliberadamente não conhece.

	`por_dentro` importa tanto quanto: **ICMS, PIS e COFINS já estão dentro** do valor da
	mercadoria; o **IPI é por fora** e soma ao total da nota. Tratar os dois igual erra o
	custo nos dois sentidos — somar um ICMS não recuperável dobraria o imposto, e ignorar
	um IPI não recuperável deixaria de fora dinheiro que foi pago.
	"""

	nome: str
	valor: Decimal
	recuperavel: bool = False
	por_dentro: bool = True

	def __post_init__(self) -> None:
		if not self.nome.strip():
			raise CustoInvalido("o tributo precisa de nome — é ele que identifica a conta de crédito")

		if self.valor < ZERO:
			raise CustoInvalido(f"valor de {self.nome} não pode ser negativo, recebido {self.valor}")


@dataclass(frozen=True)
class ResultadoCusto:
	"""A decomposição da nota: o que vira estoque, o que vira crédito.

	Devolver só o custo esconderia a conta. Quem compra precisa ver quanto do que pagou
	volta como crédito — é essa diferença que explica por que a mesma nota gera custos
	diferentes em empresas diferentes.
	"""

	custo: Decimal
	"""O que integra o estoque."""

	creditos: Decimal
	"""O que vai para "Impostos a Recuperar", não para o estoque."""

	creditos_por_tributo: dict[str, Decimal] = field(default_factory=dict)

	@property
	def total_pago(self) -> Decimal:
		"""Custo mais créditos — tem de bater com o desembolso, e há teste provando."""
		return self.custo + self.creditos


def custo_de_aquisicao(
	valor_mercadoria: Decimal,
	tributos: list[TributoDaAquisicao] | None = None,
	frete: Decimal = ZERO,
	seguro: Decimal = ZERO,
	outras_despesas: Decimal = ZERO,
	descontos: Decimal = ZERO,
) -> ResultadoCusto:
	"""Separa o que vira custo de estoque do que vira crédito fiscal.

	Frete, seguro e outras despesas **integram** o custo (RIR/2018, art. 301: o custo
	compreende o transporte e o seguro até o estabelecimento). Desconto reduz.

	Tributo **não recuperável integra** o custo; recuperável **não integra** e é
	devolvido em `creditos`, para o chamador lançar em "Impostos a Recuperar".

	Pós-condição: `custo + créditos` é igual ao total pago. Se não fosse, algum valor
	teria sumido ou sido contado duas vezes — e um erro assim se propaga para a margem e
	para o preço sem dar sinal.
	"""
	for nome, valor in (
		("valor_mercadoria", valor_mercadoria),
		("frete", frete),
		("seguro", seguro),
		("outras_despesas", outras_despesas),
		("descontos", descontos),
	):
		if not isinstance(valor, Decimal):
			raise CustoInvalido(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

		if valor < ZERO:
			raise CustoInvalido(f"{nome} não pode ser negativo, recebido {valor}")

	tributos = list(tributos or [])

	recuperaveis = [t for t in tributos if t.recuperavel]
	creditos = sum((t.valor for t in recuperaveis), ZERO)

	# Tributo **por fora** (IPI) não está no valor da mercadoria: soma ao que se pagou.
	# Tributo **por dentro** (ICMS, PIS, COFINS) já está lá — somá-lo dobraria o imposto.
	por_fora = sum((t.valor for t in tributos if not t.por_dentro), ZERO)

	base = valor_mercadoria + frete + seguro + outras_despesas - descontos

	if base < ZERO:
		raise CustoInvalido(
			f"os descontos ({descontos}) superam mercadoria e acessórios — "
			"custo negativo não é resultado válido de uma aquisição"
		)

	# Do total desembolsado, sai o que volta como crédito. O que sobra é o custo.
	custo = base + por_fora - creditos

	if custo < ZERO:
		raise CustoInvalido(
			f"os créditos ({creditos}) superam o valor da aquisição ({base + por_fora}) — "
			"algum tributo foi informado com valor maior que o da própria nota"
		)

	return ResultadoCusto(
		custo=arredondar(custo),
		creditos=arredondar(creditos),
		creditos_por_tributo={t.nome: arredondar(t.valor) for t in recuperaveis},
	)
