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

MODAL_CTE_POR_ROTULO = {
	"Rodoviário": "01",
	"Aéreo": "02",
	"Aquaviário": "03",
	"Ferroviário": "04",
	"Dutoviário": "05",
	"Multimodal": "06",
}
"""`ide/modal` — o Select guarda o rótulo, o leiaute espera o código."""
OPCOES_MODAL_CTE = "\n".join(["", *MODAL_CTE_POR_ROTULO])

TIPO_SERVICO_CTE_POR_ROTULO = {
	"Normal": "0",
	"Subcontratação": "1",
	"Redespacho": "2",
	"Redespacho intermediário": "3",
	"Serviço vinculado a multimodal": "4",
}
"""`ide/tpServ`."""
OPCOES_TIPO_SERVICO_CTE = "\n".join(["", *TIPO_SERVICO_CTE_POR_ROTULO])

OPCOES_TOMADOR_CTE = "\n".join(["", "Remetente", "Destinatário", "Outros"])
TOMADOR_CTE_POR_ROTULO = {"Remetente": "0", "Destinatário": "3", "Outros": "4"}
"""`toma3/toma` (0 remetente, 3 destinatário) e `toma4` (4 outros) do leiaute do CT-e."""

UNIDADE_CARGA_POR_ROTULO = {
	"M3": "00",
	"KG": "01",
	"TON": "02",
	"Unidade": "03",
	"Litros": "04",
	"MMBTU": "05",
}
"""`infQ/cUnid` — as seis unidades da anotação do XSD."""
OPCOES_UNIDADE_CARGA = "\n".join(["", *UNIDADE_CARGA_POR_ROTULO])

RODADO_MDFE_POR_ROTULO = {
	"Truck": "01",
	"Toco": "02",
	"Cavalo mecânico": "03",
	"VAN": "04",
	"Utilitário": "05",
	"Outros": "06",
}
"""`veicTracao/tpRod` — os seis tipos de rodado da anotação do XSD do MDF-e."""
OPCOES_RODADO_MDFE = "\n".join(["", *RODADO_MDFE_POR_ROTULO])

CST_ICMS_CTE = ("00", "20", "40", "41", "51", "90", "SN")
OPCOES_CST_ICMS_CTE = "\n".join(["", *CST_ICMS_CTE])


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


def _campos_de_transporte() -> list[dict]:
	"""Os campos do CT-e na `Sales Invoice` — a fatura da prestação de transporte.

	Só a venda emite CT-e: `Delivery Note`, `Purchase Invoice` e `POS Invoice` não recebem estes
	campos. Declarados aqui, e não no laço de `CABECALHOS`, para não criar quinze Custom Fields
	em documentos que nunca os leem.
	"""
	return [
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
			"options": OPCOES_MODAL_CTE,
			"default": "Rodoviário",
			"insert_after": "br_coluna_transporte",
		},
		{
			"fieldname": "br_tipo_servico_cte",
			"label": "Tipo de serviço",
			"fieldtype": "Select",
			"options": OPCOES_TIPO_SERVICO_CTE,
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
		{
			"fieldname": "br_secao_partes_cte",
			"label": "Partes do CT-e",
			"fieldtype": "Section Break",
			"insert_after": "br_numero_cte",
			"collapsible": 1,
		},
		{
			"fieldname": "br_tomador_cte",
			"label": "Tomador do serviço",
			"fieldtype": "Select",
			"options": OPCOES_TOMADOR_CTE,
			"insert_after": "br_secao_partes_cte",
			"description": (
				"Quem paga o frete. Remetente e Destinatário reaproveitam a parte já informada; "
				"Outros usa o cliente desta fatura, com cadastro completo."
			),
		},
		{
			"fieldname": "br_remetente_cte",
			"label": "Remetente da carga",
			"fieldtype": "Link",
			"options": "Customer",
			"insert_after": "br_tomador_cte",
		},
		{
			"fieldname": "br_destinatario_cte",
			"label": "Destinatário da carga",
			"fieldtype": "Link",
			"options": "Customer",
			"insert_after": "br_remetente_cte",
		},
		{
			"fieldname": "br_coluna_partes_cte",
			"fieldtype": "Column Break",
			"insert_after": "br_destinatario_cte",
		},
		{
			"fieldname": "br_produto_predominante",
			"label": "Produto predominante",
			"fieldtype": "Data",
			"length": 60,
			"insert_after": "br_coluna_partes_cte",
			"description": "Natureza da carga (ex.: Grãos, Fertilizantes). Obrigatório no CT-e.",
		},
		{
			"fieldname": "br_valor_carga",
			"label": "Valor da carga",
			"fieldtype": "Currency",
			"insert_after": "br_produto_predominante",
			"description": "Opcional no leiaute; base de seguro e de averbação.",
		},
		{
			"fieldname": "br_quantidade_carga",
			"label": "Quantidade da carga",
			"fieldtype": "Float",
			"precision": "4",
			"insert_after": "br_valor_carga",
		},
		{
			"fieldname": "br_unidade_carga",
			"label": "Unidade da carga",
			"fieldtype": "Select",
			"options": OPCOES_UNIDADE_CARGA,
			"insert_after": "br_quantidade_carga",
		},
		{
			"fieldname": "br_tipo_medida_carga",
			"label": "Tipo da medida",
			"fieldtype": "Data",
			"length": 20,
			"default": "PESO BRUTO",
			"insert_after": "br_unidade_carga",
			"description": "Ex.: PESO BRUTO, PESO BASE DE CÁLCULO, CAIXAS.",
		},
		{
			"fieldname": "br_secao_icms_cte",
			"label": "ICMS do CT-e",
			"fieldtype": "Section Break",
			"insert_after": "br_tipo_medida_carga",
			"collapsible": 1,
		},
		{
			"fieldname": "br_cst_icms_cte",
			"label": "CST do ICMS",
			"fieldtype": "Select",
			"options": OPCOES_CST_ICMS_CTE,
			"insert_after": "br_secao_icms_cte",
			"description": "SN = Simples Nacional. CST 60 e ICMS de outra UF ainda não são suportados.",
		},
		{
			"fieldname": "br_aliquota_icms_cte",
			"label": "Alíquota do ICMS (%)",
			"fieldtype": "Percent",
			"insert_after": "br_cst_icms_cte",
			"description": "Informada, não deduzida: depende da rota e do tomador.",
		},
		{
			"fieldname": "br_reducao_base_icms_cte",
			"label": "Redução da base (%)",
			"fieldtype": "Percent",
			"insert_after": "br_aliquota_icms_cte",
			"description": "Obrigatória no CST 20; opcional no 90.",
		},
	]


