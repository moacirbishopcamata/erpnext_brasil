# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Controller da tabela filha `Evento do Lote eSocial`.

Existe porque o Frappe **exige** o módulo, mesmo para tabela filha sem comportamento:
`load_doctype_module` importa `<doctype>.py` em todo `on_doctype_update`, e a ausência
derruba o `bench migrate` inteiro com "Module import failed ... the DocType you're trying
to open might be deleted".

Foi assim que o gap apareceu, em 2026-09-04: o DocType tinha JSON e `__init__.py`, o teste
puro não olha para isso, e o erro só surgiu na primeira migração num site real. É o mesmo
formato dos 31 campos de `docs/gaps.md` — arquivo declarado, nada verificando que o site
o aceita.

Sem `validate` próprio: a validação do lote é do **pai** (`Lote eSocial`), que conhece o
conjunto de eventos e a coerência entre situação e protocolo. Uma linha isolada não tem
invariante que se possa afirmar sem esse contexto — e inventar uma aqui produziria regra
que o pai teria de contornar.
"""

from frappe.model.document import Document


class EventoDoLoteESocial(Document):
	pass
