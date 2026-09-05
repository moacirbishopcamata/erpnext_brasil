# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Controller do DocType `Numeracao Fiscal`.

Guarda apenas a invariante do registro. A **alocação** — que é onde mora o problema de
concorrência — fica em `integracao/numeracao_fiscal.py`, porque depende de transação e
trava de linha, coisas que não pertencem a um `validate`.
"""

import frappe
from frappe.model.document import Document

from erpnext_brasil.fiscal.documento.numeracao import (
	NUMERO_MAXIMO,
	NumeracaoInvalida,
	validar_serie,
)


class NumeracaoFiscal(Document):
	def validate(self):
		"""Série no formato do XML e contador dentro da faixa do leiaute.

		O contador aceita **zero**, ao contrário do `nNF`: zero aqui significa "nenhum
		número alocado ainda", estado legítimo de uma série recém-criada. O que o leiaute
		recusa é um documento com `nNF` zero, e nenhum documento sai daqui com esse valor
		porque a alocação sempre soma um antes de devolver.
		"""
		try:
			self.serie = validar_serie(self.serie)
		except NumeracaoInvalida as erro:
			frappe.throw(str(erro), title="Série inválida")

		if self.ultimo_numero is None or self.ultimo_numero < 0:
			frappe.throw(
				f"O último número não pode ser negativo, recebido {self.ultimo_numero}",
				title="Contador inválido",
			)

		if self.ultimo_numero > NUMERO_MAXIMO:
			frappe.throw(
				f"O último número passou do máximo do leiaute ({NUMERO_MAXIMO}); "
				"a continuação é abrir uma série nova, não reiniciar a contagem",
				title="Faixa esgotada",
			)
