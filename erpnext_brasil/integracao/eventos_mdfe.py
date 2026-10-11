# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Encerramento e cancelamento do MDF-e acionáveis de um site — tarefa 5.4 de `fechar-laco-cte-mdfe`.

Irmão de `eventos_cte.py`, com a mesma disciplina — UF e CNPJ do autor saem **da chave de acesso**, o
protocolo sai do `Transmissao Fiscal` da autorização e o registro é gravado em todo desfecho antes do
`throw` — e três diferenças que vêm do manifesto:

- **O `Shipment` não tem `company`.** A empresa é a de origem da coleta (`empresa_do_shipment`) e o
  `Transmissao Fiscal` a exige; por isso este módulo tem o seu próprio `_registrar`, em vez de reaproveitar
  o do CT-e, que lê `doc.company`.
- **O encerramento fecha a viagem** (`110112`): informa data, UF e município de encerramento. O padrão é o
  município de **descarga** do `Shipment` (onde a viagem termina); `codigo_municipio` permite informar
  outro, e quem encerra por conta de terceiro não é coberto (`indEncPorTerceiro` fica de fora).
- **Encerrado não se cancela.** Cancelar um manifesto já encerrado recusa **antes** de assinar ou chamar a
  SEFAZ.

  ⚠️ Esta guarda local é conservadora: a regra de que o evento de cancelamento exige o MDF-e ainda não
  encerrado vem do entendimento corrente do MOC e **não foi lida no texto oficial** nesta frente. Se a
  SEFAZ admitir o caso, a guarda só adianta uma recusa; ela não grava nada falso.

**Não reenvia o que já foi aceito**: encerrar um manifesto já encerrado, ou cancelar um já cancelado,
recusa antes de chamar a SEFAZ. Evento recusado fica registrado como `Rejeitado`, com o motivo.

`nSeqEvento` é sempre 1: cada um dos dois eventos ocorre uma vez por manifesto.

Os demais eventos (condutor, inclusão de DF-e, pagamento…) **não ganham gatilho nesta mudança** — ver a
tarefa 5.6 e `docs/mdfe-estado.md`.

`xml_enviado` fica vazio, como em `eventos_nfe.py`: o evento é montado e assinado dentro do transporte,
que não o devolve. O `xml_retorno` é gravado normalmente.

