# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cancelamento e carta de correção do CT-e acionáveis de um site — tarefa 3.4.

Irmão de `eventos_nfe.py`, com a mesma disciplina — UF e CNPJ do autor saem **da chave de acesso**,
o protocolo sai do `Transmissao Fiscal` da autorização, e o registro é gravado em todo desfecho
antes do `throw` — e três diferenças que vêm do leiaute do CT-e:

- **Quem monta o evento é este módulo**, não o `TransporteSefaz`: o transporte só assina e envia
  (`transmitir_evento_cte`), porque o evento do CT-e (raiz `eventoCTe`, corpo em `evCancCTe` /
  `evCCeCTe`) não é o da NF-e que `cancelar`/`corrigir` montam.
- **A CC-e é uma lista estruturada** de alterações campo a campo, não texto livre.
- **`nSeqEvento` conta.** O cancelamento é sempre o evento 1; cada CC-e aceita ocupa uma sequência
  (1 a 20), então a próxima é a quantidade de CC-e já aceitas mais um. Sem isso a segunda carta
  repetiria o `@Id` da primeira e a SEFAZ a recusaria por duplicidade.

**Não reenvia o que já foi aceito**: cancelar um CT-e já cancelado recusa antes de assinar ou
chamar a SEFAZ.

`xml_enviado` fica vazio, como em `eventos_nfe.py`: o evento é montado e assinado dentro do
transporte, que não o devolve. O `xml_retorno` é gravado normalmente.

Estado de verificação: camada Frappe, **não** exercitada contra a SEFAZ real.
"""

from datetime import datetime
from functools import partial

import frappe
from frappe import _

from erpnext_brasil.fiscal.codigos.uf import sigla_da_uf
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.evento import EventoInvalido
from erpnext_brasil.fiscal.documento.evento_cte import (
	CorrecaoCte,
	montar_evento_cancelamento_cte,
	montar_evento_correcao_cte,
)
from erpnext_brasil.fiscal.documento.transmissao_registro import (
	SITUACAO_AUTORIZADO,
	SITUACAO_CANCELADO,
	SITUACAO_REJEITADO,
	TIPO_CANCELAMENTO,
	TIPO_CARTA_DE_CORRECAO,
)
from erpnext_brasil.integracao.certificado_a1 import (
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)
from erpnext_brasil.integracao.consumo_indevido import garantir_liberado, registrar_resposta
from erpnext_brasil.integracao.emissao_nfe import AMBIENTE_POR_CHAVE
from erpnext_brasil.integracao.eventos_nfe import autorizacao_do_documento
from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

__all__ = ["cancelar_cte", "corrigir_cte"]

SEQUENCIA_MAXIMA = 20
"""`nSeqEvento` vai de 1 a 20 (`evento_cte`): são 20 cartas por CT-e."""


def _transporte(chave: str, company: str, ambiente: str) -> TransporteSefaz:
	"""UF e CNPJ lidos da chave — mesma razão de `eventos_nfe._transporte`."""
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


def _agora() -> str:
	return datetime.now().astimezone().isoformat(timespec="seconds")


def _eventos_aceitos(doc, tipo: str, situacao: str) -> int:
	return frappe.db.count(
		"Transmissao Fiscal",
		{"documento_tipo": doc.doctype, "documento": doc.name, "tipo": tipo, "situacao": situacao},
	)


def _registrar(doc, tipo: str, resposta, ambiente: str, chave: str, situacao: str) -> str:
	autorizacao = resposta.autorizacao

	registro = frappe.get_doc(
		{
			"doctype": "Transmissao Fiscal",
			"documento_tipo": doc.doctype,
			"documento": doc.name,
			"chave_acesso": chave,
			"tipo": tipo,
			"ambiente": AMBIENTE_POR_CHAVE[ambiente],
			"company": doc.company,
			"situacao": situacao,
			"codigo_status": resposta.codigo,
			"mensagem": resposta.mensagem,
			"protocolo": autorizacao.protocolo if autorizacao else "",
			"xml_retorno": frappe.as_json(resposta.bruto),
		}
	)
	registro.insert(ignore_permissions=True)

	return registro.name


def _concluir(doc, tipo, resposta, ambiente, chave, situacao_aceita, rotulo) -> dict:
	"""Grava o registro e, se a SEFAZ recusou, **commita antes** de levantar (`throw` desfaz)."""
	aceito = resposta.autorizada
	registro = _registrar(
		doc, tipo, resposta, ambiente, chave, situacao_aceita if aceito else SITUACAO_REJEITADO
	)

	if not aceito:
		frappe.db.commit()
		frappe.throw(
			_("A SEFAZ recusou {0} ({1}): {2}. Detalhes no registro {3}.").format(
				rotulo, resposta.codigo, resposta.mensagem, registro
			)
		)

	return {
		"situacao": situacao_aceita,
		"chave_acesso": chave,
		"protocolo": resposta.autorizacao.protocolo,
		"registro": registro,
	}


@frappe.whitelist()
def cancelar_cte(doctype: str, name: str, justificativa: str) -> dict:
	"""Cancela na SEFAZ o CT-e autorizado deste documento (evento 110111).

	A justificativa (15 a 255 caracteres) é validada por `montar_evento_cancelamento_cte`, no
	domínio puro. Devolve `{"situacao", "chave_acesso", "protocolo", "registro"}`.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("cancel")

	if _eventos_aceitos(doc, TIPO_CANCELAMENTO, SITUACAO_CANCELADO):
		frappe.throw(_("O CT-e de {0} {1} já foi cancelado.").format(doctype, name))

	chave, protocolo = autorizacao_do_documento(doctype, name)

	if not protocolo:
		frappe.throw(
			_("A autorização de {0} {1} não guardou o protocolo, exigido para cancelar.").format(
				doctype, name
			)
		)

	ambiente = ambiente_sefaz_da_empresa(doc.company)

	try:
		evento = montar_evento_cancelamento_cte(
			chave_acesso=chave,
			protocolo=protocolo,
			justificativa=justificativa,
			cnpj_autor=ler_chave(chave).cnpj,
			data_evento=_agora(),
			ambiente="1" if ambiente == "producao" else "2",
		)
	except EventoInvalido as erro:
		frappe.throw(str(erro))

	with _transporte(chave, doc.company, ambiente) as transporte:
		resposta = transporte.transmitir_evento_cte(evento, chave)

	return _concluir(
		doc, TIPO_CANCELAMENTO, resposta, ambiente, chave, SITUACAO_CANCELADO, _("o cancelamento do CT-e")
	)


