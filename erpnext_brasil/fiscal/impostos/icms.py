# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cálculo de ICMS: imposto por dentro, redução de base, substituição tributária e DIFAL.

Por que existe
--------------
O motor de impostos do ERPNext modela bem *como* um imposto entra no documento
(`included_in_print_rate` para imposto por dentro, `On Previous Row Amount` para
encadear base, `category: Valuation` para compor custo). O que ele não tem é a
**aritmética fiscal brasileira**: gross-up do ICMS, MVA ajustada, base dupla do DIFAL.
É isso que está aqui.

Decimal, não float
------------------
Todo valor monetário é `Decimal`. Cálculo fiscal com ponto flutuante acumula erro que
não aparece no teste unitário e aparece na conferência do contador: `0.1 + 0.2` já
difere de `0.3`, e uma nota tem dezenas de itens somados e rateados. O arredondamento é
explícito e `ROUND_HALF_UP` — a regra usada nos documentos fiscais, diferente do
`ROUND_HALF_EVEN` que o Python usa por padrão.

Alíquotas entram como fração (0.18 para 18%), nunca como percentual, para eliminar a
classe de bug em que alguém passa 18 e obtém um imposto dezoito vezes maior.

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import Decimal, ROUND_HALF_UP

__all__ = [
	"CENTAVO",
	"ResultadoICMS",
	"ResultadoST",
	"arredondar",
	"base_por_dentro",
	"calcular_difal",
	"calcular_icms",
	"calcular_icms_st",
	"mva_ajustada",
	"reduzir_base",
]

from dataclasses import dataclass

CENTAVO = Decimal("0.01")


def arredondar(valor: Decimal, casas: Decimal = CENTAVO) -> Decimal:
	"""Arredonda meio-para-cima, que é a regra dos documentos fiscais.

	O padrão do Python é `ROUND_HALF_EVEN` (banqueiro), que arredonda 0.125 para 0.12.
	Num documento fiscal isso destoa do que o validador da SEFAZ espera.
	"""
	return valor.quantize(casas, rounding=ROUND_HALF_UP)


def _fracao(aliquota: Decimal, nome: str) -> Decimal:
	"""Valida que a alíquota veio como fração, não como percentual."""
	if not (Decimal(0) <= aliquota < Decimal(1)):
		raise ValueError(
			f"{nome} deve ser fração entre 0 e 1 (0.18 para 18%), recebido {aliquota}"
		)

	return aliquota


@dataclass(frozen=True)
class ResultadoICMS:
	base: Decimal
	aliquota: Decimal
	valor: Decimal


@dataclass(frozen=True)
class ResultadoST:
	base_st: Decimal
	icms_proprio: Decimal
	icms_st: Decimal
	mva_aplicada: Decimal


def base_por_dentro(valor_sem_imposto: Decimal, aliquota: Decimal) -> Decimal:
	"""Embute o ICMS no preço ("imposto por dentro").

	O ICMS integra a própria base de cálculo, então não basta somar a alíquota ao preço:
	é preciso dividir por (1 - alíquota). Um produto de R$ 100 sem imposto com ICMS de
	18% não custa R$ 118, custa R$ 121,95 — e o imposto é R$ 21,95, não R$ 18.

	Este é o cálculo que `included_in_print_rate` do ERPNext pressupõe já ter sido feito
	quando o preço cadastrado já contém o imposto.
	"""
	_fracao(aliquota, "aliquota")

	return arredondar(valor_sem_imposto / (Decimal(1) - aliquota))


def reduzir_base(base: Decimal, percentual_reducao: Decimal) -> Decimal:
	"""Aplica redução de base de cálculo (benefício fiscal por produto ou operação)."""
	_fracao(percentual_reducao, "percentual_reducao")

	return arredondar(base * (Decimal(1) - percentual_reducao))


def calcular_icms(
	base: Decimal,
	aliquota: Decimal,
	percentual_reducao: Decimal = Decimal(0),
) -> ResultadoICMS:
	"""ICMS próprio da operação, com redução de base opcional."""
	_fracao(aliquota, "aliquota")

	base_final = reduzir_base(base, percentual_reducao) if percentual_reducao else arredondar(base)

	return ResultadoICMS(
		base=base_final,
		aliquota=aliquota,
		valor=arredondar(base_final * aliquota),
	)


