# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Sugestão de CFOP em Pedidos de Compra/Venda e Subcontratação.

Fecha a lacuna registrada em `docs/pcp-estado.md`: `fiscal/cfop.py` já sabia
calcular o código certo, mas nenhum documento chamava. Este módulo é a costura —
lê `mesmo_estado` (comparando a UF da empresa com a da outra parte, reaproveitando
`integracao/party.uf_da_parte`) e a finalidade/produção-própria (campos novos no
`Item`, nunca inferidos de outro campo) e escreve o resultado como **sugestão**,
não como valor final.

Dois campos novos no `Item`, propositalmente separados de campos já existentes
------------------------------------------------------------------------------------------
`Item.producao_propria` (venda) e `Item.finalidade_compra` (compra) — nenhum dos
dois reaproveita `br_destinado_a_revenda`/`Operacao.destinado_a_industrializacao_
ou_comercio`, que decide uma coisa diferente (IPI na base do ICMS, consumo final ×
não consumo final). Ver `docs/pcp-estado.md` para o processo que evitou esse erro.

Por que "sugestão" nunca sobrescreve nada de errado aqui
------------------------------------------------------------------------
`br_cfop_sugerido` é um campo só de leitura, recalculado a cada `validate` — não
existe um "valor confirmado pelo usuário" para essa coluna, então recalcular
sempre é seguro (diferente de um campo que o usuário edita e salva, que uma
sugestão jamais deveria pisar). Sem dado suficiente (item sem `producao_propria`
marcado, ou sem `finalidade_compra` escolhida, ou UF que não pôde ser
determinada), o campo fica vazio — nunca um CFOP inventado.

Subcontratação usa uma regra mais simples: não depende de nenhum campo do Item
------------------------------------------------------------------------------------------
`Subcontracting Order` (remessa) e `Subcontracting Receipt` (retorno) usam
`cfop_remessa_para_industrializacao`/`cfop_retorno_de_industrializacao` — só
precisam de `mesmo_estado`, sem finalidade nem produção própria (o insumo enviado
para industrializar não é nem venda nem compra no sentido comercial).

Estado de verificação: não exercitado contra um bench real
------------------------------------------------------------------------
Mesma situação de `integracao/documento.py`/`integracao/party.py`: depende do
Frappe, sem bench disponível nesta sessão — a regra pura (`fiscal/cfop.py`) está
testada exaustivamente sem bench, esta camada não.
"""

import frappe

from erpnext_brasil.fiscal.cfop import (
	FINALIDADE_COMERCIALIZACAO,
	FINALIDADE_INDUSTRIALIZACAO,
	cfop_compra,
	cfop_retorno_de_industrializacao,
	cfop_remessa_para_industrializacao,
	cfop_venda,
)
from erpnext_brasil.integracao.party import uf_da_parte

__all__ = ["sugerir_cfop_compra_venda", "sugerir_cfop_subcontratacao"]

# doctype do documento -> (campo da outra parte, doctype da outra parte, "compra"|"venda")
_DOCUMENTOS_COMPRA_VENDA = {
	"Sales Order": ("customer", "Customer", "venda"),
	"Sales Invoice": ("customer", "Customer", "venda"),
	"Delivery Note": ("customer", "Customer", "venda"),
	"Purchase Order": ("supplier", "Supplier", "compra"),
	"Purchase Invoice": ("supplier", "Supplier", "compra"),
	"Purchase Receipt": ("supplier", "Supplier", "compra"),
}

_MAPA_FINALIDADE_COMPRA = {
	"Industrialização": FINALIDADE_INDUSTRIALIZACAO,
	"Comercialização": FINALIDADE_COMERCIALIZACAO,
}


def _mesmo_estado(doc, campo_parte: str, doctype_parte: str) -> bool | None:
	"""`None` quando a UF de qualquer um dos dois lados não pôde ser determinada —
	nunca assume `mesmo_estado` por omissão."""
	nome_parte = doc.get(campo_parte)

	if not nome_parte or not doc.get("company"):
		return None

	uf_empresa = uf_da_parte(frappe.get_cached_doc("Company", doc.company))
	uf_parte = uf_da_parte(frappe.get_cached_doc(doctype_parte, nome_parte))

	if not uf_empresa or not uf_parte:
		return None

	return uf_empresa == uf_parte


def sugerir_cfop_compra_venda(doc, method=None):
	"""`doc_event` de `validate` para pedidos/documentos de compra e venda —
	escreve `br_cfop_sugerido` em cada linha de item, quando há dado suficiente."""
	config = _DOCUMENTOS_COMPRA_VENDA.get(doc.doctype)

	if not config:
		return

	campo_parte, doctype_parte, direcao = config
	mesmo_estado = _mesmo_estado(doc, campo_parte, doctype_parte)

	if mesmo_estado is None:
		return

	for linha in doc.get("items", []):
		item = frappe.get_cached_doc("Item", linha.item_code) if linha.get("item_code") else None

		if not item:
			continue

		if direcao == "venda":
			producao_propria = item.get("producao_propria")

			if producao_propria is None:
				continue

			linha.br_cfop_sugerido = cfop_venda(mesmo_estado=mesmo_estado, producao_propria=bool(producao_propria))
		else:
			finalidade_bruta = item.get("finalidade_compra")
			finalidade = _MAPA_FINALIDADE_COMPRA.get(finalidade_bruta)

			if not finalidade:
				continue

			linha.br_cfop_sugerido = cfop_compra(mesmo_estado=mesmo_estado, finalidade=finalidade)


def sugerir_cfop_subcontratacao(doc, method=None):
	"""`doc_event` de `validate` para `Subcontracting Order`/`Subcontracting
	Receipt` — não depende de campo nenhum do `Item`, só de `mesmo_estado`."""
	if not doc.get("supplier") or not doc.get("company"):
		return

	mesmo_estado = _mesmo_estado(doc, "supplier", "Supplier")

	if mesmo_estado is None:
		return

	if doc.doctype == "Subcontracting Order":
		cfop = cfop_remessa_para_industrializacao(mesmo_estado=mesmo_estado)
	elif doc.doctype == "Subcontracting Receipt":
		cfop = cfop_retorno_de_industrializacao(mesmo_estado=mesmo_estado)
	else:
		return

	for linha in doc.get("items", []):
		linha.br_cfop_sugerido = cfop
