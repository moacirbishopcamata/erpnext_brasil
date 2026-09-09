# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Gancho de validação: recusa gravar item com classificação incompatível.

Camada mínima de propósito — quatro linhas de decisão. Toda a regra vive em
`fiscal/codigos/compatibilidade.py`, que depende de uma interface e não sabe que este
módulo existe.

O único conhecimento que fica aqui é o que é genuinamente do ERPNext: qual indicador da
tabela oficial corresponde a cada DocType. Isso não é regra fiscal, é mapeamento de
framework.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.codigos.compatibilidade import problemas_dos_itens
from erpnext_brasil.fiscal.codigos_de_erro import (
	DOCUMENTO_CLASSIFICACAO_INCOMPATIVEL,
	formatar,
)
from erpnext_brasil.integracao.repositorio_frappe import repositorio_da_requisicao

INDICADOR_POR_DOCUMENTO = {
	"Sales Invoice": "indNFe",
	"Delivery Note": "indNFe",
	"Purchase Invoice": "indNFe",
	"Purchase Receipt": "indNFe",
}
"""DocType -> indicador de aplicabilidade na Tabela de Classificação Tributária.

⚠️ **Todo DocType ligado a esta validação precisa estar aqui.** A leitura abaixo usa
`.get(doc.doctype, "indNFe")`, e o padrão é o que torna a omissão perigosa: um documento de
cupom que caísse no padrão seria classificado como **nota modelo 55** em vez de **cupom
modelo 65**, e a combinação CST/cClassTrib passaria por uma tabela que não é a dele.

`tests/test_indicador_por_documento.py` compara esta lista com o `doc_events` real do
`hooks.py` — não com o texto dele — e reprova a divergência nos dois sentidos.
"""

INDICADOR_QUANDO_LIGARMOS = {
	"POS Invoice": "indNFCe",
}
"""O indicador que cada DocType **ainda não ligado** deve receber quando for.

`POS Invoice` é o documento de ponto de venda do ERPNext, e é por ele que a NFC-e sairia
para quem usa o POS. Hoje ele não recebe campo fiscal nenhum e não está em `hooks.py`:
a NFC-e do app é emitida a partir de `Sales Invoice` com modelo 65.

Separado do mapa vivo de propósito. A entrada estava misturada com os quatro ligados, e ali
era **inalcançável** — a função nunca recebe um `POS Invoice`. Código inalcançável dentro de
uma estrutura viva é pior que ausência: dá a impressão de que o caso está coberto.

Aqui ela vira o que de fato é — a decisão já tomada para quando o gap for pago, registrada
no lugar onde quem for pagá-lo vai olhar. O gap está em `docs/gaps.md`.
"""


def validar_classificacao_dos_itens(doc, method=None):
	"""Confere CST e cClassTrib de cada item antes de gravar."""
	if not doc.get("items"):
		return

	empresa = doc.get("company")

	if not empresa or frappe.get_cached_value("Company", empresa, "country") != "Brazil":
		return

	mensagens = problemas_dos_itens(
		[linha.as_dict() for linha in doc.items],
		repositorio_da_requisicao(),
		INDICADOR_POR_DOCUMENTO.get(doc.doctype, "indNFe"),
	)

	if mensagens:
		frappe.throw(
			formatar(DOCUMENTO_CLASSIFICACAO_INCOMPATIVEL, "<br>".join(mensagens)),
			title=_("Classificação tributária incompatível"),
		)
