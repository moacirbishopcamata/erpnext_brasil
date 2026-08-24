# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Aplicação das regras fiscais brasileiras aos DocTypes de parte.

Esta é a camada de tradução: as funções puras de `validators` não conhecem o Frappe,
e aqui o resultado delas vira `frappe.throw`. A separação existe para que a regra
fiscal seja testável sem site e sem banco.

A validação roda apenas quando a Company (ou o país do sistema) é o Brasil. Uma
instalação multiempresa com filial no exterior não deve ter o CNPJ exigido de um
fornecedor estrangeiro.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.validators import (
	ValidacaoFiscalError,
	formatar_cnpj,
	formatar_cpf,
	limpar,
	validar_cpf_cnpj,
)


def _pais_e_brasil() -> bool:
	"""Indica se o contexto atual é brasileiro.

	Usa a Company em foco quando houver; do contrário, o país das configurações.
	"""
	empresa = frappe.local.flags.company or frappe.defaults.get_user_default("Company")

	if empresa:
		return frappe.get_cached_value("Company", empresa, "country") == "Brazil"

	return frappe.get_system_settings("country") == "Brazil"


def validar_tax_id(doc, method=None):
	"""Valida o CPF/CNPJ em `tax_id` e o normaliza para o formato com máscara.

	Ligado via `doc_events` para Company, Customer e Supplier. Campo vazio é aceito:
	obrigatoriedade é decisão de configuração do DocType, não desta validação.
	"""
	if not doc.get("tax_id") or not _pais_e_brasil():
		return

	try:
		limpo = validar_cpf_cnpj(doc.tax_id)
	except ValidacaoFiscalError as e:
		frappe.throw(
			_("CPF/CNPJ inválido em {0}: {1}").format(doc.doctype, str(e)),
			title=_("Documento fiscal inválido"),
		)
		return

	# Normaliza na gravação para que buscas e comparações não dependam da máscara
	# que o usuário digitou. O valor canônico é sempre o formatado.
	doc.tax_id = formatar_cpf(limpo) if len(limpo) == 11 else formatar_cnpj(limpo)


def validar_codigo_municipio(doc, method=None):
	"""Valida o código IBGE do município em Address (7 dígitos)."""
	codigo = doc.get("codigo_municipio_ibge")

	if not codigo or not _pais_e_brasil():
		return

	limpo = limpar(codigo)

	if not limpo.isdigit() or len(limpo) != 7:
		frappe.throw(
			_("Código do Município (IBGE) deve ter 7 dígitos numéricos, recebido {0}").format(codigo),
			title=_("Documento fiscal inválido"),
		)

	doc.codigo_municipio_ibge = limpo


def validar_ncm(doc, method=None):
	"""Valida o NCM do Item (8 dígitos)."""
	ncm = doc.get("ncm")

	if not ncm or not _pais_e_brasil():
		return

	limpo = limpar(ncm)

	if not limpo.isdigit() or len(limpo) != 8:
		frappe.throw(
			_("NCM deve ter 8 dígitos numéricos, recebido {0}").format(ncm),
			title=_("Documento fiscal inválido"),
		)

	doc.ncm = limpo
