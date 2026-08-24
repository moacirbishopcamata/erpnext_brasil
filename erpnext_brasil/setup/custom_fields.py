# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Campos fiscais brasileiros adicionados aos DocTypes do ERPNext.

Princípio que guia este módulo: **não duplicar o que o ERPNext já tem**. Company,
Customer e Supplier já possuem `tax_id`, que é onde o CNPJ/CPF deve morar — criar um
campo `cnpj` paralelo produziria dois lugares para o mesmo dado, divergindo em silêncio.
O que se acrescenta aqui é só o que o núcleo genuinamente não modela.

A instalação é idempotente: `create_custom_fields` com `update=True` reaplica as
definições sem duplicar, o que torna seguro rodar a cada `bench migrate`.
"""

REGIMES_TRIBUTARIOS = "\n".join(
	[
		"",
		"Simples Nacional",
		"Simples Nacional - excesso de sublimite de receita bruta",
		"Regime Normal",
		"Simples Nacional - MEI",
	]
)

# Indicador de Inscrição Estadual do destinatário (campo indIEDest da NF-e).
INDICADORES_IE = "\n".join(
	[
		"",
		"Contribuinte ICMS",
		"Contribuinte isento de Inscrição no cadastro de Contribuintes",
		"Não Contribuinte",
	]
)

# Origem da mercadoria (tabela A da NF-e) — compõe o CST junto com a tributação.
ORIGENS_MERCADORIA = "\n".join(
	[
		"",
		"0 - Nacional",
		"1 - Estrangeira - Importação direta",
		"2 - Estrangeira - Adquirida no mercado interno",
		"3 - Nacional - Conteúdo de importação superior a 40%",
		"4 - Nacional - Processos produtivos básicos",
		"5 - Nacional - Conteúdo de importação inferior ou igual a 40%",
		"6 - Estrangeira - Importação direta sem similar nacional",
		"7 - Estrangeira - Adquirida no mercado interno sem similar nacional",
		"8 - Nacional - Conteúdo de importação superior a 70%",
	]
)


def _campos_de_parte(insert_after: str) -> list[dict]:
	"""Campos comuns a Customer e Supplier.

	`tax_id` (nativo) guarda o CPF/CNPJ; aqui entram apenas os complementos.
	"""
	return [
		{
			"fieldname": "secao_fiscal_br",
			"label": "Dados Fiscais (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": insert_after,
			"collapsible": 1,
		},
		{
			"fieldname": "indicador_ie",
			"label": "Indicador de Inscrição Estadual",
			"fieldtype": "Select",
			"options": INDICADORES_IE,
			"insert_after": "secao_fiscal_br",
			"description": "Determina o indIEDest da NF-e. Isento não é o mesmo que Não Contribuinte.",
		},
		{
			"fieldname": "inscricao_estadual",
			"label": "Inscrição Estadual",
			"fieldtype": "Data",
			"insert_after": "indicador_ie",
			"depends_on": "eval:doc.indicador_ie=='Contribuinte ICMS'",
			"mandatory_depends_on": "eval:doc.indicador_ie=='Contribuinte ICMS'",
		},
		{
			"fieldname": "coluna_fiscal_br",
			"fieldtype": "Column Break",
			"insert_after": "inscricao_estadual",
		},
		{
			"fieldname": "inscricao_municipal",
			"label": "Inscrição Municipal",
			"fieldtype": "Data",
			"insert_after": "coluna_fiscal_br",
		},
		{
			"fieldname": "suframa",
			"label": "Inscrição SUFRAMA",
			"fieldtype": "Data",
			"insert_after": "inscricao_municipal",
		},
	]


def get_custom_fields() -> dict[str, list[dict]]:
	"""Devolve o mapa {DocType: [definições de campo]} aplicado na instalação."""
	return {
		"Company": [
			{
				"fieldname": "secao_fiscal_br",
				"label": "Dados Fiscais (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "tax_id",
				"collapsible": 1,
			},
			{
				"fieldname": "regime_tributario",
				"label": "Regime Tributário",
				"fieldtype": "Select",
				"options": REGIMES_TRIBUTARIOS,
				"insert_after": "secao_fiscal_br",
				"description": "Define o CRT informado na NF-e e como o ICMS é apurado.",
			},
			{
				"fieldname": "inscricao_estadual",
				"label": "Inscrição Estadual",
				"fieldtype": "Data",
				"insert_after": "regime_tributario",
			},
			{
				"fieldname": "coluna_fiscal_br",
				"fieldtype": "Column Break",
				"insert_after": "inscricao_estadual",
			},
			{
				"fieldname": "inscricao_municipal",
				"label": "Inscrição Municipal",
				"fieldtype": "Data",
				"insert_after": "coluna_fiscal_br",
			},
			{
				"fieldname": "cnae_principal",
				"label": "CNAE Principal",
				"fieldtype": "Data",
				"insert_after": "inscricao_municipal",
			},
		],
		"Customer": _campos_de_parte("tax_id"),
		"Supplier": _campos_de_parte("tax_id"),
		"Address": [
			{
				"fieldname": "secao_fiscal_br",
				"label": "Dados Fiscais (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "pincode",
				"collapsible": 1,
			},
			{
				"fieldname": "codigo_municipio_ibge",
				"label": "Código do Município (IBGE)",
				"fieldtype": "Data",
				"insert_after": "secao_fiscal_br",
				"description": "7 dígitos. Obrigatório na NF-e; não é derivável do CEP com segurança.",
			},
		],
		"Item": [
			{
				"fieldname": "secao_fiscal_br",
				"label": "Dados Fiscais (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "item_group",
				"collapsible": 1,
			},
			{
				"fieldname": "ncm",
				"label": "NCM",
				"fieldtype": "Data",
				"insert_after": "secao_fiscal_br",
				"description": "8 dígitos. Determina IPI e, em muitos casos, a alíquota de ICMS.",
			},
			{
				"fieldname": "cest",
				"label": "CEST",
				"fieldtype": "Data",
				"insert_after": "ncm",
				"description": "7 dígitos. Obrigatório quando a mercadoria está sujeita a ICMS-ST.",
			},
			{
				"fieldname": "coluna_fiscal_br",
				"fieldtype": "Column Break",
				"insert_after": "cest",
			},
			{
				"fieldname": "origem_mercadoria",
				"label": "Origem da Mercadoria",
				"fieldtype": "Select",
				"options": ORIGENS_MERCADORIA,
				"insert_after": "coluna_fiscal_br",
			},
			{
				"fieldname": "codigo_servico_lc116",
				"label": "Código de Serviço (LC 116)",
				"fieldtype": "Data",
				"insert_after": "origem_mercadoria",
				"depends_on": "eval:!doc.is_stock_item",
				"description": "Usado na NFS-e. Só se aplica a itens de serviço.",
			},
		],
	}
