# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê o saldo de estoque do site e produz o Bloco H (inventário) do EFD.

O leiaute já existia em `contabil/efd_bloco_h.py`, com as validações cruzadas do guia;
faltava quem lesse o estoque na data. Esta é essa camada.

O saldo vem do `Bin`, e a data importa
----------------------------------------------
O ERPNext guarda o saldo corrente em `Bin` (por item e depósito) e o histórico em
`Stock Ledger Entry`. Para inventário de **31/12** o que vale é o saldo **naquela data**,
não o de hoje — usar o `Bin` num arquivo gerado em fevereiro declararia o estoque errado.

Por isso a leitura é do razão (`Stock Ledger Entry`), pegando o último lançamento de cada
combinação item+depósito até a data. É mais caro que ler o `Bin` e é o único jeito de
responder à pergunta certa: *quanto havia naquele dia?*

`qty_after_transaction` já é o acumulado — somar os `actual_qty` daria o mesmo número com
mais chance de erro, porque exigiria não perder nenhum lançamento.

Os dois valores do item, de novo
----------------------------------------
`H010` tem `VL_ITEM` (ótica ICMS/IPI) e `VL_ITEM_IR` (ótica do imposto de renda), e a
diferença é o tributo recuperável — o achado documentado em `docs/sped-fiscal.md` e
implementado em `contabil/custo_aquisicao.py`.

Aqui **os dois saem iguais**, e isso é uma limitação declarada: o ERPNext guarda um único
custo de estoque (`stock_value`), que já é o custo contábil. Separar as duas óticas exigiria
saber, por item, quanto de tributo recuperável está embutido — dado que existe na
`Purchase Invoice` mas não sobrevive à valoração do estoque. Preencher `VL_ITEM_IR` com o
mesmo número é dizer "não há exclusão a fazer", que é verdade para quem não credita e falso
para quem credita.

É a limitação mais relevante deste módulo, e por isso está aqui e não numa nota de rodapé.

O que este módulo **não** faz
-------------------------------------
- **Não decide o motivo do inventário.** `MOT_INV` tem seis valores e cinco deles
  dependem de fato que o ERPNext não registra (mudança de tributação, baixa cadastral,
  determinação do Fisco). O padrão é `01` (final do período), e quem precisa de outro
  informa.
- **Não trata `MOT_INV = 06`** (mercadorias sujeitas a ST), que exige um `H030` por item
  com valores médios unitários de ICMS-ST — `montar_bloco_h` inclusive recusa esse motivo.
- **Não filtra por tipo de item.** O guia lista os tipos que entram; o filtro depende do
  `br_efd_tipo_item`, e itens sem ele preenchido entrariam ou sairiam por omissão. Fica
  para quando houver o cadastro completo.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

from decimal import Decimal

import frappe

from erpnext_brasil.contabil.efd_bloco_h import ItemInventario, montar_bloco_h

__all__ = ["bloco_h_do_periodo", "saldos_na_data"]

ZERO = Decimal("0.00")


def _decimal(valor) -> Decimal:
	if valor in (None, ""):
		return ZERO

	return Decimal(str(valor))


def saldos_na_data(company: str, data: str) -> list[ItemInventario]:
	"""O saldo de cada item na data, lido do razão de estoque.

	Itens com saldo **zero** ficam de fora: o guia diz que informá-los é desnecessário, e
	incluí-los inflaria o arquivo sem acrescentar informação. Saldo **negativo** também
	sai — `ItemInventario` o recusaria, e com razão: estoque negativo é inconsistência do
	sistema, não fato a declarar ao Fisco.
	"""
	# Um `Stock Ledger Entry` por item+depósito, o mais recente até a data. `qty_after_
	# transaction` e `stock_value` já são acumulados, então basta o último de cada.
	lancamentos = frappe.db.sql(
		"""
		SELECT sle.item_code, SUM(sle.qty_after_transaction) AS quantidade,
		       SUM(sle.stock_value) AS valor
		FROM `tabStock Ledger Entry` sle
		INNER JOIN (
			SELECT item_code, warehouse, MAX(CONCAT(posting_date, posting_time, name)) AS marca
			FROM `tabStock Ledger Entry`
			WHERE company = %(company)s AND posting_date <= %(data)s AND is_cancelled = 0
			GROUP BY item_code, warehouse
		) ultimo
			ON ultimo.item_code = sle.item_code
			AND ultimo.warehouse = sle.warehouse
			AND CONCAT(sle.posting_date, sle.posting_time, sle.name) = ultimo.marca
		GROUP BY sle.item_code
		""",
		{"company": company, "data": data},
		as_dict=True,
	)

	itens = []

	for linha in lancamentos:
		quantidade = _decimal(linha.quantidade)

		if quantidade <= ZERO:
			continue

		valor = _decimal(linha.valor)
		item = frappe.get_cached_doc("Item", linha.item_code)

		itens.append(
			ItemInventario(
				codigo_item=linha.item_code,
				unidade=item.get("stock_uom") or "",
				quantidade=quantidade,
				valor_unitario=(valor / quantidade).quantize(Decimal("0.000001")),
				valor_item=valor.quantize(Decimal("0.01")),
				# Ver docstring: o ERPNext guarda um custo só, então as duas óticas
				# coincidem. Dizer "não há exclusão" é verdade para quem não credita.
				valor_item_ir=valor.quantize(Decimal("0.01")),
			)
		)

	return sorted(itens, key=lambda i: i.codigo_item)


def bloco_h_do_periodo(company: str, data_final: str) -> list[dict]:
	"""O Bloco H na data de encerramento do período.

	Sem itens em estoque o bloco sai vazio (`IND_MOV = 1`), o que é estado válido e
	diferente de omitir o bloco — `montar_bloco_h` já trata os dois casos.
	"""
	return montar_bloco_h(frappe.utils.getdate(data_final), saldos_na_data(company, data_final))
