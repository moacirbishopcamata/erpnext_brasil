# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio da inutilização de faixa de numeração via `NFeInutilizacao4`.

Extraído de `transporte_sefaz.py` pelo mesmo motivo de `eventos_sefaz.py`: manter cada
módulo de integração abaixo do limite de 320 linhas que `test_arquitetura.py` impõe.
Não é uma operação em lote nem assíncrona (diferente de `transmitir` e dos eventos) —
uma única requisição, uma única resposta, um único `cStat`.
"""

from erpnext_brasil.fiscal.documento.autorizadores_sefaz import endpoint
from erpnext_brasil.fiscal.documento.inutilizacao import (
	assinar_inutilizacao,
	interpretar_retorno_inutilizacao,
	montar_inutilizacao,
)
from erpnext_brasil.fiscal.documento.porta import ResultadoInutilizacao
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap import extrair_resultado, montar_envelope
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel

__all__ = ["enviar_inutilizacao"]


def enviar_inutilizacao(
	contexto: ContextoSefaz,
	*,
	cuf: str,
	ano: str,
	cnpj: str,
	modelo: str,
	serie: str,
	numero_inicial: str,
	numero_final: str,
	justificativa: str,
	assinador,
) -> ResultadoInutilizacao:
	"""Monta, assina e envia a inutilização; traduz o `retInutNFe` recebido.

	`contexto.uf` (sigla, para resolver o endpoint) e `cuf` (código IBGE, para o corpo do
	documento) são coisas diferentes — ver `inutilizacao.CODIGO_UF_POR_SIGLA` sobre por
	que essa conversão existe.
	"""
	tp_amb = "1" if contexto.ambiente == "producao" else "2"

	arvore = montar_inutilizacao(
		cuf=cuf,
		ano=ano,
		cnpj=cnpj,
		modelo=modelo,
		serie=serie,
		numero_inicial=numero_inicial,
		numero_final=numero_final,
		justificativa=justificativa,
		ambiente=tp_amb,
	)
	assinada = assinar_inutilizacao(arvore, assinador)

	# modelo já resolve o endpoint específico de NFC-e quando o grupo o tem (ver
	# autorizadores_sefaz.ENDPOINTS_NFCE) — mesma tabela usada por transmitir/consultar.
	url = endpoint(contexto.uf, "NfeInutilizacao", ambiente=contexto.ambiente, modelo=modelo)

	if not url:
		raise TransporteIndisponivel(f"Não há endpoint de NfeInutilizacao confirmado para a UF {contexto.uf!r}")

	xml_interno = para_xml(assinada)
	soap = montar_envelope("NfeInutilizacao", xml_interno)

	resposta = contexto.sessao_http.post(
		url,
		data=soap.encode("utf-8"),
		headers={"Content-Type": "application/soap+xml; charset=utf-8"},
		cert=(str(contexto.arquivo_cert), str(contexto.arquivo_chave)),
		timeout=30,
	)
	resposta.raise_for_status()

	resultado = interpretar_retorno_inutilizacao(extrair_resultado(resposta.content))

	from datetime import datetime

	recebido_em = (
		datetime.fromisoformat(resultado.data_registro) if resultado.data_registro else None
	)

	return ResultadoInutilizacao(
		codigo=resultado.cstat,
		mensagem=resultado.motivo,
		homologada=resultado.homologada,
		protocolo=resultado.protocolo or "",
		recebido_em=recebido_em,
	)
