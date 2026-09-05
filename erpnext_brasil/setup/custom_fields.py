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

from erpnext_brasil.contabil.efd_bloco_0 import TIPOS_ITEM
from erpnext_brasil.fiscal.codigos.tabelas import ORIGEM_MERCADORIA, opcoes_select
from erpnext_brasil.fiscal.impostos.pis_cofins import REGIMES_VALIDOS
from erpnext_brasil.fiscal.natureza_operacao import TAMANHO_MAXIMO as TAMANHO_MAXIMO_NATUREZA

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

# Finalidade da compra do item, para decidir CFOP (`fiscal/cfop.py`) — não confundir
# com `br_destinado_a_revenda`/`Operacao.destinado_a_industrializacao_ou_comercio`,
# que decide se o IPI compõe a base do ICMS (consumo final × não consumo final), um
# eixo diferente (ver `docs/pcp-estado.md` para o erro que quase aconteceu ao
# reaproveitar aquele campo aqui).
FINALIDADES_COMPRA = "\n".join(["", "Industrialização", "Comercialização"])

# Origem da mercadoria: as opções do Select saem da mesma tabela normativa que alimenta
# o Code List. Escrever a lista aqui de novo criaria duas fontes para o mesmo dado, que
# divergiriam na primeira alteração — o mesmo motivo pelo qual não se duplica `tax_id`.
ORIGENS_MERCADORIA = opcoes_select(ORIGEM_MERCADORIA)

# Tipo do item na EFD (campo TIPO_ITEM do registro 0200). Derivado da mesma tabela que
# `contabil/efd_bloco_0.py` usa para validar o registro — se as duas listas fossem
# escritas separadamente, um valor aceito no Select seria recusado na montagem do
# arquivo (ou vice-versa), e ninguém descobriria até o Fisco recusar. Mesmo motivo de
# `ORIGENS_MERCADORIA` sair da tabela normativa em vez de ser redigitada aqui.
TIPOS_ITEM_EFD = "\n".join(["", *(f"{codigo} - {titulo}" for codigo, titulo in TIPOS_ITEM.items())])

# Modelo do documento fiscal → campo da Company que guarda a série padrão dele. Mora
# aqui, junto das definições de campo, e não em `integracao/configuracao_fiscal.py`,
# porque é a mesma classe de dado: "qual campo guarda o quê". Assim a suíte pura
# consegue conferir que todo campo referenciado existe de verdade — se o mapa vivesse
# no lado do Frappe, um nome errado devolveria vazio para sempre, sem ninguém perceber.
SERIE_POR_MODELO = {
	"55": "br_serie_nfe",
	"65": "br_serie_nfce",
	"57": "br_serie_cte",
	"58": "br_serie_mdfe",
}


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


DOCUMENTOS_COM_CHAVE_DE_ACESSO = (
	"Sales Invoice",
	"Delivery Note",
	"Purchase Invoice",
	"Purchase Receipt",
)
"""Os quatro DocTypes em que `chave_acesso_documento.validar_chave_acesso` está ligado.

A lista existe aqui, e não só em `hooks.py`, porque o hook lê `doc.get("br_chave_acesso")`
e **retorna cedo quando o campo não existe** — sem erro, sem aviso. Enquanto o campo não
era declarado, a validação nunca rodava em site real, e o teste puro não pegava porque
monta o campo por conta própria. Manter as duas listas juntas é o que impede a regressão.
"""

DOCUMENTOS_COM_CFOP_SUGERIDO = (
	"Sales Order Item",
	"Sales Invoice Item",
	"Delivery Note Item",
	"Purchase Order Item",
	"Purchase Invoice Item",
	"Purchase Receipt Item",
	"Subcontracting Order Item",
	"Subcontracting Receipt Item",
)
"""Os DocTypes filhos em que `cfop_sugestao` escreve `br_cfop_sugerido`.

Mesma armadilha do campo acima, com um agravante: atribuir atributo não declarado num
`Document` do Frappe **não levanta erro** — o valor some no save. A sugestão era
recalculada a cada `validate` e descartada.
"""


