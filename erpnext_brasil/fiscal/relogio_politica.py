# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Política do relógio: a configuração validada e o veredito sobre uma medição — sem `frappe`.

O alerta periódico e a guarda de emissão (`fonte-de-tempo-ntp-br`) fazem a **mesma pergunta** — "o
relógio está bom o bastante?" — e por isso a resposta mora numa função só, `avaliar`. Se o alerta e
a guarda tivessem cada um a sua régua, um avisaria que está tudo bem enquanto o outro recusa a
emissão.

Quatro níveis, e o que cada um autoriza
---------------------------------------
- `ok`: desvio abaixo do limite de aviso.
- `aviso`: a partir do limite de aviso — emite e avisa.
- `critico`: a partir do limite crítico — a guarda recusa a emissão.
- `sem_medicao`: não há medição **utilizável** (ausente, vencida, não medida ou não confiável).
  **Nunca bloqueia e nunca alerta deriva**: rede fora, ou fontes que discordam, não é prova de que
  o relógio está errado, e parar a emissão fiscal por isso trocaria um risco por outro maior.

Os limites são **escolha de engenharia**, não prazo da SEFAZ
------------------------------------------------------------
Aviso a partir de 1 s, crítico a partir de 60 s, medição válida por 2 h. A tolerância oficial de
`dhEmi` está no MOC e **não foi verificada** neste projeto; o app já recusa cravar prazo legal sem
fonte (`integracao/alerta_fiscal.py`). Por isso tudo é configurável, e `docs/fonte-de-tempo.md`
registra que a calibração contra o MOC é pendência (tarefa 6.2).

Funções puras: nenhuma dependência do Frappe.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from erpnext_brasil.fiscal.tempo_ntp import DISPERSAO_MAXIMA_MS, Medicao

__all__ = [
	"CHAVES",
	"INTERVALO_DE_REAVISO_S",
	"SERVIDORES_PADRAO",
	"ConfiguracaoInvalida",
	"ConfiguracaoRelogio",
	"UltimaMedicao",
	"Veredito",
	"avaliar",
	"deve_notificar",
	"ler_configuracao",
	"mensagem_de_alerta",
]

INTERVALO_DE_REAVISO_S = 86_400
"""Enquanto o desvio persiste no mesmo nível, o aviso se repete no máximo uma vez por dia: a medição
é horária, e 24 notificações por dia ensinariam o administrador a ignorá-las."""

_GRAVIDADE = {"ok": 0, "sem_medicao": 0, "aviso": 1, "critico": 2}

SERVIDORES_PADRAO = ("a.st1.ntp.br", "b.st1.ntp.br", "c.st1.ntp.br")
"""Três stratum 1 do NTP.br — o mínimo para um consenso de 2 em 3."""

CHAVES = {
	"servidores": "brasil_ntp_servidores",
	"limite_aviso_ms": "brasil_ntp_limite_aviso_ms",
	"limite_critico_ms": "brasil_ntp_limite_critico_ms",
	"ttl_s": "brasil_ntp_ttl_s",
	"dispersao_ms": "brasil_ntp_dispersao_ms",
	"guarda_ligada": "brasil_ntp_guarda",
	"correcao_ligada": "brasil_ntp_corrigir_dhemi",
}
"""As chaves de `site_config.json`, num lugar só: a mensagem de erro cita a chave exata."""

Nivel = Literal["ok", "aviso", "critico", "sem_medicao"]


class ConfiguracaoInvalida(ValueError):
	"""Valor de `site_config` fora do que a política aceita — sempre nomeia a chave."""

	def __init__(self, chave: str, mensagem: str):
		super().__init__(f"{chave}: {mensagem}")
		self.chave = chave


@dataclass(frozen=True)
class ConfiguracaoRelogio:
	servidores: tuple[str, ...] = SERVIDORES_PADRAO
	limite_aviso_ms: float = 1_000.0
	limite_critico_ms: float = 60_000.0
	ttl_s: int = 7_200
	dispersao_ms: float = DISPERSAO_MAXIMA_MS
	guarda_ligada: bool = True
	correcao_ligada: bool = False


@dataclass(frozen=True)
class UltimaMedicao:
	"""A medição guardada, com o instante em que terminou e por que fontes falharam."""

	medicao: Medicao
	medida_em: float
	erros: dict[str, str] = field(default_factory=dict)

	def idade_s(self, agora: float) -> float:
		return agora - self.medida_em


@dataclass(frozen=True)
class Veredito:
	nivel: Nivel
	desvio_ms: float | None = None
	motivo: str = ""
	idade_s: float | None = None


def _numero(conf: Mapping, chave: str, padrao: float, minimo: float, inteiro: bool = False) -> float:
	if chave not in conf or conf[chave] is None:
		return padrao

	valor = conf[chave]

	if isinstance(valor, bool) or not isinstance(valor, int | float):
		raise ConfiguracaoInvalida(chave, f"deve ser um número, recebido {valor!r}")

	if inteiro and valor != int(valor):
		raise ConfiguracaoInvalida(chave, f"deve ser inteiro, recebido {valor!r}")

	if valor < minimo:
		raise ConfiguracaoInvalida(chave, f"deve ser no mínimo {minimo}, recebido {valor!r}")

	return int(valor) if inteiro else float(valor)


def _booleano(conf: Mapping, chave: str, padrao: bool) -> bool:
	if chave not in conf or conf[chave] is None:
		return padrao

	if not isinstance(conf[chave], bool):
		raise ConfiguracaoInvalida(chave, f"deve ser true ou false, recebido {conf[chave]!r}")

	return conf[chave]


