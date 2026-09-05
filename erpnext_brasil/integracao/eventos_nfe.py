# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cancelamento e carta de correção acionáveis de um site — o item 4 de `docs/gaps.md`.

O mesmo gap que `emissao_nfe.py` fechou para a autorização, agora para os eventos. Tudo
o que um cancelamento exige já existia e estava testado:

```text
fiscal/documento/evento.py        monta 110111 e 110110, lidos do XSD
integracao/eventos_sefaz.py       assina, envia por NFeRecepcaoEvento4, traduz o retorno
TransporteSefaz.cancelar/corrigir encadeia os dois
Transmissao Fiscal                já tem os tipos "Cancelamento" e "Carta de Correção"
```

E nada disso era alcançável: nenhum método `@frappe.whitelist()` chamava a cadeia. Uma
nota emitida pelo app não podia ser cancelada pelo app — que é, para o contribuinte, o
mesmo que não ter cancelamento. Código completo e inalcançável é o formato de gap que
este projeto trata como pior que bug.

De onde saem a UF e o CNPJ do autor
-----------------------------------------
**Da própria chave de acesso**, não de uma segunda leitura da `Company`. A chave carrega
o código da UF nas duas primeiras posições e o CNPJ do emitente da 7ª à 20ª — foi ela que
a SEFAZ autorizou, e é dela que o evento tem de falar.

Reler o cadastro abriria a hipótese de a `Company` ter mudado de endereço ou de CNPJ
entre a emissão e o cancelamento: o evento iria para a SEFAZ errada, ou com autor que não
confere, e a rejeição não diria o porquê. É a mesma disciplina que `emissao_nfe` aplica ao
tirar a UF da árvore que será transmitida, e não do cadastro.

Por que a autorização é procurada em `Transmissao Fiscal`
---------------------------------------------------------------
Cancelar exige o `nProt` da autorização — o protocolo que a SEFAZ devolveu. Ele não fica
no documento do ERPNext: fica no registro que `emissao_nfe` gravou. Procurá-lo ali é o que
garante que só se cancela o que este app realmente conseguiu autorizar.

Sem esse registro a operação **falha alto**, em vez de tentar com protocolo vazio: uma
tentativa de cancelar algo que não foi autorizado é erro de premissa, não caso de borda.

O registro é gravado em todos os desfechos
------------------------------------------------
Idêntico a `emissao_nfe`, e pela mesma razão: rejeição de evento é resultado, não defeito
de programa. Quem tentou cancelar precisa poder ler o que a SEFAZ respondeu.

⚠️ O que **não** está aqui, declarado
-------------------------------------------
- **`xml_enviado` fica vazio nestes registros.** O XML do evento é montado dentro do
  `TransporteSefaz`, que não o devolve. Trazê-lo até aqui exigiria montar o evento fora do
  transporte — e então duplicar o ciclo de vida do certificado que `contexto_sefaz.py`
  proíbe explicitamente de duplicar. Preferiu-se um campo vazio e declarado a uma
  duplicação que vaza chave privada em disco. O `xml_retorno` é gravado normalmente.
- **O documento do ERPNext não é marcado como cancelado.** Não existe campo declarado para
  a situação fiscal, e gravar atributo não declarado num `Document` do Frappe **some no
  save, sem erro** — foi assim que 31 campos ficaram inertes (gap 1.2-bis). A situação vive
  no `Transmissao Fiscal`; criar o campo é decisão à parte, com o campo declarado antes.
- **Sequência de evento.** `nSeqEvento` fica em 1: retransmitir o mesmo evento é outro
  fluxo, e um contador sem controle de concorrência repetiria o problema que
  `numeracao_fiscal` resolve com trava de linha.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.codigos.uf import sigla_da_uf
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.transmissao_registro import (
	SITUACAO_AUTORIZADO,
	SITUACAO_CANCELADO,
	SITUACAO_REJEITADO,
	TIPO_AUTORIZACAO,
	TIPO_CANCELAMENTO,
	TIPO_CARTA_DE_CORRECAO,
)
from erpnext_brasil.integracao.certificado_a1 import (
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)
from erpnext_brasil.integracao.emissao_nfe import AMBIENTE_POR_CHAVE
from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

__all__ = ["autorizacao_do_documento", "cancelar_nfe", "enviar_carta_correcao"]


def autorizacao_do_documento(doctype: str, name: str) -> tuple[str, str]:
	"""Devolve `(chave_acesso, protocolo)` da autorização deste documento.

	Falha alto quando não há autorização registrada — ver a docstring do módulo sobre por
	que isso não é caso de borda.
	"""
	registros = frappe.get_all(
		"Transmissao Fiscal",
		filters={
			"documento_tipo": doctype,
			"documento": name,
			"tipo": TIPO_AUTORIZACAO,
			"situacao": SITUACAO_AUTORIZADO,
		},
		fields=["chave_acesso", "protocolo"],
		order_by="creation desc",
		limit=1,
	)

	if not registros:
		frappe.throw(
			_("{0} {1} não tem autorização registrada — não há o que cancelar ou corrigir.").format(
				doctype, name
			)
		)

	chave = (registros[0].get("chave_acesso") or "").strip()
	protocolo = (registros[0].get("protocolo") or "").strip()

	if not chave:
		frappe.throw(
			_("A autorização registrada de {0} {1} não guardou a chave de acesso.").format(doctype, name)
		)

	return chave, protocolo


