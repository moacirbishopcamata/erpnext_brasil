# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial: leitura de XML → os tipos puros de `esocial_retorno.py`.

`esocial_retorno.py` modela `RetornoEnvioLote`/`RetornoProcessamentoLote` como dados
já prontos — mas nada no projeto ainda sabia produzi-los a partir do XML de verdade
que o eSocial devolve. Este módulo fecha essa lacuna, mesmo papel de
`fiscal/documento/resposta_sefaz.interpretar_autorizacao` para a NF-e: interpreta o
XML já isolado do envelope SOAP (o que `esocial_soap.extrair_resultado` devolve), sem
decidir o que fazer com o resultado.

Estrutura confirmada diretamente nos XSDs, não suposta por semelhança com a NF-e
------------------------------------------------------------------------------------------
`RetornoEnvioLoteEventos-v1_1_0.xsd` e `RetornoProcessamentoLote-v1_3_0.xsd`
(`nfephp-org/sped-esocial`, `schemes/comunicacao/v1_5_0/`) confirmam campo a campo os
nomes que `esocial_retorno.StatusRetorno`/`Ocorrencia`/`DadosRecepcaoLote` já
declaravam (`cdResposta`/`descResposta`/`ocorrencias/ocorrencia/codigo,descricao,
tipo,localizacao`, `dadosRecepcaoLote/dhRecepcao,versaoAplicativoRecepcao,
protocoloEnvio`) — a leitura do XSD aqui é confirmação, não descoberta de campo novo.

O que fica de fora, deliberadamente
------------------------------------------
`dadosProcessamentoLote/versaoAplicativoProcessamentoLote` (só no retorno de
processamento) não é capturado — `RetornoProcessamentoLote` não tem campo para ele, e
criar um só para este dado de baixo valor (versão do aplicativo que processou,
irrelevante para decidir sucesso/pendência/erro) não parecia justificar mexer num
dataclass já usado — mesma disciplina de não modelar tudo que o XSD permite, só o que
tem uso real.

Funções puras: nenhuma dependência do Frappe, `lxml` só na leitura (import tardio,
mesmo motivo dos outros módulos do bloco eSocial).
"""

from erpnext_brasil.folha.esocial_retorno import (
	DadosRecepcaoLote,
	EsocialRetornoInvalido,
	Ocorrencia,
	RetornoEnvioLote,
	RetornoEvento,
	RetornoProcessamentoLote,
	StatusRetorno,
)

__all__ = ["ler_retorno_envio_lote", "ler_retorno_processamento_lote"]


def _raiz(xml: str | bytes):
	from lxml import etree

	bruto = xml.encode("utf-8") if isinstance(xml, str) else xml

	try:
		return etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise EsocialRetornoInvalido(f"Resposta do eSocial não é XML válido: {e}") from e


def _filho(no, nome: str):
	encontrados = no.xpath(f"*[local-name()='{nome}']")

	return encontrados[0] if encontrados else None


def _texto(no, nome: str) -> str | None:
	elemento = _filho(no, nome)

	return elemento.text.strip() if elemento is not None and elemento.text else None


def _ler_status(no_status) -> StatusRetorno:
	ocorrencias = []
	no_ocorrencias = _filho(no_status, "ocorrencias")

	if no_ocorrencias is not None:
		for no_ocorrencia in no_ocorrencias.xpath("*[local-name()='ocorrencia']"):
			ocorrencias.append(
				Ocorrencia(
					codigo=int(_texto(no_ocorrencia, "codigo")),
					descricao=_texto(no_ocorrencia, "descricao") or "",
					tipo=int(_texto(no_ocorrencia, "tipo")),
					localizacao=_texto(no_ocorrencia, "localizacao"),
				)
			)

	return StatusRetorno(
		cd_resposta=int(_texto(no_status, "cdResposta")),
		desc_resposta=_texto(no_status, "descResposta") or "",
		ocorrencias=tuple(ocorrencias),
	)


def _ler_dados_recepcao(no_raiz) -> DadosRecepcaoLote | None:
	no_dados = _filho(no_raiz, "dadosRecepcaoLote")

	if no_dados is None:
		return None

	return DadosRecepcaoLote(
		protocolo_envio=_texto(no_dados, "protocoloEnvio") or "",
		dh_recepcao=_texto(no_dados, "dhRecepcao"),
		versao_aplicativo_recepcao=_texto(no_dados, "versaoAplicativoRecepcao"),
	)


def ler_retorno_envio_lote(xml_resposta: str | bytes) -> RetornoEnvioLote:
	"""Interpreta `retornoEnvioLoteEventos` — a resposta imediata ao enviar um lote.

	Recebe o XML já isolado do envelope SOAP (o que `esocial_soap.extrair_resultado`
	devolve), não a resposta HTTP crua.
	"""
	raiz = _raiz(xml_resposta)
	no_corpo = _filho(raiz, "retornoEnvioLoteEventos")
	corpo = no_corpo if no_corpo is not None else raiz

	no_status = _filho(corpo, "status")

	if no_status is None:
		raise EsocialRetornoInvalido(
			"Resposta sem elemento 'status' — não é um retornoEnvioLoteEventos reconhecível"
		)

	return RetornoEnvioLote(status=_ler_status(no_status), dados_recepcao=_ler_dados_recepcao(corpo))


def ler_retorno_processamento_lote(xml_resposta: str | bytes) -> RetornoProcessamentoLote:
	"""Interpreta `retornoProcessamentoLoteEventos` — a resposta completa, consultada
	com o `protocolo_envio` de um `RetornoEnvioLote` anterior."""
	raiz = _raiz(xml_resposta)
	no_corpo = _filho(raiz, "retornoProcessamentoLoteEventos")
	corpo = no_corpo if no_corpo is not None else raiz

	no_status = _filho(corpo, "status")

	if no_status is None:
		raise EsocialRetornoInvalido(
			"Resposta sem elemento 'status' — não é um retornoProcessamentoLoteEventos reconhecível"
		)

	eventos = []
	no_retorno_eventos = _filho(corpo, "retornoEventos")

	if no_retorno_eventos is not None:
		for no_evento in no_retorno_eventos.xpath("*[local-name()='evento']"):
			no_retorno_evento = _filho(no_evento, "retornoEvento")
			conteudo = _conteudo_opaco(no_retorno_evento)

			eventos.append(
				RetornoEvento(
					id_evento=no_evento.get("Id") or "",
					xml_retorno=conteudo,
					evento_duplicado=(no_evento.get("evtDupl") or "false").lower() == "true",
				)
			)

	return RetornoProcessamentoLote(
		status=_ler_status(no_status),
		eventos=tuple(eventos),
		dados_recepcao=_ler_dados_recepcao(corpo),
	)


def _conteudo_opaco(no) -> str:
	"""Serializa o conteúdo de `retornoEvento` (`TArquivoEsocial`, `xs:any`) como XML
	opaco — mesma decisão já registrada em `esocial_retorno.RetornoEvento`: o schema
	de verdade por dentro não foi localizado, então não se finge de interpretado."""
	from lxml import etree

	filhos = list(no) if no is not None else []

	if not filhos:
		return (no.text or "").strip() if no is not None else ""

	return etree.tostring(filhos[0], encoding="unicode")
