# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Emissão do CT-e: o adaptador que liga o mapeador, a assinatura e o transporte à fatura.

Irmão de `emissao_nfe.py` (tarefa 3.2 de `fechar-laco-cte-mdfe`) e com a mesma disciplina:

```text
cte_documento.montar_cte_do_documento   árvore do CT-e + chave (número alocado só depois de validar)
certificado_a1.carregar_certificado…    PKCS#12 + senha da Company
cte.assinar_cte                         assinatura enveloped
TransporteSefaz.transmitir_cte          CTeRecepcaoSincV4, uma chamada
Transmissao Fiscal                      o que aconteceu, persistido
```

O registro é gravado em **todos os desfechos** (autorizado, rejeitado, denegado), antes de
qualquer `throw` — o motivo está em `emissao_nfe.py` e vale igual aqui: emissão que falha sem
deixar rastro obriga o usuário a adivinhar o que a SEFAZ respondeu.

O que difere da NF-e
----------------------
- Não há lote nem recibo: a resposta vem na própria chamada, então não há o que reconsultar.
- A chave e o **protocolo** vão para o documento de origem (`br_chave_acesso`,
  `br_protocolo_autorizacao`), só quando autorizado. Rejeitado não grava nenhum dos dois na
  fatura: a chave de um CT-e que a SEFAZ recusou não identifica documento nenhum.
- **Não reenvia o que já foi autorizado.** Autorizar de novo o mesmo número volta como
  duplicidade (539) e, pior, esconderia que a fatura já tem CT-e. A recusa sai antes de alocar
  número, montar ou chamar a SEFAZ.
- A recusa de cadastro (`CteInvalido`, códigos 1206/1207) sai com `mensagem_com_codigo` e **sem**
  `Transmissao Fiscal`: nada foi enviado, não há desfecho da SEFAZ a registrar.

⚠️ `throw` faz rollback: sem o `commit` antes dele o `Transmissao Fiscal` da rejeição some junto.
`emissao_nfe.emitir_nfe` não tem esse `commit` — ver o relatório da tarefa 3.2.

