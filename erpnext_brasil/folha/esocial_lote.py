# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial: envelope de lote de eventos e endpoints de transmissão/consulta.

Primeiro pedaço da "camada de transporte" do eSocial (`docs/rh-estado-esocial.md`
tinha deixado como fatia à parte, depois de `docs/rh-esocial-s1200.md` ter coberto a
árvore de negócio do evento). Modela só a **estrutura do envelope** — `envioLoteEventos`
com `ideEmpregador`/`ideTransmissor`/`eventos` — e a tabela de endpoints; não modela
assinatura XML nem envio HTTP de verdade (isso ainda depende de decidir se
`fiscal/documento/assinador_local.py` é reaproveitável ou se o formato do envelope do
eSocial exige um assinador próprio — não confirmado nesta rodada, ver
`docs/rh-esocial-lote.md`).

`TIdeEmpregador`/`TIdeTransmissor` do envelope ≠ `TEmpregador` do evento
------------------------------------------------------------------------------
Pegadinha confirmada ao ler o XSD do envelope: `ideEmpregador`/`ideTransmissor` aqui
usam um tipo com `tpInsc` **enumerado** (`1` ou `2` apenas — CNPJ ou CPF), diferente
do `TEmpregador` usado dentro do próprio evento S-1200 (`esocial_s1200.IdeEmpregador`),
cujo XSD só exige um dígito único sem enumerar valores. Mesmo nome de campo, XSD
diferente — por isso este módulo define suas próprias classes
(`IdeEmpregadorLote`/`IdeTransmissorLote`) em vez de reaproveitar as de
`esocial_s1200.py`.

Limite de 50 eventos: regra de negócio, não do XSD
------------------------------------------------------------
O XSD do envelope (`EnvioLoteEventos-v1_1_1.xsd`, `nfephp-org/sped-esocial`) declara
`eventos`/`evento` com `maxOccurs="unbounded"` — sem limite estrutural. O limite de 50
eventos por lote vem de uma regra de negócio documentada em fontes de mercado (não
confirmada por leitura direta do Manual de Orientação do Desenvolvedor oficial nesta
rodada) — `LoteEventos` a aplica como pós-condição própria, sem ela existir no XSD.

Fonte: `github.com/nfephp-org/sped-esocial`, não o `gov.br/esocial` diretamente
------------------------------------------------------------------------------------------
Mesma estratégia de `esocial_s1200.py`: o XSD literal veio de um projeto open-source de
integração fiscal (`schemes/comunicacao/v1_5_0/EnvioLoteEventos-v1_1_1.xsd`), mesma
família do `nfephp-org/sped-nfe` já usado para a NF-e — não a fonte primária.

