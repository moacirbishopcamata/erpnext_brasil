# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio de eventos do CT-e (cancelamento, carta de correção) via `CTeRecepcaoEventoV4`.

Irmão de `eventos_sefaz.py` (que fala `NFeRecepcaoEvento4`) e, como `autorizacao_sefaz_cte.py`,
propositalmente **não** uma generalização dele: o evento do CT-e não tem lote (`envEvento`), a
raiz é `eventoCTe`, o corpo vai em texto no `cteDadosMsg` e a resposta é um `retEventoCTe` direto.

Função livre que recebe um `ContextoSefaz` pronto — `TransporteSefaz` continua o único ponto que o
constrói (e que aplica a guarda de consumo indevido). Não importa `frappe`.

⚠️ Estado de verificação: envelope e resposta vêm de fonte secundária (`sped-cte`) e do XSD; nada
foi enviado a uma SEFAZ real.
"""

from datetime import datetime

from erpnext_brasil.fiscal.codigos.uf import codigo_da_uf
from erpnext_brasil.fiscal.documento.autorizadores_cte import endpoint
from erpnext_brasil.fiscal.documento.evento_cte import assinar_evento_cte
from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.fiscal.documento.resposta_cte import interpretar_retorno_evento_cte
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap_cte import (
	SERVICO_EVENTO,
	content_type_evento,
	montar_envelope_evento,
)
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel

__all__ = ["enviar_evento_cte"]


def enviar_evento_cte(
	evento: dict, contexto: ContextoSefaz, *, chave_acesso: str, assinador
) -> RespostaTransmissao:
	"""Assina, envia o `eventoCTe` e traduz o retorno. Uma requisição, sem lote.

	`autorizacao` só vem preenchida quando a SEFAZ **registrou** o evento (135/136, e 155 no
	cancelamento) — quem chama não repete a tabela de códigos. A chave devolvida em `chCTe` tem de
	ser a do pedido: se divergir, gravar a resposta ligaria o protocolo a outro CT-e.
	"""
	url = endpoint(contexto.uf, SERVICO_EVENTO, ambiente=contexto.ambiente)

	if not url:
		raise TransporteIndisponivel(
			f"Não há endpoint confirmado para {SERVICO_EVENTO!r} do CT-e na UF {contexto.uf!r} "
			f"(ambiente {contexto.ambiente!r})"
		)

	assinado = assinar_evento_cte(evento, assinador)
	envelope = montar_envelope_evento(para_xml(assinado), codigo_da_uf(contexto.uf))

	resposta = contexto.sessao_http.post(
		url,
		data=envelope.encode("utf-8"),
		headers={"Content-Type": content_type_evento()},
		cert=(str(contexto.arquivo_cert), str(contexto.arquivo_chave)),
		timeout=30,
	)
	resposta.raise_for_status()

	retorno = interpretar_retorno_evento_cte(resposta.content)
	bruto = {
		"cStat": retorno.codigo,
		"xMotivo": retorno.motivo,
		"tpEvento": retorno.tipo_evento,
		"nProt": retorno.protocolo,
		"chCTe": retorno.chave,
	}

	if retorno.chave and retorno.chave != chave_acesso:
		raise TransporteIndisponivel(
			f"A SEFAZ respondeu pela chave {retorno.chave}, mas o evento enviado é de {chave_acesso}"
		)

	if not retorno.registrado:
		return RespostaTransmissao(codigo=retorno.codigo, mensagem=retorno.motivo, bruto=bruto)

	return RespostaTransmissao(
		codigo=retorno.codigo,
		mensagem=retorno.motivo,
		bruto=bruto,
		autorizacao=Autorizacao(
			protocolo=retorno.protocolo,
			recebido_em=retorno.registrado_em or datetime.now().astimezone(),
			chave_acesso=retorno.chave or chave_acesso,
		),
	)
