# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Imposto de Renda Retido na Fonte (IRRF) sobre a folha de pagamento.

Segundo cálculo do bloco RH, depois de `inss.py`. Mesma cautela sobre tabela que muda
por ano — `_TABELA_POR_ANO`/`_REDUTOR_POR_ANO` são dicionários por ano, nunca uma
constante única, e as funções levantam erro explícito para ano sem tabela embutida.

2026 não é "mais um ano" para o IRRF — é o primeiro ano de um mecanismo novo
--------------------------------------------------------------------------------------
A **Lei nº 15.270, de 26 de novembro de 2025** criou um "redutor" que soma à tabela
progressiva tradicional, isentando de fato quem ganha até R$ 5.000,00 mensais e
reduzindo progressivamente o imposto até R$ 7.350,00 — sem reescrever a tabela
tradicional em si. Isto não é uma tabela nova, é uma **segunda camada** por cima da
tabela de sempre: `calcular_irrf` primeiro calcula pela tabela tradicional
(`calcular_irrf_tradicional`), depois subtrai o redutor (`calcular_redutor`), nunca
menos que zero.

Fórmula do redutor, confirmada com os 5 exemplos oficiais da Receita Federal
--------------------------------------------------------------------------------------
`redutor = máx(0, 978,62 − 0,133145 × rendimento_bruto_mensal)` — aplicada sobre o
**rendimento bruto**, não sobre a base de cálculo (depois de INSS/dependentes). A
fórmula por si só já produz zero a partir de ~R$ 7.350,00 (não precisa de um corte
separado) e, abaixo de R$ 5.000,00, o valor que produz é grande o bastante para zerar
qualquer imposto tradicional calculado nessa faixa — não é coincidência, é o próprio
mecanismo da lei.

`gov.br/receitafederal` publicou uma página com **5 exemplos numéricos completos**
(rendimento bruto, INSS/desconto simplificado, base de cálculo, faixa da tabela
tradicional, redutor, IRRF final) — usados aqui como o teste mais forte deste módulo:
reproduzidos exatamente, não só a fórmula isolada (`tests/test_irrf.py`,
`TestExemplosOficiaisRFB`: João, José, Maria, Rita, Vera).

Tabela tradicional vigente em 2026
--------------------------------------
| Faixa | Base de cálculo (R$) | Alíquota | Parcela a deduzir (R$) |
|---|---|---|---|
| 1 | até 2.428,80 | 0% | 0,00 |
| 2 | de 2.428,81 até 2.826,65 | 7,5% | 182,16 |
| 3 | de 2.826,66 até 3.751,05 | 15% | 394,16 |
| 4 | de 3.751,06 até 4.664,68 | 22,5% | 675,49 |
| 5 | acima de 4.664,68 | 27,5% | 908,73 |

Confirmada pelos próprios exemplos oficiais (cada exemplo cita a faixa/alíquota/parcela
usada) — não por uma fonte secundária isolada. Uma primeira busca encontrou uma fonte
com o limite de isenção errado (`R$ 2.259,20`, valor de uma tabela anterior) antes desta
confirmação — registrado aqui como o próprio processo de verificação, não escondido.

`calcular_irrf` não calcula a base sozinho
------------------------------------------------
"Base de cálculo" (rendimento bruto menos INSS **ou** desconto simplificado — o maior
benefício, à escolha do contribuinte —, menos dedução por dependente quando não se usa
o simplificado) é responsabilidade de quem chama, não deste módulo — mesma disciplina
de `gerar_lancamentos_compra` receber `creditos_tributarios` já decidido: a escolha
simplificado × deduções legais depende de dado (dependentes, pensão alimentícia) que
este módulo não tem e não deveria inferir. `calcular_desconto_simplificado` é fornecido
como utilidade — não é chamado internamente por `calcular_irrf`.

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import ROUND_HALF_UP, Decimal

__all__ = [
	"ANO_VIGENTE",
	"IRRFInvalido",
	"calcular_desconto_simplificado",
	"calcular_irrf",
	"calcular_irrf_tradicional",
	"calcular_redutor",
]

ANO_VIGENTE = 2026

# (limite superior da faixa, alíquota, parcela a deduzir) — confirmada pelos 5 exemplos
# oficiais da Receita Federal (cada um cita a faixa usada), ver docstring do módulo.
_TABELA_POR_ANO = {
	2026: (
		(Decimal("2428.80"), Decimal("0"), Decimal("0")),
		(Decimal("2826.65"), Decimal("0.075"), Decimal("182.16")),
		(Decimal("3751.05"), Decimal("0.15"), Decimal("394.16")),
		(Decimal("4664.68"), Decimal("0.225"), Decimal("675.49")),
		(None, Decimal("0.275"), Decimal("908.73")),
	),
}