Funções puras: nenhuma dependência do Frappe, nenhuma chamada de rede.
"""

from dataclasses import dataclass

from erpnext_brasil.folha.esocial_s1200 import AMBIENTE_PRODUCAO, AMBIENTE_PRODUCAO_RESTRITA

__all__ = [
	"AMBIENTE_PRODUCAO",
	"AMBIENTE_PRODUCAO_RESTRITA",
	"LIMITE_MAXIMO_EVENTOS_POR_LOTE",
	"EsocialLoteInvalido",
	"EventoLote",
	"IdeEmpregadorLote",
	"IdeTransmissorLote",
	"LoteEventos",
	"endpoint",
]

# (serviço, ambiente) -> URL. Serviços confirmados: envio e consulta de lote. Cada
# ambiente/serviço tem subdomínio próprio em produção (envio.esocial.gov.br,
# consulta.esocial.gov.br); produção restrita usa o mesmo host para os dois, só o
# caminho muda — assimetria real da fonte, não erro de transcrição.
_ENDPOINTS = {
	("enviarLoteEventos", AMBIENTE_PRODUCAO): (
		"https://webservices.envio.esocial.gov.br/servicos/empregador/"
		"enviarloteeventos/WsEnviarLoteEventos.svc"
	),
	("enviarLoteEventos", AMBIENTE_PRODUCAO_RESTRITA): (
		"https://webservices.producaorestrita.esocial.gov.br/servicos/empregador/"
		"enviarloteeventos/WsEnviarLoteEventos.svc"
	),
	("consultarLoteEventos", AMBIENTE_PRODUCAO): (
		"https://webservices.consulta.esocial.gov.br/servicos/empregador/"
		"consultarloteeventos/WsConsultarLoteEventos.svc"
	),
	("consultarLoteEventos", AMBIENTE_PRODUCAO_RESTRITA): (
		"https://webservices.producaorestrita.esocial.gov.br/servicos/empregador/"
		"consultarloteeventos/WsConsultarLoteEventos.svc"
	),
}

LIMITE_MAXIMO_EVENTOS_POR_LOTE = 50


class EsocialLoteInvalido(ValueError):
	"""Dado que impede a montagem do envelope de lote."""


def endpoint(servico: str, ambiente: int) -> str:
	"""URL do serviço de transmissão/consulta — `servico` em
	`"enviarLoteEventos"`/`"consultarLoteEventos"`, `ambiente` em
	`AMBIENTE_PRODUCAO`/`AMBIENTE_PRODUCAO_RESTRITA`."""
	chave = (servico, ambiente)

	if chave not in _ENDPOINTS:
		raise EsocialLoteInvalido(
			f"Endpoint não confirmado para serviço {servico!r}, ambiente {ambiente!r} — "
			f"serviços conhecidos: {sorted({s for s, _ in _ENDPOINTS})}"
		)

	return _ENDPOINTS[chave]


def _validar_ide(tp_insc: int, nr_insc: str, nome: str) -> None:
	if tp_insc not in (1, 2):
		raise EsocialLoteInvalido(f"tpInsc de {nome} deve ser 1 (CNPJ) ou 2 (CPF), recebido {tp_insc}")

	if not nr_insc.isdigit() or not (8 <= len(nr_insc) <= 15):
		raise EsocialLoteInvalido(
			f"nrInsc de {nome} deve ter entre 8 e 15 dígitos numéricos, recebido {nr_insc!r}"
		)


@dataclass(frozen=True)
class IdeEmpregadorLote:
	"""`ideEmpregador` do envelope de lote (`TIdeEmpregador`) — `tp_insc` enumerado
	(1=CNPJ, 2=CPF), diferente do `TEmpregador` usado dentro do próprio evento S-1200
	(ver docstring do módulo)."""

	tp_insc: int
	nr_insc: str

	def __post_init__(self):
		_validar_ide(self.tp_insc, self.nr_insc, "ideEmpregador")


@dataclass(frozen=True)
class IdeTransmissorLote:
	"""`ideTransmissor` do envelope de lote — quem efetivamente transmite pode ser
	diferente do empregador (ex. um contador que centraliza o envio de vários
	clientes); mesmo formato de `IdeEmpregadorLote`."""

	tp_insc: int
	nr_insc: str

	def __post_init__(self):
		_validar_ide(self.tp_insc, self.nr_insc, "ideTransmissor")


@dataclass(frozen=True)
class EventoLote:
	"""Uma linha de `eventos/evento` — `xml_assinado` é o XML do evento (ex. S-1200)
	já assinado, como texto pronto; este módulo não o produz (a assinatura é a parte
	da camada de transporte que ainda não foi implementada, ver docstring do módulo).
	`id_evento` é o atributo `Id` do elemento `evento` no envelope — usado pelo
	eSocial para casar cada evento do lote com seu resultado de processamento."""

	id_evento: str
	xml_assinado: str

	def __post_init__(self):
		if not self.id_evento:
			raise EsocialLoteInvalido("id_evento não pode ser vazio — é a chave de casamento evento↔resultado")

		if not self.xml_assinado:
			raise EsocialLoteInvalido("xml_assinado não pode ser vazio")


@dataclass(frozen=True)
class LoteEventos:
	"""`envioLoteEventos` — o envelope que agrupa até `LIMITE_MAXIMO_EVENTOS_POR_LOTE`
	eventos assinados para um único envio.

	`grupo` é um atributo obrigatório do elemento raiz — o significado exato dos
	valores (categorias de grupo de eventos) não foi confirmado nesta rodada; só o
	formato (inteiro não negativo) é validado."""

	grupo: int
	ide_empregador: IdeEmpregadorLote
	ide_transmissor: IdeTransmissorLote
	eventos: tuple[EventoLote, ...]

	def __post_init__(self):
		if self.grupo < 0:
			raise EsocialLoteInvalido(f"grupo deve ser um inteiro não negativo, recebido {self.grupo}")

		if not self.eventos:
			raise EsocialLoteInvalido("um lote precisa de ao menos um evento")

		if len(self.eventos) > LIMITE_MAXIMO_EVENTOS_POR_LOTE:
			raise EsocialLoteInvalido(
				f"lote aceita no máximo {LIMITE_MAXIMO_EVENTOS_POR_LOTE} eventos "
				f"(regra de negócio, não do XSD), recebido {len(self.eventos)}"
			)
