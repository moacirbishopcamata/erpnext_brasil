# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê estoque e produção do site e produz o Bloco K do EFD.

Quarto e último bloco a ganhar leitura do site. O leiaute está em
`contabil/efd_bloco_k.py`, com os três achados que o guia esconde — precisão diferente
entre saldo e movimentação, tipos de item distintos por registro, e um campo que não deve
ser preenchido.

Reaproveita o inventário, e isso não é economia
--------------------------------------------------------
O `K200` (estoque escriturado) e o `H010` (inventário) respondem à **mesma pergunta**:
quanto havia de cada item na data final. Calcular duas vezes produziria dois números que
podem divergir — e um arquivo em que o Bloco H e o Bloco K discordam sobre o mesmo estoque
é rejeitado, com o agravante de que descobrir qual dos dois está errado exige refazer as
duas contas.

Por isso `saldos_na_data` (de `efd_inventario`) é a **única** fonte, e este módulo converte
o resultado. A conversão não é livre de conteúdo: o `H010` usa três casas decimais no
saldo e o `K200` também três, mas o `K220`/`K230`/`K235` usam **seis** —
`arredondar_quantidade` existe justamente para essa fronteira.

Produção: `Work Order` é a ordem, `Stock Entry` é o que aconteceu
--------------------------------------------------------------------------
O `K230` pede a **produção acabada** e o `K235` o **consumo de insumos**, ambos vinculados
à ordem. No ERPNext a ordem é a `Work Order` e o movimento real é o `Stock Entry` do tipo
`Manufacture` — e é o movimento que vale, porque uma ordem planejada e não executada não
produziu nada.

O `Stock Entry` de manufatura tem itens com depósito de origem (consumo) e de destino
(produção): linha com `t_warehouse` e sem `s_warehouse` é o **que saiu pronto**; o
inverso é insumo. Ler os dois lados de um mesmo documento é o que liga `K230` e `K235`
sem depender de a `Work Order` estar corretamente encerrada.

O que este módulo **não** faz
-------------------------------------
- **Não emite `K220`** (movimentação interna entre mercadorias). Exige saber que uma
  transferência foi **reclassificação de código**, e não simples mudança de depósito — o
  `Stock Entry` do tipo `Material Transfer` não distingue as duas.
- **Não emite `K210`/`K215`, `K250`-`K302`.** Desmontagem, industrialização por terceiros,
  reprocessamento, correção de apontamento e produção conjunta; cada um pede seu próprio
  incremento verificado.
- **Não decide o tipo de leiaute.** `K010` admite simplificado, completo e restrito a
  saldos, e a escolha é do contribuinte, condicionada ao Ajuste SINIEF 02/09. O padrão é
  completo, que é o que exige mais e portanto nunca informa a menos.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

from decimal import Decimal

import frappe

from erpnext_brasil.contabil.efd_bloco_k import (
	DECIMAIS_MOVIMENTACAO,
	DECIMAIS_SALDO,
	EstoqueEscriturado,
	InsumoConsumido,
	ItemProduzido,
	arredondar_quantidade,
	montar_bloco_k,
	montar_k230,
	montar_k235,
	montar_k990,
)
from erpnext_brasil.integracao.efd_inventario import saldos_na_data

__all__ = ["bloco_k_do_periodo", "estoques_escriturados", "producao_do_periodo"]

ZERO = Decimal("0.00")

TIPO_MANUFATURA = "Manufacture"


def estoques_escriturados(company: str, data_final: str) -> list[EstoqueEscriturado]:
	"""Converte o inventário em `K200`.

	Fonte única com o Bloco H — ver docstring do módulo sobre por que não se calcula duas
	vezes.
	"""
	data = frappe.utils.getdate(data_final)

	return [
		EstoqueEscriturado(
			data_estoque=data,
			codigo_item=item.codigo_item,
			quantidade=arredondar_quantidade(item.quantidade, DECIMAIS_SALDO),
		)
		for item in saldos_na_data(company, data_final)
	]


