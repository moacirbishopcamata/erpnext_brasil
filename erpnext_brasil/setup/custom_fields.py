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
from erpnext_brasil.fiscal.documento.imposto_item import CST_ICMS_SUPORTADOS
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

# Rótulo do Select → código do leiaute. Moram aqui, ao lado da lista de opções que os
# origina, e não na camada de integração, pelo mesmo motivo de `SERIE_POR_MODELO`: assim a
# suíte pura consegue conferir que toda opção oferecida na tela tem tradução. Se vivessem
# do lado do Frappe, uma opção nova sem tradução só apareceria como erro na emissão, no
# cliente.
INDICADOR_IE_POR_ROTULO = {
	"Contribuinte ICMS": "1",
	"Contribuinte isento de Inscrição no cadastro de Contribuintes": "2",
	"Não Contribuinte": "9",
}
"""`indIEDest` da NF-e: 1 = contribuinte, 2 = isento, 9 = não contribuinte."""

CRT_POR_REGIME = {
	"Simples Nacional": "1",
	"Simples Nacional - MEI": "1",
	"Simples Nacional - excesso de sublimite de receita bruta": "2",
	"Regime Normal": "3",
}
"""`CRT` da NF-e. O MEI não tem código próprio no leiaute — é Simples Nacional."""

# Rótulo do Select → `modFrete` da NF-e. Mora aqui, junto das demais tabelas de tradução,
# porque a camada de integração importa `frappe` e a suíte pura não a alcançaria — mesmo
# motivo de `INDICADOR_IE_POR_ROTULO` e `SERIE_POR_MODELO`.
#
# Este é o domínio de 2018 do `C100`/NF-e, com os códigos 3 e 4. **Não** é o do `D100` do
# EFD, que ficou em [0,1,2,9] — ver `contabil/efd_bloco_d.py`.
MODALIDADES_FRETE = {
	"Contratação do frete por conta do Remetente (CIF)": "0",
	"Contratação do frete por conta do Destinatário (FOB)": "1",
	"Contratação do frete por conta de Terceiros": "2",
	"Transporte próprio por conta do Remetente": "3",
	"Transporte próprio por conta do Destinatário": "4",
	"Sem ocorrência de transporte": "9",
}