Estado de verificação: camada Frappe, **não** exercitada contra bench real nem contra a SEFAZ
(falta a prova em homologação da 3.1).
"""

from functools import partial

import frappe
from frappe import _

from erpnext_brasil.fiscal.cte import CteInvalido, assinar_cte
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.transmissao_registro import SITUACAO_AUTORIZADO, TIPO_AUTORIZACAO
from erpnext_brasil.integracao.assinador_local import AssinadorLocal
from erpnext_brasil.integracao.certificado_a1 import (
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)
from erpnext_brasil.integracao.consumo_indevido import garantir_liberado, registrar_resposta
from erpnext_brasil.integracao.cte_documento import montar_cte_do_documento
from erpnext_brasil.integracao.emissao_nfe import AMBIENTE_POR_CHAVE, situacao_da_resposta
from erpnext_brasil.integracao.guarda_de_relogio import garantir_relogio_confiavel
from erpnext_brasil.integracao.instante_de_emissao import instante_de_emissao
from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

__all__ = ["emitir_cte"]


def _ja_autorizado(doc) -> str | None:
	"""O nome do `Transmissao Fiscal` que já autorizou um CT-e desta fatura, ou `None`."""
	return frappe.db.get_value(
		"Transmissao Fiscal",
		{
			"documento_tipo": doc.doctype,
			"documento": doc.name,
			"tipo": TIPO_AUTORIZACAO,
			"situacao": SITUACAO_AUTORIZADO,
		},
		"name",
	)


def _registrar(
	doc, arvore: dict, resposta, ambiente: str, chave: str, deslocamento_ms: float | None = None
) -> str:
	"""Grava o `Transmissao Fiscal` em qualquer desfecho. Devolve o nome do registro."""
	autorizacao = resposta.autorizacao

	registro = frappe.get_doc(
		{
			"doctype": "Transmissao Fiscal",
			"documento_tipo": doc.doctype,
			"documento": doc.name,
			"chave_acesso": chave,
			"tipo": TIPO_AUTORIZACAO,
			"ambiente": AMBIENTE_POR_CHAVE[ambiente],
			"company": doc.company,
			"situacao": situacao_da_resposta(resposta),
			"codigo_status": resposta.codigo,
			"mensagem": resposta.mensagem,
			"protocolo": autorizacao.protocolo if autorizacao else "",
			"xml_enviado": para_xml(arvore),
			"xml_retorno": frappe.as_json(resposta.bruto),
			"deslocamento_relogio_ms": deslocamento_ms,
			"instante_corrigido": 0 if deslocamento_ms is None else 1,
		}
	)
	registro.insert(ignore_permissions=True)

	return registro.name


@frappe.whitelist()
def emitir_cte(doctype: str, name: str) -> dict:
	"""Monta, assina, transmite e registra o CT-e de uma `Sales Invoice` de transporte.

	Devolve `{"situacao", "chave_acesso", "protocolo", "registro"}`. Rejeição e denegação
	**também** são gravadas antes de virarem erro — ver docstring do módulo.
	"""
	# Primeira instrução, de propósito: antes de ler o documento e **antes de alocar número**. Um
	# relógio comprovadamente errado recusa aqui, sem queimar número da série nem chamar a SEFAZ.
	garantir_relogio_confiavel()

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")

	existente = _ja_autorizado(doc)

	if existente:
		frappe.throw(
			_("{0} {1} já tem CT-e autorizado (registro {2}). Para desfazer, cancele o CT-e.").format(
				doctype, name, existente
			)
		)

	ambiente = ambiente_sefaz_da_empresa(doc.company)
	instante = instante_de_emissao()

	try:
		arvore, chave = montar_cte_do_documento(doc, ambiente, instante.momento)
	except CteInvalido as erro:
		frappe.throw(erro.mensagem_com_codigo)

	pfx, senha = carregar_certificado_da_empresa(doc.company)
	assinada = assinar_cte(arvore, AssinadorLocal(pfx, senha))

	emitente = arvore["CTe"]["infCte"]["emit"]

	# UF e CNPJ saem da própria árvore transmitida, não de uma segunda leitura do cadastro — mesma
	# razão de `emitir_nfe`: o autorizador é necessariamente o da UF declarada no documento.
	transporte = TransporteSefaz(
		pfx=pfx,
		senha=senha,
		uf=emitente["enderEmit"]["UF"],
		cnpj_emitente=emitente["CNPJ"],
		ambiente=ambiente,
		guarda=garantir_liberado,
		registrador=partial(registrar_resposta, company=doc.company),
	)
	resposta = transporte.transmitir_cte(assinada)

	registro = _registrar(doc, assinada, resposta, ambiente, chave, instante.deslocamento_ms)

	if not resposta.autorizada:
		# `commit` explícito: `throw` desfaz a transação do request/worker e levaria o registro
		# junto — a rejeição ficaria sem rastro, o oposto do que o módulo promete. Mesmo motivo de
		# `consumo_indevido.registrar_resposta`. O número alocado fica gravado com ele: rejeição não
		# o consome na SEFAZ (a reemissão o reaproveita) e denegação consome.
		frappe.db.commit()
		frappe.throw(
			_("A SEFAZ recusou o CT-e ({0}): {1}. Detalhes no registro {2}.").format(
				resposta.codigo, resposta.mensagem, registro
			)
		)

	doc.db_set("br_chave_acesso", chave)
	doc.db_set("br_protocolo_autorizacao", resposta.autorizacao.protocolo)

	return {
		"situacao": SITUACAO_AUTORIZADO,
		"chave_acesso": chave,
		"protocolo": resposta.autorizacao.protocolo,
		"registro": registro,
	}
