# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê a conta de cobrança de uma `Company` a partir do `Bank Account` do ERPNext.

Fecha metade do gap descrito em `docs/tropicalizacao-por-area.md`: `contabil/boleto.py`
monta código de barras e linha digitável desde sempre, e **nada num site tinha de onde
tirar os dados** — o `Bank Account` do ERPNext guarda `branch_code` e `bank_account_no`, e
nem carteira, nem convênio, nem os dígitos verificadores separados.

Os campos foram declarados em `setup/custom_fields.py`; este módulo é quem os lê.

O número da conta continua sendo `bank_account_no`
---------------------------------------------------------
Não se criou um `br_conta`. O ERPNext já tem o campo, é ele que o resto do sistema usa, e
duplicá-lo produziria duas verdades sobre a mesma conta — a divergência apareceria no dia
em que alguém corrigisse uma e não a outra. Só o **dígito** virou campo novo, porque o
campo livre do boleto o posiciona à parte.

Qual conta é escolhida
----------------------------
A marcada como `is_default` entre as `is_company_account` da empresa. Havendo mais de uma e
nenhuma padrão, **falha alto**: escolher a primeira produziria boleto no banco errado, e o
dinheiro entraria numa conta que ninguém está conciliando.

⚠️ Isto ainda **não emite boleto**. Falta o montador de campo livre, específico por banco.
"""

import frappe
from frappe import _

from erpnext_brasil.contabil.conta_bancaria import ContaBancaria, montar_conta_bancaria

__all__ = ["ContaBancariaAusente", "conta_de_cobranca_da_empresa"]

CAMPOS_DA_CONTA = (
	"name",
	"bank",
	"bank_account_no",
	"br_agencia",
	"br_agencia_dv",
	"br_conta_dv",
	"br_carteira",
	"br_convenio",
)


class ContaBancariaAusente(frappe.ValidationError):
	"""Não há conta de cobrança utilizável para esta empresa."""


def _conta_da_empresa(company: str) -> dict:
	contas = frappe.get_all(
		"Bank Account",
		filters={"company": company, "is_company_account": 1, "disabled": 0},
		fields=[*CAMPOS_DA_CONTA, "is_default"],
		order_by="is_default desc, creation asc",
	)

	if not contas:
		frappe.throw(
			_("A empresa {0} não tem conta bancária própria cadastrada.").format(company),
			exc=ContaBancariaAusente,
		)

	if len(contas) > 1 and not contas[0].get("is_default"):
		frappe.throw(
			_(
				"A empresa {0} tem mais de uma conta bancária e nenhuma marcada como padrão. "
				"Marque a conta de cobrança como padrão — emitir na conta errada faz o "
				"dinheiro entrar onde ninguém concilia."
			).format(company),
			exc=ContaBancariaAusente,
		)

	return contas[0]


def conta_de_cobranca_da_empresa(company: str) -> ContaBancaria:
	"""A conta de cobrança da empresa, já limpa e conferida.

	O código COMPE vem do `Bank` vinculado, não do `Bank Account`: é atributo da
	instituição, e repeti-lo em cada conta faria duas contas do mesmo banco poderem
	discordar sobre qual banco é.
	"""
	conta = _conta_da_empresa(company)

	codigo_banco = ""

	if conta.get("bank"):
		codigo_banco = frappe.db.get_value("Bank", conta["bank"], "br_codigo_banco") or ""

	if not codigo_banco:
		frappe.throw(
			_("O banco da conta {0} não tem o código COMPE preenchido.").format(conta["name"]),
			exc=ContaBancariaAusente,
		)

	return montar_conta_bancaria(
		codigo_banco=codigo_banco,
		agencia=conta.get("br_agencia") or "",
		conta=conta.get("bank_account_no") or "",
		agencia_dv=conta.get("br_agencia_dv") or "",
		conta_dv=conta.get("br_conta_dv") or "",
		carteira=conta.get("br_carteira") or "",
		convenio=conta.get("br_convenio") or "",
	)
