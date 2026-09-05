# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê os `Transmissao Fiscal` de um documento e devolve a situação fiscal dele.

Por que a tela precisa disto
----------------------------------
Antes deste módulo, o `Sales Invoice` decidia o que oferecer olhando `br_chave_acesso`: um
campo local, gravado na emissão. Isso basta para saber que **houve** emissão e não basta
para nada além — uma nota cancelada continua com a chave preenchida, então a tela seguia
oferecendo "Cancelar NF-e" para algo já cancelado, e nada dizia ao usuário que o documento
não vale mais.

A situação real não está no documento: está espalhada pelos registros de transmissão, e
depende do **tipo** de cada um (ver `fiscal/documento/situacao_fiscal.py`, onde a regra
vive e é testada sem bench).

Este módulo é só o adaptador: lê o site, monta `RegistroLido`, chama a função pura e
serializa. Nenhuma regra de domínio aqui — se aparecer um `if` decidindo o que vale perante
o Fisco, ele está no arquivo errado.

Permissão
---------------
`frappe.has_permission(..., throw=True)` antes de ler. O método é `@frappe.whitelist()`,
portanto alcançável por qualquer sessão autenticada: sem a checagem, ele contaria quantas
notas um documento teve e devolveria chave e protocolo a quem não pode nem abrir o
documento.
"""

from dataclasses import asdict

import frappe

from erpnext_brasil.fiscal.documento.situacao_fiscal import RegistroLido, situacao_do_documento

__all__ = ["registros_do_documento", "situacao_fiscal"]

CAMPOS_LIDOS = ("name", "tipo", "situacao", "chave_acesso", "protocolo")
"""O que basta para decidir a situação — deliberadamente sem os XML.

Um `Transmissao Fiscal` guarda o XML enviado e o de retorno, que somam centenas de KB. A
tela precisa deles nunca; trazê-los a cada `refresh` de formulário transformaria um
indicador em transferência de megabytes por clique.
"""


def registros_do_documento(doctype: str, name: str) -> list[RegistroLido]:
	"""Os registros de transmissão deste documento, no vocabulário do módulo puro."""
	linhas = frappe.get_all(
		"Transmissao Fiscal",
		filters={"documento_tipo": doctype, "documento": name},
		fields=list(CAMPOS_LIDOS),
		order_by="creation asc",
	)

	return [
		RegistroLido(
			tipo=linha.get("tipo") or "",
			situacao=linha.get("situacao") or "",
			chave_acesso=linha.get("chave_acesso") or "",
			protocolo=linha.get("protocolo") or "",
			nome=linha.get("name") or "",
		)
		for linha in linhas
	]


@frappe.whitelist()
def situacao_fiscal(doctype: str, name: str) -> dict:
	"""Situação fiscal do documento, para a tela.

	Devolve os campos de `SituacaoFiscal` — `situacao`, `chave_acesso`, `protocolo`,
	`registro`, `cartas_de_correcao`, `registros`, `motivos` — mais `emitido` e `vale`,
	que são propriedades e não entram no `asdict`.

	Nunca levanta por ausência de registro: documento sem transmissão é o caso comum, e
	tem resposta própria (`Não emitido`).
	"""
	frappe.has_permission(doctype, "read", doc=name, throw=True)

	situacao = situacao_do_documento(registros_do_documento(doctype, name))

	return {
		**asdict(situacao),
		"motivos": list(situacao.motivos),
		"emitido": situacao.emitido,
		"vale": situacao.vale,
	}
