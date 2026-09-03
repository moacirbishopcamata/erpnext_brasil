# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Contribuição previdenciária do empregado (INSS) — tabela progressiva.

Primeiro cálculo do bloco RH, depois do levantamento do estado do `hrms` (ver
`docs/rh-estado-hrms.md`). Mesmo destino final documentado ali:
`SalarySlip.apply_regional_deductions`, o hook que o `hrms` já expõe para isto — não
implementado ainda, só a conta em si.

A tabela muda todo ano — nunca hardcode "a" tabela, hardcode "a de <ano>"
--------------------------------------------------------------------------------
Diferente de uma regra fiscal estável (um XSD, uma fórmula constitucional), a tabela de
salário de contribuição do INSS é reajustada anualmente por Portaria Interministerial
(MPS/MF) — o mesmo padrão de risco já visto no fator de vencimento do boleto (mudou de
base em 2025) e na alíquota-teste de IBS/CBS (só 2026 embutida, resto levanta erro
explícito em vez de extrapolar). Por isso `FAIXAS_POR_ANO` é um dicionário por ano, não
uma constante única, e `calcular_inss` **levanta erro para qualquer ano sem tabela
embutida** — nunca extrapola nem reaproveita o ano anterior por semelhança.

Tabela vigente: 2026 (Portaria Interministerial MPS/MF nº 13, de 9/01/2026)
--------------------------------------------------------------------------------
Vigência a partir de 1º de janeiro de 2026. A fonte primária
(`gov.br/previdencia`) foi localizada e citada, mas o PDF publicado é digitalizado como
imagem e não pôde ser lido por texto pelas ferramentas de busca — mesma limitação já
registrada para outras fontes `gov.br` neste projeto. Os valores abaixo foram
confirmados em duas fontes secundárias independentes, que reproduziram exatamente os
mesmos quatro limites de faixa, alíquotas e parcelas a deduzir — e conferidos por mim
com o cálculo de faixa a faixa (sem o atalho da "parcela a deduzir"), batendo dentro de
centavos de arredondamento em cada limite superior.

| Faixa | Salário de contribuição (R$) | Alíquota | Parcela a deduzir (R$) |
|---|---|---|---|
| 1 | até 1.621,00 | 7,5% | 0,00 |
| 2 | de 1.621,01 até 2.902,84 | 9% | 24,32 |
| 3 | de 2.902,85 até 4.354,27 | 12% | 111,40 |
| 4 | de 4.354,28 até 8.475,55 (teto) | 14% | 198,49 |

O "método da parcela a deduzir" é equivalente a somar o valor faixa a faixa (é a mesma
fórmula progressiva, só reorganizada algebricamente para não precisar iterar) — usado
aqui porque é como a fonte publica a tabela, não uma simplificação própria deste módulo.

Teto: acima de R$ 8.475,55 de salário de contribuição, o desconto não cresce mais —
a base de cálculo é limitada ao teto, não ao salário efetivo (quem ganha R$ 20.000,00
desconta o mesmo que quem ganha exatamente R$ 8.475,55).

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import ROUND_HALF_UP, Decimal

__all__ = ["ANO_VIGENTE", "TETO_POR_ANO", "INSSInvalido", "calcular_inss"]

ANO_VIGENTE = 2026

# (limite superior da faixa, alíquota, parcela a deduzir) — nessa ordem, faixas em
# ordem crescente. O limite superior da última faixa é o teto do salário de
# contribuição.
_FAIXAS_POR_ANO = {
	2026: (
		(Decimal("1621.00"), Decimal("0.075"), Decimal("0.00")),
		(Decimal("2902.84"), Decimal("0.09"), Decimal("24.32")),
		(Decimal("4354.27"), Decimal("0.12"), Decimal("111.40")),
		(Decimal("8475.55"), Decimal("0.14"), Decimal("198.49")),
	),
}

TETO_POR_ANO = {ano: faixas[-1][0] for ano, faixas in _FAIXAS_POR_ANO.items()}


class INSSInvalido(ValueError):
	"""Dado que impede o cálculo — salário negativo, ou ano sem tabela embutida."""


def _arredondar(valor: Decimal) -> Decimal:
	return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_inss(salario_contribuicao: Decimal, ano: int = ANO_VIGENTE) -> Decimal:
	"""Contribuição do empregado, pelo método da parcela a deduzir.

	Pré-condição: `salario_contribuicao` não pode ser negativo. `ano` precisa ter
	tabela embutida (`_FAIXAS_POR_ANO`) — nunca extrapola de um ano vizinho.

	Pós-condição: o valor devolvido nunca excede o desconto máximo (o do teto), mesmo
	para salário muito acima dele — verificado por `assert`, não só por construção da
	fórmula, porque um teto errado na tabela produziria um valor "plausível" e alto
	demais sem nenhum sinal de erro visível.
	"""
	if salario_contribuicao < Decimal("0"):
		raise INSSInvalido(f"salario_contribuicao não pode ser negativo, recebido {salario_contribuicao}")

	if ano not in _FAIXAS_POR_ANO:
		raise INSSInvalido(
			f"Tabela do INSS não embutida para o ano {ano} — anos com tabela: "
			f"{sorted(_FAIXAS_POR_ANO)}. Nunca extrapolar de outro ano: a tabela muda "
			"por Portaria Interministerial e precisa ser conferida na fonte."
		)

	faixas = _FAIXAS_POR_ANO[ano]
	teto = TETO_POR_ANO[ano]
	base = min(salario_contribuicao, teto)

	for limite_superior, aliquota, parcela_a_deduzir in faixas:
		if base <= limite_superior:
			valor = _arredondar(base * aliquota - parcela_a_deduzir)
			break
	else:
		# Só alcançável se `base` (já limitada ao teto) exceder o próprio teto — não
		# deveria acontecer nunca, dado o `min()` acima; falha alto em vez de devolver
		# um valor calculado sobre premissa quebrada.
		raise INSSInvalido(f"salario_contribuicao {salario_contribuicao} excede o teto {teto} após limitação")

	desconto_maximo = _arredondar(teto * faixas[-1][1] - faixas[-1][2])
	assert valor <= desconto_maximo, (
		f"INSS calculado ({valor}) maior que o desconto máximo da tabela ({desconto_maximo}) "
		"— a tabela ou a fórmula têm um erro, não é o salário que está errado"
	)

	return valor
