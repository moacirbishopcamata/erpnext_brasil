# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Renomeia os campos deste app para o prefixo `br_`.

⚠️ **Sem este patch, um site já instalado perde o dado.** `create_custom_fields` criaria os
campos novos vazios e deixaria os antigos órfãos: a inscrição estadual continuaria na coluna
`inscricao_estadual`, e o app leria `br_inscricao_estadual` — vazia. Nada quebraria; o
cadastro é que apareceria em branco.

Por que renomear
-----------------------
Vinte e três campos nasceram com nome genérico — `ncm`, `cest`, `bairro`,
`inscricao_estadual`, `suframa`. Não colidiam com nada **hoje**, e o dia em que o ERPNext
criar um `ncm` os dois disputam a mesma coluna. O prefixo `br_`, que 169 campos já usavam,
passa a valer para todos: a regra vira "todo campo deste app começa com `br_`", sem exceção
a memorizar.

Os breaks de layout entram junto. Não guardam dado — `rename_field` sobre eles é barato — e
ficam na regra para que ela não tenha caso especial.

`rename_field` e não SQL
-------------------------------
`frappe.model.utils.rename_field` renomeia a coluna **e** o `Custom Field`, além de ajustar
Property Setter, filtros salvos e a ordem do formulário. Um `ALTER TABLE` moveria só a
coluna, e o campo continuaria apontando para um nome que não existe mais.

Idempotente: `rename_field` verifica se o campo novo existe e se o antigo tem coluna, e
avisa sem levantar quando não há o que fazer — então rodar de novo é inofensivo.
"""

import frappe
from frappe.model.utils.rename_field import rename_field

RENOMES = {
	"Address": [
		("bairro", "br_bairro"),
		("codigo_municipio_ibge", "br_codigo_municipio_ibge"),
		("numero_endereco", "br_numero_endereco"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
	],
	"Bank": [
		("coluna_banco_br", "br_coluna_banco_br"),
		("secao_banco_br", "br_secao_banco_br"),
	],
	"Bank Account": [
		("coluna_conta_br", "br_coluna_conta_br"),
		("secao_conta_br", "br_secao_conta_br"),
	],
	"Company": [
		("chave_pix", "br_chave_pix"),
		("cnae_principal", "br_cnae_principal"),
		("coluna_certificado_a1", "br_coluna_certificado_a1"),
		("coluna_efd", "br_coluna_efd"),
		("coluna_esocial", "br_coluna_esocial"),
		("coluna_fiscal_br", "br_coluna_fiscal_br"),
		("coluna_series", "br_coluna_series"),
		("inscricao_estadual", "br_inscricao_estadual"),
		("inscricao_municipal", "br_inscricao_municipal"),
		("regime_tributario", "br_regime_tributario"),
		("secao_certificado_a1", "br_secao_certificado_a1"),
		("secao_efd", "br_secao_efd"),
		("secao_esocial", "br_secao_esocial"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
		("secao_nfce", "br_secao_nfce"),
		("secao_series", "br_secao_series"),
		("secao_transporte", "br_secao_transporte"),
		("suframa", "br_suframa"),
	],
	"Customer": [
		("coluna_fiscal_br", "br_coluna_fiscal_br"),
		("indicador_ie", "br_indicador_ie"),
		("inscricao_estadual", "br_inscricao_estadual"),
		("inscricao_municipal", "br_inscricao_municipal"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
		("suframa", "br_suframa"),
	],
	"Delivery Note": [
		("indicador_ie", "br_indicador_ie"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
	],
	"Delivery Note Item": [
		("coluna_apuracao_br", "br_coluna_apuracao_br"),
		("secao_apuracao_br", "br_secao_apuracao_br"),
	],
	"Employee": [
		("coluna_esocial_br", "br_coluna_esocial_br"),
		("secao_esocial_br", "br_secao_esocial_br"),
	],
	"Item": [
		("cest", "br_cest"),
		("codigo_servico_lc116", "br_codigo_servico_lc116"),
		("coluna_fiscal_br", "br_coluna_fiscal_br"),
		("finalidade_compra", "br_finalidade_compra"),
		("ncm", "br_ncm"),
		("origem_mercadoria", "br_origem_mercadoria"),
		("producao_propria", "br_producao_propria"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
	],
	"Purchase Invoice": [
		("indicador_ie", "br_indicador_ie"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
	],
	"Purchase Invoice Item": [
		("coluna_apuracao_br", "br_coluna_apuracao_br"),
		("secao_apuracao_br", "br_secao_apuracao_br"),
	],
	"Purchase Receipt": [
		("indicador_ie", "br_indicador_ie"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
	],
	"Purchase Receipt Item": [
		("coluna_apuracao_br", "br_coluna_apuracao_br"),
		("secao_apuracao_br", "br_secao_apuracao_br"),
	],
	"Salary Component": [
		("secao_esocial_br", "br_secao_esocial_br"),
	],
	"Sales Invoice": [
		("indicador_ie", "br_indicador_ie"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
	],
	"Sales Invoice Item": [
		("coluna_apuracao_br", "br_coluna_apuracao_br"),
		("secao_apuracao_br", "br_secao_apuracao_br"),
	],
	"Supplier": [
		("coluna_fiscal_br", "br_coluna_fiscal_br"),
		("indicador_ie", "br_indicador_ie"),
		("inscricao_estadual", "br_inscricao_estadual"),
		("inscricao_municipal", "br_inscricao_municipal"),
		("secao_fiscal_br", "br_secao_fiscal_br"),
		("suframa", "br_suframa"),
	],
}
"""`{DocType: [(nome antigo, nome novo)]}` — gerado da diferença real, não deduzido.

⚠️ Deduzir "todo `br_x` veio de `x`" estaria errado: 169 campos **nasceram** com o prefixo,
e tentar renomeá-los procuraria colunas que nunca existiram.
"""


def execute():
	for doctype, pares in RENOMES.items():
		if not frappe.db.exists("DocType", doctype):
			# `Salary Component` vem do `hrms`, opcional neste projeto.
			continue

		for antigo, novo in pares:
			if not frappe.db.has_column(doctype, antigo):
				# Site novo: os campos já nasceram com o nome certo.
				continue

			rename_field(doctype, antigo, novo)

	frappe.clear_cache()
