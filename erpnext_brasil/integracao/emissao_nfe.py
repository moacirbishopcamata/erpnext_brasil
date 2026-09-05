# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Emissão da NF-e: o método que faltava para tornar a cadeia alcançável.

Fecha a outra metade do gap 1.3 de `docs/gaps.md`. Antes deste módulo o app **montava,
assinava e transmitia** — e nada disso podia ser acionado num site real: os únicos quatro
métodos expostos eram dois importadores, o Pix e a prontidão do EFD. Do ponto de vista de
quem usa o sistema, o app não emitia nota, por falta de um adaptador.

`emitir_nfe` é esse adaptador e não faz nada além de encadear o que já existe:

```text
nfe_documento.montar_nfe_do_documento   árvore da NF-e
certificado_a1.carregar_certificado…    PKCS#12 + senha da Company
nfe.assinar_nfe                         assinatura enveloped
TransporteSefaz.transmitir              TLS, envio e resolução do recibo
Transmissao Fiscal                      o que aconteceu, persistido
```

Quem monta o `ContextoSefaz` é o `TransporteSefaz`, não este módulo
--------------------------------------------------------------------------
A primeira versão deste arquivo construía um `ContextoSefaz` à mão. A docstring de
`contexto_sefaz.py` diz o contrário, com todas as letras: *"`TransporteSefaz` é quem monta
— os módulos extraídos só recebem e usam, nunca constroem um `ContextoSefaz` sozinhos."*

O motivo é concreto: o contexto carrega os **arquivos PEM do TLS mútuo**, extraídos do
PKCS#12 num diretório temporário que só o `TransporteSefaz` sabe criar e limpar. Montá-lo
de fora significaria duplicar esse ciclo de vida — e vazar arquivo de chave privada em
disco quando algo desse errado no meio.

O registro é gravado **em todos os desfechos**, não só no sucesso
--------------------------------------------------------------------------
Rejeição e denegação são resultados, não erros de programa. Emissão que falha sem deixar
rastro obriga o usuário a adivinhar o que a SEFAZ respondeu — o tipo de silêncio que este
projeto trata como pior que um erro alto.

Por isso o `Transmissao Fiscal` é gravado **antes** de qualquer `throw`, com a situação
real, o código de status, a mensagem e os dois XML. Só depois a rejeição vira mensagem de
erro para quem clicou, citando o registro onde os detalhes ficaram.

O que ainda **não** está aqui, e por quê
------------------------------------------------
- **Contingência.** `ativar_contingencia_svc` existe no módulo puro; decidir *quando*
  entrar em contingência depende de detectar indisponibilidade, que é outra frente.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.documento.nfe import MODELO_NFE, assinar_nfe
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.transmissao_registro import (
	SITUACAO_AUTORIZADO,
	SITUACAO_DENEGADO,
	SITUACAO_REJEITADO,
	TIPO_AUTORIZACAO,
)
from erpnext_brasil.integracao.assinador_local import AssinadorLocal
from erpnext_brasil.integracao.certificado_a1 import (
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)
from erpnext_brasil.integracao.cobranca_documento import montar_cobranca_do_documento
from erpnext_brasil.integracao.configuracao_fiscal import serie_padrao
from erpnext_brasil.integracao.nfe_documento import montar_nfe_do_documento
from erpnext_brasil.integracao.numeracao_fiscal import numero_do_documento
from erpnext_brasil.integracao.transporte_pagamento import pag_do_documento, transp_do_documento
from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

__all__ = ["AMBIENTE_POR_CHAVE", "emitir_nfe", "situacao_da_resposta"]

AMBIENTE_POR_CHAVE = {"producao": "Produção", "homologacao": "Homologação"}
"""Chave interna (`certificado_a1`) → rótulo do DocType `Transmissao Fiscal`."""


def situacao_da_resposta(resposta) -> str:
	"""Traduz a resposta da SEFAZ para o domínio de `Transmissao Fiscal`.

	Denegação **não** é rejeição: a SEFAZ recebeu e recusou por irregularidade do
	destinatário, e o documento passa a existir com número consumido. Tratar as duas como
	a mesma coisa esconderia essa diferença de quem precisa reemitir.
	"""
	if resposta.autorizada:
		return SITUACAO_AUTORIZADO

	return SITUACAO_DENEGADO if resposta.denegado else SITUACAO_REJEITADO


