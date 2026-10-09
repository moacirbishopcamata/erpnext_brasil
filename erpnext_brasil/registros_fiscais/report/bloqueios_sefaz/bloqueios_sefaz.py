# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Script Report "Bloqueios SEFAZ": lê `Bloqueio Sefaz` (cStat 656) e delega a classificação à regra pura."""

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from erpnext_brasil.fiscal.relatorio_bloqueios import classificar

CAMPOS = ["cnpj", "ambiente", "bloqueado_em", "liberado_em", "codigo_status", "mensagem"]


def _colunas() -> list[dict]:
	return [
		{"fieldname": "cnpj", "label": _("CNPJ"), "fieldtype": "Data", "width": 150},
		{"fieldname": "ambiente", "label": _("Ambiente"), "fieldtype": "Data", "width": 110},
		{"fieldname": "situacao", "label": _("Situação"), "fieldtype": "Data", "width": 90},
		{"fieldname": "bloqueado_em", "label": _("Bloqueado em"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "liberado_em", "label": _("Liberado em"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "restante_min", "label": _("Restam (min)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "codigo_status", "label": _("cStat"), "fieldtype": "Data", "width": 70},
		{"fieldname": "mensagem", "label": _("Mensagem"), "fieldtype": "Data", "width": 320},
	]


def execute(filters=None):
	filtros = frappe._dict(filters or {})

	if not filtros.get("company"):
		frappe.throw(_("Informe a empresa."))

	criterios = {"company": filtros.company}

	if filtros.get("ambiente"):
		criterios["ambiente"] = filtros.ambiente

	linhas = frappe.get_all("Bloqueio Sefaz", filters=criterios, fields=CAMPOS, limit_page_length=0)

	for linha in linhas:
		for campo in ("bloqueado_em", "liberado_em"):
			linha[campo] = get_datetime(linha[campo]) if linha.get(campo) else None

	resultado = classificar(linhas, now_datetime())

	if filtros.get("somente_ativos"):
		resultado = [r for r in resultado if r["situacao"] == "Ativo"]

	return _colunas(), resultado
