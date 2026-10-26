# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Reserva da medição do relógio: o serviço `hora-legal-br` (HTTP), quando o NTP direto não responde.

Por que existe
--------------
A medição principal (`relogio_oficial.py`) fala NTP/UDP 123 com o NTP.br. Redes corporativas costumam bloquear essa
porta; nesse caso o relógio fica "não medido" e a guarda de emissão e o alerta de deriva ficam cegos. O
`hora-legal-br` é um serviço interno que já fala NTP com o NTP.br e expõe `GET /api/v1/hora` em HTTP, que passa por
qualquer firewall. Este módulo o usa **só como reserva**: a medição direta continua mandando.

Contrato (pré, pós, invariantes)
--------------------------------
- *Pré:* `url` não vazia. Ausência de configuração é estado normal (devolve "não medido", nunca levanta).
- *Pós:* devolve sempre uma `Medicao`. Falha de rede, JSON estranho, resposta `degradado`, atraso alto ou relógio local
  andando para trás viram "não medido" com o motivo — **nunca** um desvio inventado nem zero.
- *Invariante:* uma só fonte nunca é tratada como corroborada além do que é: `fontes_responderam == 1` e a dispersão
  fica `None` (não há com o que comparar), mas a medição conta como confiável porque o próprio serviço já descarta
  amostra ruim e se declara `degradado` quando serve cache.

⚠️ Limite honesto: a resposta HTTP não é autenticada. Numa rede em que isso importa, o serviço deve ficar em
loopback ou rede privada, e a defesa verdadeira continua sendo o daemon de tempo do servidor (chrony com NTS).

Sinal: igual ao de `tempo_ntp.py` — `deslocamento_ms > 0` significa relógio local ATRASADO.

Sem `frappe` e só biblioteca padrão (o app não depende do `sus_brasil`). Rede e relógio injetáveis.
"""

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Any

from erpnext_brasil.fiscal.tempo_ntp import Medicao
from erpnext_brasil.integracao.relogio_oficial import Rodada

__all__ = ["ATRASO_MAXIMO_MS", "CAMINHO", "PRAZO_S", "com_reserva", "medir_pelo_hora_legal"]

CAMINHO = "/api/v1/hora"
PRAZO_S = 2.0
ATRASO_MAXIMO_MS = 500.0

_FRACAO = re.compile(r"(\.\d{6})\d+")


def _nao_medido(motivo: str) -> Medicao:
	return Medicao(
		deslocamento_ms=None,
		confiavel=False,
		fontes_responderam=0,
		fontes_concordantes=0,
		dispersao_ms=None,
		motivo=motivo,
	)


def _unix(texto: str) -> float:
	"""RFC 3339 com fração de até 9 dígitos → segundos Unix."""
	instante = datetime.fromisoformat(_FRACAO.sub(r"\1", texto).replace("Z", "+00:00"))

	if instante.tzinfo is None:
		raise ValueError("instante sem fuso")

	return instante.timestamp()


def medir_pelo_hora_legal(
	url: str,
	*,
	abrir: Callable[..., Any] = urllib.request.urlopen,
	relogio: Callable[[], float] = time.time,
	prazo: float = PRAZO_S,
	atraso_maximo_ms: float = ATRASO_MAXIMO_MS,
) -> Medicao:
	"""Desvio do relógio deste servidor contra a hora legal, pelo ponto médio da ida e volta."""
	if not (url or "").strip():
		return _nao_medido("hora-legal-br não configurado")

	pedido = urllib.request.Request(url.rstrip("/") + CAMINHO, headers={"Accept": "application/json"})
	t0 = relogio()

	try:
		with abrir(pedido, timeout=prazo) as resposta:
			status = getattr(resposta, "status", 200)
			corpo = resposta.read()
	except (urllib.error.URLError, TimeoutError, OSError, ValueError) as erro:
		return _nao_medido(f"hora-legal-br não respondeu: {erro}")

	t3 = relogio()

	if status != 200:
		return _nao_medido(f"hora-legal-br respondeu HTTP {status}")

	try:
		dados = json.loads(corpo)
		utc = _unix(dados["utc"])
		degradado = bool(dados.get("degradado", False))
		fonte = str(dados.get("fonte", ""))
	except (ValueError, KeyError, TypeError) as erro:
		return _nao_medido(f"resposta inesperada do hora-legal-br: {erro}")

	atraso_ms = (t3 - t0) * 1000

	if atraso_ms < 0:
		return _nao_medido("o relógio local andou para trás durante a medida")

	if degradado:
		return _nao_medido(f"hora-legal-br degradado (fonte {fonte or 'desconhecida'})")

	if atraso_ms > atraso_maximo_ms:
		return _nao_medido(f"atraso de {atraso_ms:.0f} ms: medida imprecisa demais")

	deslocamento_ms = (utc - (t0 + t3) / 2) * 1000

	return Medicao(
		deslocamento_ms=deslocamento_ms,
		confiavel=True,
		fontes_responderam=1,
		fontes_concordantes=1,
		dispersao_ms=None,
		motivo=f"hora-legal-br ({fonte or 'fonte não informada'})",
	)


def com_reserva(
	rodada: Rodada,
	url: str,
	agora: Callable[[], float],
	medir_reserva: Callable[[str], Medicao] = medir_pelo_hora_legal,
) -> Rodada:
	"""Se o NTP direto não deu medição confiável, tenta o `hora-legal-br`; a medição direta sempre manda.

	*Pré:* nenhuma. *Pós:* devolve uma `Rodada`; a reserva só **substitui** a medição quando ela mesma é confiável, e a
	causa fica em `erros["hora-legal-br"]` nos dois casos (para o administrador ver por que o NTP direto não valeu).
	Sem URL configurada, devolve a rodada intacta.
	"""
	if rodada.medicao.confiavel or not url:
		return rodada

	reserva = medir_reserva(url)

	if not reserva.confiavel:
		return replace(rodada, erros={**rodada.erros, "hora-legal-br": reserva.motivo})

	return replace(
		rodada,
		medicao=reserva,
		medida_em=agora(),
		erros={**rodada.erros, "hora-legal-br": "usado como reserva: o NTP direto não deu medição confiável"},
	)
