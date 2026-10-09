# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Script Report "Notas por situação e rejeição": lê `Transmissao Fiscal` e delega o agrupamento à regra pura."""

import frappe
from frappe import _

from erpnext_brasil.fiscal.relatorio_notas import autorizadas_sem_chave, resumir

CAMPOS = ["tipo", "situacao", "codigo_status", "mensagem", "chave_acesso", "creation"]


def _colunas() -> list[dict]:
	return [
		{"fieldname": "tipo", "label": _("Tipo"), "fieldtype": "Data", "width": 140},
		{"fieldname": "situacao", "label": _("Situação"), "fieldtype": "Data", "width": 110},
		{"fieldname": "codigo_status", "label": _("cStat"), "fieldtype": "Data", "width": 70},
		{"fieldname": "mensagem", "label": _("Mensagem"), "fieldtype": "Data", "width": 360},
		{"fieldname": "quantidade", "label": _("Quantidade"), "fieldtype": "Int", "width": 100},
		{"fieldname": "primeira", "label": _("Primeira"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "ultima", "label": _("Última"), "fieldtype": "Datetime", "width": 160},
	]


def ler_linhas(filtros: dict) -> list[dict]:
	"""Lê `Transmissao Fiscal` da empresa e do período. Empresa e datas são obrigatórias: relatório fiscal sem
	recorte confunde empresas e ambientes."""
	for obrigatorio in ("company", "from_date", "to_date"):
		if not filtros.get(obrigatorio):
			frappe.throw(_("Informe empresa e período."))

	criterios = {
		"company": filtros["company"],
		"creation": [
			"between",
			[f"{filtros['from_date']} 00:00:00", f"{filtros['to_date']} 23:59:59.999999"],
		],
	}

	if filtros.get("ambiente"):
		criterios["ambiente"] = filtros["ambiente"]

	return frappe.get_all("Transmissao Fiscal", filters=criterios, fields=CAMPOS, limit_page_length=0)


def execute(filters=None):
	linhas = ler_linhas(frappe._dict(filters or {}))
	sem_chave = autorizadas_sem_chave(linhas)
	aviso = (
		_("{0} autorização(ões) sem chave de acesso: conferir antes de declarar.").format(sem_chave)
		if sem_chave
		else None
	)

	return _colunas(), resumir(linhas), aviso
