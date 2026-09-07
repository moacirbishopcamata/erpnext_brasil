# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Dados da tela de navegação pelo endereçamento do estoque.

O que o ERPNext já tem, e por que não bastava
------------------------------------------------------
`Warehouse` **é uma árvore** (`is_tree`, `parent_warehouse`, `lft`/`rgt`) e tem uma visão
nativa, o `warehouse_tree.js`. Ela é excelente para **cadastrar** o endereçamento: cria nó,
renomeia, move.

O que ela não responde é o que o estoquista pergunta, que são duas perguntas e sempre as
mesmas:

1. **"O que tem neste endereço?"** — está de pé na frente da prateleira.
2. **"Onde está este item?"** — tem o produto na mão e precisa guardá-lo ou buscá-lo.

A árvore de cadastro mostra a estrutura e **nenhum saldo**; o relatório de saldo mostra
números e **não deixa navegar**. As duas metades existem separadas, e o operador é que faz a
junção — trocando de tela, no meio do galpão.

De onde vem o saldo
--------------------------
Do `Bin`, que é o saldo **por item e por armazém** já materializado pelo ERPNext
(`actual_qty`, `stock_uom`, `valuation_rate`). Somar `Stock Ledger Entry` daria o mesmo
número por um caminho caro — o `Bin` existe exatamente para não ter de fazer isso.

⚠️ O `Bin` guarda saldo só de armazém **folha**: um armazém-grupo não tem `Bin` próprio.
Por isso o total de um grupo é somado dos descendentes, com `lft`/`rgt` — e não com uma
recursão que faria uma consulta por nó.

Camada de integração: só leitura, sem escrita. A tela navega; quem move estoque são os
documentos do ERPNext.
"""

import frappe

__all__ = ["conteudo_do_endereco", "enderecos_do_item", "filhos_do_endereco"]

LIMITE = 200
"""Teto de linhas por consulta.

Um endereço com milhares de itens travaria a tela do coletor, que costuma ser um aparelho
modesto. Quem precisa da lista inteira usa o relatório de saldo; esta tela é para navegar.
"""


def _empresa(empresa: str | None) -> str | None:
	"""A empresa do filtro, ou a padrão do usuário."""
	return empresa or frappe.defaults.get_user_default("Company")


@frappe.whitelist()
def filhos_do_endereco(pai: str | None = None, empresa: str | None = None) -> list[dict]:
	"""Os armazéns imediatamente abaixo de `pai` — a navegação em si.

	`pai` vazio devolve as raízes. Cada nó já vem com o total de itens distintos abaixo
	dele, para que a tela mostre "onde tem coisa" **antes** de o operador entrar.
	"""
	filtros = {"parent_warehouse": pai or "", "disabled": 0}
	empresa = _empresa(empresa)

	if empresa:
		filtros["company"] = empresa

	nos = frappe.get_all(
		"Warehouse",
		filters=filtros,
		fields=["name", "warehouse_name", "is_group", "warehouse_type", "lft", "rgt"],
		order_by="warehouse_name",
		limit=LIMITE,
	)

	for no in nos:
		no["itens"] = _itens_distintos_abaixo(no["lft"], no["rgt"], empresa)

	return nos


def _itens_distintos_abaixo(lft: int, rgt: int, empresa: str | None) -> int:
	"""Quantos itens distintos existem no nó e em tudo abaixo dele.

	⚠️ Usa `lft`/`rgt` em vez de descer a árvore nó a nó. Numa árvore de endereçamento real
	— rua, prédio, nível, apartamento — a recursão faria centenas de consultas para
	responder o que o *nested set* responde numa.
	"""
	condicoes = ["b.actual_qty != 0", "w.lft >= %(lft)s", "w.rgt <= %(rgt)s"]
	valores = {"lft": lft, "rgt": rgt}

	if empresa:
		condicoes.append("b.company = %(empresa)s")
		valores["empresa"] = empresa

	return (
		frappe.db.sql(
			f"""
			select count(distinct b.item_code)
			from `tabBin` b
			join `tabWarehouse` w on w.name = b.warehouse
			where {" and ".join(condicoes)}
			""",
			valores,
		)[0][0]
		or 0
	)


@frappe.whitelist()
def conteudo_do_endereco(endereco: str, empresa: str | None = None) -> list[dict]:
	""" "O que tem neste endereço?" — a primeira pergunta do estoquista.

	Inclui o que está nos endereços **abaixo** dele: quem está na frente da rua quer saber o
	que a rua tem, não só o que foi lançado no nó-grupo (que, sendo grupo, não tem nada).
	"""
	lft, rgt = frappe.db.get_value("Warehouse", endereco, ["lft", "rgt"]) or (None, None)

	if lft is None:
		frappe.throw(frappe._("Endereço {0} não encontrado").format(endereco))

	empresa = _empresa(empresa)
	condicoes = ["b.actual_qty != 0", "w.lft >= %(lft)s", "w.rgt <= %(rgt)s"]
	valores = {"lft": lft, "rgt": rgt, "limite": LIMITE}

	if empresa:
		condicoes.append("b.company = %(empresa)s")
		valores["empresa"] = empresa

	return frappe.db.sql(
		f"""
		select b.item_code, i.item_name, b.warehouse, b.actual_qty, b.stock_uom
		from `tabBin` b
		join `tabWarehouse` w on w.name = b.warehouse
		join `tabItem` i on i.name = b.item_code
		where {" and ".join(condicoes)}
		order by b.item_code
		limit %(limite)s
		""",
		valores,
		as_dict=True,
	)


@frappe.whitelist()
def enderecos_do_item(item: str, empresa: str | None = None) -> list[dict]:
	""" "Onde está este item?" — a segunda pergunta, e a que mais economiza caminhada.

	Só endereços com saldo diferente de zero: listar prateleira vazia é mandar o operador
	andar até ela para não achar nada.
	"""
	filtros = {"item_code": item, "actual_qty": ("!=", 0)}
	empresa = _empresa(empresa)

	if empresa:
		filtros["company"] = empresa

	return frappe.get_all(
		"Bin",
		filters=filtros,
		fields=["warehouse", "actual_qty", "stock_uom"],
		order_by="actual_qty desc",
		limit=LIMITE,
	)
