# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Controller do DocType `Lote eSocial` — fino, como o do `Transmissao Fiscal`.

A regra está em `folha/esocial_lote_registro.py`, pura e testada sem bench. Aqui só o
que exige o Frappe.

O método `registrar_retorno` existe porque a tradução do retorno para o registro é a
costura entre duas formas do mesmo dado (`RetornoProcessamentoLote` → `Lote eSocial`), e
costura tem de ficar num lugar só. Quem chama a transmissão não deveria precisar saber
que `cdResposta=203` significa "Em processamento" — `situacao_para_codigo` já sabe.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext_brasil.folha.esocial_lote_registro import (
	LoteInvalido,
	situacao_para_codigo,
	validar_lote,
)


class LoteeSocial(Document):
	def validate(self):
		try:
			validar_lote(self.as_dict())
		except LoteInvalido as e:
			frappe.throw(str(e), title=_("Lote do eSocial inconsistente"))

	def registrar_retorno(self, retorno) -> None:
		"""Grava um `RetornoProcessamentoLote` neste registro.

		Não chama `save()`: quem orquestra decide quando persistir, e um método que
		grava sozinho impediria registrar retorno e outra alteração na mesma transação.
		"""
		self.situacao = situacao_para_codigo(retorno.status.cd_resposta)
		self.codigo_resposta = retorno.status.cd_resposta
		self.descricao_resposta = retorno.status.desc_resposta

		if retorno.dados_recepcao:
			self.protocolo_envio = retorno.dados_recepcao.protocolo_envio

		self.set("eventos", [])

		for evento in retorno.eventos:
			self.append(
				"eventos",
				{
					"id_evento": evento.id_evento,
					"evento_duplicado": 1 if evento.evento_duplicado else 0,
					"xml_retorno": evento.xml_retorno,
				},
			)