def _campos_de_mdfe() -> list[dict]:
	"""Os campos do MDF-e no `Shipment` — a viagem que o manifesto representa.

	O `Shipment` do ERPNext não modela veículo nem motorista (`design.md`, decisão 2); os dados da
	viagem moram aqui, no próprio documento, e não num DocType novo nem no `Vehicle` do core. O RNTRC
	vem da `Company`. Município e UF de carregamento/descarga saem dos endereços do `Shipment`.
	"""
	return [
		{
			"fieldname": "br_secao_mdfe",
			"label": "Manifesto (MDF-e)",
			"fieldtype": "Section Break",
			"insert_after": "total_weight",
			"collapsible": 1,
		},
		{
			"fieldname": "br_numero_mdfe",
			"label": "Número do MDF-e",
			"fieldtype": "Data",
			"insert_after": "br_secao_mdfe",
			"read_only": 1,
			"no_copy": 1,
			"description": "Alocado na emissão; a reemissão do mesmo Shipment reaproveita.",
		},
		{
			"fieldname": "br_placa_mdfe",
			"label": "Placa do veículo de tração",
			"fieldtype": "Data",
			"length": 7,
			"insert_after": "br_numero_mdfe",
			"description": "Sem hífen (ex.: ABC1D23).",
		},
		{
			"fieldname": "br_tara_mdfe",
			"label": "Tara do veículo (kg)",
			"fieldtype": "Data",
			"insert_after": "br_placa_mdfe",
		},
		{
			"fieldname": "br_rodado_mdfe",
			"label": "Tipo de rodado",
			"fieldtype": "Select",
			"options": OPCOES_RODADO_MDFE,
			"insert_after": "br_tara_mdfe",
		},
		{
			"fieldname": "br_coluna_mdfe",
			"fieldtype": "Column Break",
			"insert_after": "br_rodado_mdfe",
		},
		{
			"fieldname": "br_condutor_nome_mdfe",
			"label": "Nome do motorista",
			"fieldtype": "Data",
			"insert_after": "br_coluna_mdfe",
		},
		{
			"fieldname": "br_condutor_cpf_mdfe",
			"label": "CPF do motorista",
			"fieldtype": "Data",
			"length": 11,
			"insert_after": "br_condutor_nome_mdfe",
			"description": "Só dígitos (11).",
		},
		{
			"fieldname": "br_placa_reboque_mdfe",
			"label": "Placa do reboque (opcional)",
			"fieldtype": "Data",
			"length": 7,
			"insert_after": "br_condutor_cpf_mdfe",
		},
		{
			"fieldname": "br_tara_reboque_mdfe",
			"label": "Tara do reboque (kg)",
			"fieldtype": "Data",
			"insert_after": "br_placa_reboque_mdfe",
		},
	]


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
		]

	campos["Sales Invoice"] = campos["Sales Invoice"] + _campos_de_transporte()
	campos["Shipment"] = _campos_de_mdfe()

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
