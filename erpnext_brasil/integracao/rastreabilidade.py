# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Rastreabilidade fiscal: liga o `Batch` do ERPNext ao grupo `rastro` da NF-e.

A pergunta do usuário era "rastreabilidade fiscal, existe?". A resposta era **meia**: a
regra pura existia (`fiscal/documento/produto.montar_rastro`, com o limite de 500 lotes
por item e a validação dos campos), mas **nada a alimentava**. Mesmo achado do grupo
`cobr`: o dado já está no ERPNext, íntegro, e não estava sendo aproveitado.

Os campos batem um a um — não é adaptação, é tradução
--------------------------------------------------------------
| ERPNext (`Batch`) | NF-e (`rastro`) |
|---|---|
| `batch_id` | `nLote` |
| `manufacturing_date` | `dFab` |
| `expiry_date` | `dVal` |
| quantidade da linha | `qLote` |

Nenhum campo novo a cadastrar. Quem já usa lote no ERPNext — porque controla validade,
ou porque o produto exige — já tem a rastreabilidade fiscal pronta; faltava traduzi-la.

Quando `rastro` é obrigatório, e por que isso não é decidido aqui
--------------------------------------------------------------------------
O grupo é exigido para medicamentos (Lei 11.903/2009), bebidas, água, e produtos sujeitos
a controle sanitário — a lista muda por norma. Este módulo **não decide** se o item
precisa: monta quando há lote, e omite quando não há. Quem sabe se a obrigação se aplica
é o cadastro do produto, não a camada de integração — e inventar aqui uma lista de NCM
"que precisa de rastro" seria criar regra fiscal sem fonte, exatamente o que o projeto
não faz.

`rastro` e SNCM são coisas diferentes
--------------------------------------------
Já registrado em `produto.py`: o Sistema Nacional de Controle de Medicamentos (o
DataMatrix da caixa) **não alimenta** `rastro`, e vice-versa. São duas obrigações com
dados próprios que se parecem. Este módulo trata só de `rastro`.

Sem teste dedicado — depende do Frappe; a regra que importa está em
`fiscal/documento/produto.py`, testada sem bench.
"""

__all__ = ["LIMITE_DE_LOTES_POR_ITEM", "montar_rastro_da_linha"]

LIMITE_DE_LOTES_POR_ITEM = 500
"""`maxOccurs="500"` no layout da NF-e — o mesmo limite que `produto.py` já conhece."""


def _data_iso(valor) -> str:
	"""`TData` do XSD é AAAA-MM-DD. O Frappe entrega `date` ou texto ISO; os dois já
	dão o formato certo, então não há conversão de fuso a fazer — e fazer uma seria
	arriscar mudar o dia."""
	if not valor:
		return ""

	return valor.isoformat() if hasattr(valor, "isoformat") else str(valor)[:10]


def montar_rastro_da_linha(linha) -> list[dict]:
	"""Traduz o lote de uma linha de item no grupo `rastro` da NF-e.

	Devolve lista (o grupo é repetível) **vazia** quando a linha não tem lote — ausência
	é o caso comum e não é erro: a maioria dos produtos não é rastreada.

	Uma linha do ERPNext carrega **um** `batch_no`. A lista existe porque o layout
	permite vários lotes por item, o que acontece quando uma mesma linha é atendida por
	lotes diferentes — situação que o ERPNext representa em outra estrutura (o
	`Serial and Batch Bundle`), ainda não coberta aqui. Devolver lista desde já evita
	mudar a assinatura quando esse caso for tratado.
	"""
	import frappe

	from erpnext_brasil.fiscal.documento.produto import montar_rastro

	numero_lote = linha.get("batch_no")

	if not numero_lote:
		return []

	lote = frappe.db.get_value(
		"Batch", numero_lote, ["batch_id", "manufacturing_date", "expiry_date"], as_dict=True
	)

	if not lote:
		return []

	fabricacao = _data_iso(lote.get("manufacturing_date"))
	validade = _data_iso(lote.get("expiry_date"))

	if not fabricacao or not validade:
		# `montar_rastro` exige as duas datas, e com razão: lote sem validade não
		# rastreia nada. Falhar aqui seria impedir a emissão por causa de um cadastro
		# incompleto que talvez nem precise de rastro — quem valida a obrigatoriedade é
		# `prontidao_fiscal`, com mensagem que diz o que preencher.
		return []

	return [
		montar_rastro(
			numero_lote=lote.get("batch_id") or numero_lote,
			quantidade_lote=linha.get("qty"),
			data_fabricacao=fabricacao,
			data_validade=validade,
		)
	]
