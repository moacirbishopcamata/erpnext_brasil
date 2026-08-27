# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Aplicação da apuração fiscal aos documentos do ERPNext.

Camada fina de propósito: converte o documento em dicionários, chama a apuração e grava
o resultado. Toda a regra está em `fiscal/`, e toda a tradução em
`integracao/mapeamento.py` — as duas testáveis sem bench.

Ligado em `validate`, e não em `on_submit`, para que o usuário veja os impostos enquanto
ainda pode corrigir o documento.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.impostos.apuracao import apurar_documento
from erpnext_brasil.integracao.mapeamento import (
	item_fiscal_de_linha,
	linhas_de_imposto,
	operacao_de_documento,
	reconciliar_tabela_de_impostos,
	resultado_para_campos,
)

# Documentos cujos itens recebem apuração fiscal.
DOCTYPES = ("Sales Invoice", "Delivery Note", "Purchase Invoice", "Purchase Receipt")


def _pais_e_brasil(doc) -> bool:
	empresa = doc.get("company")

	if not empresa:
		return False

	return frappe.get_cached_value("Company", empresa, "country") == "Brazil"


def _contas_configuradas(empresa: str) -> dict[str, str]:
	"""Lê as contas contábeis por tributo das configurações da empresa.

	Devolve só o que estiver preenchido: tributo sem conta é omitido da tabela de
	impostos em vez de cair numa conta genérica — imposto em conta errada some na
	conciliação, o que é pior que imposto não lançado.
	"""
	nomes = {
		"ICMS": "br_conta_icms",
		"IPI": "br_conta_ipi",
		"PIS": "br_conta_pis",
		"COFINS": "br_conta_cofins",
		"IBS": "br_conta_ibs",
		"CBS": "br_conta_cbs",
	}

	valores = frappe.db.get_value("Company", empresa, list(nomes.values()), as_dict=True) or {}

	return {
		tributo: valores.get(campo) for tributo, campo in nomes.items() if valores.get(campo)
	}


def apurar_impostos(doc, method=None):
	"""Calcula os tributos brasileiros de cada item e sincroniza a tabela de impostos."""
	if not _pais_e_brasil(doc) or not doc.get("items"):
		return

	if not doc.get("br_apurar_impostos", True):
		# Escape consciente: documento importado de terceiro já traz os impostos do
		# emitente, e recalcular sobre eles produziria valores que não conferem com o
		# XML recebido.
		return

	cabecalho = {
		campo: doc.get(campo)
		for campo in (
			"br_indicador_ie",
			"br_destinado_a_revenda",
			"br_regime_pis_cofins",
			"br_ano_competencia",
			"br_excluir_icms_pis_cofins",
		)
	}

	operacao = operacao_de_documento(cabecalho)

	try:
		itens = [item_fiscal_de_linha(linha.as_dict()) for linha in doc.items]
		apuracao = apurar_documento(itens, operacao)
	except ValueError as e:
		frappe.throw(_("Não foi possível apurar os impostos: {0}").format(str(e)))
		return

	for linha, resultado in zip(doc.items, apuracao.itens, strict=True):
		for campo, valor in resultado_para_campos(resultado).items():
			linha.set(campo, valor)

	_sincronizar_tabela_de_impostos(doc, apuracao.itens)


def _sincronizar_tabela_de_impostos(doc, apuracoes) -> None:
	"""Reescreve as linhas de imposto geradas por este app, preservando as demais.

	A decisão de o que sobrevive está em `reconciliar_tabela_de_impostos`, que é pura e
	testada; aqui fica só a persistência.
	"""
	contas = _contas_configuradas(doc.company)

	if not contas:
		return

	existentes = [linha.as_dict() for linha in doc.get("taxes", [])]
	final = reconciliar_tabela_de_impostos(existentes, linhas_de_imposto(apuracoes, contas))

	doc.set("taxes", [])

	for linha in final:
		doc.append("taxes", linha)
