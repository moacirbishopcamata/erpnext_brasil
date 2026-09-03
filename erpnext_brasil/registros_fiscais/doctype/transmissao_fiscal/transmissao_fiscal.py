# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Controller do DocType `Transmissao Fiscal` — deliberadamente fino.

Toda a regra de "o que é um registro coerente" está em
`fiscal/documento/transmissao_registro.py`, pura e testada sem bench. Aqui fica só o que
exige o Frappe: receber o `Document`, entregar seus campos à regra e traduzir a exceção
em `frappe.throw`.

Por que este módulo não está em `fiscal/`
------------------------------------------------
O DocType precisa morar num módulo declarado em `modules.txt`, e seu controller importa
`frappe` por definição do framework. Colocá-lo em `fiscal/` violaria a regra de camada
pura — que `tests/test_arquitetura.py` verifica de verdade. O framework exige *um*
módulo, não exige que seja aquele: daí o módulo `Registros Fiscais`, que existe para
guardar o que precisa de banco, deixando `fiscal/` intacto.

É o caso exato de "ceder só onde o framework impede": não dá para ter DocType sem
controller que importe `frappe`, mas dá para escolher onde ele mora.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext_brasil.fiscal.documento.transmissao_registro import (
	RegistroInvalido,
	validar_registro,
)


class TransmissaoFiscal(Document):
	def validate(self):
		"""Delega à regra pura; só a tradução do erro é responsabilidade daqui."""
		try:
			validar_registro(self.as_dict())
		except RegistroInvalido as e:
			frappe.throw(str(e), title=_("Transmissão fiscal inconsistente"))