def _registrar(doc, arvore: dict, resposta, ambiente: str, chave: str) -> str:
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
			"protocolo": getattr(autorizacao, "protocolo", "") if autorizacao else "",
			"xml_enviado": para_xml(arvore),
			"xml_retorno": frappe.as_json(resposta.bruto),
		}
	)
	registro.insert(ignore_permissions=True)

	return registro.name


@frappe.whitelist()
def emitir_nfe(
	doctype: str,
	name: str,
	transp: dict | None = None,
	pag: dict | None = None,
	cobr: dict | None = None,
) -> dict:
	"""Monta, assina, transmite e registra a NF-e de um documento do ERPNext.

	Chamável só com `doctype` e `name`: os três grupos são derivados do próprio documento
	quando não informados. Continuam como parâmetro para quem precise sobrescrever — uma
	tela que pergunte o frete ao usuário, por exemplo.

	Devolve `{"situacao", "chave_acesso", "protocolo", "registro"}`. Rejeição e denegação
	**também** são gravadas antes de virarem erro — ver docstring do módulo.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")

	ambiente = ambiente_sefaz_da_empresa(doc.company)
	serie = serie_padrao(doc.company, MODELO_NFE)

	# Aloca antes de montar: o `nNF` entra na chave de acesso, que é derivada do `ide`.
	# Fica na mesma transação do request, para que a trava da linha do contador só solte
	# quando o documento estiver gravado — ver `numeracao_fiscal`.
	numero_do_documento(doc, MODELO_NFE, serie)

	# A cobrança é **derivada**, não recebida: as duplicatas saem do `Payment Schedule`,
	# que já é o parcelamento acordado. Diferente de `transp` e `pag`, aqui não há
	# afirmação a inventar — ou o documento tem parcelas, ou não tem, e
	# `montar_cobranca_do_documento` devolve `None` no segundo caso. O parâmetro segue
	# existindo para quem precise sobrescrever.
	if cobr is None:
		cobr = montar_cobranca_do_documento(doc)

	# `transp` e `pag` também derivam do documento quando não vêm prontos. A diferença é
	# que a derivação deles **pode falhar alto**: `transp_do_documento` recusa documento
	# sem modalidade de frete escolhida, porque "sem ocorrência de transporte" é afirmação,
	# não padrão. É o comportamento certo — melhor recusar aqui, com mensagem que diz o
	# campo, do que declarar ao Fisco algo que ninguém disse.
	if transp is None:
		transp = transp_do_documento(doc)

	if pag is None:
		pag = pag_do_documento(doc)

	arvore = montar_nfe_do_documento(
		doc,
		serie=serie,
		ambiente=ambiente,
		transp=transp,
		pag=pag,
		cobr=cobr,
	)
	chave = arvore["NFe"]["infNFe"]["@Id"].removeprefix("NFe")

	pfx, senha = carregar_certificado_da_empresa(doc.company)
	assinada = assinar_nfe(arvore, AssinadorLocal(pfx, senha))

	emitente = arvore["NFe"]["infNFe"]["emit"]

	# UF e CNPJ saem da **própria árvore** que será transmitida, não de uma segunda
	# leitura do cadastro: assim o autorizador para onde se envia é necessariamente o da
	# UF declarada no documento. Reler a Company abriria a hipótese de o cadastro ter
	# mudado entre a montagem e o envio — e a nota iria para a SEFAZ errada, em silêncio.
	transporte = TransporteSefaz(
		pfx=pfx,
		senha=senha,
		uf=emitente["enderEmit"]["UF"],
		cnpj_emitente=emitente["CNPJ"],
		ambiente=ambiente,
	)
	resposta = transporte.transmitir(assinada)

	registro = _registrar(doc, assinada, resposta, ambiente, chave)

	if not resposta.autorizada:
		frappe.throw(
			_("A SEFAZ recusou a NF-e ({0}): {1}. Detalhes no registro {2}.").format(
				resposta.codigo, resposta.mensagem, registro
			)
		)

	doc.db_set("br_chave_acesso", chave)

	return {
		"situacao": SITUACAO_AUTORIZADO,
		"chave_acesso": chave,
		"protocolo": resposta.autorizacao.protocolo,
		"registro": registro,
	}