# (constante, coeficiente) de `redutor = constante - coeficiente * rendimento_bruto` —
# Lei 15.270/2025. Só 2026 embutido: é o primeiro ano do mecanismo.
_REDUTOR_POR_ANO = {
	2026: (Decimal("978.62"), Decimal("0.133145")),
}

# Teto mensal do desconto simplificado (25% do rendimento, até este limite).
_LIMITE_DESCONTO_SIMPLIFICADO_POR_ANO = {
	2026: Decimal("607.20"),
}


class IRRFInvalido(ValueError):
	"""Dado que impede o cálculo — rendimento negativo, ou ano sem tabela embutida."""


def _arredondar(valor: Decimal) -> Decimal:
	return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _tabela_do_ano(ano: int) -> tuple:
	if ano not in _TABELA_POR_ANO:
		raise IRRFInvalido(
			f"Tabela do IRRF não embutida para o ano {ano} — anos com tabela: "
			f"{sorted(_TABELA_POR_ANO)}. Nunca extrapolar de outro ano."
		)

	return _TABELA_POR_ANO[ano]


def calcular_irrf_tradicional(base_de_calculo: Decimal, ano: int = ANO_VIGENTE) -> Decimal:
	"""IRRF pela tabela progressiva tradicional, sem o redutor da Lei 15.270/2025 —
	método da parcela a deduzir, mesma disciplina de `inss.calcular_inss`."""
	if base_de_calculo < Decimal("0"):
		raise IRRFInvalido(f"base_de_calculo não pode ser negativa, recebida {base_de_calculo}")

	for limite_superior, aliquota, parcela_a_deduzir in _tabela_do_ano(ano):
		if limite_superior is None or base_de_calculo <= limite_superior:
			return _arredondar(base_de_calculo * aliquota - parcela_a_deduzir)

	raise AssertionError("tabela sem faixa final aberta — erro de construção da tabela")


def calcular_redutor(rendimento_bruto: Decimal, ano: int = ANO_VIGENTE) -> Decimal:
	"""Redutor da Lei 15.270/2025 — sobre o rendimento **bruto**, não a base de
	cálculo. Nunca negativo: a fórmula já cai a zero por volta de R$ 7.350,00sozinha,
	`max(0, ...)` só formaliza isso para rendimentos ainda maiores."""
	if rendimento_bruto < Decimal("0"):
		raise IRRFInvalido(f"rendimento_bruto não pode ser negativo, recebido {rendimento_bruto}")

	if ano not in _REDUTOR_POR_ANO:
		raise IRRFInvalido(
			f"Redutor da Lei 15.270/2025 não embutido para o ano {ano} — anos com "
			f"fórmula: {sorted(_REDUTOR_POR_ANO)}."
		)

	constante, coeficiente = _REDUTOR_POR_ANO[ano]

	return max(Decimal("0.00"), _arredondar(constante - coeficiente * rendimento_bruto))


def calcular_irrf(rendimento_bruto: Decimal, base_de_calculo: Decimal, ano: int = ANO_VIGENTE) -> Decimal:
	"""IRRF final: tabela tradicional sobre `base_de_calculo`, menos o redutor sobre
	`rendimento_bruto` — nunca menos que zero.

	Os dois valores são propositalmente distintos: a tabela incide sobre a base já
	líquida de INSS/dependentes, o redutor incide sobre o bruto, antes de qualquer
	dedução — confirmado nos 5 exemplos oficiais (`test_irrf.TestExemplosOficiaisRFB`).
	"""
	tradicional = calcular_irrf_tradicional(base_de_calculo, ano)
	redutor = calcular_redutor(rendimento_bruto, ano)

	return max(Decimal("0.00"), _arredondar(tradicional - redutor))


def calcular_desconto_simplificado(rendimento_bruto: Decimal, ano: int = ANO_VIGENTE) -> Decimal:
	"""25% do rendimento bruto, até o teto mensal — alternativa a
	INSS + dedução por dependente, à escolha do contribuinte (não decidida aqui, ver
	docstring do módulo)."""
	if rendimento_bruto < Decimal("0"):
		raise IRRFInvalido(f"rendimento_bruto não pode ser negativo, recebido {rendimento_bruto}")

	if ano not in _LIMITE_DESCONTO_SIMPLIFICADO_POR_ANO:
		raise IRRFInvalido(f"Limite do desconto simplificado não embutido para o ano {ano}.")

	limite = _LIMITE_DESCONTO_SIMPLIFICADO_POR_ANO[ano]

	return min(limite, _arredondar(rendimento_bruto * Decimal("0.25")))
