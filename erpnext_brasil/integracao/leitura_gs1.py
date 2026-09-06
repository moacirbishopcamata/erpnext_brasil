# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Ensina o leitor do estoque a entender etiqueta GS1 — decorando, não substituindo.

O desenho: decorador, não substituto
-------------------------------------------
`erpnext.stock.utils.scan_barcode` já resolve EAN, número de série, lote e armazém, e faz
isso bem. O que ele não sabe é que uma etiqueta GS1-128 **não é um identificador**: é uma
cadeia de elementos, e procurar o texto inteiro nos cadastros não acha nada.

Então este módulo **não reescreve** aquela função. Ele a envolve:

1. a cadeia parece GS1? → separa os elementos e resolve pelo GTIN;
2. não parece, ou o GTIN não está cadastrado? → **delega** ao `scan_barcode` do ERPNext.

Toda melhoria que o ERPNext fizer no resolvedor dele continua valendo. Reimplementar as
quatro buscas aqui criaria uma segunda verdade que envelheceria calada — o mesmo motivo de
não haver `br_taxa_depreciacao` ao lado de `rate_of_depreciation`.

⚠️ O GTIN-14 com zeros e o EAN-13 do cadastro
------------------------------------------------------
O AI (01) é **sempre** GTIN-14, com zeros à esquerda. O `Item Barcode` quase sempre guarda o
EAN-13 impresso na caixa. Procurar os 14 dígitos crus não acha nada, e o estoquista conclui
que o item não está cadastrado quando está.

Por isso a busca tenta as duas formas — com e sem enchimento. É uma linha de código e é a
diferença entre a leitura funcionar e não funcionar no mundo real.

O que se devolve, e por que exatamente estas chaves
--------------------------------------------------------------
`barcode_scanner.js` desestrutura `{ item_code, barcode, batch_no, serial_no, uom,
default_warehouse }`. O contrato é dele, não nosso: devolver um dicionário com outros nomes
faria o leitor bipar, o servidor responder, e **nada acontecer na tela**.

O que a etiqueta traz e o ERPNext não tem onde guardar — validade e data de fabricação —
volta em `br_gs1`, ignorado pelo JS do ERPNext e disponível para quem quiser usar.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

import frappe

from erpnext_brasil.fiscal.gs1 import Gs1Invalido, ler_gs1, parece_gs1

__all__ = ["ler_codigo"]

METODO_DO_ERPNEXT = "erpnext.stock.utils.scan_barcode"
"""O resolvedor que este módulo decora. Trocá-lo de lugar é mudança do ERPNext, não nossa."""


def _delegar(search_value: str, ctx):
	"""Chama o resolvedor do ERPNext, importado aqui dentro de propósito.

	Import tardio porque `erpnext.stock` é de outro app: no topo do arquivo, um site sem
	ERPNext (ou durante um `migrate` que ainda não o carregou) quebraria a importação deste
	módulo inteiro por causa de um caminho que talvez nem seja usado.
	"""
	from erpnext.stock.utils import scan_barcode

	return scan_barcode(search_value, ctx)


def _item_do_gtin(gtin: str, sem_enchimento: str | None):
	"""Procura o GTIN no `Item Barcode`, nas duas formas. `None` quando não achar."""
	formas = [gtin]

	if sem_enchimento and sem_enchimento != gtin:
		formas.append(sem_enchimento)

	for forma in formas:
		achado = frappe.db.get_value(
			"Item Barcode",
			{"barcode": forma},
			["barcode", "parent as item_code", "uom"],
			as_dict=True,
		)

		if achado:
			return achado

	return None


@frappe.whitelist()
def ler_codigo(search_value: str, ctx: dict | str | None = None):
	"""Resolve o que o estoquista leu. Mesma assinatura de `scan_barcode`, de propósito.

	A assinatura é igual porque o `barcode_scanner.js` chama o método pelo nome, com esses
	dois argumentos — divergir exigiria também trocar o JS do ERPNext, e aí não seria mais
	decoração.
	"""
	if not parece_gs1(search_value):
		return _delegar(search_value, ctx)

	try:
		etiqueta = ler_gs1(search_value)
	except Gs1Invalido:
		# Parecia GS1 e não era, ou veio malformada. Ainda pode ser um código que os
		# cadastros do ERPNext conhecem — recusar aqui esconderia uma leitura boa.
		return _delegar(search_value, ctx)

	if not etiqueta.gtin:
		return _delegar(search_value, ctx)

	achado = _item_do_gtin(etiqueta.gtin, etiqueta.gtin_sem_enchimento)

	if not achado:
		return _delegar(search_value, ctx)

	if etiqueta.lote:
		achado["batch_no"] = etiqueta.lote

	if etiqueta.serie:
		achado["serial_no"] = etiqueta.serie

	# Fora do contrato do JS do ERPNext, e é isso mesmo: são os dados que a etiqueta traz e
	# o `Item Barcode` não guarda. Ficam disponíveis sem atrapalhar quem não os espera.
	achado["br_gs1"] = {
		"validade": str(etiqueta.validade) if etiqueta.validade else None,
		"fabricacao": str(etiqueta.fabricacao) if etiqueta.fabricacao else None,
		"quantidade": etiqueta.quantidade,
		"sscc": etiqueta.sscc,
	}

	return achado
