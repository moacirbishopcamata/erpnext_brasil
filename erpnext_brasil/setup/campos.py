# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A união dos mapas de campos customizados deste app.

Por que é módulo próprio, e não uma função em `install.py`
-----------------------------------------------------------------
Porque `install.py` importa `frappe`, e **a suíte de costura precisa desta união sem bench**.

Enquanto ela não existia, o teste montava a sua por conta própria — e conhecia só **um** dos
três mapas. O sintoma apareceu no dia em que os campos de folha nasceram: o teste os
reprovou dizendo que não estavam declarados, quando estavam.

> Um teste que constrói o seu próprio universo mede o universo dele, não o do app.

Aqui a união é **dado**, e instalação e teste leem o mesmo dado.

Por que mesclar por DocType
----------------------------------
`Company` aparece em `custom_fields` e em `campos_documento`; `Employee`, em
`campos_folha`. Um `dict.update` faria o segundo mapa **apagar a lista** do primeiro — e o
sintoma seria campo sumindo da instalação sem que ninguém o tivesse removido.

Sem dependência do Frappe.
"""

from erpnext_brasil.setup.campos_documento import get_custom_fields as _campos_documento
from erpnext_brasil.setup.campos_estoque import get_custom_fields as _campos_estoque
from erpnext_brasil.setup.campos_folha import get_custom_fields as _campos_folha
from erpnext_brasil.setup.custom_fields import get_custom_fields as _campos_cadastro

__all__ = ["MAPAS", "todos_os_campos"]

MAPAS = (_campos_cadastro, _campos_documento, _campos_folha, _campos_estoque)
"""As fontes, em ordem de aplicação.

Declarado como tupla para que acrescentar um quarto mapa seja uma linha aqui — e não uma
linha aqui **mais** outra no teste, que foi exatamente como os dois divergiram.
"""


def todos_os_campos() -> dict[str, list[dict]]:
	"""`{DocType: [definições]}` com todos os campos que a instalação aplica."""
	campos: dict[str, list[dict]] = {}

	for mapa in MAPAS:
		for doctype, definicoes in mapa().items():
			campos.setdefault(doctype, []).extend(definicoes)

	return campos
