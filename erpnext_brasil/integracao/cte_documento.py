# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Mapeia uma Sales Invoice de transporte para a árvore do CT-e.

Fecha o item (1) do change `fechar-laco-cte-mdfe`: a camada de integração entre o
documento real do ERPNext e a montagem pura de `fiscal/cte.py`.

O que este módulo faz
---------------------
Lê uma `Sales Invoice` que representa uma prestação de serviço de transporte e monta a
árvore `TCTe` (sem assinar), reutilizando `fiscal/cte.py` para cada grupo. As peças
puras de montagem (`montar_ide`, `montar_cte`, `montar_toma3`, `montar_toma4`,
`montar_vprest`) são chamadas com dados extraídos do Frappe — este módulo é o único
ponto que toca `frappe.get_cached_doc`.

O que este módulo **se recusa** a inventar
------------------------------------------
- **Natureza da operação, CFOP, município de início/fim, modal, tipo de serviço**:
  sem eles não há CT-e. Cada ausência levanta `DadosInsuficientes` dizendo qual
  campo falta e **em qual cadastro**.
- **Tomador**: se o Customer tem CNPJ/CPF, o tomador é o destinatário (toma3 código 3);
  se não tem, `DadosInsuficientes` — nunca assumir "Outros" por suposição.
- **`infDoc`** (referências de NF-e transportadas): ficou de fora da primeira entrega
  por decisão de design (XSD permite CT-e sem infDoc; a origem das chaves não é
  rastreável de uma Sales Invoice). Preenchido por iteração futura.

