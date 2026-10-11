# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Ano de um período de folha — o que decide qual tabela de INSS e IRRF vale.

Por que existe
--------------
`inss.py` e `irrf.py` guardam uma tabela por ano e levantam erro para ano sem tabela, mas as duas
funções têm `ANO_VIGENTE` como valor padrão do parâmetro `ano`. Quem esquece de passar o ano calcula
com a tabela de 2026 para qualquer período, sem erro (RT-01 de `docs/revisao-total/folha-rh.md`).
Este módulo é a pergunta que faltava na costura: "de que ano é este holerite?".

Regra adotada: o ano do **fim** do período; o início só vale quando o fim não existe. Um período que
atravessa a virada (16/12 a 15/01) é tratado pelo ano em que termina. **Premissa a confirmar** contra a
regra de competência do INSS e do IRRF para folha que cruza o ano: a tabela vigente depende do mês de
competência e do mês do pagamento, e este módulo não decide isso. Sem nenhuma das duas datas, recusa
em vez de supor o ano corrente.
"""

from datetime import date, datetime

__all__ = ["PeriodoInvalido", "ano_do_periodo"]


class PeriodoInvalido(ValueError):
	"""Período de folha sem data utilizável."""


def _como_data(valor: date | str | None) -> date | None:
	if valor is None or valor == "":
		return None

	if isinstance(valor, datetime):
		return valor.date()

	if isinstance(valor, date):
		return valor

	try:
		return date.fromisoformat(str(valor)[:10])
	except ValueError as erro:
		raise PeriodoInvalido(f"Data de período ilegível: {valor!r}") from erro


def ano_do_periodo(fim: date | str | None, inicio: date | str | None = None) -> int:
	"""Ano do fim do período; o do início só se o fim faltar.

	Pré-condição: ao menos uma das datas existe e é ISO (`AAAA-MM-DD`) ou `date`. Sem isso levanta
	`PeriodoInvalido`: devolver o ano corrente esconderia exatamente o erro que este módulo previne.
	"""
	data = _como_data(fim) or _como_data(inicio)

	if data is None:
		raise PeriodoInvalido(
			"O holerite não tem data de início nem de fim; sem elas não há tabela a escolher."
		)

	return data.year
