# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Criação das listas de códigos normativas como Code List / Common Code.

Roda no `after_install` e de novo a cada `after_migrate`, então **precisa ser
idempotente**: reexecutar não pode duplicar código nem sobrescrever ajuste feito pelo
usuário sem necessidade. A estratégia é procurar pelo par (code_list, common_code) —
que é justamente o índice que o ERPNext cria em `Common Code` — e só gravar quando algo
de fato mudou.

`Common Code` usa autoname "hash", então nunca se busca pelo nome do documento: a
identidade de negócio é o par acima.
"""

import frappe

from erpnext_brasil.fiscal.codigos.tabelas import TABELAS, Tabela


def criar_listas_de_codigos() -> dict[str, int]:
	"""Cria ou atualiza todas as tabelas normativas. Devolve o que foi gravado por lista."""
	resultado = {}

	for tabela in TABELAS:
		resultado[tabela.nome] = _sincronizar(tabela)

	return resultado


def _sincronizar(tabela: Tabela) -> int:
	_garantir_code_list(tabela)

	gravados = 0

	for codigo, titulo in tabela.codigos.items():
		if _garantir_common_code(tabela.nome, codigo, titulo):
			gravados += 1

	return gravados


def _garantir_code_list(tabela: Tabela) -> None:
	campos = {
		"title": tabela.titulo,
		"description": tabela.descricao,
		"publisher": tabela.publicador,
	}

	if frappe.db.exists("Code List", tabela.nome):
		atual = frappe.db.get_value("Code List", tabela.nome, list(campos), as_dict=True)

		# Só grava se divergiu — evita marcar o documento como modificado a cada migrate.
		if all(atual.get(chave) == valor for chave, valor in campos.items()):
			return

		doc = frappe.get_doc("Code List", tabela.nome)
		doc.update(campos)
		doc.save(ignore_permissions=True)

		return

	doc = frappe.new_doc("Code List")
	doc.name = tabela.nome  # autoname = "prompt"
	doc.update(campos)
	doc.insert(ignore_permissions=True)


def _garantir_common_code(code_list: str, codigo: str, titulo: str) -> bool:
	"""Cria o código, ou atualiza o título se ele mudou. Devolve True se gravou."""
	existente = frappe.db.get_value(
		"Common Code",
		{"code_list": code_list, "common_code": codigo},
		["name", "title"],
		as_dict=True,
	)

	if existente:
		if existente.title == titulo:
			return False

		doc = frappe.get_doc("Common Code", existente.name)
		doc.title = titulo
		doc.save(ignore_permissions=True)

		return True

	doc = frappe.new_doc("Common Code")
	doc.code_list = code_list
	doc.common_code = codigo
	doc.title = titulo
	doc.insert(ignore_permissions=True)

	return True
