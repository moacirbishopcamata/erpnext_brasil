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

Ainda não é a extração inteira
------------------------------------------------
Só cobre `Delivery Note` (modelo `"55"`, NF-e) — nenhuma fonte de chave de CT-e (modelo `"57"`)
existe ainda no lado de quem contrata o transporte (ver item (4), ainda pendente, de
`docs/integracao-cte-mapeamento.md`).
"""

import frappe

from erpnext_brasil.integracao.mapeamento_cte import ReferenciaDocumentoFiscal

__all__ = ["CteExtracaoInvalida", "referencias_do_shipment"]


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
	codigo = endereco and frappe.db.get_value("Address", endereco, "codigo_municipio_ibge")
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