REGIMES_PIS_COFINS = "\n".join(["", *REGIMES_VALIDOS])
"""Os dois valores que `fiscal/impostos/pis_cofins.py` aceita, escritos como ele os lê.

Sem rótulo bonito de propósito: o valor gravado é consumido direto por
`ALIQUOTAS_POR_REGIME[regime]`, e um Select com "Não cumulativo" gravaria uma chave que
aquele dicionário não tem. Se um dia a tela pedir rótulo, o lugar de traduzir é a camada
de tradução, não o valor gravado.
"""

DOCUMENTOS_COM_APURACAO = (
	"Sales Invoice",
	"Delivery Note",
	"Purchase Invoice",
	"Purchase Receipt",
)
"""Os DocTypes em que `documento.apurar_impostos` está ligado no `validate`."""

LINHAS_COM_APURACAO = tuple(f"{doctype} Item" for doctype in DOCUMENTOS_COM_APURACAO)


def _campos_de_apuracao_do_documento() -> list[dict]:
	"""Os seis campos de cabeçalho que `mapeamento.operacao_de_documento` lê.

	**Nenhum deles existia até a varredura de 2026-09-04** (ver `docs/gaps.md`). O hook
	`apurar_impostos` estava ligado, rodava a cada gravação, e lia seis campos ausentes —
	`doc.get` devolvia `None` para todos, e a apuração saía com alíquota zero em silêncio.
	"""
	return [
		{
			"fieldname": "br_apurar_impostos",
			"label": "Apurar impostos brasileiros",
			"fieldtype": "Check",
			"default": "1",
			"insert_after": "secao_fiscal_br",
			"description": (
				"Desmarque para documento importado de terceiro, que já traz os impostos do "
				"emitente — recalcular sobre eles produziria valores que não conferem com o "
				"XML recebido."
			),
		},
		{
			"fieldname": "br_natureza_operacao",
			"label": "Natureza da Operação",
			"fieldtype": "Data",
			"length": TAMANHO_MAXIMO_NATUREZA,
			"insert_after": "br_apurar_impostos",
			"description": (
				"Campo natOp da NF-e/CT-e, máximo de 60 caracteres (verificado nos XSD "
				"oficiais). Sugerido a partir do CFOP quando vazio — a sugestão nunca "
				"sobrescreve o que você gravou."
			),
		},
		{
			"fieldname": "br_indicador_ie",
			"label": "Indicador de IE do Destinatário",
			"fieldtype": "Select",
			"options": INDICADORES_IE,
			"insert_after": "br_natureza_operacao",
			"description": "Mesmo campo que alimenta o indIEDest da NF-e; decide se o destinatário é contribuinte.",
		},
		{
			"fieldname": "br_regime_pis_cofins",
			"label": "Regime de PIS/COFINS",
			"fieldtype": "Select",
			"options": REGIMES_PIS_COFINS,
			"default": "cumulativo",
			"insert_after": "br_indicador_ie",
			"description": (
				"Cumulativo (0,65% e 3,00%, sem crédito) é típico do Lucro Presumido; não "
				"cumulativo (1,65% e 7,60%, com crédito) é do Lucro Real."
			),
		},
		{
			"fieldname": "br_destinado_a_revenda",
			"label": "Destinado a industrialização ou comércio",
			"fieldtype": "Check",
			"default": "1",
			"insert_after": "br_regime_pis_cofins",
			"description": (
				"Decide se o IPI compõe a base do ICMS. Eixo diferente de "
				"`finalidade_compra` do Item, que decide CFOP — ver docs/pcp-estado.md."
			),
		},
		{
			"fieldname": "br_excluir_icms_pis_cofins",
			"label": "Excluir ICMS da base de PIS/COFINS",
			"fieldtype": "Check",
			"default": "1",
			"insert_after": "br_destinado_a_revenda",
			"description": "Tese do século (RE 574.706); marcado por padrão porque é o entendimento vinculante.",
		},
		{
			"fieldname": "br_ano_competencia",
			"label": "Ano de competência (reforma)",
			"fieldtype": "Int",
			"insert_after": "br_excluir_icms_pis_cofins",
			"description": (
				"Só para forçar um ano diferente do da própria data do documento. Vazio é o "
				"caso normal — ver a correção de risco silencioso em mapeamento._ano_da_operacao."
			),
		},
	]


