# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Mede o desvio do relógio do servidor contra a Hora Legal Brasileira (servidores do NTP.br).

Tarefa 2.1 de `fonte-de-tempo-ntp-br`. A conta e a decisão de "as fontes concordam" estão em
`fiscal/tempo_ntp.py` (puro); aqui fica só o que toca o mundo — o socket UDP e o relógio —, os dois
**injetáveis**, para que a suíte rode sem rede e sem esperar.

Não importa `frappe`: guardar a medição e ler a configuração é de `medicao_do_relogio.py`. A divisão
mantém a sonda testável sem bench.

Cuidados com um serviço público sem limite declarado
----------------------------------------------------
O NTP.br não publica política de uso (a página só recomenda NTS). Por isso a sonda é
**conservadora**: poucos pacotes por servidor, com pausa entre eles, nunca em laço; um servidor que
devolve `RATE` (kiss-o'-death) deixa de ser consultado nesta rodada e vai para a lista de pausa que
quem chama persiste; e a resposta que vem de **outro endereço** que não o do servidor consultado é
descartada.

⚠️ O que isto **não** é: não autentica (sem NTS) — a defesa é o consenso entre fontes e o eco do
carimbo de origem. Quem precisa de autenticação é o daemon de tempo do servidor (chrony com NTS),
que é o que corrige o relógio de verdade; ver `docs/fonte-de-tempo.md`.
"""

import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from erpnext_brasil.fiscal.relogio_politica import SERVIDORES_PADRAO
from erpnext_brasil.fiscal.tempo_ntp import (
	DISPERSAO_MAXIMA_MS,
	MINIMO_CONCORDANTES,
	Amostra,
	Medicao,
	NtpInvalido,
	NtpKissOfDeath,
	calcular_deslocamento_e_atraso,
	consolidar,
	ler_resposta,
	melhor_amostra,
	montar_pedido,
)

__all__ = [
	"AMOSTRAS_POR_SERVIDOR",
	"PORTA_NTP",
	"PRAZO_POR_PACOTE_S",
	"SERVIDORES_PADRAO",
	"Rodada",
	"medir_relogio",
]

PORTA_NTP = 123
AMOSTRAS_POR_SERVIDOR = 3
PRAZO_POR_PACOTE_S = 2.0
PAUSA_ENTRE_PACOTES_S = 1.0

Transporte = Callable[[str, int, bytes, float], bytes]


@dataclass(frozen=True)
class Rodada:
	"""Uma rodada de medição: o resultado consolidado e o que a explica."""

	medicao: Medicao
	medida_em: float
	"""Instante Unix local da conclusão — a idade da medição se conta daqui."""
	servidores_rate: tuple[str, ...] = ()
	"""Quem devolveu `RATE`: quem chama deve pausá-los por um tempo."""
	erros: dict[str, str] = field(default_factory=dict)
	"""Por servidor, por que não contribuiu — a causa que o administrador precisa ver."""


def _udp(servidor: str, porta: int, pacote: bytes, prazo: float) -> bytes:
	"""Um pedido, uma resposta, e só do endereço consultado."""
	familia, tipo, protocolo, _, endereco = socket.getaddrinfo(servidor, porta, type=socket.SOCK_DGRAM)[0]

	with socket.socket(familia, tipo, protocolo) as soquete:
		soquete.settimeout(prazo)
		soquete.sendto(pacote, endereco)
		dados, origem = soquete.recvfrom(512)

	if origem[0] != endereco[0]:
		raise OSError(f"resposta de {origem[0]}, mas o consultado foi {endereco[0]}")

	return dados


def _consultar(
	servidor: str,
	transporte: Transporte,
	agora: Callable[[], float],
	dormir: Callable[[float], None],
	amostras: int,
	prazo: float,
) -> tuple[Amostra | None, str]:
	"""A melhor amostra do servidor e, se nenhuma serviu, o motivo. `NtpKissOfDeath` sobe."""
	colhidas: list[Amostra] = []
	ultimo_erro = ""

	for numero in range(amostras):
		if numero:
			dormir(PAUSA_ENTRE_PACOTES_S)

		t0 = agora()
		pacote, carimbo = montar_pedido(t0)

		try:
			dados = transporte(servidor, PORTA_NTP, pacote, prazo)
			t3 = agora()
			resposta = ler_resposta(dados, carimbo)
		except NtpKissOfDeath:
			raise
		except (OSError, NtpInvalido) as erro:
			# `TimeoutError` e falha de DNS são `OSError`: ambos são "não respondeu", não bug.
			ultimo_erro = f"{type(erro).__name__}: {erro}"
			continue

		deslocamento, atraso = calcular_deslocamento_e_atraso(t0, resposta.t1, resposta.t2, t3)
		colhidas.append(Amostra(servidor, deslocamento * 1000, atraso * 1000, resposta.estrato))

	return melhor_amostra(colhidas), ultimo_erro or "nenhuma amostra válida"


def medir_relogio(
	servidores: tuple[str, ...] | list[str] = SERVIDORES_PADRAO,
	*,
	transporte: Transporte = _udp,
	agora: Callable[[], float] = time.time,
	dormir: Callable[[float], None] = time.sleep,
	pausados: set[str] | frozenset[str] = frozenset(),
	amostras: int = AMOSTRAS_POR_SERVIDOR,
	prazo: float = PRAZO_POR_PACOTE_S,
	dispersao_maxima_ms: float = DISPERSAO_MAXIMA_MS,
	minimo_concordantes: int = MINIMO_CONCORDANTES,
) -> Rodada:
	"""Consulta os servidores e devolve a rodada. **Nunca levanta por falha de rede.**

	Servidor em `pausados` é pulado (e contado como consultado, para a mensagem dizer a verdade).
	Falha de rede, resposta inválida e `RATE` não derrubam a rodada: viram `erros` e, se for o caso,
	`servidores_rate`. Sem nenhuma resposta, a medição sai como "não medido".
	"""
	melhores: list[Amostra] = []
	erros: dict[str, str] = {}
	rate: list[str] = []

	for servidor in servidores:
		if servidor in pausados:
			erros[servidor] = "em pausa por kiss-o'-death anterior (RATE)"
			continue

		try:
			melhor, motivo = _consultar(servidor, transporte, agora, dormir, amostras, prazo)
		except NtpKissOfDeath as kiss:
			rate.append(servidor)
			erros[servidor] = f"kiss-o'-death {kiss.codigo!r}: a frequência de consulta será reduzida"
			continue

		if melhor is None:
			erros[servidor] = motivo
		else:
			melhores.append(melhor)

	medicao = consolidar(
		melhores,
		dispersao_maxima_ms=dispersao_maxima_ms,
		minimo_concordantes=minimo_concordantes,
		total_consultado=len(servidores),
	)

	return Rodada(medicao=medicao, medida_em=agora(), servidores_rate=tuple(rate), erros=erros)
