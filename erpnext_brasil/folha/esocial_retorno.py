# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial: leitura da resposta de envio e de processamento de lote.

Continuação da camada de transporte, depois de `esocial_lote.py` (o envelope de
envio). Aqui é a direção contrária: interpretar o que o eSocial devolve — a resposta
imediata ao enviar (`RetornoEnvioLoteEventos`, "recebi o lote, aqui está o protocolo")
e a resposta de processamento por evento, consultada depois com esse protocolo
(`RetornoProcessamentoLote`, "cada evento do lote foi aceito ou rejeitado, e por
quê"). Mesma separação de `fiscal/documento/resposta_sefaz.py` interpretar a resposta
da SEFAZ como dado puro, sem decidir o que fazer com ela — isso é responsabilidade de
quem chama.

`RetornoProcessamentoLote` estruturalmente confirma o limite de 50
------------------------------------------------------------------------------
`docs/rh-esocial-lote.md` registrou que o envelope de **envio**
(`EnvioLoteEventos-v1_1_1.xsd`) declara `eventos`/`evento` como `maxOccurs="unbounded"`
— o limite de 50 ali é regra de negócio, não do schema. Este módulo lê um XSD
diferente (`RetornoProcessamentoLote-v1_3_0.xsd`), e nele `retornoEventos/evento` **é**
`maxOccurs="50"` — um limite estrutural de verdade, do lado da resposta. As duas
fontes concordam no número (50), uma sem confirmação estrutural e outra com — o
achado aqui reforça, mas não substitui, a advertência já registrada em
`esocial_lote.py` sobre a fonte do lado do envio.

Códigos de `cdResposta`: parcialmente confirmados, não uma tabela completa
------------------------------------------------------------------------------------
O XSD não enumera valores de `cdResposta` (é `xs:int` livre) — os códigos abaixo vêm
de busca agregada, não do Manual de Orientação do Desenvolvedor lido diretamente
nesta rodada. Mesma cautela de `cnab400_retorno.CODIGOS_OCORRENCIA_CORROBORADOS`:
só os cinco códigos mais citados são usados nas propriedades (`sucesso`/`pendente`),
qualquer outro código não vira "sucesso" nem "pendente" por omissão — fica só como
"nem um nem outro", nunca assumido.

Fonte do XSD: mesma família já usada em `esocial_lote.py`
------------------------------------------------------------------------
`github.com/nfephp-org/sped-esocial`, `schemes/comunicacao/v1_5_0/`
(`RetornoEnvioLoteEventos-v1_1_0.xsd`, `RetornoProcessamentoLote-v1_3_0.xsd`) — não a
fonte primária oficial, mesma advertência já registrada para os outros módulos de
eSocial deste projeto.

Funções puras: nenhuma dependência do Frappe, nenhuma chamada de rede.
"""

from dataclasses import dataclass

from erpnext_brasil.folha.esocial_consulta import protocolo_e_valido

__all__ = [
	"CODIGO_ERRO_PREENCHIMENTO",
	"CODIGO_ERRO_SERVIDOR",
	"CODIGO_LOTE_JA_RECEBIDO_EM_FILA",
	"CODIGO_LOTE_RECEBIDO_COM_ADVERTENCIAS",
	"CODIGO_LOTE_RECEBIDO_SUCESSO",
	"CODIGOS_SUCESSO",
	"LIMITE_MAXIMO_EVENTOS_NO_RETORNO",
	"TIPO_OCORRENCIA_AVISO",
	"TIPO_OCORRENCIA_ERRO",
	"DadosRecepcaoLote",
	"EsocialRetornoInvalido",
	"Ocorrencia",
	"RetornoEnvioLote",
	"RetornoEvento",
	"RetornoProcessamentoLote",
	"StatusRetorno",
	"eventos_com_erro",
]

# Códigos de cdResposta confirmados por busca agregada — não uma tabela completa
# (ver docstring do módulo).
CODIGO_LOTE_RECEBIDO_SUCESSO = 201
CODIGO_LOTE_RECEBIDO_COM_ADVERTENCIAS = 202
CODIGO_LOTE_JA_RECEBIDO_EM_FILA = 203
CODIGO_ERRO_SERVIDOR = 301
CODIGO_ERRO_PREENCHIMENTO = 401

CODIGOS_SUCESSO = frozenset({CODIGO_LOTE_RECEBIDO_SUCESSO, CODIGO_LOTE_RECEBIDO_COM_ADVERTENCIAS})

TIPO_OCORRENCIA_ERRO = 1
TIPO_OCORRENCIA_AVISO = 2

# Confirmado estruturalmente no XSD de retorno (`maxOccurs="50"`) — ver docstring.
LIMITE_MAXIMO_EVENTOS_NO_RETORNO = 50

_TAMANHO_MAXIMO_DESCRICAO = 2048


class EsocialRetornoInvalido(ValueError):
	"""Dado que impede a leitura da resposta — campo fora do padrão do XSD."""


@dataclass(frozen=True)
class Ocorrencia:
	"""Uma linha de `ocorrencias/ocorrencia` — um erro ou aviso associado a um
	status. `tipo`: 1 = erro, 2 = aviso (`TIPO_OCORRENCIA_ERRO`/`_AVISO`)."""

	codigo: int
	descricao: str
	tipo: int
	localizacao: str | None = None

	def __post_init__(self):
		if self.tipo not in (TIPO_OCORRENCIA_ERRO, TIPO_OCORRENCIA_AVISO):
			raise EsocialRetornoInvalido(f"tipo de ocorrência deve ser 1 (erro) ou 2 (aviso), recebido {self.tipo}")

		if len(self.descricao) > _TAMANHO_MAXIMO_DESCRICAO:
			raise EsocialRetornoInvalido(f"descricao excede {_TAMANHO_MAXIMO_DESCRICAO} caracteres")

		if self.localizacao is not None and len(self.localizacao) > _TAMANHO_MAXIMO_DESCRICAO:
			raise EsocialRetornoInvalido(f"localizacao excede {_TAMANHO_MAXIMO_DESCRICAO} caracteres")


@dataclass(frozen=True)
class StatusRetorno:
	"""`status` (`TStatus`) — presente tanto no retorno do lote inteiro quanto,
	replicado, no retorno de cada evento (`RetornoEvento.status`).

	`sucesso`/`pendente` só reconhecem os códigos confirmados em
	`CODIGOS_SUCESSO`/`CODIGO_LOTE_JA_RECEBIDO_EM_FILA` — qualquer outro código não é
	nem sucesso nem pendente por omissão, é só "nenhum dos dois confirmados" (mesma
	disciplina de `cnab400_retorno.foi_pago` nunca assumir um código não tabelado).
	"""

	cd_resposta: int
	desc_resposta: str
	ocorrencias: tuple[Ocorrencia, ...] = ()
	tempo_estimado_conclusao: int | None = None

	def __post_init__(self):
		if len(self.desc_resposta) > _TAMANHO_MAXIMO_DESCRICAO:
			raise EsocialRetornoInvalido(f"descResposta excede {_TAMANHO_MAXIMO_DESCRICAO} caracteres")

	@property
	def sucesso(self) -> bool:
		return self.cd_resposta in CODIGOS_SUCESSO

	@property
	def pendente(self) -> bool:
		return self.cd_resposta == CODIGO_LOTE_JA_RECEBIDO_EM_FILA

	@property
	def tem_erro(self) -> bool:
		return any(o.tipo == TIPO_OCORRENCIA_ERRO for o in self.ocorrencias)


@dataclass(frozen=True)
class DadosRecepcaoLote:
	"""`dadosRecepcaoLote` (`TDadosRecepcao`) — carrega o `protocolo_envio`, a chave
	usada depois para consultar o processamento
	(`esocial_consulta.montar_consulta_lote_eventos`, `esocial_lote.endpoint`).

	Formato de `protocolo_envio` confirmado contra `ConsultaLoteEventos-v1_0_0.xsd`
	(`esocial_consulta.PADRAO_PROTOCOLO_ENVIO`) — "A.B." + 19 dígitos sequenciais —
	desde que `esocial_consulta.py` leu o XSD que documenta esse formato
	explicitamente; a ressalva anterior ("formato não confirmado, só o tamanho
	validado") não vale mais para este campo."""

	protocolo_envio: str
	dh_recepcao: str | None = None
	versao_aplicativo_recepcao: str | None = None

	def __post_init__(self):
		if not protocolo_e_valido(self.protocolo_envio):
			raise EsocialRetornoInvalido(
				f"protocoloEnvio deve seguir o formato 'A.B.' + 19 dígitos "
				f"(ex. '1.1.0000000000000000001'), recebido {self.protocolo_envio!r}"
			)


@dataclass(frozen=True)
class RetornoEnvioLote:
	"""`retornoEnvioLoteEventos` — a resposta imediata ao enviar um lote
	(`esocial_lote.LoteEventos`). `dados_recepcao` só existe quando o lote foi
	recebido (êxito ou pendente) — em erro de preenchimento não há protocolo."""

	status: StatusRetorno
	dados_recepcao: DadosRecepcaoLote | None = None


@dataclass(frozen=True)
class RetornoEvento:
	"""Uma linha de `retornoEventos/evento` — o resultado do processamento de **um**
	evento específico do lote. `id_evento` casa com o `EventoLote.id_evento` que foi
	enviado (mesma chave, ida e volta). `evento_duplicado` reflete o atributo
	`evtDupl` do XSD — o eSocial já tinha recebido este evento antes (reenvio)."""

	id_evento: str
	status: StatusRetorno
	evento_duplicado: bool = False

	def __post_init__(self):
		if not self.id_evento:
			raise EsocialRetornoInvalido("id_evento não pode ser vazio")


@dataclass(frozen=True)
class RetornoProcessamentoLote:
	"""`retornoProcessamentoLoteEventos` — a resposta completa, consultada com o
	`protocolo_envio` de `RetornoEnvioLote.dados_recepcao`, com o resultado de cada
	evento do lote."""

	status: StatusRetorno
	eventos: tuple[RetornoEvento, ...] = ()
	dados_recepcao: DadosRecepcaoLote | None = None

	def __post_init__(self):
		if len(self.eventos) > LIMITE_MAXIMO_EVENTOS_NO_RETORNO:
			raise EsocialRetornoInvalido(
				f"retornoEventos aceita no máximo {LIMITE_MAXIMO_EVENTOS_NO_RETORNO} eventos, "
				f"recebido {len(self.eventos)}"
			)


def eventos_com_erro(retorno: RetornoProcessamentoLote) -> tuple[RetornoEvento, ...]:
	"""Filtra os eventos do lote cujo processamento teve ao menos um erro — o ponto
	de partida natural para decidir o que reenviar/corrigir, sem que quem chama
	precise conhecer a estrutura de `StatusRetorno`/`Ocorrencia` por dentro."""
	return tuple(evento for evento in retorno.eventos if evento.status.tem_erro)