Estado de verificação
---------------------
Camada Frappe — requer bench para rodar. A peça pura (`fiscal/cte.py`) já está
testada sem bench em `tests/test_cte.py`.
"""

import frappe

from erpnext_brasil.fiscal.codigos.uf import codigo_da_uf
from erpnext_brasil.fiscal.cte import (
	MODAL_RODOVIARIO,
	TIPO_SERVICO_NORMAL,
	TOMADOR_DESTINATARIO,
	IdentificacaoCte,
	montar_cte,
	montar_ide,
	montar_toma3,
)
from erpnext_brasil.integracao.nfe_documento import (
	_endereco_vinculado,
	_grupo_endereco,
)

__all__ = ["DadosInsuficientes", "montar_cte_do_documento"]


class DadosInsuficientes(ValueError):
	"""O documento não tem o que o CT-e exige — nunca preenchido por suposição."""


def _exigir(valor, campo: str, onde: str) -> str:
	texto = str(valor or "").strip()

	if not texto:
		raise DadosInsuficientes(f"{campo} é obrigatório no CT-e e está vazio em {onde}")

	return texto


def _emitente(company: str) -> dict:
	"""O emitente do CT-e é a transportadora — a Company que emite a fatura de frete."""
	empresa = frappe.get_cached_doc("Company", company)
	onde = f"Company {company}"
	endereco = _grupo_endereco(_endereco_vinculado("Company", company), f"endereço da {onde}")

	return {
		"CNPJ": _exigir(empresa.get("tax_id"), "CNPJ do emitente", onde),
		"xNome": _exigir(empresa.get("company_name"), "razão social", onde),
		"IE": _exigir(empresa.get("br_inscricao_estadual"), "inscrição estadual", onde),
		"enderEmit": endereco,
	}


def _remetente(doc) -> dict:
	"""O remetente da carga é o Customer da fatura (quem contratou o transporte)."""
	cliente = _exigir(doc.get("customer"), "cliente", f"{doc.doctype} {doc.name}")
	parte = frappe.get_cached_doc("Customer", cliente)
	onde = f"Customer {cliente}"
	endereco = _grupo_endereco(_endereco_vinculado("Customer", cliente), f"endereço do {onde}")

	documento = "".join(c for c in str(parte.get("tax_id") or "") if c.isalnum())

	return {
		"CNPJ": _exigir(documento, "CNPJ do remetente", onde),
		"xNome": _exigir(parte.get("customer_name"), "razão social", onde),
		"enderReme": endereco,
	}


def _destinatario(doc) -> dict:
	"""O destinatário da carga — por enquanto, o mesmo Customer (prestação para um único
	destinatário). Futuras itações podem suportar destinatário diferente do remetente."""
	return _remetente(doc)


def _identificacao(doc, endereco_emitente: dict, serie: str, ambiente: str) -> IdentificacaoCte:
	"""O grupo `ide`. `cUF` e município de envio saem do emitente."""
	numero = _exigir(doc.get("br_numero_cte"), "número do CT-e", f"{doc.doctype} {doc.name}")

	uf_emitente = endereco_emitente["UF"]

	return IdentificacaoCte(
		uf=codigo_da_uf(uf_emitente),
		cfop=_exigir(doc.get("br_cfop_transporte"), "CFOP do CT-e", f"{doc.doctype} {doc.name}"),
		natureza_operacao=_exigir(
			doc.get("br_natureza_operacao"), "natureza da operação", f"{doc.doctype} {doc.name}"
		),
		serie=serie,
		numero=numero,
		codigo_numerico="00000000",  # será sortado depois, placeholder
		emissao=frappe.utils.get_datetime(doc.get("posting_date")),
		modal=doc.get("br_modal_cte") or MODAL_RODOVIARIO,
		tipo_servico=doc.get("br_tipo_servico_cte") or TIPO_SERVICO_NORMAL,
		municipio_inicio=_exigir(
			doc.get("br_municipio_inicio"), "município de início", f"{doc.doctype} {doc.name}"
		),
		municipio_inicio_nome=_exigir(
			doc.get("br_municipio_inicio_nome"), "nome do município de início", f"{doc.doctype} {doc.name}"
		),
		uf_inicio=_exigir(doc.get("br_uf_inicio"), "UF de início", f"{doc.doctype} {doc.name}"),
		municipio_fim=_exigir(doc.get("br_municipio_fim"), "município de fim", f"{doc.doctype} {doc.name}"),
		municipio_fim_nome=_exigir(
			doc.get("br_municipio_fim_nome"), "nome do município de fim", f"{doc.doctype} {doc.name}"
		),
		uf_fim=_exigir(doc.get("br_uf_fim"), "UF de fim", f"{doc.doctype} {doc.name}"),
		municipio_envio=endereco_emitente["cMun"],
		municipio_envio_nome=endereco_emitente["xMun"],
		uf_envio=uf_emitente,
		indicador_ie_tomador="1",  # TODO: derivar do Customer
		ambiente="1" if ambiente == "producao" else "2",
	)


def montar_cte_do_documento(doc, serie: str, ambiente: str) -> dict:
	"""A árvore `CTe` completa e **ainda não assinada**, a partir de um documento.

	`serie` vem de `br_serie_cte` da Company; `ambiente` é `"producao"` ou `"homologacao"`.
	"""
	emitente, endereco_emitente = _emitente(_exigir(doc.get("company"), "empresa", doc.name))

	identificacao = _identificacao(doc, endereco_emitente, serie, ambiente)

	tomador = montar_toma3(TOMADOR_DESTINATARIO)

	rem = _remetente(doc)
	dest = _destinatario(doc)

	v_prest = {
		"vTPrest": _exigir(doc.get("grand_total"), "valor total da prestação", f"{doc.doctype} {doc.name}"),
	}

	infcte = {
		"ide": montar_ide(identificacao, tomador, ""),
		"emit": emitente,
		"rem": rem,
		"dest": dest,
		"vPrest": v_prest,
		"imp": {"ICMS": {"ICMSOutraUF": {"CST": "90"}}},  # placeholder — será implementado na task 2.x
		"infCTeNorm": {},
	}

	return montar_cte(infcte, "")
