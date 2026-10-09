# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Script Report "Lacunas de Numeracao": cruza `Numeracao Fiscal` (até onde se consumiu) com `Transmissao Fiscal`
(o que aconteceu com cada número) e delega ao cálculo puro. O número vem da **chave de acesso** da transmissão."""

import frappe
from frappe import _

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.relatorio_numeracao import faixas_sem_desfecho


def _colunas() -> list[dict]:
	return [
		{"fieldname": "modelo", "label": _("Modelo"), "fieldtype": "Data", "width": 70},
		{"fieldname": "serie", "label": _("Série"), "fieldtype": "Data", "width": 70},
		{"fieldname": "inicio", "label": _("De"), "fieldtype": "Int", "width": 100},
		{"fieldname": "fim", "label": _("Até"), "fieldtype": "Int", "width": 100},
		{"fieldname": "quantidade", "label": _("Quantidade"), "fieldtype": "Int", "width": 100},
		{"fieldname": "motivo", "label": _("Motivo"), "fieldtype": "Data", "width": 140},
	]


def situacoes_por_numero(company: str, modelo: str, serie: str) -> dict[int, set[str]]:
	"""`{número: {situações}}` das autorizações da série. Chave ilegível não entra: o `DocType` já valida a chave."""
	registros = frappe.get_all(
		"Transmissao Fiscal",
		filters={"company": company, "tipo": "Autorização", "chave_acesso": ["is", "set"]},
		fields=["chave_acesso", "situacao"],
		limit_page_length=0,
	)
	resultado: dict[int, set[str]] = {}

	for registro in registros:
		try:
			chave = ler_chave(registro.chave_acesso)
		except ValueError:
			continue

		if chave.modelo == modelo and int(chave.serie) == int(serie):
			resultado.setdefault(int(chave.numero), set()).add(registro.situacao)

	return resultado


def execute(filters=None):
	filtros = frappe._dict(filters or {})

	if not filtros.get("company"):
		frappe.throw(_("Informe a empresa."))

	series = frappe.get_all(
		"Numeracao Fiscal",
		filters={"company": filtros.company},
		fields=["modelo", "serie", "ultimo_numero"],
		order_by="modelo, serie",
		limit_page_length=0,
	)
	linhas = []

	for serie in series:
		ultimo = int(serie.ultimo_numero or 0)

		for faixa in faixas_sem_desfecho(
			ultimo, situacoes_por_numero(filtros.company, serie.modelo, serie.serie)
		):
			linhas.append({"modelo": serie.modelo, "serie": serie.serie, **faixa})

	aviso = _(
		"Candidatas à inutilização: o app ainda não registra a faixa já inutilizada, então ela também aparece aqui."
	)

	return _colunas(), linhas, aviso