Estado de verificação: camada Frappe, exercitada por `tests_bench/test_eventos_mdfe.py` com o transporte
trocado por um duplo; **não** testada contra a SEFAZ real.
"""

from datetime import datetime
from functools import partial

import frappe
from frappe import _

from erpnext_brasil.fiscal.codigos.uf import sigla_da_uf
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.evento import EventoInvalido
from erpnext_brasil.fiscal.documento.evento_mdfe import (
	montar_evento_cancelamento_mdfe,
	montar_evento_encerramento_mdfe,
)
from erpnext_brasil.fiscal.documento.transmissao_registro import (
	SITUACAO_AUTORIZADO,
	SITUACAO_CANCELADO,
	SITUACAO_REJEITADO,
	TIPO_CANCELAMENTO,
	TIPO_ENCERRAMENTO,
)
from erpnext_brasil.fiscal.mdfe import MdfeInvalido
from erpnext_brasil.integracao.certificado_a1 import (
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)
from erpnext_brasil.integracao.consumo_indevido import garantir_liberado, registrar_resposta
from erpnext_brasil.integracao.emissao_nfe import AMBIENTE_POR_CHAVE
from erpnext_brasil.integracao.eventos_nfe import autorizacao_do_documento
from erpnext_brasil.integracao.mdfe_documento import empresa_do_shipment, municipio_de_descarga
from erpnext_brasil.integracao.situacao_fiscal import situacao_fiscal
from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

__all__ = ["cancelar_mdfe", "encerrar_mdfe", "estado_do_mdfe"]


def _agora() -> datetime:
	return datetime.now().astimezone()


def _aceitos(doc, tipo: str, situacao: str) -> int:
	"""Quantos registros deste `tipo` e `situacao` o documento já tem — a base de "não reenvia"."""
	return frappe.db.count(
		"Transmissao Fiscal",
		{"documento_tipo": doc.doctype, "documento": doc.name, "tipo": tipo, "situacao": situacao},
	)


def _transporte(chave: str, company: str, ambiente: str) -> TransporteSefaz:
	"""UF e CNPJ lidos da chave — mesma razão de `eventos_cte._transporte`."""
	lida = ler_chave(chave)
	pfx, senha = carregar_certificado_da_empresa(company)

	return TransporteSefaz(
		pfx=pfx,
		senha=senha,
		uf=sigla_da_uf(lida.uf),
		cnpj_emitente=lida.cnpj,
		ambiente=ambiente,
		guarda=garantir_liberado,
		registrador=partial(registrar_resposta, company=company),
	)


def _registrar(doc, company: str, tipo: str, resposta, ambiente: str, chave: str, situacao: str) -> str:
	"""Grava o `Transmissao Fiscal` do evento. A `company` vem de fora: o `Shipment` não tem."""
	autorizacao = resposta.autorizacao

	registro = frappe.get_doc(
		{
			"doctype": "Transmissao Fiscal",
			"documento_tipo": doc.doctype,
			"documento": doc.name,
			"chave_acesso": chave,
			"tipo": tipo,
			"ambiente": AMBIENTE_POR_CHAVE[ambiente],
			"company": company,
			"situacao": situacao,
			"codigo_status": resposta.codigo,
			"mensagem": resposta.mensagem,
			"protocolo": autorizacao.protocolo if autorizacao else "",
			"xml_retorno": frappe.as_json(resposta.bruto),
		}
	)
	registro.insert(ignore_permissions=True)

	return registro.name


def _enviar(
	doc, company: str, tipo: str, evento: dict, chave: str, ambiente: str, aceita: str, rotulo
) -> dict:
	"""Transmite o evento, grava o desfecho e, se a SEFAZ recusou, **commita antes** de levantar."""
	with _transporte(chave, company, ambiente) as transporte:
		resposta = transporte.transmitir_evento_mdfe(evento, chave)

	aceito = resposta.autorizada
	registro = _registrar(
		doc, company, tipo, resposta, ambiente, chave, aceita if aceito else SITUACAO_REJEITADO
	)

	if not aceito:
		# `throw` desfaz a transação do request e levaria o registro junto: a recusa ficaria sem rastro.
		frappe.db.commit()
		frappe.throw(
			_("A SEFAZ recusou {0} ({1}): {2}. Detalhes no registro {3}.").format(
				rotulo, resposta.codigo, resposta.mensagem, registro
			)
		)

	return {
		"situacao": aceita,
		"chave_acesso": chave,
		"protocolo": resposta.autorizacao.protocolo,
		"registro": registro,
	}


def _contexto(name: str, permissao: str):
	"""`(Shipment, company, ambiente)` — com a permissão checada e a empresa resolvida."""
	doc = frappe.get_doc("Shipment", name)
	doc.check_permission(permissao)

	try:
		company = empresa_do_shipment(doc)
	except MdfeInvalido as erro:
		frappe.throw(str(erro))

	return doc, company, ambiente_sefaz_da_empresa(company)


@frappe.whitelist()
def estado_do_mdfe(name: str) -> dict:
	"""O que a tela precisa para decidir os botões: a situação fiscal **e** se a viagem já foi encerrada.

	O encerramento não muda a situação fiscal (o manifesto continua autorizado), por isso vem à parte.
	"""
	doc = frappe.get_doc("Shipment", name)
	doc.check_permission("read")

	return {
		**situacao_fiscal("Shipment", name),
		"encerrado": bool(_aceitos(doc, TIPO_ENCERRAMENTO, SITUACAO_AUTORIZADO)),
	}


@frappe.whitelist()
def encerrar_mdfe(name: str, codigo_municipio: str | None = None) -> dict:
	"""Encerra a viagem do MDF-e autorizado deste `Shipment` (evento 110112).

	O município de encerramento é, por padrão, o de descarga do `Shipment`; `codigo_municipio` (IBGE, 7
	dígitos) o substitui, e a UF sai dos dois primeiros dígitos dele. Devolve
	`{"situacao", "chave_acesso", "protocolo", "registro"}`.
	"""
	doc, company, ambiente = _contexto(name, "submit")

	if _aceitos(doc, TIPO_CANCELAMENTO, SITUACAO_CANCELADO):
		frappe.throw(_("O MDF-e do Shipment {0} foi cancelado e não pode ser encerrado.").format(name))

	if _aceitos(doc, TIPO_ENCERRAMENTO, SITUACAO_AUTORIZADO):
		frappe.throw(_("O MDF-e do Shipment {0} já foi encerrado.").format(name))

	chave, protocolo = autorizacao_do_documento("Shipment", name)

	try:
		municipio = codigo_municipio or municipio_de_descarga(doc)[0]
		evento = montar_evento_encerramento_mdfe(
			chave_acesso=chave,
			protocolo=protocolo,
			data_encerramento=_agora().date().isoformat(),
			codigo_uf=municipio[:2],
			codigo_municipio=municipio,
			cnpj_autor=ler_chave(chave).cnpj,
			data_evento=_agora().isoformat(timespec="seconds"),
			ambiente="1" if ambiente == "producao" else "2",
		)
	except (EventoInvalido, MdfeInvalido) as erro:
		frappe.throw(str(erro))

	return _enviar(
		doc,
		company,
		TIPO_ENCERRAMENTO,
		evento,
		chave,
		ambiente,
		SITUACAO_AUTORIZADO,
		_("o encerramento do MDF-e"),
	)


@frappe.whitelist()
def cancelar_mdfe(name: str, justificativa: str) -> dict:
	"""Cancela na SEFAZ o MDF-e autorizado deste `Shipment` (evento 110111).

	A justificativa (15 a 255 caracteres) é validada por `montar_evento_cancelamento_mdfe`, no domínio
	puro. Manifesto já cancelado ou já encerrado recusa antes de assinar ou chamar a SEFAZ.
	"""
	doc, company, ambiente = _contexto(name, "cancel")

	if _aceitos(doc, TIPO_CANCELAMENTO, SITUACAO_CANCELADO):
		frappe.throw(_("O MDF-e do Shipment {0} já foi cancelado.").format(name))

	if _aceitos(doc, TIPO_ENCERRAMENTO, SITUACAO_AUTORIZADO):
		frappe.throw(_("O MDF-e do Shipment {0} já foi encerrado e não pode ser cancelado.").format(name))

	chave, protocolo = autorizacao_do_documento("Shipment", name)

	try:
		evento = montar_evento_cancelamento_mdfe(
			chave_acesso=chave,
			protocolo=protocolo,
			justificativa=justificativa,
			cnpj_autor=ler_chave(chave).cnpj,
			data_evento=_agora().isoformat(timespec="seconds"),
			ambiente="1" if ambiente == "producao" else "2",
		)
	except EventoInvalido as erro:
		frappe.throw(str(erro))

	return _enviar(
		doc,
		company,
		TIPO_CANCELAMENTO,
		evento,
		chave,
		ambiente,
		SITUACAO_CANCELADO,
		_("o cancelamento do MDF-e"),
	)
