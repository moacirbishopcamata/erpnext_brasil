# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio de `transmitir`/`consultar` via `NFeAutorizacao4`/`NfeConsultaProtocolo4`.

Extraído de `transporte_sefaz.py` pelo mesmo motivo de `eventos_sefaz.py` e
`inutilizacao_sefaz.py`: manter cada módulo de integração abaixo do limite de 320 linhas
que `test_arquitetura.py` impõe, e — a pedido explícito do usuário — fatorar por
responsabilidade em vez de só enxugar prosa para caber no limite. Não é responsabilidade
nova: mesmo transporte, mesma UF/certificado, só outro arquivo. `TransporteSefaz`
continua sendo o único ponto que implementa `TransporteFiscal`.

Funções livres, não métodos de classe: recebem um `ContextoSefaz` já pronto (montado por
`TransporteSefaz`) — mesma disciplina de `eventos_sefaz.py`/`inutilizacao_sefaz.py`.
"""

from datetime import datetime

from erpnext_brasil.fiscal.documento.autorizadores_sefaz import endpoint
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.consulta import montar_cons_reci_nfe, montar_cons_sit_nfe
from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao, ResultadoConsulta
from erpnext_brasil.fiscal.documento.resposta_sefaz import RetornoAutorizacao, interpretar_autorizacao
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap import extrair_resultado, montar_envelope
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel

__all__ = ["consultar_situacao", "enviar_autorizacao"]


def _mapear_resultado(resultado: RetornoAutorizacao) -> RespostaTransmissao:
	"""Traduz a leitura pura da resposta (`RetornoAutorizacao`) para o formato que a
	porta `TransporteFiscal` exige (`RespostaTransmissao`). Nunca é chamada com um
	resultado ainda `pendente` — quem chama resolve o polling antes."""
	if resultado.denegado:
		return RespostaTransmissao(
			codigo=resultado.cstat_nfe or "", mensagem=resultado.motivo_nfe or "", denegado=True
		)

	if resultado.autorizado:
		recebido_em = (
			datetime.fromisoformat(resultado.data_recebimento)
			if resultado.data_recebimento
			else datetime.now().astimezone()
		)

		return RespostaTransmissao(
			codigo=resultado.cstat_nfe,
			mensagem=resultado.motivo_nfe or "",
			autorizacao=Autorizacao(
				protocolo=resultado.protocolo,
				recebido_em=recebido_em,
				chave_acesso=resultado.chave_conferida or "",
			),
		)

	return RespostaTransmissao(
		codigo=resultado.cstat_nfe or resultado.cstat_lote,
		mensagem=resultado.motivo_nfe or resultado.motivo_lote,
	)


def _enviar(servico: str, arvore: dict, modelo: str, contexto: ContextoSefaz) -> RetornoAutorizacao:
	url = endpoint(contexto.uf, servico, ambiente=contexto.ambiente, modelo=modelo)

	if not url:
		raise TransporteIndisponivel(
			f"Não há endpoint confirmado para {servico!r} na UF {contexto.uf!r} "
			f"(ambiente {contexto.ambiente!r}, modelo {modelo!r})"
		)

	xml_interno = para_xml(arvore)
	envelope = montar_envelope(servico, xml_interno)

	resposta = contexto.sessao_http.post(
		url,
		data=envelope.encode("utf-8"),
		headers={"Content-Type": "application/soap+xml; charset=utf-8"},
		cert=(str(contexto.arquivo_cert), str(contexto.arquivo_chave)),
		timeout=30,
	)
	resposta.raise_for_status()

	return interpretar_autorizacao(extrair_resultado(resposta.content))


def _resolver_pendencia(
	resultado: RetornoAutorizacao,
	modelo: str,
	contexto: ContextoSefaz,
	*,
	tp_amb: str,
	dormir,
	tentativas: int,
	intervalo: float,
) -> RetornoAutorizacao:
	"""Consulta o recibo até o lote sair do estado `pendente`, ou desiste. `modelo`
	segue o do lote original (o endpoint de consulta pode ser o de NFC-e)."""
	if not resultado.pendente:
		return resultado

	if not resultado.numero_recibo:
		raise TransporteIndisponivel(
			"Lote pendente sem número de recibo — não há como consultar o resultado depois"
		)

	for _ in range(tentativas):
		dormir(intervalo)

		resultado = _enviar(
			"NFeRetAutorizacao", montar_cons_reci_nfe(resultado.numero_recibo, tp_amb), modelo, contexto
		)

		if not resultado.pendente:
			return resultado

	raise TransporteIndisponivel(
		f"Lote continuou pendente após {tentativas} consultas — "
		"a SEFAZ não decidiu a tempo, não é rejeição nem autorização"
	)


def enviar_autorizacao(
	documento: dict,
	contexto: ContextoSefaz,
	*,
	dormir,
	tentativas_consulta_recibo: int,
	intervalo_consulta_recibo: float,
) -> RespostaTransmissao:
	"""Envia `documento` (a árvore `NFe` já assinada) e resolve até um estado final.

	`documento` é a árvore de `montar_nfe`/`assinar_nfe` — serializa e envelopa, não
	recebe XML pronto. Modelo (`"55"`/`"65"`) lido de `ide.mod`, não de parâmetro à
	parte: uma só fonte, sem risco de documento e parâmetro divergirem.
	"""
	tp_amb = "1" if contexto.ambiente == "producao" else "2"
	modelo = documento["NFe"]["infNFe"]["ide"]["mod"]

	resultado = _enviar("NFeAutorizacao", documento, modelo, contexto)
	resultado = _resolver_pendencia(
		resultado, modelo, contexto,
		tp_amb=tp_amb, dormir=dormir,
		tentativas=tentativas_consulta_recibo, intervalo=intervalo_consulta_recibo,
	)  # fmt: skip

	return _mapear_resultado(resultado)


def consultar_situacao(chave_acesso: str, contexto: ContextoSefaz) -> ResultadoConsulta:
	"""Modelo lido da própria chave (posições 21-22) — mesma razão de `enviar_autorizacao`."""
	tp_amb = "1" if contexto.ambiente == "producao" else "2"
	modelo = ler_chave(chave_acesso).modelo

	resultado = _enviar("NfeConsultaProtocolo", montar_cons_sit_nfe(chave_acesso, tp_amb), modelo, contexto)

	return ResultadoConsulta(
		codigo=resultado.cstat_nfe or resultado.cstat_lote,
		mensagem=resultado.motivo_nfe or resultado.motivo_lote,
		estado_sefaz=resultado.cstat_nfe or resultado.cstat_lote,
	)
