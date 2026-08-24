# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cálculo de IPI, e a regra constitucional que decide se ele entra na base do ICMS.

O IPI em si é aritmética simples — ad valorem ou por unidade. O que não é simples, e o
que este módulo existe para não deixar ninguém errar, é a regra do art. 155, §2º, XI da
Constituição:

    O IPI **não** compõe a base do ICMS quando a operação, entre contribuintes, destina
    o produto a industrialização ou comercialização. Nos demais casos — venda a
    consumidor final, ou a destinatário não contribuinte — ele **compõe**.

Errar isso não gera erro de sistema: gera nota aceita pela SEFAZ com ICMS a menor, que
vira autuação na fiscalização. Por isso a decisão é uma função explícita, com nome, e
não um `if` perdido dentro do cálculo.

Funções puras, `Decimal`, alíquota como fração — mesmas regras de `icms.py`.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = [
	"ResultadoIPI",
	"calcular_ipi",
	"calcular_ipi_por_unidade",
	"ipi_compoe_base_icms",
]


@dataclass(frozen=True)
class ResultadoIPI:
	base: Decimal
	valor: Decimal
	compoe_base_icms: bool


def ipi_compoe_base_icms(
	destinatario_contribuinte: bool,
	destinado_a_industrializacao_ou_comercio: bool,
) -> bool:
	"""Decide se o IPI integra a base de cálculo do ICMS (CF art. 155, §2º, XI).

	Só fica de fora na conjunção das duas condições: destinatário contribuinte **e**
	produto destinado a industrialização ou comércio. Basta uma delas falhar — venda a
	consumidor final, ou a não contribuinte — para o IPI compor a base.
	"""
	return not (destinatario_contribuinte and destinado_a_industrializacao_ou_comercio)


def calcular_ipi(
	valor_produtos: Decimal,
	aliquota: Decimal,
	frete: Decimal = Decimal(0),
	seguro: Decimal = Decimal(0),
	outras_despesas: Decimal = Decimal(0),
	descontos: Decimal = Decimal(0),
	destinatario_contribuinte: bool = True,
	destinado_a_industrializacao_ou_comercio: bool = True,
) -> ResultadoIPI:
	"""IPI ad valorem.

	A base inclui frete, seguro e demais despesas acessórias, menos descontos
	incondicionais. Diferente do ICMS, o IPI é imposto **por fora**: soma-se ao total da
	nota em vez de estar embutido no preço.
	"""
	if not (Decimal(0) <= aliquota < Decimal(1)):
		raise ValueError(f"aliquota deve ser fração entre 0 e 1, recebido {aliquota}")

	base = valor_produtos + frete + seguro + outras_despesas - descontos

	if base < 0:
		raise ValueError("A base do IPI ficou negativa; verifique descontos e acréscimos")

	base = arredondar(base)

	return ResultadoIPI(
		base=base,
		valor=arredondar(base * aliquota),
		compoe_base_icms=ipi_compoe_base_icms(
			destinatario_contribuinte, destinado_a_industrializacao_ou_comercio
		),
	)


def calcular_ipi_por_unidade(
	quantidade: Decimal,
	valor_por_unidade: Decimal,
	destinatario_contribuinte: bool = True,
	destinado_a_industrializacao_ou_comercio: bool = True,
) -> ResultadoIPI:
	"""IPI específico, cobrado por unidade de medida em vez de percentual.

	Aplica-se a produtos com tributação por quantidade — bebidas e cigarros, entre
	outros. Aqui não existe "base" no sentido de valor da operação; o que consta na nota
	é a quantidade tributada, e é ela que fica registrada como base.
	"""
	if quantidade < 0 or valor_por_unidade < 0:
		raise ValueError("Quantidade e valor por unidade não podem ser negativos")

	return ResultadoIPI(
		base=arredondar(quantidade),
		valor=arredondar(quantidade * valor_por_unidade),
		compoe_base_icms=ipi_compoe_base_icms(
			destinatario_contribuinte, destinado_a_industrializacao_ou_comercio
		),
	)