@frappe.whitelist()
def corrigir_cte(doctype: str, name: str, correcoes) -> dict:
	"""Envia uma carta de correção do CT-e (evento 110110).

	`correcoes` é uma lista de `{"grupo_alterado", "campo_alterado", "valor_alterado"}` (mais
	`"numero_item_alterado"` quando o campo está numa lista) — ou o JSON dela, como vem da tela.
	Cada carta reporta as alterações que traz; quem chama decide se repete as anteriores.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")

	chave, _protocolo = autorizacao_do_documento(doctype, name)
	sequencia = _eventos_aceitos(doc, TIPO_CARTA_DE_CORRECAO, SITUACAO_AUTORIZADO) + 1

	if sequencia > SEQUENCIA_MAXIMA:
		frappe.throw(
			_("O CT-e de {0} {1} já tem {2} cartas de correção — o limite do leiaute.").format(
				doctype, name, SEQUENCIA_MAXIMA
			)
		)

	ambiente = ambiente_sefaz_da_empresa(doc.company)

	try:
		itens = frappe.parse_json(correcoes) if isinstance(correcoes, str) else correcoes
		evento = montar_evento_correcao_cte(
			chave_acesso=chave,
			correcoes=[CorrecaoCte(**item) for item in (itens or [])],
			cnpj_autor=ler_chave(chave).cnpj,
			data_evento=_agora(),
			numero_sequencia=sequencia,
			ambiente="1" if ambiente == "producao" else "2",
		)
	except (EventoInvalido, TypeError) as erro:
		frappe.throw(str(erro))

	with _transporte(chave, doc.company, ambiente) as transporte:
		resposta = transporte.transmitir_evento_cte(evento, chave)

	return _concluir(
		doc,
		TIPO_CARTA_DE_CORRECAO,
		resposta,
		ambiente,
		chave,
		SITUACAO_AUTORIZADO,
		_("a carta de correção do CT-e"),
	)
