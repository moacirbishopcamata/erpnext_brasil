# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Controller do DocType `Pendencia Nfce` — fino, como o do `Bloqueio Sefaz`.

A regra vive em `fiscal/contingencia_nfce.py`, pura e testada sem bench. Aqui só o que o
Frappe exige, mais duas derivações que não se digitam: o prazo e o sinal de tratamento
humano.

⚠️ O nome da classe **precisa** ser `PendenciaNfce`
---------------------------------------------------------
O Frappe resolve o controller pelo nome do DocType sem espaços, **preservando a caixa**:
`"Pendencia Nfce"` → `PendenciaNfce`. O `PendenciaNFCe` que o bom senso sugere falha, e
falha calado — o framework cai no `Document` genérico, estes métodos **nunca rodam**, e o
registro é gravado sem as derivações. Pior: um `ImportError` aqui faz o `migrate` seguinte
tratar o DocType como órfão e **apagar o registro**. Ver `docs/doctypes.md`.

Por que um registro por documento, e não um por tentativa
----------------------------------------------------------------
A pergunta que a fila faz é *"o que ainda falta autorizar?"*, e ela tem uma resposta por
documento. Um registro por tentativa responderia *"quantas vezes tentamos?"* — que é outra
pergunta, e que aqui cabe num contador.

⚠️ **Por que não é um campo de situação no próprio cupom**: o requisito é sobreviver a
reinício **e** ser consultável por prazo ("quantos, e há quanto tempo"). Campo no documento
atende o primeiro e não o segundo sem varrer todos os cupons — e não teria onde guardar as
tentativas.
"""

import frappe
from frappe.model.document import Document

from erpnext_brasil.fiscal.contingencia_nfce import (
	SituacaoDaPendencia,
	exige_tratamento_humano,
	transmitir_ate,
)


class PendenciaNfce(Document):
	def before_save(self) -> None:
		"""Deriva o prazo e o sinal de tratamento humano.

		Campos derivados, nunca digitados: um prazo digitado à mão divergiria da emissão, e
		a divergência apareceria como pendência vencida que ninguém viu — ou como alerta
		que dispara cedo e é ignorado por isso.
		"""
		if self.emitida_em:
			self.transmitir_ate = transmitir_ate(frappe.utils.get_datetime(self.emitida_em))

		self.exige_tratamento = int(exige_tratamento_humano(self._situacao()))

	def _situacao(self) -> SituacaoDaPendencia:
		"""A situação como valor do domínio.

		⚠️ Um valor fora das opções chega aqui de verdade: `frappe.db.set_value` grava sem
		validar `Select`. Tratar como `PENDENTE` seria a degradação errada — diria "ainda
		vamos tentar" sobre um registro cuja situação ninguém sabe. Falhar alto é o certo,
		porque o dado já está corrompido no banco e o silêncio o esconderia.
		"""
		return SituacaoDaPendencia(self.situacao or SituacaoDaPendencia.PENDENTE.value)
