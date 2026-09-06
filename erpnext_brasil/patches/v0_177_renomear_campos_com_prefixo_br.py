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

⚠️ A ordem importa, e o bench provou isso
------------------------------------------------
`rename_field` **não renomeia coluna**: ele faz `UPDATE tabX SET novo = antigo` — copia o
valor de uma coluna para a outra, e pressupõe que **as duas já existem**.

A primeira versão deste patch só chamava `rename_field`, e no bench saiu
`rename_field: br_inscricao_estadual not found in Company`, repetido 65 vezes. A causa é de
ordem: os patches rodam **antes** do `after_migrate`, e é o `after_migrate` que cria os
campos. Quando o patch corria, a coluna de destino ainda não existia — então ele não fazia
nada, e o `after_migrate` logo depois criava o campo novo **vazio**. O dado ficaria na
coluna antiga, invisível.

Não quebraria nada. O cadastro é que apareceria em branco — e é por isso que só um bench
mostra: a suíte pura via um patch bem-formado, e ele era inerte.

Por isso a ordem aqui é **criar, copiar, remover**:

1. `criar_campos_fiscais()` — garante a coluna de destino;
2. `rename_field` — copia o valor, e ainda ajusta Property Setter, relatórios e filtros
   salvos, o que um `UPDATE` cru não faria;
3. remoção do `Custom Field` antigo — sem ela o formulário mostraria **os dois** campos, o
   novo preenchido e o velho também, sem que nada dissesse qual vale.

Idempotente nos três passos: `create_custom_fields` usa `update=True`, `rename_field` avisa
sem levantar quando não há o que fazer, e a remoção confere a existência antes.
"""

import frappe
from frappe.model.utils.rename_field import rename_field

from erpnext_brasil.setup.install import criar_campos_fiscais

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
	# Passo 1: os campos novos precisam existir **antes** de receber o valor — ver a nota
	# de ordem na docstring. Os patches rodam antes do `after_migrate`, então adiantar a
	# criação aqui é o que torna o resto possível.
	criar_campos_fiscais()

	for doctype, pares in RENOMES.items():
		if not frappe.db.exists("DocType", doctype):
			# `Salary Component` vem do `hrms`, opcional neste projeto.
			continue

		for antigo, novo in pares:
			if not frappe.db.has_column(doctype, antigo):
				# Site novo: os campos já nasceram com o nome certo, e não há de onde copiar.
				continue

			# Passo 2: copia o valor da coluna antiga para a nova.
			rename_field(doctype, antigo, novo)

			# Passo 3: o `Custom Field` antigo continua declarado, e sem removê-lo o
			# formulário mostraria os dois campos — o novo com o valor e o velho também,
			# sem nada dizendo qual vale.
			nome_do_campo = f"{doctype}-{antigo}"

			if frappe.db.exists("Custom Field", nome_do_campo):
				frappe.delete_doc("Custom Field", nome_do_campo, ignore_permissions=True)

	frappe.clear_cache()
