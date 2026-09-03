# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio de verdade de `enviarLoteEventos`/`consultarLoteEventos` ao eSocial.

Fecha o item registrado em `docs/rh-estado-esocial.md` desde a implementação do
S-1200: "o envio HTTP de verdade (`requests.post` com o certificado como client cert
TLS, cabeçalhos `Content-Type`/`SOAPAction`, equivalente ao `_enviar` de
`integracao/autorizacao_sefaz.py` da NF-e)". É exatamente esse espelhamento —
`_enviar`/`_resolver_pendencia` aqui têm a mesma forma dos homônimos daquele módulo,
adaptados às duas diferenças reais do eSocial (não cosméticas):

- **SOAP 1.1, não 1.2** (`esocial_soap.py`, já confirmado): o cabeçalho HTTP muda de
  `application/soap+xml` para `text/xml`, e entra o cabeçalho `SOAPAction` que o SOAP
  1.2 dispensa (a ação vai dentro do próprio `Content-Type` no 1.2 — aqui é campo
  HTTP separado, `esocial_soap.soap_action`).
- **Polling por `cdResposta=203`** ("lote já recebido, em fila"), não pelo `cStat` de
  lote da NF-e — domínios de código diferentes, mesma ideia de "ainda não decidido,
  consulte de novo" (`esocial_retorno.StatusRetorno.pendente`).

Resolve, de passagem, a ressalva de `esocial_soap.py` sobre o wrapper `<consulta>`
------------------------------------------------------------------------------------------
`esocial_soap.py` tinha registrado que "a estrutura XML exata do conteúdo... não foi
verificada nesta rodada — só o nome do elemento wrapper". `ConsultaLoteEventos-v1_0_0.xsd`
(lido para montar este módulo) confirma: o elemento raiz da consulta é `eSocial >
consultaLoteEventos > protocoloEnvio` — exatamente a árvore que
`esocial_consulta.montar_consulta_lote_eventos` já produzia. A dúvida era só sobre o
que ia dentro do wrapper `<consulta>`; a resposta é "a árvore inteira, serializada",
mesma técnica de `para_xml` já usada para o corpo de `enviarLoteEventos`.

