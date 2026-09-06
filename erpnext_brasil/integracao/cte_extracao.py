# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Extração de referências fiscais a partir de `Shipment`, para `mapeamento_cte.py`.

Fecha o item (3) pendente de `docs/integracao-cte-mapeamento.md`
------------------------------------------------------------------------------
Com `br_chave_acesso` existindo em `Delivery Note` (`docs/integracao-chave-acesso.md`), a
extração real passa a ter de onde ler. `referencias_do_shipment` percorre `Shipment` →
`Shipment Delivery Note` (tabela filha) → `Delivery Note` → `br_chave_acesso`, e resolve o
município de descarga a partir do `Address` de entrega do `Shipment` — devolve uma lista de
`ReferenciaDocumentoFiscal`, pronta para `mapeamento_cte.agrupar_por_municipio_descarga`.

Município vem do endereço de entrega do `Shipment`, não de cada `Delivery Note`
------------------------------------------------------------------------------------------
Decisão deliberada, não descuido: um `Shipment` pode agrupar vários `Delivery Note` — a viagem
tem um único destino físico (o MDF-e representa a viagem, não cada nota isoladamente, mesmo
raciocínio que motivou `fiscal.mdfe_rodoviario` a modelar veículo/motorista no MDF-e e não no
CT-e). Usar o endereço de cada `Delivery Note` individualmente arriscaria fragmentar um único
descarregamento físico em municípios diferentes por causa de cadastro divergente entre notas do
mesmo carregamento.

Falha alta quando falta o código IBGE, não silenciosa
------------------------------------------------------------------------------
Se existe ao menos uma `Delivery Note` com `br_chave_acesso` preenchida mas o endereço de
entrega do `Shipment` não tem `codigo_municipio_ibge`, este módulo levanta erro em vez de
descartar a referência em silêncio — perder um documento fiscal do `infDoc` sem avisar é o tipo
de bug que só apareceria na rejeição da SEFAZ (mesma disciplina de "falhar alto" já aplicada a
`fiscal.mdfe.montar_infdoc`/`montar_ide` em todo o projeto).

Item (4) fechado em seguida: `referencia_cte_do_documento_frete`
------------------------------------------------------------------------------
Fecha o item (4) pendente de `docs/integracao-cte-mapeamento.md` — o lado de quem
**contrata** o transporte (a empresa recebe um CT-e da transportadora, não emite um).
**Achado real, verificado antes de implementar**: `Shipment` (core do ERPNext,
`erpnext/stock/doctype/shipment/shipment.json`, lido diretamente) **não tem** nenhum
campo que vincule um `Purchase Invoice` de frete — `carrier` é texto livre (nome do
transportador para APIs de courier externas), `pickup_supplier`/`delivery_supplier` não
amarram fatura nenhuma. Diferente de `referencias_do_shipment` (que tem de onde partir,
`Shipment Delivery Note`), não existe uma relação de doctype pronta para percorrer do
lado do CT-e — inventar uma seria supor uma estrutura de dados que o ERPNext não tem.

Por isso `referencia_cte_do_documento_frete` opera sobre um `Purchase Invoice` já
identificado como fatura de frete (decisão de quem chama, não deste módulo) e faz a
parte que é responsabilidade de uma extração: ler `br_chave_acesso`, decompor via
`ler_chave` e **recusar** se a chave não for modelo `"57"` — mesma defesa em
profundidade já aplicada em `infEntrega`/`infDoc` em todo o projeto (um `Purchase
Invoice` de frete com uma chave de NF-e colada por engano é exatamente o tipo de erro
que essa checagem existe para pegar).
"""

import frappe

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.integracao.mapeamento_cte import ReferenciaDocumentoFiscal

__all__ = ["CteExtracaoInvalida", "referencia_cte_do_documento_frete", "referencias_do_shipment"]


class CteExtracaoInvalida(ValueError):
	"""Dado insuficiente no ERPNext para montar uma referência de `infDoc` — nunca
	descartado em silêncio."""


def referencias_do_shipment(shipment) -> list[ReferenciaDocumentoFiscal]:
	"""Extrai as referências de NF-e vinculadas a um `Shipment` já carregado.

	Devolve lista vazia quando o `Shipment` não tem nenhuma `Delivery Note` com
	`br_chave_acesso` preenchida — não é erro, é o estado normal antes da emissão da
	NF-e (mesma disciplina de `br_cfop_sugerido` ficar vazio sem dado suficiente, em
	vez de inventar).
	"""
	chaves = []

	for linha in shipment.get("shipment_delivery_note") or []:
		if not linha.get("delivery_note"):
			continue

		chave = frappe.db.get_value("Delivery Note", linha.delivery_note, "br_chave_acesso")

		if chave:
			chaves.append(chave)

	if not chaves:
		return []

	endereco = shipment.get("delivery_address_name")
	codigo = endereco and frappe.db.get_value("Address", endereco, "br_codigo_municipio_ibge")
	nome = endereco and frappe.db.get_value("Address", endereco, "city")

	if not codigo or not nome:
		raise CteExtracaoInvalida(
			f"Shipment {shipment.name} tem {len(chaves)} NF-e com chave de acesso, mas o "
			f"endereço de entrega não tem código IBGE do município cadastrado — não é "
			f"possível montar infDoc sem saber o município de descarga."
		)

	return [
		ReferenciaDocumentoFiscal(chave=chave, modelo="55", municipio_codigo=codigo, municipio_nome=nome)
		for chave in chaves
	]


def referencia_cte_do_documento_frete(
	purchase_invoice, municipio_codigo: str, municipio_nome: str
) -> ReferenciaDocumentoFiscal | None:
	"""Extrai a referência de CT-e de um `Purchase Invoice` já identificado como
	fatura de frete (decisão de quem chama — este módulo não descobre isso sozinho,
	ver docstring do módulo).

	Devolve `None` quando `br_chave_acesso` está vazio — não é erro, é o estado
	normal antes de a fatura de frete ter a chave preenchida (mesma disciplina de
	`referencias_do_shipment` devolver lista vazia). `municipio_codigo`/
	`municipio_nome` não são derivados daqui — o `Purchase Invoice` sozinho não
	amarra a viagem/`Shipment` a que o frete se refere (achado real, ver docstring do
	módulo); é responsabilidade de quem chama sabê-los.
	"""
	chave = purchase_invoice.get("br_chave_acesso")

	if not chave:
		return None

	decomposta = ler_chave(chave)

	if decomposta.modelo != "57":
		raise CteExtracaoInvalida(
			f"Purchase Invoice {purchase_invoice.name} tem br_chave_acesso de modelo "
			f"{decomposta.modelo} ({decomposta.documento}), mas uma fatura de frete "
			f"referencia um CT-e (modelo 57)."
		)

	return ReferenciaDocumentoFiscal(
		chave=decomposta.valor, modelo="57", municipio_codigo=municipio_codigo, municipio_nome=municipio_nome
	)
