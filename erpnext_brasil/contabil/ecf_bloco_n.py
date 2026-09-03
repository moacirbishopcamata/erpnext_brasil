# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""ECF: Bloco N (Cálculo do IRPJ/CSLL — Lucro Real) — abertura/encerramento apenas.

Ver `docs/ecf-blocos-l-m-n.md` para o dimensionamento completo. Resumo do achado: oito
dos treze registros (`N500`/`N600`/`N610`/`N620`/`N630`/`N650`/`N660`/`N670`) seguem o
mesmo formato genérico "código+descrição+valor" já visto nos Blocos K/P — cada um é uma
memória de cálculo (compensação de prejuízo fiscal, lucro operacional, isenção/redução,
estimativa mensal, cálculo final do IRPJ/CSLL) referenciando um catálogo de códigos da
Receita não verificado. `N605` depende de saber quais contas compõem "lucro
operacional" — regra de negócio não modelada. `N615` é um cálculo bem específico
(incentivos FINOR/FINAM/FUNRES, regime regional raro) — baixa prioridade mesmo se o
catálogo de código existisse. `N030` tem a mesma pendência de `K030`/`L030`/`P030`.

Funções puras: nenhuma dependência do Frappe.

Fonte: `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
bloco-n.htm`, consultada em 2026-09-03.
"""

__all__ = ["montar_n001", "montar_n990"]


def montar_n001(tem_dados: bool) -> dict:
	"""Monta o registro `N001` — abertura do Bloco N, mesma convenção dos demais blocos."""
	return {"REG": "N001", "IND_DAD": "0" if tem_dados else "1"}


def montar_n990(quantidade_linhas: int) -> dict:
	"""Monta `N990` — encerramento do Bloco N."""
	return {"REG": "N990", "QTD_LIN": str(quantidade_linhas)}
