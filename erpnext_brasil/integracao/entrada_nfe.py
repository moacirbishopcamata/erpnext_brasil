# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Importa o XML da NF-e do fornecedor para um `Purchase Invoice` já criado.

O que este módulo resolve
-------------------------------
`fiscal/documento/leitura_nfe.py` sabe ler a nota; sem um método alcançável, saberia em
vão — o mesmo gap que a emissão teve antes de `emissao_nfe.py`. Aqui a leitura vira ação de
um usuário: anexar o XML e ter a chave de 44 dígitos, o número e a natureza da operação
preenchidos sem ninguém digitar.

Por que **não** cria o documento nem os itens
----------------------------------------------------
Deliberado, e é a decisão central deste módulo.

O código do produto na nota é o **do fornecedor** (`cProd`), não o do comprador. Casá-lo
com o `Item` do site exige uma tabela de correspondência que este app não tem — e adivinhar
por descrição ou por EAN produziria entrada de estoque no item errado, que é dos erros mais
caros de desfazer: contamina custo médio, saldo e a própria escrituração.

Então o módulo preenche o que a nota afirma **sobre si mesma** (chave, número, natureza) e
**confere** o resto, devolvendo divergências para quem decide. Preencher o que não se sabe
seria pior que não preencher.

⚠️ A conferência de destinatário falha alto
--------------------------------------------------
Se o CNPJ do destinatário na nota não é o da `Company` do documento, a importação **para**.
Não é excesso de zelo: escriturar a nota de outra empresa gera crédito indevido de ICMS, e
o erro só apareceria numa fiscalização. Um aviso amarelo seria clicado sem ler.

A comparação é entre dígitos, não entre strings: `12.345.678/0001-99` e `12345678000199`
são o mesmo CNPJ, e o `tax_id` da `Company` costuma vir formatado.
"""

import re

import frappe
from frappe import _

from erpnext_brasil.fiscal.documento.leitura_nfe import ler_nfe

__all__ = ["DestinatarioDivergente", "importar_nfe"]

CAMPOS_PREENCHIDOS = {
	"br_chave_acesso": "chave_acesso",
	"br_numero_nfe": "numero",
	"br_natureza_operacao": "natureza_operacao",
}
"""Campo do `Purchase Invoice` → atributo de `NotaLida`.

Só o que a nota afirma sobre si mesma. Valor, item e imposto ficam de fora — ver a
docstring do módulo.
"""


class DestinatarioDivergente(frappe.ValidationError):
	"""A nota não é para esta empresa."""


def _digitos(valor: str | None) -> str:
	return re.sub(r"\D", "", valor or "")


def _conferir_destinatario(doc, nota) -> None:
	cnpj_da_empresa = _digitos(frappe.db.get_value("Company", doc.company, "tax_id"))
	cnpj_da_nota = _digitos(nota.destinatario.documento)

	if not cnpj_da_empresa:
		frappe.throw(
			_(
				"A empresa {0} não tem CNPJ preenchido — sem ele não dá para conferir se a nota é dela."
			).format(doc.company),
			exc=DestinatarioDivergente,
		)

	if cnpj_da_nota != cnpj_da_empresa:
		frappe.throw(
			_(
				"Esta NF-e é destinada ao CNPJ {0}, e a empresa {1} tem CNPJ {2}. "
				"Escriturar nota de outra empresa gera crédito indevido."
			).format(cnpj_da_nota or _("não informado"), doc.company, cnpj_da_empresa),
			exc=DestinatarioDivergente,
		)


def _divergencias(doc, nota) -> list[str]:
	"""O que não bate entre a nota e o documento — relatado, nunca corrigido em silêncio."""
	achadas = []

	total_do_documento = doc.get("grand_total") or 0

	if total_do_documento and nota.totais.valor_nota != total_do_documento:
		achadas.append(
			_("Total da nota é {0} e o do documento é {1}.").format(
				nota.totais.valor_nota, total_do_documento
			)
		)

	itens_do_documento = len(doc.get("items") or [])

	if itens_do_documento != len(nota.itens):
		achadas.append(
			_("A nota tem {0} item(ns) e o documento tem {1}.").format(len(nota.itens), itens_do_documento)
		)

	if not nota.tem_protocolo:
		achadas.append(_("O XML não traz protocolo de autorização — pode ser um arquivo pré-envio."))

	return achadas


@frappe.whitelist()
def importar_nfe(doctype: str, name: str, xml: str) -> dict:
	"""Lê o XML e preenche o documento com o que a nota afirma sobre si mesma.

	Devolve `{"chave_acesso", "numero", "emitente", "itens", "valor_nota", "divergencias"}`.
	`divergencias` é uma lista de frases para mostrar ao usuário — o módulo não corrige
	nada por conta própria.

	Falha alto quando o destinatário não é a empresa do documento.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")

	nota = ler_nfe(xml)

	_conferir_destinatario(doc, nota)

	for campo, atributo in CAMPOS_PREENCHIDOS.items():
		doc.db_set(campo, getattr(nota, atributo))

	return {
		"chave_acesso": nota.chave_acesso,
		"numero": nota.numero,
		"serie": nota.serie,
		"emitente": nota.emitente.nome,
		"cnpj_emitente": nota.emitente.documento,
		"itens": len(nota.itens),
		"valor_nota": str(nota.totais.valor_nota),
		"divergencias": _divergencias(doc, nota),
	}
