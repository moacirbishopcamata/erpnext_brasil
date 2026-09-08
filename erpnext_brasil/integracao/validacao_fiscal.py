# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Gancho de validação: recusa gravar item com classificação incompatível.

Camada mínima de propósito — quatro linhas de decisão. Toda a regra vive em
`fiscal/codigos/compatibilidade.py`, que depende de uma interface e não sabe que este
módulo existe.

O único conhecimento que fica aqui é o que é genuinamente do ERPNext: qual indicador da
tabela oficial corresponde a cada DocType. Isso não é regra fiscal, é mapeamento de
framework.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.codigos.compatibilidade import problemas_dos_itens
from erpnext_brasil.fiscal.codigos_de_erro import (
	DOCUMENTO_CLASSIFICACAO_INCOMPATIVEL,
	formatar,
)
from erpnext_brasil.integracao.repositorio_frappe import repositorio_da_requisicao

# DocType -> indicador de aplicabilidade na Tabela de Classificação Tributária.
INDICADOR_POR_DOCUMENTO = {
	"Sales Invoice": "indNFe",
	"Delivery Note": "indNFe",
	"Purchase Invoice": "indNFe",
	"Purchase Receipt": "indNFe",
	"POS Invoice": "indNFCe",
}


def validar_classificacao_dos_itens(doc, method=None):
	"""Confere CST e cClassTrib de cada item antes de gravar."""
	if not doc.get("items"):
		return

	empresa = doc.get("company")

	if not empresa or frappe.get_cached_value("Company", empresa, "country") != "Brazil":
		return

	mensagens = problemas_dos_itens(
		[linha.as_dict() for linha in doc.items],
		repositorio_da_requisicao(),
		INDICADOR_POR_DOCUMENTO.get(doc.doctype, "indNFe"),
	)

	if mensagens:
		frappe.throw(
			formatar(DOCUMENTO_CLASSIFICACAO_INCOMPATIVEL, "<br>".join(mensagens)),
			title=_("Classificação tributária incompatível"),
		)
