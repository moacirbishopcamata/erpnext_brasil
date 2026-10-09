# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio do CT-e à SEFAZ via `CTeRecepcaoSincV4` — autorização **síncrona e unitária**.

Irmão de `autorizacao_sefaz.py` (que fala `NFeAutorizacao4`), e propositalmente **não** uma
generalização dele: `design.md`, decisão 3, recusa fazer `transmitir` conhecer três envelopes, e o
pior resultado possível seria mandar um CT-e ao serviço da NF-e. Aqui há **uma** requisição: o
CT-e 4.00 não tem lote nem recibo, então não há polling, não há `dormir` e não há tentativas — a
resposta vem na própria chamada.

O que a tarefa 3.1 pedia e o que ficou diferente
----------------------------------------------------
A tarefa fala em `dormir` injetado. Num serviço síncrono não há o que esperar, e um parâmetro que
nunca é usado seria inventar uma espera que o leiaute não tem; ficou de fora, e há teste que
trava a assinatura.

Função livre que recebe um `ContextoSefaz` pronto — mesma disciplina de `eventos_sefaz.py` e
`inutilizacao_sefaz.py`. `TransporteSefaz` continua o único ponto que o constrói (e que aplica a
guarda de consumo indevido), e este módulo **não importa `frappe`**.

⚠️ Estado de verificação: o envelope e a leitura da resposta vêm de fonte secundária (ver
`fiscal/documento/soap_cte.py`). Nada foi enviado a uma SEFAZ real.
"""

from datetime import datetime

from erpnext_brasil.fiscal.codigos.uf import codigo_da_uf
from erpnext_brasil.fiscal.documento.autorizadores_cte import endpoint
from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.fiscal.documento.resposta_cte import (
	RetornoCte,
	RetornoCteInvalido,
	interpretar_retorno_cte,
)
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap_cte import (
	SERVICO_AUTORIZACAO,
	content_type_autorizacao,
	montar_envelope_autorizacao,
)
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel

__all__ = ["enviar_autorizacao_cte"]


def _chave_do_documento(documento: dict) -> str:
	"""A chave que a camada pura gravou em `infCte/@Id` (`CTe` + 44 dígitos)."""
	return documento["CTe"]["infCte"]["@Id"].removeprefix("CTe")


def _mapear(retorno: RetornoCte, chave_enviada: str) -> RespostaTransmissao:
	"""Traduz a leitura pura para o formato da porta `TransporteFiscal`.

	A chave devolvida em `infProt/chCTe` tem de ser a do documento enviado: se divergir, gravar a
	resposta associaria o protocolo de **outro** CT-e a este.
	"""
	if retorno.chave and retorno.chave != chave_enviada:
		raise RetornoCteInvalido(
			f"A SEFAZ respondeu pela chave {retorno.chave}, mas o documento enviado é {chave_enviada}"
		)

	# O que a SEFAZ disse, guardado cru: sem isto o `xml_retorno` do `Transmissao Fiscal` ficaria `{}`.
	bruto = {
		"cStat": retorno.codigo,
		"xMotivo": retorno.motivo,
		"nProt": retorno.protocolo,
		"chCTe": retorno.chave,
	}

	if retorno.autorizado:
		return RespostaTransmissao(
			codigo=retorno.codigo,
			mensagem=retorno.motivo,
			bruto=bruto,
			autorizacao=Autorizacao(
				protocolo=retorno.protocolo,
				recebido_em=retorno.recebido_em or datetime.now().astimezone(),
				chave_acesso=retorno.chave or chave_enviada,
			),
		)

	return RespostaTransmissao(
		codigo=retorno.codigo, mensagem=retorno.motivo, denegado=retorno.denegado, bruto=bruto
	)


def enviar_autorizacao_cte(documento: dict, contexto: ContextoSefaz) -> RespostaTransmissao:
	"""Envia `documento` (a árvore `CTe` já assinada) e devolve o desfecho — numa só chamada.

	Serializa e envelopa, não recebe XML pronto: mesma razão de `enviar_autorizacao`. A UF vem do
	contexto (a do emitente) e decide tanto o endpoint quanto o `cUF` do cabeçalho SOAP.
	"""
	url = endpoint(contexto.uf, SERVICO_AUTORIZACAO, ambiente=contexto.ambiente)

	if not url:
		raise TransporteIndisponivel(
			f"Não há endpoint confirmado para {SERVICO_AUTORIZACAO!r} do CT-e na UF {contexto.uf!r} "
			f"(ambiente {contexto.ambiente!r})"
		)

	envelope = montar_envelope_autorizacao(para_xml(documento), codigo_da_uf(contexto.uf))

	resposta = contexto.sessao_http.post(
		url,
		data=envelope.encode("utf-8"),
		headers={"Content-Type": content_type_autorizacao()},
		cert=(str(contexto.arquivo_cert), str(contexto.arquivo_chave)),
		timeout=30,
	)
	resposta.raise_for_status()

	return _mapear(interpretar_retorno_cte(resposta.content), _chave_do_documento(documento))
