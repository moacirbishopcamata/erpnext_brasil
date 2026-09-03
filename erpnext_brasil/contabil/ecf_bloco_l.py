# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""ECF: Bloco L (Lucro Real — Lucro Líquido) — abertura/encerramento apenas.

Ver `docs/ecf-blocos-l-m-n.md` para o dimensionamento completo dos três blocos do
núcleo de Lucro Real. Resumo do achado que limitou este incremento: `L100`/`L300`
(Balanço/DRE) têm a mesma forma de `P100`/`P150` (plano de contas + saldo, dúvida real
sobre referencial × próprio) e `L210` tem o mesmo formato genérico "código+valor" sem
catálogo oficial verificado — mesmas razões já registradas para o Bloco P.
`L200` (método de avaliação de estoque) é um indicador único, mas depende de uma
decisão de negócio (qual método a empresa usa) que este projeto não modela. `L030`
tem a mesma pendência de `K030`/`P030` (método de apuração).

Funções puras: nenhuma dependência do Frappe.

Fonte: `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
bloco-l.htm`, consultada em 2026-09-03.
"""

__all__ = ["montar_l001", "montar_l990"]


def montar_l001(tem_dados: bool) -> dict:
	"""Monta o registro `L001` — abertura do Bloco L, mesma convenção dos demais blocos."""
	return {"REG": "L001", "IND_DAD": "0" if tem_dados else "1"}


def montar_l990(quantidade_linhas: int) -> dict:
	"""Monta `L990` — encerramento do Bloco L."""
	return {"REG": "L990", "QTD_LIN": str(quantidade_linhas)}