Funções livres, não métodos de classe — recebem um `ContextoEsocial` já pronto, mesma
disciplina de `autorizacao_sefaz.py`/`eventos_sefaz.py` para a NF-e.
"""

from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.folha.esocial_consulta import montar_consulta_lote_eventos
from erpnext_brasil.folha.esocial_retorno import RetornoEnvioLote, RetornoProcessamentoLote
from erpnext_brasil.folha.esocial_retorno_leitura import (
	ler_retorno_envio_lote,
	ler_retorno_processamento_lote,
)
from erpnext_brasil.folha.esocial_soap import extrair_resultado, montar_envelope, soap_action
from erpnext_brasil.integracao.contexto_esocial import ContextoEsocial
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel

__all__ = ["consultar_lote", "enviar_lote"]


_NAMESPACE_CONSULTA = "http://www.esocial.gov.br/schema/lote/eventos/envio/consulta/retornoProcessamento/v1_0_0"
"""Confirmado no `targetNamespace` de `ConsultaLoteEventos-v1_0_0.xsd` — diferente do
namespace da operação SOAP (`esocial_soap.py`'s `.../servicos/empregador/.../v1_0_0`).
Sem declarar este aqui, o `<eSocial>` da consulta herdaria por engano o namespace da
operação SOAP ao ser aninhado dentro do wrapper `<consulta>` — os dois parecem o
mesmo caminho, mas `schema/` e `servicos/empregador/` são namespaces distintos."""


def _xml_consulta(protocolo_envio: str) -> str:
	return para_xml(montar_consulta_lote_eventos(protocolo_envio), namespace=_NAMESPACE_CONSULTA)


def _enviar(servico: str, xml_interno: str, contexto: ContextoEsocial) -> str:
	"""Monta o envelope, faz o POST com TLS mútuo e devolve o XML de resultado já
	extraído do `soap:Body` — sem interpretar (isso é responsabilidade de quem
	chama, `ler_retorno_envio_lote`/`ler_retorno_processamento_lote`)."""
	from erpnext_brasil.folha.esocial_lote import endpoint

	url = endpoint(servico, contexto.ambiente)
	envelope = montar_envelope(servico, xml_interno)

	resposta = contexto.sessao_http.post(
		url,
		data=envelope.encode("utf-8"),
		headers={
			"Content-Type": "text/xml; charset=utf-8",
			"SOAPAction": soap_action(servico),
		},
		cert=(str(contexto.arquivo_cert), str(contexto.arquivo_chave)),
		timeout=30,
	)
	resposta.raise_for_status()

	return extrair_resultado(resposta.content)


def _resolver_pendencia(
	resultado: RetornoProcessamentoLote,
	protocolo_envio: str,
	contexto: ContextoEsocial,
	*,
	dormir,
	tentativas: int,
	intervalo: float,
) -> RetornoProcessamentoLote:
	"""Consulta o lote até sair do estado `pendente` (`cdResposta=203`, "já recebido
	em fila"), ou desiste — mesmo papel de `autorizacao_sefaz._resolver_pendencia`,
	domínio de código diferente (ver docstring do módulo)."""
	if not resultado.status.pendente:
		return resultado

	for _ in range(tentativas):
		dormir(intervalo)

		xml_resultado = _enviar("consultarLoteEventos", _xml_consulta(protocolo_envio), contexto)
		resultado = ler_retorno_processamento_lote(xml_resultado)

		if not resultado.status.pendente:
			return resultado

	raise TransporteIndisponivel(
		f"Lote continuou pendente após {tentativas} consultas — o eSocial não decidiu a tempo"
	)


def enviar_lote(
	xml_lote_assinado: str,
	contexto: ContextoEsocial,
	*,
	dormir,
	tentativas_consulta: int = 5,
	intervalo_consulta: float = 5.0,
) -> RetornoProcessamentoLote:
	"""Envia `xml_lote_assinado` (de `esocial_lote.montar_xml_lote`, com cada evento
	já assinado por `esocial_montagem.montar_evento_assinado`) e resolve até um
	estado final.

	Diferente de `autorizacao_sefaz.enviar_autorizacao`: a resposta imediata do
	eSocial ao `enviarLoteEventos` (`RetornoEnvioLote`) não traz o resultado por
	evento — só confirma a recepção do lote e, em sucesso, o `protocolo_envio` para
	consultar o processamento depois via `consultarLoteEventos`. Por isso este
	adaptador sempre faz ao menos uma segunda chamada quando o envio foi aceito
	(sucesso ou pendente), nunca devolve `RetornoEnvioLote` como resultado final.
	"""
	xml_resultado = _enviar("enviarLoteEventos", xml_lote_assinado, contexto)
	retorno_envio: RetornoEnvioLote = ler_retorno_envio_lote(xml_resultado)

	if not retorno_envio.status.sucesso and not retorno_envio.status.pendente:
		raise TransporteIndisponivel(
			f"eSocial recusou o lote: cdResposta={retorno_envio.status.cd_resposta} "
			f"({retorno_envio.status.desc_resposta})"
		)

	if retorno_envio.dados_recepcao is None:
		raise TransporteIndisponivel(
			"Lote aceito sem dadosRecepcaoLote — não há protocoloEnvio para consultar o processamento"
		)

	protocolo_envio = retorno_envio.dados_recepcao.protocolo_envio

	xml_processamento = _enviar("consultarLoteEventos", _xml_consulta(protocolo_envio), contexto)
	resultado = ler_retorno_processamento_lote(xml_processamento)

	return _resolver_pendencia(
		resultado, protocolo_envio, contexto,
		dormir=dormir, tentativas=tentativas_consulta, intervalo=intervalo_consulta,
	)  # fmt: skip


def consultar_lote(protocolo_envio: str, contexto: ContextoEsocial) -> RetornoProcessamentoLote:
	"""Consulta o processamento de um lote já enviado antes, sem reenviá-lo —
	equivalente a `autorizacao_sefaz.consultar_situacao` para a NF-e."""
	xml_resultado = _enviar("consultarLoteEventos", _xml_consulta(protocolo_envio), contexto)

	return ler_retorno_processamento_lote(xml_resultado)
