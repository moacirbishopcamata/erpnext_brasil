# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cálculo de PIS e COFINS, incluindo a exclusão do ICMS da base.

Duas regras dominam este módulo, e as duas mudam o valor devido:

**Regime.** No cumulativo (típico do Lucro Presumido) as alíquotas são 0,65% e 3,00% e
não há crédito. No não cumulativo (Lucro Real) são 1,65% e 7,60%, com direito a crédito
na aquisição. Aplicar o par errado erra a contribuição em mais de quatro vezes.

**Exclusão do ICMS da base (RE 574.706, a "tese do século").** O STF decidiu que o ICMS
destacado na nota não compõe a base de PIS/COFINS. É subtração, não detalhe: numa
operação de R$ 1.000 com ICMS de 18%, a base cai de 1.000 para 820. Manter o ICMS na
base é recolher a maior — dinheiro que a empresa não deve.

A exclusão é parâmetro e não constante porque a decisão tem modulação e há situações em
que a empresa opta por não aplicá-la; o padrão, porém, é excluir, que é o entendimento
vigente.

Funções puras, `Decimal`, alíquota como fração — mesmas regras de `icms.py`.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = [
	"ALIQUOTAS_CUMULATIVO",
	"ALIQUOTAS_NAO_CUMULATIVO",
	"ResultadoContribuicao",
	"aliquotas_do_regime",
	"base_de_calculo",
	"calcular_pis_cofins",
]

# (PIS, COFINS)
ALIQUOTAS_CUMULATIVO = (Decimal("0.0065"), Decimal("0.03"))
ALIQUOTAS_NAO_CUMULATIVO = (Decimal("0.0165"), Decimal("0.076"))

_REGIMES = {
	"cumulativo": ALIQUOTAS_CUMULATIVO,
	"nao_cumulativo": ALIQUOTAS_NAO_CUMULATIVO,
}


@dataclass(frozen=True)
class ResultadoContribuicao:
	base: Decimal
	aliquota_pis: Decimal
	aliquota_cofins: Decimal
	pis: Decimal
	cofins: Decimal

	@property
	def total(self) -> Decimal:
		return self.pis + self.cofins


def aliquotas_do_regime(regime: str) -> tuple[Decimal, Decimal]:
	"""Devolve (PIS, COFINS) para "cumulativo" ou "nao_cumulativo"."""
	if regime not in _REGIMES:
		raise ValueError(
			f"Regime deve ser um de {sorted(_REGIMES)}, recebido {regime!r}. "
			"Empresas do Simples Nacional não destacam PIS/COFINS: as contribuições "
			"estão no DAS."
		)

	return _REGIMES[regime]


def base_de_calculo(
	receita: Decimal,
	icms_destacado: Decimal = Decimal(0),
	excluir_icms: bool = True,
	outras_exclusoes: Decimal = Decimal(0),
) -> Decimal:
	"""Base de PIS/COFINS, por padrão já sem o ICMS destacado (RE 574.706)."""
	base = receita - outras_exclusoes

	if excluir_icms:
		base -= icms_destacado

	if base < 0:
		raise ValueError("A base de PIS/COFINS ficou negativa; verifique as exclusões")

	return arredondar(base)


def calcular_pis_cofins(
	receita: Decimal,
	regime: str,
	icms_destacado: Decimal = Decimal(0),
	excluir_icms: bool = True,
	outras_exclusoes: Decimal = Decimal(0),
	aliquota_pis: Decimal | None = None,
	aliquota_cofins: Decimal | None = None,
) -> ResultadoContribuicao:
	"""PIS e COFINS sobre a receita, com a exclusão do ICMS aplicada por padrão.

	As alíquotas podem ser sobrescritas para cobrir regimes especiais — monofásico com
	alíquota zero na revenda, por exemplo, é `aliquota_pis=0` e `aliquota_cofins=0`
	mantendo o regime para efeito de escrituração.
	"""
	padrao_pis, padrao_cofins = aliquotas_do_regime(regime)

	pis = padrao_pis if aliquota_pis is None else aliquota_pis
	cofins = padrao_cofins if aliquota_cofins is None else aliquota_cofins

	for nome, valor in (("aliquota_pis", pis), ("aliquota_cofins", cofins)):
		if not (Decimal(0) <= valor < Decimal(1)):
			raise ValueError(f"{nome} deve ser fração entre 0 e 1, recebido {valor}")

	base = base_de_calculo(
		receita,
		icms_destacado=icms_destacado,
		excluir_icms=excluir_icms,
		outras_exclusoes=outras_exclusoes,
	)

	return ResultadoContribuicao(
		base=base,
		aliquota_pis=pis,
		aliquota_cofins=cofins,
		pis=arredondar(base * pis),
		cofins=arredondar(base * cofins),
	)