def _servidores(conf: Mapping) -> tuple[str, ...]:
	chave = CHAVES["servidores"]

	if chave not in conf or conf[chave] is None:
		return SERVIDORES_PADRAO

	valor = conf[chave]

	if not isinstance(valor, list | tuple) or not all(isinstance(s, str) and s.strip() for s in valor):
		raise ConfiguracaoInvalida(chave, f"deve ser uma lista de nomes de servidor, recebido {valor!r}")

	if len({s.strip().lower() for s in valor}) < 2:
		raise ConfiguracaoInvalida(chave, "precisa de ao menos 2 servidores distintos para haver consenso")

	return tuple(s.strip().lower() for s in valor)


def ler_configuracao(conf: Mapping) -> ConfiguracaoRelogio:
	"""Lê e valida as chaves de `site_config`; ausente vale o padrão, inválido nomeia a chave.

	Validar aqui, e não deixar o valor ruim chegar à guarda, evita o pior caso: um limite crítico
	digitado em segundos (`60`) tomado como milissegundos recusaria toda emissão com 61 ms de desvio.
	"""
	aviso = _numero(conf, CHAVES["limite_aviso_ms"], 1_000.0, minimo=1)
	critico = _numero(conf, CHAVES["limite_critico_ms"], 60_000.0, minimo=1)

	if critico <= aviso:
		raise ConfiguracaoInvalida(
			CHAVES["limite_critico_ms"],
			f"o limite crítico ({critico:g} ms) precisa ser maior que o de aviso ({aviso:g} ms)",
		)

	return ConfiguracaoRelogio(
		servidores=_servidores(conf),
		limite_aviso_ms=aviso,
		limite_critico_ms=critico,
		ttl_s=int(_numero(conf, CHAVES["ttl_s"], 7_200, minimo=60, inteiro=True)),
		dispersao_ms=_numero(conf, CHAVES["dispersao_ms"], DISPERSAO_MAXIMA_MS, minimo=1),
		guarda_ligada=_booleano(conf, CHAVES["guarda_ligada"], True),
		correcao_ligada=_booleano(conf, CHAVES["correcao_ligada"], False),
	)


def avaliar(ultima: UltimaMedicao | None, agora: float, config: ConfiguracaoRelogio) -> Veredito:
	"""O veredito sobre a última medição — a régua única do alerta e da guarda."""
	if ultima is None:
		return Veredito("sem_medicao", motivo="ainda não há medição do relógio")

	idade = ultima.idade_s(agora)

	if idade > config.ttl_s:
		return Veredito(
			"sem_medicao",
			motivo=f"a última medição tem {idade / 60:.0f} min e está vencida (validade {config.ttl_s / 60:.0f} min)",
			idade_s=idade,
		)

	medicao = ultima.medicao

	if not medicao.medido:
		return Veredito("sem_medicao", motivo=medicao.motivo or "o relógio não foi medido", idade_s=idade)

	if not medicao.confiavel:
		return Veredito(
			"sem_medicao",
			desvio_ms=medicao.deslocamento_ms,
			motivo=f"a medição não é confiável: {medicao.motivo}",
			idade_s=idade,
		)

	desvio = medicao.deslocamento_ms
	modulo = abs(desvio)

	if modulo >= config.limite_critico_ms:
		return Veredito("critico", desvio, idade_s=idade)

	if modulo >= config.limite_aviso_ms:
		return Veredito("aviso", desvio, idade_s=idade)

	return Veredito("ok", desvio, idade_s=idade)


def deve_notificar(
	veredito: Veredito,
	ultimo_nivel: str | None,
	ultimo_aviso_em: float | None,
	agora: float,
	intervalo_s: int = INTERVALO_DE_REAVISO_S,
) -> bool:
	"""Avisa quando o desvio **piora de nível** ou, no mesmo nível, depois do intervalo de reaviso.

	`ok` e `sem_medicao` nunca avisam (ver o módulo). Sem aviso anterior, avisa na hora.
	"""
	gravidade = _GRAVIDADE[veredito.nivel]

	if gravidade == 0:
		return False

	if ultimo_nivel is None or ultimo_aviso_em is None:
		return True

	if gravidade > _GRAVIDADE.get(ultimo_nivel, 0):
		return True

	return agora - ultimo_aviso_em >= intervalo_s


def mensagem_de_alerta(veredito: Veredito, config: ConfiguracaoRelogio) -> tuple[str, str]:
	"""`(assunto, texto)` do alerta: o desvio medido, o limite violado e o que fazer."""
	segundos = veredito.desvio_ms / 1000
	sentido = "atrasado" if veredito.desvio_ms > 0 else "adiantado"
	limite = config.limite_critico_ms if veredito.nivel == "critico" else config.limite_aviso_ms
	consequencia = (
		"A emissão de NF-e, CT-e e MDF-e está recusada até o relógio ser corrigido."
		if veredito.nivel == "critico" and config.guarda_ligada
		else "Documentos fiscais emitidos agora levam um instante de emissão (dhEmi) fora da hora legal."
	)

	return (
		"Relógio do servidor fora da Hora Legal Brasileira",
		(
			f"O relógio do servidor está {sentido} cerca de {abs(segundos):.1f} s em relação à Hora Legal "
			f"Brasileira (NTP.br), acima do limite de {limite / 1000:g} s. {consequencia} "
			"Sincronize o servidor com o NTP.br (de preferência com NTS) — ver docs/fonte-de-tempo.md."
		),
	)