OPCOES_MODALIDADE_FRETE = "\n".join(["", *MODALIDADES_FRETE])
"""Derivado do mapa acima: escrever a lista duas vezes é como uma opção nova fica sem
tradução."""


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
			"fieldname": "br_secao_fiscal_br",
			"label": "Dados Fiscais (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": insert_after,
			"collapsible": 1,
		},
		{
			"fieldname": "br_indicador_ie",
			"label": "Indicador de Inscrição Estadual",
			"fieldtype": "Select",
			"options": INDICADORES_IE,
			"insert_after": "br_secao_fiscal_br",
			"description": "Determina o indIEDest da NF-e. Isento não é o mesmo que Não Contribuinte.",
		},
		{
			"fieldname": "br_inscricao_estadual",
			"label": "Inscrição Estadual",
			"fieldtype": "Data",
			"insert_after": "br_indicador_ie",
			"depends_on": "eval:doc.indicador_ie=='Contribuinte ICMS'",
			"mandatory_depends_on": "eval:doc.indicador_ie=='Contribuinte ICMS'",
		},
		{
			"fieldname": "br_coluna_fiscal_br",
			"fieldtype": "Column Break",
			"insert_after": "br_inscricao_estadual",
		},
		{
			"fieldname": "br_inscricao_municipal",
			"label": "Inscrição Municipal",
			"fieldtype": "Data",
			"insert_after": "br_coluna_fiscal_br",
		},
		{
			"fieldname": "br_suframa",
			"label": "Inscrição SUFRAMA",
			"fieldtype": "Data",
			"insert_after": "br_inscricao_municipal",
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


OPCOES_CST_ICMS = "\n".join(["", *CST_ICMS_SUPORTADOS])
"""Derivado de `CST_ICMS_SUPORTADOS`: um valor a mais na tela vira `ImpostoInvalido` no
meio da emissão, depois de o usuário já ter escolhido."""

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
			"insert_after": "br_secao_fiscal_br",
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
			"fieldname": "br_numero_nfe",
			"label": "Número da NF-e",
			"fieldtype": "Data",
			"read_only": 1,
			"insert_after": "br_chave_acesso",
			"description": (
				"nNF do leiaute. Preenchido na emissão. O controle de numeração sequencial "
				"por série é exigência da SEFAZ e ainda não está implementado — gap "
				"declarado em docs/gaps.md."
			),
		},
		{
			"fieldname": "br_modalidade_frete",
			"label": "Modalidade do Frete",
			"fieldtype": "Select",
			"options": OPCOES_MODALIDADE_FRETE,
			"insert_after": "br_numero_nfe",
			"description": (
				'modFrete da NF-e. Sem padrão de propósito: "sem ocorrência de transporte" '
				"é uma afirmação sobre a operação, não a ausência de resposta."
			),
		},
		{
			"fieldname": "br_transportadora",
			"label": "Transportadora",
			"fieldtype": "Link",
			"options": "Supplier",
			"insert_after": "br_modalidade_frete",
			"description": "Opcional. Preenche o grupo transporta da NF-e quando informada.",
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

	# CST do ICMS é `Select`, não `Data`, e por um motivo concreto: `montar_imposto_item`
	# recusa CST que não sabe montar, e a recusa acontece **no meio da emissão** — depois
	# de o usuário ter escolhido e clicado. Oferecer só o que o código monta transforma um
	# erro de tempo de execução em uma opção que não existe na tela.
	entradas.append(("br_cst_icms", "CST do ICMS", "Select"))

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
			"fieldname": "br_secao_apuracao_br",
			"label": "Tributos (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "br_cfop_sugerido",
			"collapsible": 1,
		}
	]

	anterior = "br_secao_apuracao_br"

	opcoes_por_campo = {"br_cst_icms": OPCOES_CST_ICMS}

	for nome, rotulo, tipo in entradas:
		campo = {
			"fieldname": nome,
			"label": rotulo,
			"fieldtype": tipo,
			"insert_after": anterior,
		}

		if nome in opcoes_por_campo:
			campo["options"] = opcoes_por_campo[nome]

		campos.append(campo)
		anterior = nome

	campos.append(
		{
			"fieldname": "br_coluna_apuracao_br",
			"label": "",
			"fieldtype": "Column Break",
			"insert_after": anterior,
		}
	)
	anterior = "br_coluna_apuracao_br"

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
			"fieldname": "br_secao_fiscal_br",
			"label": "Dados Fiscais (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "company",
			"collapsible": 1,
		},
		{
			"fieldname": "br_chave_acesso",
			"label": "Chave de Acesso",
			"fieldtype": "Data",
			"insert_after": "br_secao_fiscal_br",
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


def _campos_do_banco() -> list[dict]:
	"""Identificação do banco no arranjo brasileiro.

	O `Bank` do ERPNext guarda só `bank_name` e `swift_number` — identificação
	internacional. No Brasil um banco é identificado por dois números diferentes, e usar um
	no lugar do outro produz arquivo recusado sem explicação:

	- **COMPE**, 3 dígitos, é o que entra nas 3 primeiras posições do código de barras do
	  boleto (`contabil/boleto.py`) e no CNAB;
	- **ISPB**, 8 dígitos, é o que identifica a instituição no PIX e no SPI.

	Nenhum dos dois é o SWIFT, e nenhum dos dois se deduz do outro.
	"""
	return [
		{
			"fieldname": "br_secao_banco_br",
			"label": "Identificação (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "swift_number",
			"collapsible": 1,
		},
		{
			"fieldname": "br_codigo_banco",
			"label": "Código do Banco (COMPE)",
			"fieldtype": "Data",
			"length": 3,
			"insert_after": "br_secao_banco_br",
			"description": (
				"Três dígitos da tabela COMPE do Bacen (001 Banco do Brasil, 237 Bradesco, "
				"341 Itaú…). É o que abre o código de barras do boleto — não é o SWIFT nem "
				"o ISPB."
			),
		},
		{
			"fieldname": "br_coluna_banco_br",
			"fieldtype": "Column Break",
			"insert_after": "br_codigo_banco",
		},
		{
			"fieldname": "br_ispb",
			"label": "ISPB",
			"fieldtype": "Data",
			"length": 8,
			"insert_after": "br_coluna_banco_br",
			"description": (
				"Oito dígitos que identificam a instituição no PIX e no SPI. Diferente do "
				"COMPE, e obrigatório para arranjos de pagamento instantâneo."
			),
		},
	]


def _campos_da_conta_bancaria() -> list[dict]:
	"""O que o boleto e o CNAB exigem e o `Bank Account` não guarda.

	`contabil/boleto.py` monta o código de barras a partir de um `campo_livre` de 25
	posições que **cada banco** compõe com agência, conta, carteira e convênio. O
	`Bank Account` do ERPNext tem `branch_code` e `bank_account_no` — e nenhum dos demais,
	nem os dígitos verificadores separados.

	Por que o dígito é campo separado, e não parte do número
	--------------------------------------------------------
	Porque o campo livre os posiciona em lugares diferentes, e alguns bancos não o incluem.
	Guardar `"1234-5"` numa `Data` obrigaria cada montador a fatiar a string por conta
	própria — e a primeira conta sem hífen produziria um boleto com dígito errado, que o
	banco aceita gerar e o cliente não consegue pagar.

	⚠️ **Isto sozinho não emite boleto.** Falta o montador de campo livre, que é específico
	por banco e exige a especificação de cada um — ver `docs/tropicalizacao-por-area.md`.
	Os campos vêm primeiro porque sem eles não há o que montar.
	"""
	return [
		{
			"fieldname": "br_secao_conta_br",
			"label": "Cobrança (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": "bank_account_no",
			"collapsible": 1,
			"depends_on": "is_company_account",
		},
		{
			"fieldname": "br_agencia",
			"label": "Agência",
			"fieldtype": "Data",
			"length": 5,
			"insert_after": "br_secao_conta_br",
			"description": "Só os dígitos, sem o verificador — ele vai no campo ao lado.",
		},
		{
			"fieldname": "br_agencia_dv",
			"label": "Dígito da Agência",
			"fieldtype": "Data",
			"length": 1,
			"insert_after": "br_agencia",
			"description": "Pode ser vazio: nem todo banco usa dígito na agência.",
		},
		{
			"fieldname": "br_conta_dv",
			"label": "Dígito da Conta",
			"fieldtype": "Data",
			"length": 1,
			"insert_after": "br_agencia_dv",
			"description": (
				"O número da conta continua em `bank_account_no`; aqui vai só o "
				"verificador, que o campo livre do boleto posiciona à parte."
			),
		},
		{
			"fieldname": "br_coluna_conta_br",
			"fieldtype": "Column Break",
			"insert_after": "br_conta_dv",
		},
		{
			"fieldname": "br_carteira",
			"label": "Carteira",
			"fieldtype": "Data",
			"length": 3,
			"insert_after": "br_coluna_conta_br",
			"description": (
				"Modalidade de cobrança contratada com o banco (ex.: 09, 17, 109). Quem "
				"define os códigos é o banco, não uma tabela nacional."
			),
		},
		{
			"fieldname": "br_convenio",
			"label": "Convênio / Código do Beneficiário",
			"fieldtype": "Data",
			"length": 20,
			"insert_after": "br_carteira",
			"description": (
				"Identifica o beneficiário perante o banco. O nome muda conforme a "
				"instituição — convênio, código do cedente, código do beneficiário — e o "
				"tamanho também."
			),
		},
	]


def get_custom_fields() -> dict[str, list[dict]]:
	"""Devolve o mapa {DocType: [definições de campo]} aplicado na instalação."""
	campos: dict[str, list[dict]] = {
		"Company": [
			{
				"fieldname": "br_secao_fiscal_br",
				"label": "Dados Fiscais (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "tax_id",
				"collapsible": 1,
			},
			{
				"fieldname": "br_regime_tributario",
				"label": "Regime Tributário",
				"fieldtype": "Select",
				"options": REGIMES_TRIBUTARIOS,
				"insert_after": "br_secao_fiscal_br",
				"description": "Define o CRT informado na NF-e e como o ICMS é apurado.",
			},
			{
				"fieldname": "br_inscricao_estadual",
				"label": "Inscrição Estadual",
				"fieldtype": "Data",
				"insert_after": "br_regime_tributario",
			},
			{
				"fieldname": "br_coluna_fiscal_br",
				"fieldtype": "Column Break",
				"insert_after": "br_inscricao_estadual",
			},
			{
				"fieldname": "br_inscricao_municipal",
				"label": "Inscrição Municipal",
				"fieldtype": "Data",
				"insert_after": "br_coluna_fiscal_br",
			},
			{
				"fieldname": "br_cnae_principal",
				"label": "CNAE Principal",
				"fieldtype": "Data",
				"insert_after": "br_inscricao_municipal",
			},
			{
				"fieldname": "br_natureza_juridica",
				"label": "Natureza Jurídica",
				"fieldtype": "Data",
				"insert_after": "br_cnae_principal",
				"description": (
					"Código da tabela de Natureza Jurídica da Receita Federal (ex.: 206-2 "
					"para Sociedade Empresária Limitada) — usado no registro 0030 da ECF."
				),
			},
			{
				"fieldname": "br_chave_pix",
				"label": "Chave Pix",
				"fieldtype": "Data",
				"insert_after": "br_cnae_principal",
				"description": (
					"CPF/CNPJ, e-mail, telefone ou chave aleatória — usada para gerar o "
					"payload Pix ('Copia e Cola') na cobrança."
				),
			},
			{
				"fieldname": "br_secao_certificado_a1",
				"label": "Certificado Digital (transmissão SEFAZ)",
				"fieldtype": "Section Break",
				"insert_after": "br_chave_pix",
				"collapsible": 1,
			},
			{
				"fieldname": "br_certificado_a1",
				"label": "Certificado A1 (.pfx/.p12)",
				"fieldtype": "Attach",
				"insert_after": "br_secao_certificado_a1",
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
				"fieldname": "br_coluna_certificado_a1",
				"fieldtype": "Column Break",
				"insert_after": "br_senha_certificado_a1",
			},
			{
				"fieldname": "br_ambiente_sefaz",
				"label": "Ambiente SEFAZ",
				"fieldtype": "Select",
				"options": "\nProdução\nHomologação",
				"default": "Homologação",
				"insert_after": "br_coluna_certificado_a1",
				"description": (
					"Homologação por padrão — troque para Produção só quando for emitir "
					"documento fiscal de verdade. Nunca o padrão de fábrica."
				),
			},
			{
				"fieldname": "br_secao_efd",
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
				"insert_after": "br_secao_efd",
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
				"fieldname": "br_coluna_efd",
				"fieldtype": "Column Break",
				"insert_after": "br_efd_atividade",
			},
			{
				"fieldname": "br_efd_versao_leiaute",
				"label": "Versão do Leiaute (EFD)",
				"fieldtype": "Data",
				"insert_after": "br_coluna_efd",
				"description": (
					"Campo COD_VER do registro 0000, 3 dígitos. Vale a versão vigente na "
					"data final da escrituração (tabela do Ato COTEPE/ICMS 09/2008) — por "
					"isso é configuração, não constante do código."
				),
			},
			{
				"fieldname": "br_suframa",
				"label": "Inscrição SUFRAMA",
				"fieldtype": "Data",
				"insert_after": "br_efd_versao_leiaute",
				"description": (
					"Campo SUFRAMA do registro 0000. A Company não tinha este campo (só "
					"Customer/Supplier tinham) e a EFD o exige de quem é inscrito."
				),
			},
			{
				"fieldname": "br_secao_nfce",
				"label": "NFC-e (Código de Segurança do Contribuinte)",
				"fieldtype": "Section Break",
				"insert_after": "br_suframa",
				"collapsible": 1,
			},
			{
				"fieldname": "br_csc_id_nfce",
				"label": "Identificador do CSC (CSCId)",
				"fieldtype": "Data",
				"insert_after": "br_secao_nfce",
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
				"fieldname": "br_secao_transporte",
				"label": "Transporte (CT-e / MDF-e)",
				"fieldtype": "Section Break",
				"insert_after": "br_csc_nfce",
				"collapsible": 1,
			},
			{
				"fieldname": "br_rntrc",
				"label": "RNTRC",
				"fieldtype": "Data",
				"insert_after": "br_secao_transporte",
				"description": (
					"Registro Nacional de Transportadores Rodoviários de Carga (ANTT), 8 "
					"dígitos. Exigido pelo modal rodoviário do CT-e e do MDF-e. Transportador "
					"dispensado usa o literal 'ISENTO'."
				),
			},
			{
				"fieldname": "br_secao_series",
				"label": "Séries dos documentos fiscais",
				"fieldtype": "Section Break",
				"insert_after": "br_rntrc",
				"collapsible": 1,
			},
			{
				"fieldname": "br_serie_nfe",
				"label": "Série da NF-e",
				"fieldtype": "Data",
				"insert_after": "br_secao_series",
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
				"fieldname": "br_coluna_series",
				"fieldtype": "Column Break",
				"insert_after": "br_serie_nfce",
			},
			{
				"fieldname": "br_serie_cte",
				"label": "Série do CT-e",
				"fieldtype": "Data",
				"insert_after": "br_coluna_series",
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
				"fieldname": "br_secao_esocial",
				"label": "eSocial / EFD-Reinf",
				"fieldtype": "Section Break",
				"insert_after": "br_serie_mdfe",
				"collapsible": 1,
			},
			{
				"fieldname": "br_esocial_classificacao_tributaria",
				"label": "Classificação Tributária (eSocial)",
				"fieldtype": "Data",
				"insert_after": "br_secao_esocial",
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
				"fieldname": "br_coluna_esocial",
				"fieldtype": "Column Break",
				"insert_after": "br_esocial_transmissor",
			},
			{
				"fieldname": "br_esocial_ambiente",
				"label": "Ambiente eSocial",
				"fieldtype": "Select",
				"options": "\nProdução\nProdução restrita",
				"default": "Produção restrita",
				"insert_after": "br_coluna_esocial",
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
				"fieldname": "br_secao_fiscal_br",
				"label": "Dados Fiscais (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "pincode",
				"collapsible": 1,
			},
			{
				"fieldname": "br_codigo_municipio_ibge",
				"label": "Código do Município (IBGE)",
				"fieldtype": "Data",
				"insert_after": "br_secao_fiscal_br",
				"description": "7 dígitos. Obrigatório na NF-e; não é derivável do CEP com segurança.",
			},
			{
				"fieldname": "br_bairro",
				"label": "Bairro",
				"fieldtype": "Data",
				"insert_after": "br_codigo_municipio_ibge",
				"description": (
					"O `Address` nativo do ERPNext não tem campo de bairro — obrigatório no "
					"endereço da NF-e (xBairro) e no registro 0030 da ECF."
				),
			},
			{
				"fieldname": "br_numero_endereco",
				"label": "Número",
				"fieldtype": "Data",
				"insert_after": "br_bairro",
				"description": (
					"O `Address` nativo do ERPNext embute o número em `address_line1` — "
					"separado aqui porque a NF-e (`nro`) e a ECF (registro 0030, `NUM`) "
					"exigem o número como campo próprio, não misturado ao logradouro."
				),
			},
		],
		"Item": [
			{
				"fieldname": "br_secao_fiscal_br",
				"label": "Dados Fiscais (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "item_group",
				"collapsible": 1,
			},
			{
				"fieldname": "br_ncm",
				"label": "NCM",
				"fieldtype": "Data",
				"insert_after": "br_secao_fiscal_br",
				"description": "8 dígitos. Determina IPI e, em muitos casos, a alíquota de ICMS.",
			},
			{
				"fieldname": "br_cest",
				"label": "CEST",
				"fieldtype": "Data",
				"insert_after": "br_ncm",
				"description": "7 dígitos. Obrigatório quando a mercadoria está sujeita a ICMS-ST.",
			},
			{
				"fieldname": "br_coluna_fiscal_br",
				"fieldtype": "Column Break",
				"insert_after": "br_cest",
			},
			{
				"fieldname": "br_origem_mercadoria",
				"label": "Origem da Mercadoria",
				"fieldtype": "Select",
				"options": ORIGENS_MERCADORIA,
				"insert_after": "br_coluna_fiscal_br",
			},
			{
				"fieldname": "br_codigo_servico_lc116",
				"label": "Código de Serviço (LC 116)",
				"fieldtype": "Data",
				"insert_after": "br_origem_mercadoria",
				"depends_on": "eval:!doc.is_stock_item",
				"description": "Usado na NFS-e. Só se aplica a itens de serviço.",
			},
			{
				"fieldname": "br_producao_propria",
				"label": "Produção Própria",
				"fieldtype": "Check",
				"insert_after": "br_codigo_servico_lc116",
				"depends_on": "eval:doc.is_stock_item",
				"description": (
					"Marque se este item é fabricado por esta empresa, não comprado pronto "
					"para revenda. Decide o CFOP de venda (produção própria × mercadoria de "
					"terceiros, ver fiscal/cfop.py)."
				),
			},
			{
				"fieldname": "br_finalidade_compra",
				"label": "Finalidade da Compra",
				"fieldtype": "Select",
				"options": FINALIDADES_COMPRA,
				"insert_after": "br_producao_propria",
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
				"insert_after": "br_finalidade_compra",
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

	campos["Mode of Payment"] = [
		{
			"fieldname": "br_tpag",
			"label": "Código tPag (NF-e)",
			"fieldtype": "Data",
			"length": 2,
			"insert_after": "type",
			"description": (
				"Código da tabela fechada do leiaute (01 Dinheiro, 15 Boleto, 17 PIX…). "
				"Vazio cai na tradução por nome e, não havendo, em 99 (Outros) — que é "
				"código válido, não erro."
			),
		}
	]

	campos["Bank"] = _campos_do_banco()
	campos["Bank Account"] = _campos_da_conta_bancaria()

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