def _campos_de_apuracao_da_linha() -> list[dict]:
	"""Os 13 campos de entrada e 10 de saída que a apuração usa em cada linha de item.

	Os de saída são **somente leitura**: são resultado calculado, e deixá-los editáveis
	convidaria a corrigir o número em vez de corrigir a alíquota que o produziu.
	"""
	entradas = [
		("br_aliquota_icms", "Alíquota ICMS (%)", "Percent"),
		("br_reducao_icms", "Redução da base de ICMS (%)", "Percent"),
		("br_aliquota_ipi", "Alíquota IPI (%)", "Percent"),
		("br_aliquota_ibs_uf", "Alíquota IBS estadual (%)", "Percent"),
		("br_aliquota_ibs_mun", "Alíquota IBS municipal (%)", "Percent"),
		("br_aliquota_cbs", "Alíquota CBS (%)", "Percent"),
		("br_imposto_seletivo", "Imposto Seletivo", "Currency"),
		("br_frete", "Frete", "Currency"),
		("br_seguro", "Seguro", "Currency"),
		("br_outras_despesas", "Outras despesas", "Currency"),
		("br_desconto_incondicional", "Desconto incondicional", "Currency"),
		("br_cst_ibs_cbs", "CST IBS/CBS", "Data"),
		("br_cclasstrib", "cClassTrib", "Data"),
	]

	saidas = [
		("br_base_icms", "Base do ICMS", "Currency"),
		("br_valor_icms", "Valor do ICMS", "Currency"),
		("br_valor_ipi", "Valor do IPI", "Currency"),
		("br_ipi_na_base_icms", "IPI na base do ICMS", "Check"),
		("br_base_pis_cofins", "Base de PIS/COFINS", "Currency"),
		("br_valor_pis", "Valor do PIS", "Currency"),
		("br_valor_cofins", "Valor da COFINS", "Currency"),
		("br_base_ibs_cbs", "Base de IBS/CBS", "Currency"),
		("br_valor_ibs", "Valor do IBS", "Currency"),
		("br_valor_cbs", "Valor da CBS", "Currency"),
	]

	campos: list[dict] = [
		{
			"fieldname": "secao_apuracao_br",
			"label": "Tributos (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "br_cfop_sugerido",
			"collapsible": 1,
		}
	]

	anterior = "secao_apuracao_br"

	for nome, rotulo, tipo in entradas:
		campos.append(
			{
				"fieldname": nome,
				"label": rotulo,
				"fieldtype": tipo,
				"insert_after": anterior,
			}
		)
		anterior = nome

	campos.append(
		{
			"fieldname": "coluna_apuracao_br",
			"label": "",
			"fieldtype": "Column Break",
			"insert_after": anterior,
		}
	)
	anterior = "coluna_apuracao_br"

	for nome, rotulo, tipo in saidas:
		campos.append(
			{
				"fieldname": nome,
				"label": rotulo,
				"fieldtype": tipo,
				"insert_after": anterior,
				"read_only": 1,
			}
		)
		anterior = nome

	return campos


def _campo_chave_de_acesso() -> list[dict]:
	return [
		{
			"fieldname": "secao_fiscal_br",
			"label": "Dados Fiscais (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "company",
			"collapsible": 1,
		},
		{
			"fieldname": "br_chave_acesso",
			"label": "Chave de Acesso",
			"fieldtype": "Data",
			"insert_after": "secao_fiscal_br",
			"length": 44,
			"description": (
				"44 dígitos. Validada (inclusive o dígito verificador) e normalizada — a "
				"máscara é removida na gravação. Preenchida à mão para documento de "
				"terceiro; o preenchimento automático após autorização depende do "
				"orquestrador de emissão, ainda não implementado (ver docs/gaps.md)."
			),
		},
	]


def _campo_cfop_sugerido() -> list[dict]:
	return [
		{
			"fieldname": "br_cfop_sugerido",
			"label": "CFOP Sugerido",
			"fieldtype": "Data",
			"insert_after": "item_code",
			"length": 4,
			"read_only": 1,
			"allow_on_submit": 0,
			"description": (
				"Recalculado a cada gravação a partir da UF das partes e da classificação "
				"do Item. Somente leitura de propósito: é sugestão derivada, não escolha do "
				"usuário — quem discorda muda a classificação do Item, não este campo."
			),
		}
	]


