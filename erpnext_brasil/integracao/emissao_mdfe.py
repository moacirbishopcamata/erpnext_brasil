# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Emissão do MDF-e: o adaptador que liga o mapeador, a assinatura e o transporte ao `Shipment`.

Irmão de `emissao_cte.py` (tarefa 5.2 de `fechar-laco-cte-mdfe`) e com a mesma disciplina:

```text
mdfe_documento.montar_mdfe_do_documento   árvore do MDF-e + chave (número alocado só depois de validar)
certificado_a1.carregar_certificado…      PKCS#12 + senha da Company
mdfe.assinar_mdfe                         assinatura enveloped
TransporteSefaz.transmitir_mdfe           MDFeRecepcao + MDFeRetRecepcao (lote e recibo)
Transmissao Fiscal                        o que aconteceu, persistido
```

O registro é gravado em **todos os desfechos** (autorizado e rejeitado), antes de qualquer `throw` — o
motivo está em `emissao_nfe.py` e vale igual aqui: emissão que falha sem deixar rastro obriga o usuário a
adivinhar o que a SEFAZ respondeu.

O que difere do CT-e
---------------------
- **Lote e recibo**, não chamada síncrona: o `idLote` é o número do MDF-e (9 dígitos, único por emitente
  e série) e o `nRec` é consultado dentro do transporte. Lote ainda em processamento depois das
  tentativas **não** é rejeição: sai como erro com o recibo na mensagem, **sem** `Transmissao Fiscal`
  de rejeição — gravar "Rejeitado" mentiria sobre o que a SEFAZ disse.
- **A empresa vem de `pickup_company`**: o `Shipment` do core não tem `company`, mas o
  `Transmissao Fiscal` exige (`empresa_do_shipment`).
- **Sem denegação**: só o `cStat` 100 autoriza (ver `resposta_mdfe.py`); qualquer outro é rejeição.
- Chave e protocolo vão para o `Shipment` (`br_chave_acesso`, `br_protocolo_autorizacao`) só quando
  autorizado; a chave de um manifesto que a SEFAZ recusou não identifica documento nenhum.
- **Não reenvia o que já foi autorizado**: autorizar de novo o mesmo número volta como duplicidade e
  esconderia que o `Shipment` já tem manifesto. A recusa sai antes de alocar número ou chamar a SEFAZ.
- A recusa de cadastro (`MdfeInvalido`) sai com a mensagem que nomeia o dado e **sem**
  `Transmissao Fiscal`: nada foi enviado, não há desfecho da SEFAZ a registrar.

⚠️ `throw` faz rollback: sem o `commit` antes dele o `Transmissao Fiscal` da rejeição some junto.

Estado de verificação: camada Frappe, exercitada por `tests_bench/test_emissao_mdfe.py` com o transporte
trocado por um duplo; **não** testada contra a SEFAZ real (falta a prova em homologação da 5.1, que
depende do certificado A1).
"""

from functools import partial

import frappe
from frappe import _

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.transmissao_registro import SITUACAO_AUTORIZADO, TIPO_AUTORIZACAO
from erpnext_brasil.fiscal.mdfe import MdfeInvalido, assinar_mdfe
from erpnext_brasil.integracao.assinador_local import AssinadorLocal
from erpnext_brasil.integracao.certificado_a1 import (
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)
from erpnext_brasil.integracao.consumo_indevido import garantir_liberado, registrar_resposta
from erpnext_brasil.integracao.emissao_nfe import AMBIENTE_POR_CHAVE, situacao_da_resposta
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel
from erpnext_brasil.integracao.guarda_de_relogio import garantir_relogio_confiavel
from erpnext_brasil.integracao.instante_de_emissao import instante_de_emissao
from erpnext_brasil.integracao.mdfe_documento import empresa_do_shipment, montar_mdfe_do_documento
from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

__all__ = ["emitir_mdfe"]


def _ja_autorizado(doc) -> str | None:
	"""O nome do `Transmissao Fiscal` que já autorizou um MDF-e deste `Shipment`, ou `None`."""
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
	doc,
	company: str,
	arvore: dict,
	resposta,
	ambiente: str,
	chave: str,
	deslocamento_ms: float | None = None,
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
			"company": company,
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
def emitir_mdfe(doctype: str, name: str) -> dict:
	"""Monta, assina, transmite e registra o MDF-e de um `Shipment`.

	Devolve `{"situacao", "chave_acesso", "protocolo", "registro"}`. A rejeição **também** é gravada
	antes de virar erro — ver a docstring do módulo.
	"""
	# Primeira instrução, de propósito: antes de ler o documento e **antes de alocar número**. Um
	# relógio comprovadamente errado recusa aqui, sem queimar número da série nem chamar a SEFAZ.
	garantir_relogio_confiavel()

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")

	existente = _ja_autorizado(doc)

	if existente:
		frappe.throw(
			_("{0} {1} já tem MDF-e autorizado (registro {2}). Para desfazer, cancele o MDF-e.").format(
				doctype, name, existente
			)
		)

	try:
		company = empresa_do_shipment(doc)
		ambiente = ambiente_sefaz_da_empresa(company)
		instante = instante_de_emissao()
		arvore, chave = montar_mdfe_do_documento(doc, ambiente, instante.momento)
	except MdfeInvalido as erro:
		frappe.throw(str(erro))

	pfx, senha = carregar_certificado_da_empresa(company)
	assinada = assinar_mdfe(arvore, AssinadorLocal(pfx, senha))

	emitente = arvore["MDFe"]["infMDFe"]["emit"]

	# UF e CNPJ saem da própria árvore transmitida, não de uma segunda leitura do cadastro — mesma razão
	# de `emitir_cte`. O MDF-e tem um autorizador nacional, mas o `cUF` do cabeçalho SOAP é o do emitente.
	transporte = TransporteSefaz(
		pfx=pfx,
		senha=senha,
		uf=emitente["enderEmit"]["UF"],
		cnpj_emitente=emitente["CNPJ"],
		ambiente=ambiente,
		guarda=garantir_liberado,
		registrador=partial(registrar_resposta, company=company),
	)

	try:
		resposta = transporte.transmitir_mdfe(assinada, ler_chave(chave).numero)
	except TransporteIndisponivel as erro:
		# Lote ainda em processamento (ou sem endpoint): não é rejeição nem autorização, e não se grava
		# como uma ou outra. O número alocado fica com o `Shipment`, e a reemissão o reaproveita.
		frappe.db.commit()
		frappe.throw(_("A SEFAZ não concluiu o MDF-e: {0}").format(erro))

	registro = _registrar(doc, company, assinada, resposta, ambiente, chave, instante.deslocamento_ms)

	if not resposta.autorizada:
		# `commit` explícito: `throw` desfaz a transação do request/worker e levaria o registro junto.
		frappe.db.commit()
		frappe.throw(
			_("A SEFAZ recusou o MDF-e ({0}): {1}. Detalhes no registro {2}.").format(
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
