# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Controller do DocType `Bloqueio Sefaz` — fino, como o do `Transmissao Fiscal`.

A regra de tempo está em `fiscal/consumo_indevido.py`, pura e testada sem bench. Aqui fica
só o que o Frappe exige, mais uma derivação: `liberado_em` é calculado do início, nunca
digitado.

⚠️ O nome da classe **precisa** ser `BloqueioSefaz`
--------------------------------------------------------
O Frappe resolve o controller pelo nome do DocType sem espaços. Errar o nome não levanta
erro: o framework cai no `Document` genérico, os `hooks` de documento deste arquivo
**nunca rodam**, e o registro é gravado sem a derivação — silenciosamente errado. Já
mordeu este projeto antes; está em `docs/doctypes.md`.

Por que um registro por `(CNPJ, ambiente)`, e não um por rejeição
------------------------------------------------------------------------
Porque a pergunta que o app faz é *"posso transmitir agora?"*, e ela tem uma resposta só
por par. Um histórico de rejeições responderia *"quantas vezes fui bloqueado?"*, que é
outra pergunta — e teria de ser varrido por data toda vez, em vez de lido por chave.

O histórico não se perde: `track_changes` guarda cada atualização em `Version`.
"""

import frappe
from frappe.model.document import Document

from erpnext_brasil.fiscal.consumo_indevido import CARENCIA


class BloqueioSefaz(Document):
	def before_save(self) -> None:
		"""Deriva `liberado_em` do início.

		Campo derivado e não digitado: dois campos de data independentes divergiriam, e a
		divergência apareceria como uma emissão liberada cedo demais — que custa outra hora
		de bloqueio.
		"""
		if self.bloqueado_em:
			self.liberado_em = frappe.utils.get_datetime(self.bloqueado_em) + CARENCIA
