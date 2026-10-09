# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Guarda a medição do relógio, mede de hora em hora e avisa a deriva.

Tarefas 2.2, 3.1 e 3.2 de `fonte-de-tempo-ntp-br`. A sonda (`relogio_oficial.py`) e a decisão
(`fiscal/relogio_politica.py`) não conhecem o Frappe; este módulo é a cola: lê `site_config`, guarda
o resultado no cache e entrega o aviso pelo mesmo canal dos outros alertas fiscais.

Por que o cache do Frappe, quando o bloqueio de consumo indevido o recusou
---------------------------------------------------------------------------
`consumo_indevido` guarda em DocType porque **perder** o dado liberaria a transmissão antes da hora
e reiniciaria a contagem da SEFAZ. Aqui é o contrário: perder a medição (Redis reiniciado, cache
limpo) cai em `sem_medicao`, que **nunca bloqueia** — o pior caso é a guarda ficar cega até a
próxima rodada horária. Um DocType por uma leitura que expira em duas horas seria peso sem ganho.

Configuração inválida: degrada, mas não calada
----------------------------------------------
Um valor errado em `site_config` (limite digitado em segundos, por exemplo) cai nos **padrões** e
fica registrado em `Error Log` com o nome da chave. Levantar aqui pararia a emissão fiscal por um
erro de digitação; ignorar em silêncio esconderia que a proteção não está como o administrador
pensa. O registro é o meio-termo.
"""

import time
from collections.abc import Callable

import frappe

from erpnext_brasil.fiscal.relogio_politica import (
	ConfiguracaoInvalida,
	ConfiguracaoRelogio,
	UltimaMedicao,
	avaliar,
	deve_notificar,
	ler_configuracao,
	mensagem_de_alerta,
)
from erpnext_brasil.fiscal.tempo_ntp import Medicao
from erpnext_brasil.integracao.notificacao import notificar_responsaveis
from erpnext_brasil.integracao.relogio_oficial import Rodada, medir_relogio

__all__ = [
	"configuracao",
	"guardar",
	"ler_ultima",
	"medir_e_guardar",
	"servidores_em_pausa",
]

CHAVE_ULTIMA = "erpnext_brasil:relogio:ultima"
CHAVE_AVISO = "erpnext_brasil:relogio:ultimo_aviso"
CHAVE_FALHA = "erpnext_brasil:relogio:ultima_falha_registrada"
PREFIXO_PAUSA = "erpnext_brasil:relogio:pausa:"

RETENCAO_S = 86_400
"""Quanto o cache guarda a última medição. Mais que a validade (`ttl_s`) de propósito: uma medição
vencida continua legível para diagnóstico ("vencida há 5 h"), só não vale para decidir."""

PAUSA_RATE_S = 3_600
"""Quanto tempo um servidor que devolveu `RATE` fica sem ser consultado."""


def _cache():
	"""O cache do Frappe — função no v15, objeto no v16."""
	cache = frappe.cache

	return cache() if callable(cache) else cache


def configuracao() -> ConfiguracaoRelogio:
	"""As chaves de `site_config`, validadas. Inválida → padrões + `Error Log` (ver o módulo)."""
	try:
		return ler_configuracao(frappe.conf)
	except ConfiguracaoInvalida as erro:
		frappe.log_error(title="Fonte de tempo: configuração inválida", message=str(erro))

		return ConfiguracaoRelogio()


def guardar(rodada: Rodada, cache=None) -> None:
	"""Grava a rodada e põe em pausa os servidores que pediram para reduzir a frequência."""
	cache = cache or _cache()
	cache.set_value(
		CHAVE_ULTIMA,
		{
			"deslocamento_ms": rodada.medicao.deslocamento_ms,
			"confiavel": rodada.medicao.confiavel,
			"fontes_responderam": rodada.medicao.fontes_responderam,
			"fontes_concordantes": rodada.medicao.fontes_concordantes,
			"dispersao_ms": rodada.medicao.dispersao_ms,
			"motivo": rodada.medicao.motivo,
			"medida_em": rodada.medida_em,
			"erros": rodada.erros,
		},
		expires_in_sec=RETENCAO_S,
	)

	for servidor in rodada.servidores_rate:
		cache.set_value(PREFIXO_PAUSA + servidor, True, expires_in_sec=PAUSA_RATE_S)


def ler_ultima(cache=None) -> UltimaMedicao | None:
	"""A última medição guardada, ou `None` se não há (ou o conteúdo não é legível).

	**Não** aplica a validade: quem decide se ainda vale é `avaliar`, que conhece o `ttl_s`.
	"""
	cache = cache or _cache()
	bruto = cache.get_value(CHAVE_ULTIMA)

	if not isinstance(bruto, dict) or "medida_em" not in bruto:
		return None

	try:
		medicao = Medicao(
			deslocamento_ms=bruto["deslocamento_ms"],
			confiavel=bool(bruto["confiavel"]),
			fontes_responderam=int(bruto["fontes_responderam"]),
			fontes_concordantes=int(bruto["fontes_concordantes"]),
			dispersao_ms=bruto.get("dispersao_ms"),
			motivo=str(bruto.get("motivo") or ""),
		)

		return UltimaMedicao(
			medicao=medicao, medida_em=float(bruto["medida_em"]), erros=dict(bruto.get("erros") or {})
		)
	except (KeyError, TypeError, ValueError):
		return None


def servidores_em_pausa(servidores, cache=None) -> set[str]:
	cache = cache or _cache()

	return {s for s in servidores if cache.get_value(PREFIXO_PAUSA + s)}


def _registrar_falha_de_medicao(rodada: Rodada, agora: float, cache) -> None:
	"""A causa de "não medido" fica no `Error Log` — no máximo uma vez por dia, para não inundá-lo."""
	ultima = cache.get_value(CHAVE_FALHA)

	if ultima and agora - float(ultima) < 86_400:
		return

	detalhes = "\n".join(f"- {servidor}: {motivo}" for servidor, motivo in rodada.erros.items())
	frappe.log_error(
		title="Fonte de tempo: relógio não medido",
		message=f"{rodada.medicao.motivo}\n{detalhes}\n\nVerifique a saída UDP 123 do servidor para o NTP.br.",
	)
	cache.set_value(CHAVE_FALHA, agora, expires_in_sec=RETENCAO_S)


def medir_e_guardar(
	medir: Callable[..., Rodada] = medir_relogio,
	agora: Callable[[], float] = time.time,
	cache=None,
	notificar: Callable[[str, str, str], int] = notificar_responsaveis,
) -> dict:
	"""A tarefa horária: mede, guarda, registra a falha e avisa a deriva.

	Tudo injetável para teste. Devolve um resumo (nível, desvio, se notificou) útil no console do
	bench. **Nunca levanta por falha de rede**: a sonda já devolve "não medido".
	"""
	cache = cache or _cache()
	config = configuracao()

	rodada = medir(
		config.servidores,
		pausados=servidores_em_pausa(config.servidores, cache),
		dispersao_maxima_ms=config.dispersao_ms,
	)
	guardar(rodada, cache)

	instante = agora()

	if not rodada.medicao.medido:
		_registrar_falha_de_medicao(rodada, instante, cache)

	veredito = avaliar(ler_ultima(cache), instante, config)
	ultimo = cache.get_value(CHAVE_AVISO) or {}
	notificou = False

	if deve_notificar(veredito, ultimo.get("nivel"), ultimo.get("em"), instante):
		assunto, texto = mensagem_de_alerta(veredito, config)

		for company in frappe.get_all("Company", pluck="name"):
			notificar(company, assunto, texto)

		cache.set_value(CHAVE_AVISO, {"nivel": veredito.nivel, "em": instante}, expires_in_sec=RETENCAO_S)
		notificou = True

	return {
		"nivel": veredito.nivel,
		"desvio_ms": veredito.desvio_ms,
		"motivo": veredito.motivo,
		"fontes_responderam": rodada.medicao.fontes_responderam,
		"notificou": notificou,
	}
