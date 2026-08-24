# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Instalação e reaplicação dos campos fiscais.

`after_migrate` repete a criação de propósito: campos customizados podem ser perdidos
ou ficar desatualizados quando o ERPNext altera o DocType base, e `create_custom_fields`
é idempotente com `update=True`.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext_brasil.fiscal.codigos.seed import criar_listas_de_codigos
from erpnext_brasil.setup.custom_fields import get_custom_fields


def after_install():
	criar_campos_fiscais()
	criar_listas_de_codigos()


def after_migrate():
	criar_campos_fiscais()
	criar_listas_de_codigos()


def criar_campos_fiscais(update: bool = True):
	create_custom_fields(get_custom_fields(), ignore_validate=frappe.flags.in_patch, update=update)
