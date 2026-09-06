# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Deriva os grupos `transp` e `pag` de um documento do ERPNext.

`montar_infnfe` recusa documento sem esses dois grupos — eles são obrigatórios no XSD,
mesmo quando não há transporte a relatar nem pagamento a destacar. `nfe_documento.py`
deliberadamente não os inventa, e `emissao_nfe.emitir_nfe` os recebe de quem chama. Este
módulo é o "quem chama" padrão: traduz o que o documento **de fato diz** em vez de
adivinhar.

A diferença entre derivar e adivinhar
---------------------------------------------
Derivar é ler um fato registrado: o `Mode of Payment` escolhido, o `Payment Schedule`
preenchido, o campo de frete com valor. Adivinhar é preencher `modFrete="9"` porque nada
foi informado — e `"9"` não é ausência de informação, é a **afirmação** de que não houve
ocorrência de transporte.

Por isso cada função tem uma saída explícita para "o documento não diz": `transp_do_documento`
exige que a modalidade tenha sido escolhida, e `pag_do_documento` cai em `90` (sem
pagamento) **apenas** quando o total do documento é zero — o único caso em que a ausência
de pagamento é dedutível do próprio documento, não suposta.

`Mode of Payment` do ERPNext ≠ `tPag` do leiaute
--------------------------------------------------------
O ERPNext tem um cadastro livre de formas de pagamento, com nomes que o usuário escreve.
O `tPag` é uma tabela fechada de 15 códigos. `FORMA_POR_MODO` cobre os nomes que o
ERPNext cria por padrão; qualquer outro cai em `99` (Outros), que é um código **válido** —
não um erro. Traduzir para `99` é honesto: diz "houve pagamento, de forma que a tabela do
Fisco não distingue". O que seria desonesto é chutar `01` (Dinheiro).

Quem quiser precisão cadastra o código no `Mode of Payment` (campo `br_tpag`), e a
tradução por nome vira só o fallback.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

from decimal import Decimal

import frappe

from erpnext_brasil.fiscal.documento.pagamento import FORMAS_PAGAMENTO, SEM_PAGAMENTO, montar_pag
from erpnext_brasil.fiscal.documento.transporte import montar_transp
from erpnext_brasil.setup.custom_fields import MODALIDADES_FRETE

__all__ = [
	"FORMA_OUTROS",
	"FORMA_POR_MODO",
	"TransporteIndefinido",
	"pag_do_documento",
	"transp_do_documento",
]

ZERO = Decimal("0.00")

FORMA_OUTROS = "99"
"""`tPag` "Outros" — código válido da tabela, não um erro de tradução."""

FORMA_POR_MODO = {
	"Cash": "01",
	"Dinheiro": "01",
	"Cheque": "02",
	"Credit Card": "03",
	"Cartão de Crédito": "03",
	"Debit Card": "04",
	"Cartão de Débito": "04",
	"Bank Draft": "16",
	"Boleto": "15",
	"Boleto Bancário": "15",
	"Pix": "17",
	"PIX": "17",
	"Wire Transfer": "18",
	"Transferência Bancária": "18",
	"Bank Transfer": "18",
}
"""Nome do `Mode of Payment` → `tPag`. Fallback de quem não cadastrou `br_tpag`."""


class TransporteIndefinido(ValueError):
	"""O documento não diz qual é a modalidade do frete, e ela não se supõe."""


def transp_do_documento(doc) -> dict:
	"""O grupo `transp` a partir do documento.

	A modalidade é **obrigatória e não tem padrão**: `"9"` significa "sem ocorrência de
	transporte", uma afirmação sobre a operação. Assumi-la por omissão declararia ao Fisco
	algo que ninguém disse.
	"""
	rotulo = (doc.get("br_modalidade_frete") or "").strip()

	if not rotulo:
		raise TransporteIndefinido(
			f"{doc.doctype} {doc.name} não informa a modalidade do frete. "
			'Ela não tem padrão: "sem ocorrência de transporte" é uma afirmação, não a '
			"ausência de resposta."
		)

	modalidade = MODALIDADES_FRETE.get(rotulo)

	if modalidade is None:
		raise TransporteIndefinido(
			f"modalidade de frete {rotulo!r} não tem modFrete correspondente; "
			f"esperado um de {sorted(MODALIDADES_FRETE)}"
		)

	transportadora = doc.get("br_transportadora")

	if not transportadora:
		return montar_transp(modalidade)

	parte = frappe.get_cached_doc("Supplier", transportadora)

	return montar_transp(
		modalidade,
		transportador_cnpj_cpf="".join(c for c in str(parte.get("tax_id") or "") if c.isalnum()),
		transportador_nome=parte.get("supplier_name") or "",
		transportador_ie=str(parte.get("br_inscricao_estadual") or "").strip(),
	)


def _forma_do_modo(nome: str) -> str:
	"""`tPag` de um `Mode of Payment`: o código cadastrado, o nome conhecido, ou `99`."""
	if not nome:
		return FORMA_OUTROS

	modo = (
		frappe.get_cached_doc("Mode of Payment", nome) if frappe.db.exists("Mode of Payment", nome) else None
	)
	cadastrado = (modo.get("br_tpag") or "").strip() if modo else ""

	if cadastrado in FORMAS_PAGAMENTO:
		return cadastrado

	return FORMA_POR_MODO.get(nome, FORMA_OUTROS)


def pag_do_documento(doc) -> dict:
	"""O grupo `pag` a partir do documento.

	Usa o `Payment Schedule` quando há parcelamento — cada parcela vira um `detPag`, o que
	espelha o que `cobranca_documento` faz do lado das duplicatas. Sem parcelamento, um
	pagamento único pelo total.

	Total zero cai em `90` (sem pagamento). É o **único** caso em que a ausência de
	pagamento é dedutível do documento em vez de suposta: uma remessa sem valor não tem o
	que pagar.
	"""
	total = Decimal(str(doc.get("grand_total") or 0))

	if total == ZERO:
		return montar_pag([{"forma": SEM_PAGAMENTO, "valor": ZERO}])

	parcelas = doc.get("payment_schedule") or []

	if parcelas:
		pagamentos = [
			{
				"forma": _forma_do_modo(parcela.get("mode_of_payment") or doc.get("mode_of_payment")),
				"valor": Decimal(str(parcela.get("payment_amount") or 0)),
			}
			for parcela in parcelas
		]
	else:
		pagamentos = [{"forma": _forma_do_modo(doc.get("mode_of_payment")), "valor": total}]

	return montar_pag(pagamentos)
