# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Avisa quando o método de valoração de estoque escolhido é o LIFO, numa instalação brasileira.

Tarefa 2.2 de `tropicalizar-demais-modulos`. A regra e a ressalva sobre a fonte legal estão em
`fiscal/valoracao.py`; aqui só se lê o documento e se mostra o aviso.

**Aviso, não bloqueio** (`msgprint`, não `throw`): a vedação ao UEPS ainda não tem o dispositivo legal citado em
fonte oficial, e travar a gravação de um item por uma regra não comprovada seria pior do que o aviso. Ligado em
`Item` e `Stock Settings`, os dois lugares onde o ERPNext guarda o método.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.valoracao import aviso_de_valoracao
from erpnext_brasil.integracao.party import pais_e_brasil

__all__ = ["avisar_valoracao_lifo"]


def avisar_valoracao_lifo(doc, method=None):
	"""Mostra o aviso se `valuation_method` for LIFO e o contexto for brasileiro. Nunca levanta."""
	texto = aviso_de_valoracao(doc.get("valuation_method"))

	if texto and pais_e_brasil():
		frappe.msgprint(texto, title=_("Valoração de estoque"), indicator="orange")