def get_custom_fields() -> dict[str, list[dict]]:
	"""Devolve o mapa {DocType: [definições de campo]} aplicado na instalação."""
	campos: dict[str, list[dict]] = {
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
			{
				"fieldname": "br_natureza_juridica",
				"label": "Natureza Jurídica",
				"fieldtype": "Data",
				"insert_after": "cnae_principal",
				"description": (
					"Código da tabela de Natureza Jurídica da Receita Federal (ex.: 206-2 "
					"para Sociedade Empresária Limitada) — usado no registro 0030 da ECF."
				),
			},
			{
				"fieldname": "chave_pix",
				"label": "Chave Pix",
				"fieldtype": "Data",
				"insert_after": "cnae_principal",
				"description": (
					"CPF/CNPJ, e-mail, telefone ou chave aleatória — usada para gerar o "
					"payload Pix ('Copia e Cola') na cobrança."
				),
			},
			{
				"fieldname": "secao_certificado_a1",
				"label": "Certificado Digital (transmissão SEFAZ)",
				"fieldtype": "Section Break",
				"insert_after": "chave_pix",
				"collapsible": 1,
			},
			{
				"fieldname": "br_certificado_a1",
				"label": "Certificado A1 (.pfx/.p12)",
				"fieldtype": "Attach",
				"insert_after": "secao_certificado_a1",
				"no_copy": 1,
				"description": (
					"Arquivo do certificado digital A1, usado para assinar e transmitir "
					"NF-e/CT-e/MDF-e direto ao SEFAZ. Fica anexado de forma privada — "
					"ver integracao/certificado_a1.py sobre como é lido."
				),
			},
			{
				"fieldname": "br_senha_certificado_a1",
				"label": "Senha do certificado A1",
				"fieldtype": "Password",
				"insert_after": "br_certificado_a1",
				"no_copy": 1,
				"description": "Armazenada criptografada pelo próprio Frappe (fieldtype Password).",
			},
			{
				"fieldname": "coluna_certificado_a1",
				"fieldtype": "Column Break",
				"insert_after": "br_senha_certificado_a1",
			},
			{
				"fieldname": "br_ambiente_sefaz",
				"label": "Ambiente SEFAZ",
				"fieldtype": "Select",
				"options": "\nProdução\nHomologação",
				"default": "Homologação",
				"insert_after": "coluna_certificado_a1",
				"description": (
					"Homologação por padrão — troque para Produção só quando for emitir "
					"documento fiscal de verdade. Nunca o padrão de fábrica."
				),
			},
			{
				"fieldname": "secao_efd",
				"label": "EFD-ICMS/IPI (SPED Fiscal)",
				"fieldtype": "Section Break",
				"insert_after": "br_ambiente_sefaz",
				"collapsible": 1,
			},
			{
				"fieldname": "br_efd_perfil",
				"label": "Perfil de Apresentação",
				"fieldtype": "Select",
				"options": "\nA\nB\nC",
				"insert_after": "secao_efd",
				"description": (
					"Campo IND_PERFIL do registro 0000. Definido pela SEFAZ do estado, não "
					"escolhido pela empresa — o perfil decide quais registros o arquivo "
					"precisa conter."
				),
			},
			{
				"fieldname": "br_efd_atividade",
				"label": "Tipo de Atividade (EFD)",
				"fieldtype": "Select",
				"options": "\nIndustrial ou equiparado a industrial\nOutros",
				"insert_after": "br_efd_perfil",
				"description": (
					"Campo IND_ATIV do registro 0000. Entidade identificada por CPF só pode "
					"ser 'Outros' — regra do próprio layout."
				),
			},
			{
				"fieldname": "coluna_efd",
				"fieldtype": "Column Break",
				"insert_after": "br_efd_atividade",
			},
			{
				"fieldname": "br_efd_versao_leiaute",
				"label": "Versão do Leiaute (EFD)",
				"fieldtype": "Data",
				"insert_after": "coluna_efd",
				"description": (
					"Campo COD_VER do registro 0000, 3 dígitos. Vale a versão vigente na "
					"data final da escrituração (tabela do Ato COTEPE/ICMS 09/2008) — por "
					"isso é configuração, não constante do código."
				),
			},
			{
				"fieldname": "suframa",
				"label": "Inscrição SUFRAMA",
				"fieldtype": "Data",
				"insert_after": "br_efd_versao_leiaute",
				"description": (
					"Campo SUFRAMA do registro 0000. A Company não tinha este campo (só "
					"Customer/Supplier tinham) e a EFD o exige de quem é inscrito."
				),
			},
			{
				"fieldname": "secao_nfce",
				"label": "NFC-e (Código de Segurança do Contribuinte)",
				"fieldtype": "Section Break",
				"insert_after": "suframa",
				"collapsible": 1,
			},
			{
				"fieldname": "br_csc_id_nfce",
				"label": "Identificador do CSC (CSCId)",
				"fieldtype": "Data",
				"insert_after": "secao_nfce",
				"description": (
					"Identificador do CSC cadastrado na SEFAZ. Entra no QR Code sem zeros à "
					"esquerda, mesmo que o cadastro os exiba."
				),
			},
			{
				"fieldname": "br_csc_nfce",
				"label": "CSC (Código de Segurança do Contribuinte)",
				"fieldtype": "Password",
				"insert_after": "br_csc_id_nfce",
				"description": (
					"Segredo compartilhado com a SEFAZ, como uma senha: participa só do hash "
					"do QR Code e NUNCA aparece na URL impressa. Campo Password para o "
					"Frappe guardar criptografado, mesmo tratamento da senha do certificado."
				),
			},
			{
				"fieldname": "secao_transporte",
				"label": "Transporte (CT-e / MDF-e)",
				"fieldtype": "Section Break",
				"insert_after": "br_csc_nfce",
				"collapsible": 1,
			},
			{
				"fieldname": "br_rntrc",
				"label": "RNTRC",
				"fieldtype": "Data",
				"insert_after": "secao_transporte",
				"description": (
					"Registro Nacional de Transportadores Rodoviários de Carga (ANTT), 8 "
					"dígitos. Exigido pelo modal rodoviário do CT-e e do MDF-e. Transportador "
					"dispensado usa o literal 'ISENTO'."
				),
			},
			{
				"fieldname": "secao_series",
				"label": "Séries dos documentos fiscais",
				"fieldtype": "Section Break",
				"insert_after": "br_rntrc",
				"collapsible": 1,
			},
			{
				"fieldname": "br_serie_nfe",
				"label": "Série da NF-e",
				"fieldtype": "Data",
				"insert_after": "secao_series",
				"description": "Série padrão deste estabelecimento para o modelo 55.",
			},
			{
				"fieldname": "br_serie_nfce",
				"label": "Série da NFC-e",
				"fieldtype": "Data",
				"insert_after": "br_serie_nfe",
				"description": "Série padrão deste estabelecimento para o modelo 65.",
			},
			{
				"fieldname": "coluna_series",
				"fieldtype": "Column Break",
				"insert_after": "br_serie_nfce",
			},
			{
				"fieldname": "br_serie_cte",
				"label": "Série do CT-e",
				"fieldtype": "Data",
				"insert_after": "coluna_series",
				"description": "Série padrão deste estabelecimento para o modelo 57.",
			},
			{
				"fieldname": "br_serie_mdfe",
				"label": "Série do MDF-e",
				"fieldtype": "Data",
				"insert_after": "br_serie_cte",
				"description": "Série padrão deste estabelecimento para o modelo 58.",
			},
			{
				"fieldname": "secao_esocial",
				"label": "eSocial / EFD-Reinf",
				"fieldtype": "Section Break",
				"insert_after": "br_serie_mdfe",
				"collapsible": 1,
			},
			{
				"fieldname": "br_esocial_classificacao_tributaria",
				"label": "Classificação Tributária (eSocial)",
				"fieldtype": "Data",
				"insert_after": "secao_esocial",
				"description": (
					"Campo classTrib do evento S-1000, 2 dígitos da Tabela 08 do eSocial. "
					"Define como o empregador é tributado e condiciona vários outros campos "
					"do próprio S-1000."
				),
			},
			{
				"fieldname": "br_esocial_transmissor",
				"label": "CNPJ do Transmissor (eSocial)",
				"fieldtype": "Data",
				"insert_after": "br_esocial_classificacao_tributaria",
				"description": (
					"ideTransmissor do envelope de lote. Em branco, o próprio empregador "
					"transmite; preencha só quando um terceiro (ex.: escritório contábil) "
					"centraliza o envio."
				),
			},
			{
				"fieldname": "coluna_esocial",
				"fieldtype": "Column Break",
				"insert_after": "br_esocial_transmissor",
			},
			{
				"fieldname": "br_esocial_ambiente",
				"label": "Ambiente eSocial",
				"fieldtype": "Select",
				"options": "\nProdução\nProdução restrita",
				"default": "Produção restrita",
				"insert_after": "coluna_esocial",
				"description": (
					"Domínio PRÓPRIO do eSocial (tpAmb 1/2), NÃO o mesmo da SEFAZ — lá é "
					"produção/homologação. Campo separado de propósito: um site pode estar "
					"homologando a NF-e e já em produção no eSocial, ou o contrário."
				),
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
			{
				"fieldname": "bairro",
				"label": "Bairro",
				"fieldtype": "Data",
				"insert_after": "codigo_municipio_ibge",
				"description": (
					"O `Address` nativo do ERPNext não tem campo de bairro — obrigatório no "
					"endereço da NF-e (xBairro) e no registro 0030 da ECF."
				),
			},
			{
				"fieldname": "numero_endereco",
				"label": "Número",
				"fieldtype": "Data",
				"insert_after": "bairro",
				"description": (
					"O `Address` nativo do ERPNext embute o número em `address_line1` — "
					"separado aqui porque a NF-e (`nro`) e a ECF (registro 0030, `NUM`) "
					"exigem o número como campo próprio, não misturado ao logradouro."
				),
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
			{
				"fieldname": "producao_propria",
				"label": "Produção Própria",
				"fieldtype": "Check",
				"insert_after": "codigo_servico_lc116",
				"depends_on": "eval:doc.is_stock_item",
				"description": (
					"Marque se este item é fabricado por esta empresa, não comprado pronto "
					"para revenda. Decide o CFOP de venda (produção própria × mercadoria de "
					"terceiros, ver fiscal/cfop.py)."
				),
			},
			{
				"fieldname": "finalidade_compra",
				"label": "Finalidade da Compra",
				"fieldtype": "Select",
				"options": FINALIDADES_COMPRA,
				"insert_after": "producao_propria",
				"description": (
					"Para que esta empresa compra este item: para industrializar (usar como "
					"insumo de produção) ou para comercializar (revender como veio). Decide o "
					"CFOP de compra — não confundir com 'destinado a revenda' na apuração de "
					"impostos, que é uma regra diferente (IPI na base do ICMS)."
				),
			},
			{
				"fieldname": "br_efd_tipo_item",
				"label": "Tipo do Item (EFD)",
				"fieldtype": "Select",
				"options": TIPOS_ITEM_EFD,
				"insert_after": "finalidade_compra",
				"description": (
					"Campo TIPO_ITEM do registro 0200 da EFD, obrigatório. Não tem "
					"equivalente nativo no ERPNext: 'produção própria' e 'finalidade da "
					"compra' respondem a outras perguntas (CFOP), não a esta classificação "
					"de estoque do Fisco."
				),
			},
			{
				"fieldname": "br_efd_codigo_genero",
				"label": "Código do Gênero (EFD)",
				"fieldtype": "Data",
				"insert_after": "br_efd_tipo_item",
				"description": (
					"Campo COD_GEN do registro 0200, 2 dígitos — o capítulo da NCM, conforme "
					"a Tabela 4.2.1. Obrigatório para quem apresenta o Bloco H (inventário)."
				),
			},
			{
				"fieldname": "br_ex_ipi",
				"label": "EX da TIPI",
				"fieldtype": "Data",
				"insert_after": "br_efd_codigo_genero",
				"description": (
					"Campo EX_IPI do registro 0200, 3 dígitos. Exceção da TIPI aplicável ao "
					"NCM deste item, quando houver."
				),
			},
		],
	}

	for doctype in DOCUMENTOS_COM_CHAVE_DE_ACESSO:
		campos[doctype] = _campo_chave_de_acesso()

	for doctype in DOCUMENTOS_COM_APURACAO:
		campos[doctype].extend(_campos_de_apuracao_do_documento())

	for doctype in DOCUMENTOS_COM_CFOP_SUGERIDO:
		campos[doctype] = _campo_cfop_sugerido()

	# Depois do CFOP sugerido de propósito: os campos de apuração se ancoram nele
	# (`insert_after`), então a ordem de criação importa.
	for doctype in LINHAS_COM_APURACAO:
		campos[doctype].extend(_campos_de_apuracao_da_linha())

	return campos
