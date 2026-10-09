# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Script Report "Lacunas de Numeracao": cruza `Numeracao Fiscal` (até onde se consumiu) com `Transmissao Fiscal`
(o que aconteceu com cada número) e delega ao cálculo puro. O número vem da **chave de acesso** da transmissão."""

import frappe
from frappe import _

from erpnext_brasil.fiscal.relatorio_numeracao import faixas_sem_desfecho
from erpnext_brasil.integracao.serie_fiscal import faixas_inutilizadas, situacoes_por_numero


def _colunas() -> list[dict]:
	return [
		{"fieldname": "modelo", "label": _("Modelo"), "fieldtype": "Data", "width": 70},
		{"fieldname": "serie", "label": _("Série"), "fieldtype": "Data", "width": 70},
		{"fieldname": "inicio", "label": _("De"), "fieldtype": "Int", "width": 100},
		{"fieldname": "fim", "label": _("Até"), "fieldtype": "Int", "width": 100},
		{"fieldname": "quantidade", "label": _("Quantidade"), "fieldtype": "Int", "width": 100},
		{"fieldname": "motivo", "label": _("Motivo"), "fieldtype": "Data", "width": 140},
	]


def execute(filters=None):
	filtros = frappe._dict(filters or {})

	if not filtros.get("company"):
		frappe.throw(_("Informe a empresa."))

	series = frappe.get_all(
		"Numeracao Fiscal",
		filters={"company": filtros.company},
		fields=["name", "modelo", "serie", "ultimo_numero"],
		order_by="modelo, serie",
		limit_page_length=0,
	)
	linhas = []

	for serie in series:
		ultimo = int(serie.ultimo_numero or 0)

		for faixa in faixas_sem_desfecho(
			ultimo,
			situacoes_por_numero(filtros.company, serie.modelo, serie.serie),
			inutilizadas=faixas_inutilizadas(serie.name),
		):
			linhas.append({"modelo": serie.modelo, "serie": serie.serie, **faixa})

	aviso = _("Candidatas à inutilização: faixas já inutilizadas pelo app não aparecem.")

	return _colunas(), linhas, aviso
