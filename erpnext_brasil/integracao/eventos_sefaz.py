# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio de eventos da NF-e (cancelamento, carta de correção) via `NFeRecepcaoEvento4`.

Extraído de `transporte_sefaz.py` só por tamanho de arquivo — `test_arquitetura.py`
limita módulo de integração a 320 linhas, e aquele adaptador já cobria
`transmitir`/`consultar` mais os dois eventos. Não é responsabilidade nova: mesmo
transporte, mesma UF/certificado, só outro arquivo. `TransporteSefaz` continua sendo o
único ponto que implementa `TransporteFiscal`; este módulo não é chamado por mais
ninguém.

`enviar_evento` é função livre, não método de classe: recebe os arquivos TLS e a sessão
HTTP já prontos (preparados por `TransporteSefaz`), em vez de duplicar aqui o ciclo de
vida do certificado — a mesma razão de `assinatura.py` não saber montar XML e
`assinador_local.py` não decidir quando assinar.
"""

from datetime import datetime

from erpnext_brasil.fiscal.documento.autorizadores_sefaz import endpoint
from erpnext_brasil.fiscal.documento.evento import (
	assinar_evento,
	interpretar_retorno_evento,
	montar_env_evento,
)
from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap import extrair_resultado, montar_envelope

__all__ = ["TransporteIndisponivel", "enviar_evento"]


class TransporteIndisponivel(RuntimeError):
	"""A SEFAZ não respondeu de forma decidida dentro do que este adaptador tenta.

	Definida aqui e reexportada por `transporte_sefaz.py`, que também a levanta para
	`transmitir`/`consultar` — uma classe só para o mesmo problema, não duas iguais.
	"""


def enviar_evento(
	evento: dict,
	*,
	uf: str,
	ambiente: str,
	chave_acesso: str,
	assinador,
	sessao_http,
	arquivo_cert,
	arquivo_chave,
	protocolo_padrao: str = "",
) -> RespostaTransmissao:
	"""Assina, envia um lote de um único evento via `NFeRecepcaoEvento4` e traduz o
	retorno.

	Compartilhado por `cancelar` e `corrigir` de `TransporteSefaz` — diferem só na
	montagem (`fiscal/documento/evento.py`), não no transporte nem na assinatura.
	`protocolo_padrao` só importa para `cancelar`: uma CC-e homologada sempre ecoa o
	`nProt` da autorização original, não precisa de fallback.
	"""
	evento_assinado = assinar_evento(evento, assinador)
	envelope = montar_env_evento([evento_assinado], id_lote=datetime.now().strftime("%Y%m%d%H%M%S"))

	url = endpoint(uf, "RecepcaoEvento", ambiente=ambiente)

	if not url:
		raise TransporteIndisponivel(f"Não há endpoint de RecepcaoEvento confirmado para a UF {uf!r}")

	xml_interno = para_xml(envelope)
	soap = montar_envelope("RecepcaoEvento", xml_interno)

	resposta = sessao_http.post(
		url,
		data=soap.encode("utf-8"),
		headers={"Content-Type": "application/soap+xml; charset=utf-8"},
		cert=(str(arquivo_cert), str(arquivo_chave)),
		timeout=30,
	)
	resposta.raise_for_status()

	resultado = interpretar_retorno_evento(extrair_resultado(resposta.content))

	if resultado.homologado:
		recebido_em = (
			datetime.fromisoformat(resultado.data_registro)
			if resultado.data_registro
			else datetime.now().astimezone()
		)

		return RespostaTransmissao(
			codigo=resultado.cstat_evento,
			mensagem=resultado.motivo_evento or "",
			autorizacao=Autorizacao(
				protocolo=resultado.protocolo or protocolo_padrao,
				recebido_em=recebido_em,
				chave_acesso=resultado.chave_conferida or chave_acesso,
			),
		)

	return RespostaTransmissao(
		codigo=resultado.cstat_evento or resultado.cstat_lote,
		mensagem=resultado.motivo_evento or resultado.motivo_lote,
	)