def _transporte(chave: str, company: str, ambiente: str) -> TransporteSefaz:
	"""Monta o transporte com UF e CNPJ lidos da chave — ver docstring do módulo."""
	lida = ler_chave(chave)
	pfx, senha = carregar_certificado_da_empresa(company)

	return TransporteSefaz(
		pfx=pfx,
		senha=senha,
		uf=sigla_da_uf(lida.uf),
		cnpj_emitente=lida.cnpj,
		ambiente=ambiente,
	)


def _registrar(doc, tipo: str, resposta, ambiente: str, chave: str, situacao: str) -> str:
	"""Grava o `Transmissao Fiscal` do evento em qualquer desfecho.

	`xml_enviado` fica vazio de propósito, e o motivo está na docstring do módulo.
	"""
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
			"protocolo": getattr(autorizacao, "protocolo", "") if autorizacao else "",
			"xml_retorno": frappe.as_json(resposta.bruto),
		}
	)
	registro.insert(ignore_permissions=True)

	return registro.name


@frappe.whitelist()
def cancelar_nfe(doctype: str, name: str, justificativa: str) -> dict:
	"""Cancela na SEFAZ a NF-e autorizada deste documento (evento 110111).

	`justificativa` é exigida pela norma entre 15 e 256 caracteres; quem valida o limite é
	`montar_evento_cancelamento`, no domínio puro, e não este adaptador — a regra é do
	leiaute, não da camada Frappe.

	Devolve `{"situacao", "chave_acesso", "protocolo", "registro"}`.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("cancel")

	chave, protocolo = autorizacao_do_documento(doctype, name)

	if not protocolo:
		frappe.throw(
			_("A autorização de {0} {1} não guardou o protocolo, exigido para cancelar.").format(
				doctype, name
			)
		)

	ambiente = ambiente_sefaz_da_empresa(doc.company)

	with _transporte(chave, doc.company, ambiente) as transporte:
		resposta = transporte.cancelar(chave, protocolo, justificativa)

	# `autorizada` aqui significa **evento homologado**: `eventos_sefaz.enviar_evento` já
	# aplicou os `cStat` de sucesso próprios de cada tipo de evento
	# (`evento.RetornoEvento.homologado`) e só preenche `autorizacao` quando a SEFAZ
	# homologou. Repetir a tabela de códigos aqui a faria divergir ao primeiro ajuste.
	aceito = resposta.autorizada
	registro = _registrar(
		doc,
		TIPO_CANCELAMENTO,
		resposta,
		ambiente,
		chave,
		SITUACAO_CANCELADO if aceito else SITUACAO_REJEITADO,
	)

	if not aceito:
		frappe.throw(
			_("A SEFAZ recusou o cancelamento ({0}): {1}. Detalhes no registro {2}.").format(
				resposta.codigo, resposta.mensagem, registro
			)
		)

	return {
		"situacao": SITUACAO_CANCELADO,
		"chave_acesso": chave,
		"protocolo": resposta.autorizacao.protocolo,
		"registro": registro,
	}


@frappe.whitelist()
def enviar_carta_correcao(doctype: str, name: str, texto_correcao: str) -> dict:
	"""Envia uma carta de correção da NF-e autorizada deste documento (evento 110110).

	⚠️ **Cada CC-e substitui a anterior para efeito de exibição.** O texto enviado precisa
	reunir todas as correções já feitas, não só a nova — regra de negócio da SEFAZ. Este
	método envia o que recebe: quem chama é quem sabe o histórico.

	Diferente do cancelamento, **não exige protocolo**: a carta se refere à chave, e o
	`nProt` da autorização é ecoado pela própria SEFAZ na resposta.

	Devolve `{"situacao", "chave_acesso", "protocolo", "registro"}`.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")

	chave, _protocolo = autorizacao_do_documento(doctype, name)
	ambiente = ambiente_sefaz_da_empresa(doc.company)

	with _transporte(chave, doc.company, ambiente) as transporte:
		resposta = transporte.corrigir(chave, texto_correcao)

	# `autorizada` aqui significa **evento homologado**: `eventos_sefaz.enviar_evento` já
	# aplicou os `cStat` de sucesso próprios de cada tipo de evento
	# (`evento.RetornoEvento.homologado`) e só preenche `autorizacao` quando a SEFAZ
	# homologou. Repetir a tabela de códigos aqui a faria divergir ao primeiro ajuste.
	aceito = resposta.autorizada
	registro = _registrar(
		doc,
		TIPO_CARTA_DE_CORRECAO,
		resposta,
		ambiente,
		chave,
		SITUACAO_AUTORIZADO if aceito else SITUACAO_REJEITADO,
	)

	if not aceito:
		frappe.throw(
			_("A SEFAZ recusou a carta de correção ({0}): {1}. Detalhes no registro {2}.").format(
				resposta.codigo, resposta.mensagem, registro
			)
		)

	return {
		"situacao": SITUACAO_AUTORIZADO,
		"chave_acesso": chave,
		"protocolo": resposta.autorizacao.protocolo,
		"registro": registro,
	}
