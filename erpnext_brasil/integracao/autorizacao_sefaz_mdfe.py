# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio do MDF-e à SEFAZ: **lote e recibo** (`MDFeRecepcao` + `MDFeRetRecepcao`).

Irmão de `autorizacao_sefaz.py` (NF-e) e de `autorizacao_sefaz_cte.py` (CT-e), e propositalmente não
uma generalização de nenhum dos dois: o envelope tem cabeçalho `mdfeCabecMsg` e corpo `mdfeDadosMsg`
(`soap_mdfe.py`), o lote vai em texto e o resultado tem dois `cStat` (`resposta_mdfe.py`).

O fluxo: envia o `enviMDFe` (um MDF-e, `idLote`) → recebe o `nRec` → consulta o recibo até o lote sair
de "em processamento" → traduz o resultado. `dormir` é injetado, como na NF-e, para a suíte rodar sem
esperar. O MDF-e também tem um serviço síncrono (`MDFeRecepcaoSinc`, GZip+Base64) que **não** é usado:
a tarefa 5.1 pede lote e recibo, e o síncrono é outro envelope.

Estados que não são rejeição nem autorização
---------------------------------------------
Lote ainda em processamento depois das tentativas levanta `TransporteIndisponivel`: a SEFAZ não
decidiu, e gravar "rejeitado" mentiria sobre o que ela disse. O MDF-e fica sem desfecho e a emissão
pode ser retomada pelo recibo (o `nRec` vai na mensagem do erro).

Função livre que recebe um `ContextoSefaz` pronto — `TransporteSefaz` continua o único ponto que o
constrói (e que aplica a guarda de consumo indevido). Não importa `frappe`.

⚠️ Estado de verificação: envelope e leitura vêm de fonte secundária (`sped-mdfe`) e do XSD. Nada foi
enviado a uma SEFAZ real; a prova em homologação depende do certificado A1.
"""

from datetime import datetime

from erpnext_brasil.fiscal.codigos.uf import codigo_da_uf
from erpnext_brasil.fiscal.documento.autorizadores_mdfe import endpoint
from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.fiscal.documento.resposta_mdfe import (
	ReciboLote,
	RespostaMdfeInvalida,
	RetornoLote,
	interpretar_recibo_lote,
	interpretar_retorno_lote,
)
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap_mdfe import (
	SERVICO_LOTE,
	SERVICO_RECIBO,
	content_type,
	montar_consulta_recibo,
	montar_envelope,
	montar_lote,
)
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel

__all__ = ["enviar_autorizacao_mdfe"]


def _chave_do_documento(documento: dict) -> str:
	"""A chave que a camada pura gravou em `infMDFe/@Id` (`MDFe` + 44 dígitos)."""
	return documento["MDFe"]["infMDFe"]["@Id"].removeprefix("MDFe")


def _post(servico: str, interno: str, contexto: ContextoSefaz) -> bytes:
	url = endpoint(contexto.uf, servico, ambiente=contexto.ambiente)

	if not url:
		raise TransporteIndisponivel(
			f"Não há endpoint confirmado para {servico!r} do MDF-e (ambiente {contexto.ambiente!r})"
		)

	envelope = montar_envelope(servico, interno, codigo_da_uf(contexto.uf))
	resposta = contexto.sessao_http.post(
		url,
		data=envelope.encode("utf-8"),
		headers={"Content-Type": content_type(servico)},
		cert=(str(contexto.arquivo_cert), str(contexto.arquivo_chave)),
		timeout=30,
	)
	resposta.raise_for_status()

	return resposta.content


def _mapear(retorno: RetornoLote, chave_enviada: str) -> RespostaTransmissao:
	"""Traduz a leitura pura para a porta `TransporteFiscal`.

	A chave devolvida em `infProt/chMDFe` tem de ser a do documento enviado: se divergir, gravar a
	resposta associaria o protocolo de **outro** manifesto a este.
	"""
	if retorno.chave and retorno.chave != chave_enviada:
		raise RespostaMdfeInvalida(
			f"A SEFAZ respondeu pela chave {retorno.chave}, mas o documento enviado é {chave_enviada}"
		)

	bruto = {
		"cStat": retorno.codigo,
		"xMotivo": retorno.motivo,
		"nProt": retorno.protocolo,
		"chMDFe": retorno.chave,
	}

	if not retorno.autorizado:
		return RespostaTransmissao(codigo=retorno.codigo, mensagem=retorno.motivo, bruto=bruto)

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


def _recusa_do_lote(recibo: ReciboLote) -> RespostaTransmissao:
	"""O lote nem foi recebido (schema inválido, certificado, consumo indevido…): não há recibo."""
	return RespostaTransmissao(
		codigo=recibo.codigo,
		mensagem=recibo.motivo,
		bruto={"cStat": recibo.codigo, "xMotivo": recibo.motivo},
	)


def enviar_autorizacao_mdfe(
	documento: dict,
	contexto: ContextoSefaz,
	*,
	id_lote: str,
	dormir,
	tentativas_consulta_recibo: int,
	intervalo_consulta_recibo: float,
) -> RespostaTransmissao:
	"""Envia `documento` (a árvore `MDFe` já assinada) e resolve até um estado final.

	Serializa e envelopa, não recebe XML pronto. Uma recusa do lote (sem recibo) volta como resposta
	com o `cStat` e o motivo da SEFAZ; lote ainda pendente depois das tentativas levanta
	`TransporteIndisponivel` — não é rejeição nem autorização.
	"""
	ambiente = "1" if contexto.ambiente == "producao" else "2"
	recibo = interpretar_recibo_lote(_post(SERVICO_LOTE, montar_lote(para_xml(documento), id_lote), contexto))

	if not recibo.recebido:
		return _recusa_do_lote(recibo)

	consulta = montar_consulta_recibo(recibo.recibo, ambiente)

	for _ in range(tentativas_consulta_recibo):
		dormir(intervalo_consulta_recibo)
		retorno = interpretar_retorno_lote(_post(SERVICO_RECIBO, consulta, contexto))

		if not retorno.pendente:
			return _mapear(retorno, _chave_do_documento(documento))

	raise TransporteIndisponivel(
		f"Lote {id_lote} (recibo {recibo.recibo}) continuou em processamento após "
		f"{tentativas_consulta_recibo} consultas — a SEFAZ não decidiu a tempo, não é rejeição nem autorização"
	)
