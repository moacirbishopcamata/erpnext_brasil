# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Tradução entre as linhas do ERPNext e a apuração fiscal.

A costura
---------
De um lado, linhas de item e de imposto do ERPNext — dicionários de campos. Do outro, os
tipos da apuração. Este módulo é a **costura** entre as duas formas, e é por isso que ele
existe separado: costura mal feita é onde bug silencioso mora, e mantê-la num arquivo
próprio permite testá-la sem bench, sem site e sem banco.

Nada aqui importa `frappe`. Recebe e devolve dicionários; quem grava é
`integracao/documento.py`.

Alíquotas: percentual na borda, fração no núcleo
------------------------------------------------
O ERPNext guarda alíquota como **percentual** (`18` para 18%), e a apuração exige
**fração** (`0.18`). A conversão acontece aqui, na entrada, e só aqui — mesma disciplina
já aplicada na fronteira do XML, onde a conversão é no sentido inverso.

Por que as linhas de imposto saem como "Actual"
-----------------------------------------------
O ERPNext recalcularia os impostos com o próprio motor se as linhas fossem
`On Net Total`. Como a aritmética brasileira já foi apurada aqui — com composição de
bases que o motor do núcleo não modela —, as linhas são gravadas com `charge_type`
`Actual` e o valor pronto. Assim o ERPNext **usa** o número em vez de recomputá-lo, e o
total do documento não diverge da apuração.
"""

from decimal import Decimal

from erpnext_brasil.fiscal.impostos.apuracao import ApuracaoItem, ItemFiscal, Operacao

__all__ = [
	"CAMPOS_RESULTADO",
	"MARCA_AUTOMATICA",
	"fracao",
	"item_fiscal_de_linha",
	"linhas_de_imposto",
	"operacao_de_documento",
	"percentual",
	"reconciliar_tabela_de_impostos",
	"resultado_para_campos",
]

# Marca as linhas criadas por este app, para distingui-las das lançadas à mão.
MARCA_AUTOMATICA = "br_gerado_automaticamente"

ZERO = Decimal("0.00")
CEM = Decimal("100")

# Campos gravados de volta na linha do item. Declarados aqui para que os campos
# customizados e a gravação não divirjam: a mesma lista alimenta os dois.
CAMPOS_RESULTADO = (
	"br_base_icms",
	"br_valor_icms",
	"br_valor_ipi",
	"br_ipi_na_base_icms",
	"br_base_pis_cofins",
	"br_valor_pis",
	"br_valor_cofins",
	"br_base_ibs_cbs",
	"br_valor_ibs",
	"br_valor_cbs",
)


def fracao(valor) -> Decimal:
	"""Converte percentual do ERPNext em fração. `18` -> `0.18`."""
	if valor in (None, ""):
		return ZERO

	return Decimal(str(valor)) / CEM


def percentual(valor: Decimal) -> Decimal:
	"""Converte fração em percentual do ERPNext. `0.18` -> `18`."""
	return valor * CEM


def _decimal(valor) -> Decimal:
	if valor in (None, ""):
		return ZERO

	return Decimal(str(valor))


def item_fiscal_de_linha(linha: dict) -> ItemFiscal:
	"""Monta um `ItemFiscal` a partir de uma linha de item do ERPNext.

	Usa os campos nativos onde existem (`net_amount`, `discount_amount`) e os
	customizados para o que é fiscal brasileiro. Campo ausente vale zero: uma nota sem
	IPI não deve exigir que o usuário preencha alíquota zero em toda linha.
	"""
	return ItemFiscal(
		valor_produtos=_decimal(linha.get("net_amount") or linha.get("amount")),
		frete=_decimal(linha.get("br_frete")),
		seguro=_decimal(linha.get("br_seguro")),
		outras_despesas=_decimal(linha.get("br_outras_despesas")),
		descontos=_decimal(linha.get("br_desconto_incondicional")),
		aliquota_icms=fracao(linha.get("br_aliquota_icms")),
		reducao_icms=fracao(linha.get("br_reducao_icms")),
		aliquota_ipi=fracao(linha.get("br_aliquota_ipi")),
		imposto_seletivo=_decimal(linha.get("br_imposto_seletivo")),
		aliquota_ibs_uf=fracao(linha["br_aliquota_ibs_uf"])
		if linha.get("br_aliquota_ibs_uf") not in (None, "")
		else None,
		aliquota_ibs_mun=fracao(linha["br_aliquota_ibs_mun"])
		if linha.get("br_aliquota_ibs_mun") not in (None, "")
		else None,
		aliquota_cbs=fracao(linha["br_aliquota_cbs"])
		if linha.get("br_aliquota_cbs") not in (None, "")
		else None,
		cst_ibs_cbs=(linha.get("br_cst_ibs_cbs") or "").strip(),
		classificacao_tributaria=(linha.get("br_cclasstrib") or "").strip(),
	)


def operacao_de_documento(documento: dict) -> Operacao:
	"""Monta a `Operacao` a partir do cabeçalho do documento.

	O indicador de IE do destinatário decide se ele é contribuinte — é o mesmo campo que
	alimenta o `indIEDest` da NF-e, então não há dado novo a cadastrar.
	"""
	indicador = (documento.get("br_indicador_ie") or "").strip()

	return Operacao(
		destinatario_contribuinte=indicador == "Contribuinte ICMS",
		destinado_a_industrializacao_ou_comercio=bool(
			documento.get("br_destinado_a_revenda", True)
		),
		regime_pis_cofins=documento.get("br_regime_pis_cofins") or "cumulativo",
		ano=int(documento["br_ano_competencia"])
		if documento.get("br_ano_competencia")
		else Operacao.ano,
		excluir_icms_de_pis_cofins=bool(documento.get("br_excluir_icms_pis_cofins", True)),
	)


def resultado_para_campos(apuracao: ApuracaoItem) -> dict:
	"""Traduz a apuração nos campos gravados de volta na linha do item."""
	return {
		"br_base_icms": apuracao.base_icms,
		"br_valor_icms": apuracao.icms.valor,
		"br_valor_ipi": apuracao.ipi.valor,
		"br_ipi_na_base_icms": 1 if apuracao.ipi_na_base_do_icms else 0,
		"br_base_pis_cofins": apuracao.pis_cofins.base,
		"br_valor_pis": apuracao.pis_cofins.pis,
		"br_valor_cofins": apuracao.pis_cofins.cofins,
		"br_base_ibs_cbs": apuracao.ibs_cbs.base,
		"br_valor_ibs": apuracao.ibs_cbs.ibs,
		"br_valor_cbs": apuracao.ibs_cbs.cbs,
	}


def linhas_de_imposto(apuracoes: list[ApuracaoItem], contas: dict[str, str]) -> list[dict]:
	"""Monta as linhas da tabela `taxes` a partir da apuração do documento.

	`contas` mapeia o tributo à conta contábil: `{"ICMS": "ICMS a Recolher - _TC", ...}`.
	Tributo sem conta configurada é **omitido**, não gravado numa conta genérica — lançar
	imposto em conta errada é pior que não lançar, porque some na conciliação.

	O ICMS e o PIS/COFINS entram com `included_in_print_rate`, porque são por dentro: já
	estão no preço, e marcá-los assim impede que o ERPNext os some de novo ao total.
	"""
	if not apuracoes:
		return []

	def soma(extrair) -> Decimal:
		return sum((extrair(a) for a in apuracoes), ZERO)

	candidatos = [
		("ICMS", soma(lambda a: a.icms.valor), True),
		("IPI", soma(lambda a: a.ipi.valor), False),
		("PIS", soma(lambda a: a.pis_cofins.pis), True),
		("COFINS", soma(lambda a: a.pis_cofins.cofins), True),
		("IBS", soma(lambda a: a.ibs_cbs.ibs), False),
		("CBS", soma(lambda a: a.ibs_cbs.cbs), False),
	]

	linhas = []

	for tributo, valor, por_dentro in candidatos:
		conta = contas.get(tributo)

		if not conta or valor == ZERO:
			continue

		linhas.append(
			{
				"charge_type": "Actual",
				"account_head": conta,
				"description": tributo,
				"tax_amount": valor,
				"included_in_print_rate": 1 if por_dentro else 0,
			}
		)

	return linhas


def reconciliar_tabela_de_impostos(existentes: list[dict], geradas: list[dict]) -> list[dict]:
	"""Decide a nova tabela de impostos preservando o que o usuário lançou à mão.

	Regra: linhas **sem** a marca automática são de autoria do usuário e sobrevivem
	intactas, na ordem original; as marcadas são descartadas e substituídas pelas recém
	apuradas. Apagar a tabela inteira e regravar destruiria uma linha de frete ou de
	desconto lançada manualmente — e o usuário só perceberia ao conferir o total.

	Está aqui, e não na camada Frappe, para ser testável sem bench: é uma decisão de
	regra, não de persistência.
	"""
	manuais = [linha for linha in existentes if not linha.get(MARCA_AUTOMATICA)]
	novas = [{**linha, MARCA_AUTOMATICA: 1} for linha in geradas]

	return manuais + novas
