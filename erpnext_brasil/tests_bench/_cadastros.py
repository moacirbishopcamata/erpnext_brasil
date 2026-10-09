# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cadastros que um site sem assistente de configuração não tem — compartilhados pelos testes
de bench (ver `docs/ambiente-dev-bench.md`, "Site sem assistente de configuração").

`garantir_ano_fiscal` existe por um achado de 2026-09-17: três suítes criavam o ano fiscal
**por nome** (`if not exists("Fiscal Year", ano)`), e num site que já rodou o `before_tests`
do ERPNext existe `_Test Fiscal Year <ano>` cobrindo o mesmo período — a criação é recusada
por sobreposição e a suíte inteira morre no `setUpClass`. Conferir por **cobertura de datas**
é o que se quer de verdade: qualquer ano fiscal que cubra o período serve.
"""

import frappe


def garantir_ano_fiscal(ano: str) -> None:
	"""Cria o ano fiscal `ano` só se nenhum outro cobrir de 1º de janeiro a 31 de dezembro."""
	coberto = frappe.db.exists(
		"Fiscal Year",
		{"year_start_date": ("<=", f"{ano}-01-01"), "year_end_date": (">=", f"{ano}-12-31")},
	)

	if coberto:
		return

	frappe.get_doc(
		{
			"doctype": "Fiscal Year",
			"year": ano,
			"year_start_date": f"{ano}-01-01",
			"year_end_date": f"{ano}-12-31",
		}
	).insert(ignore_permissions=True)