def mva_ajustada(
	mva_original: Decimal,
	aliquota_interestadual: Decimal,
	aliquota_interna_destino: Decimal,
) -> Decimal:
	"""Ajusta a MVA para operação interestadual.

	A MVA publicada no convênio pressupõe operação interna. Numa venda interestadual, a
	carga na origem é menor, e usar a MVA original subestimaria a substituição. O ajuste
	recompõe a diferença:

        MVA aj = [(1 + MVA) × (1 - Aliq inter) / (1 - Aliq intra)] - 1

	Devolve fração (0.4523 para 45,23%), com quatro casas — a precisão usada nos
	convênios.
	"""
	_fracao(aliquota_interestadual, "aliquota_interestadual")
	_fracao(aliquota_interna_destino, "aliquota_interna_destino")

	if mva_original < 0:
		raise ValueError(f"mva_original não pode ser negativa, recebido {mva_original}")

	ajustada = (
		(Decimal(1) + mva_original)
		* (Decimal(1) - aliquota_interestadual)
		/ (Decimal(1) - aliquota_interna_destino)
	) - Decimal(1)

	return arredondar(ajustada, Decimal("0.0001"))


def calcular_icms_st(
	valor_produtos: Decimal,
	aliquota_proprio: Decimal,
	aliquota_interna_destino: Decimal,
	mva: Decimal,
	ipi: Decimal = Decimal(0),
	frete: Decimal = Decimal(0),
	seguro: Decimal = Decimal(0),
	outras_despesas: Decimal = Decimal(0),
	descontos: Decimal = Decimal(0),
	percentual_reducao_proprio: Decimal = Decimal(0),
) -> ResultadoST:
	"""ICMS por substituição tributária.

	A base da ST parte do valor da operação **acrescido de IPI, frete, seguro e outras
	despesas, menos descontos**, e sobre isso incide a margem de valor agregado. O IPI
	entra na base da ST mesmo quando não entra na base do ICMS próprio — é a pegadinha
	que mais produz ST calculada a menos.

	O ICMS-ST é o imposto da cadeia inteira menos o que já se pagou na operação própria,
	e nunca é negativo: quando o próprio supera o da cadeia, não há ST a recolher.
	"""
	_fracao(aliquota_proprio, "aliquota_proprio")
	_fracao(aliquota_interna_destino, "aliquota_interna_destino")

	if mva < 0:
		raise ValueError(f"mva não pode ser negativa, recebido {mva}")

	base_operacao = valor_produtos + ipi + frete + seguro + outras_despesas - descontos

	if base_operacao < 0:
		raise ValueError("A base da operação ficou negativa; verifique descontos e acréscimos")

	# O ICMS próprio não considera o IPI na base (salvo exceções), mas considera frete,
	# seguro e demais despesas acessórias.
	base_propria = valor_produtos + frete + seguro + outras_despesas - descontos
	proprio = calcular_icms(base_propria, aliquota_proprio, percentual_reducao_proprio)

	base_st = arredondar(base_operacao * (Decimal(1) + mva))
	icms_st = arredondar(base_st * aliquota_interna_destino) - proprio.valor

	return ResultadoST(
		base_st=base_st,
		icms_proprio=proprio.valor,
		icms_st=max(icms_st, Decimal("0.00")),
		mva_aplicada=mva,
	)


def calcular_difal(
	valor_operacao: Decimal,
	aliquota_interestadual: Decimal,
	aliquota_interna_destino: Decimal,
	base_dupla: bool = True,
	aliquota_fcp: Decimal = Decimal(0),
) -> dict[str, Decimal]:
	"""Diferencial de alíquotas da EC 87/2015, para consumidor final.

	Duas metodologias convivem, e os estados divergem — por isso `base_dupla` é
	parâmetro, não constante:

	- **base dupla** (padrão, adotada pela maioria após a LC 190/2022): retira-se o ICMS
	  de origem do valor e reembute-se o ICMS interno do destino, porque o imposto do
	  destino também é calculado por dentro;
	- **base única**: aplica-se direto a diferença entre as alíquotas sobre o valor.

	O FCP, quando o destino o institui, incide sobre a mesma base do destino e é
	recolhido em separado — por isso vem discriminado no retorno.
	"""
	_fracao(aliquota_interestadual, "aliquota_interestadual")
	_fracao(aliquota_interna_destino, "aliquota_interna_destino")
	_fracao(aliquota_fcp, "aliquota_fcp")

	if aliquota_interna_destino < aliquota_interestadual:
		raise ValueError(
			"A alíquota interna do destino não pode ser menor que a interestadual; "
			"não haveria diferencial a recolher"
		)

	icms_origem = arredondar(valor_operacao * aliquota_interestadual)

	if base_dupla:
		base_destino = arredondar(
			(valor_operacao - icms_origem) / (Decimal(1) - aliquota_interna_destino)
		)
	else:
		base_destino = arredondar(valor_operacao)

	icms_destino = arredondar(base_destino * aliquota_interna_destino)
	difal = arredondar(icms_destino - icms_origem)

	return {
		"base_origem": arredondar(valor_operacao),
		"icms_origem": icms_origem,
		"base_destino": base_destino,
		"icms_destino": icms_destino,
		"difal": max(difal, Decimal("0.00")),
		"fcp": arredondar(base_destino * aliquota_fcp) if aliquota_fcp else Decimal("0.00"),
	}
