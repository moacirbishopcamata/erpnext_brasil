# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Alíquota do ICMS nas operações interestaduais — a regra do Senado, não do estado.

Quem fixa a alíquota interestadual **não é o estado**: é o Senado Federal, por resolução
(CF/1988, art. 155, § 2º, IV). Por isso a tabela é nacional e cabe num módulo puro; a
alíquota **interna** é que varia por UF e por produto, e essa não está aqui.

As duas resoluções que valem
-----------------------------------
- **Resolução SF nº 22/1989** — 12% como regra geral; **7%** nas operações que saem do Sul
  ou do Sudeste (**exceto o Espírito Santo**) com destino ao Norte, Nordeste, Centro-Oeste
  ou ao próprio Espírito Santo.
- **Resolução SF nº 13/2012** — **4%** para bem ou mercadoria importada do exterior que,
  após o desembaraço, não tenha sido industrializada, ou que, industrializada, resulte em
  Conteúdo de Importação superior a 40%. Vigente desde 1º/01/2013.

⚠️ O Espírito Santo está nos dois lados da regra
--------------------------------------------------------
O ES é estado do **Sudeste** e, mesmo assim, é **destino** de 7% — e não é **origem** de
7%. Escrever "Sudeste manda a 7%" produziria 7% saindo do ES, que está errado; escrever
"destino é Norte/Nordeste/Centro-Oeste" esqueceria o ES, que também recebe a 7%.

É o tipo de exceção que uma tabela por região, sem o caso nomeado, silencia — e o erro
seria de 5 pontos percentuais numa nota que ninguém confere.

O que **não** está aqui, declarado
-----------------------------------------
- **Alíquota interna** — varia por UF e por produto (RICMS de cada estado), e uma tabela
  nacional dela seria invenção.
- **DIFAL** — o cálculo já existe em `impostos/icms.py::calcular_difal`, que recebe as duas
  alíquotas prontas. Este módulo fornece uma delas; não duplica o cálculo.
- **Conteúdo de Importação** — o percentual de 40% da Resolução 13/2012 depende da ficha
  CI do produto, que é dado do contribuinte. Aqui o chamador informa `importado=True` ou
  não; decidir por ele exigiria a ficha, que este app não tem.

Alíquota é **fração** (`Decimal("0.12")`), como em todo o app.

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import Decimal

from erpnext_brasil.fiscal.ufs import SIGLAS

__all__ = [
	"ALIQUOTA_GERAL",
	"ALIQUOTA_IMPORTADO",
	"ALIQUOTA_REDUZIDA",
	"ORIGENS_DE_ALIQUOTA_REDUZIDA",
	"UfInvalida",
	"aliquota_interestadual",
]

ALIQUOTA_GERAL = Decimal("0.12")
"""Regra geral da Resolução SF 22/1989."""

ALIQUOTA_REDUZIDA = Decimal("0.07")
"""Sul/Sudeste (menos ES) → Norte/Nordeste/Centro-Oeste/ES, Resolução SF 22/1989."""

ALIQUOTA_IMPORTADO = Decimal("0.04")
"""Resolução SF 13/2012 — importado sem industrialização, ou com CI acima de 40%.

Não depende de origem nem de destino: **substitui** as outras duas em qualquer par de UF.
"""

ORIGENS_DE_ALIQUOTA_REDUZIDA = frozenset(
	{
		# Sul
		"PR", "RS", "SC",
		# Sudeste, **sem** o Espírito Santo
		"MG", "RJ", "SP",
	}
)  # fmt: skip
"""As UF que **mandam** a 7%.

O ES fica de fora de propósito: é Sudeste, mas a Resolução 22/1989 o trata como destino da
alíquota reduzida, não como origem dela. Ver a nota na docstring do módulo.
"""

DESTINOS_DE_ALIQUOTA_REDUZIDA = frozenset(SIGLAS - ORIGENS_DE_ALIQUOTA_REDUZIDA)
"""As UF que **recebem** a 7% — Norte, Nordeste, Centro-Oeste e o ES.

Derivado por diferença, e não digitado: a regra da resolução é exatamente "todo o resto",
e uma segunda lista de 21 siglas divergiria da primeira no dia em que alguém a editasse.
"""


class UfInvalida(ValueError):
	"""Sigla que não é unidade federativa, ou operação que não é interestadual."""


def aliquota_interestadual(origem: str, destino: str, importado: bool = False) -> Decimal:
	"""A alíquota da operação, como fração.

	`importado=True` para bem que se enquadre na Resolução 13/2012 — quem chama decide,
	porque o enquadramento depende da ficha de Conteúdo de Importação do produto.

	Levanta quando `origem == destino`: operação dentro do mesmo estado **não tem** alíquota
	interestadual, e devolver 12% ali seria dar um número plausível para uma pergunta que
	não existe.
	"""
	origem = (origem or "").strip().upper()
	destino = (destino or "").strip().upper()

	for sigla, papel in ((origem, "origem"), (destino, "destino")):
		if sigla not in SIGLAS:
			raise UfInvalida(f"{papel} {sigla!r} não é uma UF válida")

	if origem == destino:
		raise UfInvalida(
			f"origem e destino são {origem} — operação interna não tem alíquota interestadual; "
			"a alíquota interna é do RICMS do estado, e não está neste módulo"
		)

	if importado:
		return ALIQUOTA_IMPORTADO

	if origem in ORIGENS_DE_ALIQUOTA_REDUZIDA and destino in DESTINOS_DE_ALIQUOTA_REDUZIDA:
		return ALIQUOTA_REDUZIDA

	return ALIQUOTA_GERAL