def producao_do_periodo(company: str, data_inicial: str, data_final: str) -> list[dict]:
	"""Os pares `K230`/`K235` dos `Stock Entry` de manufatura do período.

	Cada documento vira **um** `K230` por item produzido, seguido dos `K235` dos insumos
	daquele documento. O leiaute é hierárquico (o `K235` é filho do `K230`), e emitir os
	consumos soltos os desvincularia da produção que os justifica.
	"""
	nomes = frappe.get_all(
		"Stock Entry",
		filters={
			"company": company,
			"posting_date": ["between", [data_inicial, data_final]],
			"docstatus": 1,
			"stock_entry_type": TIPO_MANUFATURA,
		},
		pluck="name",
		order_by="posting_date, name",
	)

	linhas: list[dict] = []

	for nome in nomes:
		documento = frappe.get_doc("Stock Entry", nome)
		data_saida = frappe.utils.getdate(documento.posting_date)

		produzidos = [linha for linha in documento.items if linha.t_warehouse and not linha.s_warehouse]
		consumidos = [linha for linha in documento.items if linha.s_warehouse and not linha.t_warehouse]

		for produzido in produzidos:
			linhas.append(
				montar_k230(
					ItemProduzido(
						codigo_item=produzido.item_code,
						quantidade=arredondar_quantidade(
							Decimal(str(produzido.qty or 0)), DECIMAIS_MOVIMENTACAO
						),
						# A ordem de produção só entra quando existe: o `K230` exige os três
						# campos juntos ou nenhum, e `ItemProduzido` recusa metade.
						**_dados_da_ordem(documento),
					)
				)
			)

			# Os insumos pendurados no primeiro produzido: sem `Work Order` não há como
			# ratear consumo entre dois produtos do mesmo documento, e dividir por conta
			# própria inventaria uma proporção que ninguém declarou.
			if produzido is produzidos[0]:
				linhas.extend(
					montar_k235(
						InsumoConsumido(
							data_saida=data_saida,
							codigo_item=consumido.item_code,
							quantidade=arredondar_quantidade(
								Decimal(str(consumido.qty or 0)), DECIMAIS_MOVIMENTACAO
							),
						)
					)
					for consumido in consumidos
				)

	return linhas


def _dados_da_ordem(documento) -> dict:
	"""Os três campos de ordem de produção — juntos ou nenhum.

	`ItemProduzido` recusa `DT_INI_OP` sem `COD_DOC_OP` e vice-versa, porque o leiaute
	exige o conjunto. Sem `Work Order` no `Stock Entry`, a produção é apontada por período,
	que é o caso previsto no guia.
	"""
	ordem = documento.get("work_order")

	if not ordem:
		return {}

	inicio = frappe.db.get_value("Work Order", ordem, "actual_start_date")

	if not inicio:
		return {}

	fim = frappe.db.get_value("Work Order", ordem, "actual_end_date")

	return {
		"codigo_ordem_producao": ordem,
		"data_inicio_op": frappe.utils.getdate(inicio),
		# Ordem não encerrada fica com `DT_FIN_OP` em branco, que é informação e não
		# omissão: significa produção em elaboração no fim do período.
		"data_fim_op": frappe.utils.getdate(fim) if fim else None,
	}


def bloco_k_do_periodo(company: str, data_inicial: str, data_final: str) -> list[dict]:
	"""O Bloco K do período: saldos escriturados mais produção.

	`montar_bloco_k` monta o recorte de saldos (`K001`/`K010`/`K100`/`K200`/`K990`); os
	`K230`/`K235` entram **antes** do `K990`, e a contagem do encerramento é refeita —
	o encerramento conta as linhas do bloco, e acrescentar registros depois de montá-lo
	deixaria o número errado.
	"""
	base = montar_bloco_k(
		frappe.utils.getdate(data_inicial),
		frappe.utils.getdate(data_final),
		estoques_escriturados(company, data_final),
	)

	producao = producao_do_periodo(company, data_inicial, data_final)

	if not producao:
		return base

	# `base[-1]` é o `K990` original; ele sai e volta com a contagem certa.
	linhas = [*base[:-1], *producao]

	return [*linhas, montar_k990(len(linhas) + 1)]
