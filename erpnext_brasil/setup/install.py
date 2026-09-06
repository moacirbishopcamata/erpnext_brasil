# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Instalação e reaplicação dos campos fiscais.

`after_migrate` repete a criação de propósito: campos customizados podem ser perdidos
ou ficar desatualizados quando o ERPNext altera o DocType base, e `create_custom_fields`
é idempotente com `update=True`.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext_brasil.integracao.depreciacao_ativo import instalar_livro_fiscal, instalar_turnos
from erpnext_brasil.integracao.folha import COMPONENTES_DESTE_MODULO
from erpnext_brasil.integracao.seed_codigos import criar_listas_de_codigos
from erpnext_brasil.setup.campos_documento import get_custom_fields as get_campos_documento
from erpnext_brasil.setup.custom_fields import get_custom_fields


def after_install():
	criar_campos_fiscais()
	criar_listas_de_codigos()
	criar_componentes_salariais()
	criar_depreciacao_fiscal()


def after_migrate():
	criar_campos_fiscais()
	criar_listas_de_codigos()
	criar_componentes_salariais()
	criar_depreciacao_fiscal()


def criar_depreciacao_fiscal() -> None:
	"""Cria o `Finance Book` fiscal e os `Asset Shift Factor` do art. 323.

	Condicional à existência dos DocTypes, pelo mesmo motivo dos componentes salariais:
	`Asset` e `Finance Book` são do ERPNext, e um site que só tenha o Frappe não os tem —
	deixar a instalação fiscal quebrar por isso seria trocar um recurso opcional por
	nenhum recurso.

	As duas funções são idempotentes e **não sobrescrevem** o que já existe: um fator de
	turno ajustado por quem administra o site é decisão dele, não ruído a corrigir a cada
	`migrate`.
	"""
	if not frappe.db.exists("DocType", "Finance Book"):
		return

	instalar_livro_fiscal()

	if frappe.db.exists("DocType", "Asset Shift Factor"):
		instalar_turnos()


def criar_componentes_salariais() -> None:
	"""Cria os `Salary Component` que `integracao/folha.py` referencia (INSS, IRRF).

	Condicional à instalação do `hrms`: `erpnext_brasil` não o exige em
	`required_apps` (o bloco fiscal funciona sem RH nenhum instalado), então o
	DocType `Salary Component` pode simplesmente não existir — checar antes de
	tentar, em vez de deixar a instalação fiscal quebrar por falta de um app opcional.
	"""
	if not frappe.db.exists("DocType", "Salary Component"):
		return

	for nome in COMPONENTES_DESTE_MODULO:
		if frappe.db.exists("Salary Component", nome):
			continue

		frappe.get_doc(
			{
				"doctype": "Salary Component",
				"salary_component": nome,
				"type": "Deduction",
			}
		).insert(ignore_permissions=True)


def criar_campos_fiscais(update: bool = True):
	"""Cria os campos de cadastro e os de apuração.

	Os dois mapas são mesclados por DocType em vez de aplicados em duas chamadas: `Company`
	aparece nos dois, e a segunda chamada sobrescreveria a lista da primeira.
	"""
	campos: dict[str, list[dict]] = {}

	for mapa in (get_custom_fields(), get_campos_documento()):
		for doctype, definicoes in mapa.items():
			campos.setdefault(doctype, []).extend(definicoes)

	create_custom_fields(campos, ignore_validate=frappe.flags.in_patch, update=update)
