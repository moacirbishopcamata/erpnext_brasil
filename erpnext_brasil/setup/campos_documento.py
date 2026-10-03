# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Campos fiscais nas linhas de item, na tabela de impostos e no cabeçalho.

Separado de `custom_fields.py` — que cuida dos cadastros (Company, Customer, Item) —
porque estes campos existem para a **apuração**, e mudam junto com ela.

Os campos de resultado são somente-leitura: são calculados na validação, e permitir
edição criaria um valor que o próximo save sobrescreve sem aviso — pior que não mostrar.
"""

from erpnext_brasil.integracao.mapeamento import CAMPOS_RESULTADO

ITENS = (
	"Sales Invoice Item",
	"Delivery Note Item",
	"Purchase Invoice Item",
	"Purchase Receipt Item",
	# Cupom do ponto de venda (NFC-e, modelo 65). Entra no mesmo laço, e não num bloco
	# próprio, porque os campos fiscais do item são exatamente os mesmos — o que muda é o
	# indicador de aplicabilidade da tabela de classificação, resolvido em
	# `integracao/validacao_fiscal.py`. Nome conferido no site v16, não deduzido de
	# `Sales Invoice Item`.
	"POS Invoice Item",
)

# Só recebem a sugestão de CFOP (`integracao/cfop_sugestao.py`), não a apuração
# fiscal inteira — Pedido/Subcontratação são documentos internos, sem chave de
# acesso nem NF-e própria.
ITENS_SO_CFOP_SUGERIDO = (
	"Sales Order Item",
	"Purchase Order Item",
	"Subcontracting Order Item",
	"Subcontracting Receipt Item",
)

CABECALHOS = (
	"Sales Invoice",
	"Delivery Note",
	"Purchase Invoice",
	"Purchase Receipt",
	"POS Invoice",
)

TABELAS_DE_IMPOSTO = ("Sales Taxes and Charges", "Purchase Taxes and Charges")

REGIMES_PIS_COFINS = "\n".join(["", "cumulativo", "nao_cumulativo"])


def _entradas_do_item() -> list[dict]:
	"""Alíquotas e valores acessórios informados pelo usuário."""
	campos = [
		{
			"fieldname": "br_secao_fiscal",
			"label": "Tributos (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "item_tax_template",
			"collapsible": 1,
		},
		{
			"fieldname": "br_aliquota_icms",
			"label": "Alíquota ICMS (%)",
			"fieldtype": "Percent",
			"insert_after": "br_secao_fiscal",
		},
		{
			"fieldname": "br_reducao_icms",
			"label": "Redução da base do ICMS (%)",
			"fieldtype": "Percent",
			"insert_after": "br_aliquota_icms",
		},
		{
			"fieldname": "br_aliquota_ipi",
			"label": "Alíquota IPI (%)",
			"fieldtype": "Percent",
			"insert_after": "br_reducao_icms",
		},
		{
			"fieldname": "br_imposto_seletivo",
			"label": "Imposto Seletivo",
			"fieldtype": "Currency",
			"insert_after": "br_aliquota_ipi",
		},
		{
			"fieldname": "br_coluna_fiscal",
			"fieldtype": "Column Break",
			"insert_after": "br_imposto_seletivo",
		},
		{
			"fieldname": "br_cst_ibs_cbs",
			"label": "CST IBS/CBS",
			"fieldtype": "Data",
			"insert_after": "br_coluna_fiscal",
			"description": "3 dígitos. Obrigatório na NF-e desde 03/08/2026.",
		},
		{
			"fieldname": "br_cclasstrib",
			"label": "cClassTrib",
			"fieldtype": "Data",
			"insert_after": "br_cst_ibs_cbs",
			"description": "6 dígitos. Deve ser compatível com o CST informado.",
		},
		{
			"fieldname": "br_aliquota_ibs_uf",
			"label": "Alíquota IBS estadual (%)",
			"fieldtype": "Percent",
			"insert_after": "br_cclasstrib",
			"description": "Em branco usa a alíquota do ano de competência.",
		},
		{
			"fieldname": "br_aliquota_ibs_mun",
			"label": "Alíquota IBS municipal (%)",
			"fieldtype": "Percent",
			"insert_after": "br_aliquota_ibs_uf",
		},
		{
			"fieldname": "br_aliquota_cbs",
			"label": "Alíquota CBS (%)",
			"fieldtype": "Percent",
			"insert_after": "br_aliquota_ibs_mun",
		},
	]

	acessorios = [
		("br_frete", "Frete"),
		("br_seguro", "Seguro"),
		("br_outras_despesas", "Outras despesas"),
		("br_desconto_incondicional", "Desconto incondicional"),
	]

	anterior = "br_aliquota_cbs"

	for nome, rotulo in acessorios:
		campos.append(
			{
				"fieldname": nome,
				"label": rotulo,
				"fieldtype": "Currency",
				"insert_after": anterior,
			}
		)
		anterior = nome

	return campos


def _resultados_do_item() -> list[dict]:
	"""Valores apurados, gravados de volta na linha. Somente-leitura."""
	rotulos = {
		"br_base_icms": ("Base do ICMS", "Currency"),
		"br_valor_icms": ("Valor do ICMS", "Currency"),
		"br_valor_ipi": ("Valor do IPI", "Currency"),
		"br_ipi_na_base_icms": ("IPI compõe a base do ICMS", "Check"),
		"br_base_pis_cofins": ("Base de PIS/COFINS", "Currency"),
		"br_valor_pis": ("Valor do PIS", "Currency"),
		"br_valor_cofins": ("Valor da COFINS", "Currency"),
		"br_base_ibs_cbs": ("Base de IBS/CBS", "Currency"),
		"br_valor_ibs": ("Valor do IBS", "Currency"),
		"br_valor_cbs": ("Valor da CBS", "Currency"),
	}

	campos = [
		{
			"fieldname": "br_secao_apurado",
			"label": "Valores apurados",
			"fieldtype": "Section Break",
			"insert_after": "br_desconto_incondicional",
			"collapsible": 1,
		}
	]

	anterior = "br_secao_apurado"

	for nome in CAMPOS_RESULTADO:
		rotulo, tipo = rotulos[nome]
		campos.append(
			{
				"fieldname": nome,
				"label": rotulo,
				"fieldtype": tipo,
				"insert_after": anterior,
				"read_only": 1,
				"no_copy": 1,
			}
		)
		anterior = nome

	return campos


def _cfop_sugerido() -> dict:
	"""Campo só de leitura, recalculado a cada `validate` — nunca um valor que o
	usuário edita e um recálculo pisaria por cima (ver `integracao/cfop_sugestao.py`
	sobre por que isso é seguro para este campo especificamente)."""
	return {
		"fieldname": "br_cfop_sugerido",
		"label": "CFOP Sugerido",
		"fieldtype": "Data",
		"insert_after": "item_code",
		"read_only": 1,
		"no_copy": 1,
		"description": "Sugestão calculada a partir da UF e do cadastro do item — confira antes de emitir.",
	}


def get_custom_fields() -> dict[str, list[dict]]:
	campos = {}

	for doctype in ITENS:
		campos[doctype] = _entradas_do_item() + _resultados_do_item() + [_cfop_sugerido()]

	for doctype in ITENS_SO_CFOP_SUGERIDO:
		campos[doctype] = [_cfop_sugerido()]

	for doctype in CABECALHOS:
		campos[doctype] = [
			{
				"fieldname": "br_secao_fiscal",
				"label": "Apuração fiscal (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "taxes_and_charges",
				"collapsible": 1,
			},
			{
				"fieldname": "br_apurar_impostos",
				"label": "Apurar impostos automaticamente",
				"fieldtype": "Check",
				"default": "1",
				"insert_after": "br_secao_fiscal",
				"description": (
					"Desmarque em documento importado de terceiro: os impostos já vêm do "
					"emitente, e recalcular produziria valores que não conferem com o XML."
				),
			},
			{
				"fieldname": "br_destinado_a_revenda",
				"label": "Destinado a industrialização ou comércio",
				"fieldtype": "Check",
				"default": "1",
				"insert_after": "br_apurar_impostos",
				"description": "Desmarcado (consumidor final) faz o IPI compor a base do ICMS.",
			},
			{
				"fieldname": "br_coluna_fiscal",
				"fieldtype": "Column Break",
				"insert_after": "br_destinado_a_revenda",
			},
			{
				"fieldname": "br_regime_pis_cofins",
				"label": "Regime de PIS/COFINS",
				"fieldtype": "Select",
				"options": REGIMES_PIS_COFINS,
				"insert_after": "br_coluna_fiscal",
			},
			{
				"fieldname": "br_ano_competencia",
				"label": "Ano de competência (IBS/CBS)",
				"fieldtype": "Int",
				"insert_after": "br_regime_pis_cofins",
				"description": "Em branco usa o ano-teste vigente.",
			},
			{
				"fieldname": "br_excluir_icms_pis_cofins",
				"label": "Excluir ICMS da base de PIS/COFINS",
				"fieldtype": "Check",
				"default": "1",
				"insert_after": "br_ano_competencia",
				"description": "RE 574.706. Desmarcar recolhe a maior.",
			},
			{
				"fieldname": "br_secao_chave_acesso",
				"label": "Documento fiscal eletrônico",
				"fieldtype": "Section Break",
				"insert_after": "br_excluir_icms_pis_cofins",
				"collapsible": 1,
			},
			{
				"fieldname": "br_chave_acesso",
				"label": "Chave de acesso",
				"fieldtype": "Data",
				"insert_after": "br_secao_chave_acesso",
				"no_copy": 1,
				"length": 44,
				"description": (
					"NF-e emitida (Sales Invoice/Delivery Note) ou recebida de terceiro "
					"(Purchase Invoice/Purchase Receipt). Preenchimento manual até a "
					"transmissão automática existir — ver docs/integracao-cte-mapeamento.md."
				),
			},
			{
				"fieldname": "br_protocolo_autorizacao",
				"label": "Protocolo de autorização",
				"fieldtype": "Data",
				"insert_after": "br_chave_acesso",
				"no_copy": 1,
			},
			{
				"fieldname": "br_secao_transporte",
				"label": "Transporte (CT-e)",
				"fieldtype": "Section Break",
				"insert_after": "br_protocolo_autorizacao",
				"collapsible": 1,
			},
			{
				"fieldname": "br_natureza_transporte",
				"label": "Natureza de operação de transporte",
				"fieldtype": "Data",
				"insert_after": "br_secao_transporte",
				"description": (
					"Marcado como fatura de transporte na emissão do CT-e. "
					"Preenchido manualmente — decide se o botão Emitir CT-e aparece."
				),
			},
			{
				"fieldname": "br_cfop_transporte",
				"label": "CFOP do CT-e",
				"fieldtype": "Data",
				"insert_after": "br_natureza_transporte",
				"description": "CFOP de 4 dígitos para o CT-e (ex.: 5352, 6352).",
			},
			{
				"fieldname": "br_coluna_transporte",
				"fieldtype": "Column Break",
				"insert_after": "br_cfop_transporte",
			},
			{
				"fieldname": "br_modal_cte",
				"label": "Modal do CT-e",
				"fieldtype": "Select",
				"options": "\nRodoviário\nAéreo\nAquaviário\nFerroviário\nDutoviário\nMultimodal",
				"default": "Rodoviário",
				"insert_after": "br_coluna_transporte",
			},
			{
				"fieldname": "br_tipo_servico_cte",
				"label": "Tipo de serviço",
				"fieldtype": "Select",
				"options": "\nNormal\nSubcontratação\nRedespacho\nRedespacho intermediário\nServiço vinculado a multimodal",
				"default": "Normal",
				"insert_after": "br_modal_cte",
			},
			{
				"fieldname": "br_secao_municipios",
				"label": "Municípios de início/fim",
				"fieldtype": "Section Break",
				"insert_after": "br_tipo_servico_cte",
				"collapsible": 1,
			},
			{
				"fieldname": "br_municipio_inicio",
				"label": "Código IBGE município de início",
				"fieldtype": "Data",
				"insert_after": "br_secao_municipios",
				"description": "7 dígitos. Código IBGE do município de início da prestação.",
			},
			{
				"fieldname": "br_municipio_inicio_nome",
				"label": "Nome município de início",
				"fieldtype": "Data",
				"insert_after": "br_municipio_inicio",
			},
			{
				"fieldname": "br_uf_inicio",
				"label": "UF início",
				"fieldtype": "Data",
				"insert_after": "br_municipio_inicio_nome",
				"description": "Sigla da UF (ex.: SP, RJ).",
			},
			{
				"fieldname": "br_coluna_municipios",
				"fieldtype": "Column Break",
				"insert_after": "br_uf_inicio",
			},
			{
				"fieldname": "br_municipio_fim",
				"label": "Código IBGE município de fim",
				"fieldtype": "Data",
				"insert_after": "br_coluna_municipios",
				"description": "7 dígitos. Código IBGE do município de fim da prestação.",
			},
			{
				"fieldname": "br_municipio_fim_nome",
				"label": "Nome município de fim",
				"fieldtype": "Data",
				"insert_after": "br_municipio_fim",
			},
			{
				"fieldname": "br_uf_fim",
				"label": "UF fim",
				"fieldtype": "Data",
				"insert_after": "br_municipio_fim_nome",
				"description": "Sigla da UF (ex.: SP, RJ).",
			},
			{
				"fieldname": "br_numero_cte",
				"label": "Número do CT-e",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "br_uf_fim",
				"description": "Preenchido na emissão. Controle de numeração sequencial por série.",
			},
		]

	for doctype in TABELAS_DE_IMPOSTO:
		campos[doctype] = [
			{
				"fieldname": "br_gerado_automaticamente",
				"label": "Gerado pela apuração fiscal",
				"fieldtype": "Check",
				"insert_after": "account_head",
				"read_only": 1,
				"no_copy": 1,
				"description": (
					"Linhas marcadas são reescritas a cada validação; linhas manuais são preservadas."
				),
			}
		]

	contas = [
		("br_conta_icms", "Conta do ICMS"),
		("br_conta_ipi", "Conta do IPI"),
		("br_conta_pis", "Conta do PIS"),
		("br_conta_cofins", "Conta da COFINS"),
		("br_conta_ibs", "Conta do IBS"),
		("br_conta_cbs", "Conta da CBS"),
	]

	campos_empresa = [
		{
			"fieldname": "br_secao_contas_fiscais",
			"label": "Contas de tributos (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "br_cnae_principal",
			"collapsible": 1,
			"description": (
				"Tributo sem conta configurada não é lançado na tabela de impostos — "
				"imposto em conta errada some na conciliação."
			),
		}
	]

	anterior = "br_secao_contas_fiscais"

	for nome, rotulo in contas:
		campos_empresa.append(
			{
				"fieldname": nome,
				"label": rotulo,
				"fieldtype": "Link",
				"options": "Account",
				"insert_after": anterior,
			}
		)
		anterior = nome

	campos["Company"] = campos_empresa

	return campos
