# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cliente SNTP puro: codec do pacote, deslocamento/atraso do relógio e consenso entre servidores.

Por que existe
--------------
Todo documento fiscal leva um instante de emissão (`dhEmi`) lido do relógio do servidor, e nada no
app dizia se esse relógio estava certo. A referência oficial no Brasil é a Hora Legal Brasileira
(Observatório Nacional), disseminada pelo NTP.br (NIC.br) por **NTP** — não por API HTTP. Este módulo
é a parte que não depende de rede nem de `frappe`: montar o pedido, ler a resposta, fazer a conta e
decidir se várias fontes concordam. O socket vive em `integracao/relogio_oficial.py`.

O que é conferido (e por quê)
-----------------------------
- **Eco do carimbo de origem.** A resposta devolve o carimbo de transmissão do pedido
  (`originate`); se não bater, a resposta não é a deste pedido (atrasada, ou forjada por quem não viu
  o pedido). É a única defesa que o SNTP sem NTS tem contra falsificação às cegas — por isso a
  comparação é no inteiro de 64 bits, não em ponto flutuante.
- **Estrato 0 é "kiss-o'-death"** (RFC 5905, 7.4): `RATE` pede para reduzir a frequência. Vira
  `NtpKissOfDeath`, com o código, para quem chama reagir. **Estrato 16** e **indicador de salto 3**
  dizem que o servidor não está sincronizado — a resposta dele não serve de referência.
- **Modo 4 (servidor), versão 3 ou 4, carimbo de transmissão diferente de zero.**

Fórmulas (RFC 5905, 8) com os quatro instantes na ordem em que acontecem — `t0` o cliente envia, `t1`
o servidor recebe, `t2` o servidor responde, `t3` o cliente recebe:

    deslocamento θ = ((t1 − t0) + (t2 − t3)) / 2     >0: o relógio local está ATRASADO
    atraso       δ = (t3 − t0) − (t2 − t1)

Consenso: uma só fonte não basta — SNTP sem autenticação pode ser forjado no caminho. A medição só é
**confiável** quando ao menos `minimo_concordantes` fontes ficam dentro da dispersão tolerada em
torno da mediana.

Limite conhecido: o campo de segundos do NTP tem 32 bits (era 0 termina em 2036). Uma janela de
pivô trata segundos < 2³¹ como era 1, o que vale de 1968 a 2104.

Funções puras: nenhuma dependência do Frappe nem de rede.
"""

import statistics
import struct
from dataclasses import dataclass

__all__ = [
	"DISPERSAO_MAXIMA_MS",
	"MINIMO_CONCORDANTES",
	"Amostra",
	"Medicao",
	"NtpInvalido",
	"NtpKissOfDeath",
	"RespostaNtp",
	"calcular_deslocamento_e_atraso",
	"consolidar",
	"de_ntp",
	"ler_resposta",
	"melhor_amostra",
	"montar_pedido",
	"para_ntp",
]

TAMANHO_DO_PACOTE = 48
SEGUNDOS_1900_A_1970 = 2_208_988_800
_ESCALA_FRACAO = 2**32
_PIVO_DA_ERA = 2**31

MODO_CLIENTE = 3
MODO_SERVIDOR = 4
VERSAO = 4
INDICADOR_NAO_SINCRONIZADO = 3
ESTRATO_KISS = 0
ESTRATO_NAO_SINCRONIZADO = 16

DISPERSAO_MAXIMA_MS = 500.0
"""Quanto duas fontes podem discordar e ainda contar como "concordam". Escolha de engenharia: a rede
de ida e volta tem assimetria, e o que se quer pegar é relógio errado em segundos, não em
milissegundos. Configurável por quem chama."""

MINIMO_CONCORDANTES = 2
"""Fontes que precisam concordar para a medição valer — a defesa contra uma resposta forjada."""


class NtpInvalido(ValueError):
	"""A resposta não serve de referência: curta, de outro pedido, ou de servidor sem sincronia."""


class NtpKissOfDeath(NtpInvalido):
	"""Estrato 0: o servidor pede para o cliente mudar de comportamento (ex.: `RATE`)."""

	def __init__(self, codigo: str):
		super().__init__(f"o servidor devolveu kiss-o'-death {codigo!r}")
		self.codigo = codigo


@dataclass(frozen=True)
class RespostaNtp:
	"""O que importa de uma resposta válida, com os carimbos já em segundos Unix."""

	estrato: int
	versao: int
	t1: float
	"""O servidor recebeu o pedido."""
	t2: float
	"""O servidor transmitiu a resposta."""


@dataclass(frozen=True)
class Amostra:
	servidor: str
	deslocamento_ms: float
	atraso_ms: float
	estrato: int = 1


@dataclass(frozen=True)
class Medicao:
	"""O resultado de consultar várias fontes — dado, não decisão.

	`deslocamento_ms` é `None` quando **nada** foi medido: "não medido" nunca vira zero, porque zero
	diria "o relógio está certo" sem que ninguém tenha olhado.
	"""

	deslocamento_ms: float | None
	confiavel: bool
	fontes_responderam: int
	fontes_concordantes: int
	dispersao_ms: float | None
	motivo: str = ""

	@property
	def medido(self) -> bool:
		return self.deslocamento_ms is not None


def para_ntp(unix: float) -> int:
	"""Segundos Unix → carimbo NTP de 64 bits (32 de segundos + 32 de fração)."""
	segundos = int(unix)
	fracao = int((unix - segundos) * _ESCALA_FRACAO)

	return (((segundos + SEGUNDOS_1900_A_1970) & 0xFFFFFFFF) << 32) | fracao


def de_ntp(carimbo: int) -> float:
	"""Carimbo NTP de 64 bits → segundos Unix, com o pivô de era descrito no módulo."""
	segundos = carimbo >> 32
	fracao = (carimbo & 0xFFFFFFFF) / _ESCALA_FRACAO

	if segundos < _PIVO_DA_ERA:
		segundos += 2**32

	return segundos - SEGUNDOS_1900_A_1970 + fracao


def montar_pedido(t0: float) -> tuple[bytes, int]:
	"""O pacote de pedido (48 bytes, modo cliente) e o carimbo que ele leva.

	O carimbo devolvido é o que a resposta tem de ecoar — quem chama o guarda e o passa a
	`ler_resposta`. Só o campo de transmissão é preenchido, como o SNTP manda.
	"""
	carimbo = para_ntp(t0)
	pacote = bytearray(TAMANHO_DO_PACOTE)
	pacote[0] = (0 << 6) | (VERSAO << 3) | MODO_CLIENTE
	struct.pack_into("!Q", pacote, 40, carimbo)

	return bytes(pacote), carimbo


def ler_resposta(dados: bytes, carimbo_enviado: int) -> RespostaNtp:
	"""Valida e lê a resposta; `NtpInvalido` (ou `NtpKissOfDeath`) quando não serve."""
	if len(dados) < TAMANHO_DO_PACOTE:
		raise NtpInvalido(f"resposta com {len(dados)} bytes; o pacote NTP tem {TAMANHO_DO_PACOTE}")

	primeiro, estrato = dados[0], dados[1]
	indicador, versao, modo = primeiro >> 6, (primeiro >> 3) & 0x7, primeiro & 0x7

	if modo != MODO_SERVIDOR:
		raise NtpInvalido(f"modo {modo} na resposta; esperado {MODO_SERVIDOR} (servidor)")

	if versao not in (3, 4):
		raise NtpInvalido(f"versão {versao} do NTP não suportada")

	origem, recebido, transmitido = struct.unpack_from("!QQQ", dados, 24)

	if origem != carimbo_enviado:
		raise NtpInvalido("o carimbo de origem não bate com o do pedido: resposta de outro pedido")

	if estrato == ESTRATO_KISS:
		raise NtpKissOfDeath(dados[12:16].rstrip(b"\x00").decode("ascii", "replace"))

	if estrato >= ESTRATO_NAO_SINCRONIZADO or indicador == INDICADOR_NAO_SINCRONIZADO:
		raise NtpInvalido(f"servidor não sincronizado (estrato {estrato}, salto {indicador})")

	if transmitido == 0 or recebido == 0:
		raise NtpInvalido("resposta sem carimbo de recepção/transmissão do servidor")

	return RespostaNtp(estrato=estrato, versao=versao, t1=de_ntp(recebido), t2=de_ntp(transmitido))


def calcular_deslocamento_e_atraso(t0: float, t1: float, t2: float, t3: float) -> tuple[float, float]:
	"""`(θ, δ)` em segundos, com `t0..t3` na ordem em que acontecem (ver o módulo)."""
	deslocamento = ((t1 - t0) + (t2 - t3)) / 2
	atraso = (t3 - t0) - (t2 - t1)

	return deslocamento, atraso


def melhor_amostra(amostras: list[Amostra]) -> Amostra | None:
	"""A de menor atraso: é a menos contaminada por fila e assimetria da rede (RFC 5905, 10)."""
	validas = [a for a in amostras if a.atraso_ms >= 0]

	return min(validas, key=lambda a: a.atraso_ms) if validas else None


def _maior_grupo(amostras: list[Amostra], amplitude_maxima_ms: float) -> list[Amostra]:
	"""O maior conjunto de amostras cuja **amplitude** (maior − menor) cabe na tolerância.

	Medir a distância até a mediana não serve: com duas fontes, cada uma fica a metade da diferença da
	mediana, e a tolerância valeria o dobro do que se declara. Empate no tamanho fica com o grupo de
	menor amplitude.
	"""
	ordenadas = sorted(amostras, key=lambda a: a.deslocamento_ms)
	melhor: list[Amostra] = []

	for inicio in range(len(ordenadas)):
		fim = inicio

		while (
			fim + 1 < len(ordenadas)
			and ordenadas[fim + 1].deslocamento_ms - ordenadas[inicio].deslocamento_ms <= amplitude_maxima_ms
		):
			fim += 1

		grupo = ordenadas[inicio : fim + 1]

		if len(grupo) > len(melhor):
			melhor = grupo

	return melhor


def consolidar(
	amostras: list[Amostra],
	dispersao_maxima_ms: float = DISPERSAO_MAXIMA_MS,
	minimo_concordantes: int = MINIMO_CONCORDANTES,
	total_consultado: int | None = None,
) -> Medicao:
	"""Uma amostra (a melhor) por servidor → a medição consolidada.

	`total_consultado` é quantos servidores se tentou, para a mensagem; sem ele usa-se o número de
	amostras. Nenhuma amostra → "não medido" (`deslocamento_ms=None`). Poucas fontes concordando →
	`confiavel=False`, mas o deslocamento da mediana é devolvido para diagnóstico.
	"""
	total = total_consultado if total_consultado is not None else len(amostras)

	if not amostras:
		return Medicao(None, False, 0, 0, None, f"nenhuma das {total} fontes respondeu")

	mediana = statistics.median(a.deslocamento_ms for a in amostras)
	concordantes = _maior_grupo(amostras, dispersao_maxima_ms)
	dispersao = max(a.deslocamento_ms for a in amostras) - min(a.deslocamento_ms for a in amostras)
	consenso = statistics.median(a.deslocamento_ms for a in concordantes)

	if len(concordantes) >= minimo_concordantes:
		return Medicao(consenso, True, len(amostras), len(concordantes), dispersao)

	if len(amostras) < minimo_concordantes:
		motivo = f"só {len(amostras)} de {total} fontes responderam; são necessárias {minimo_concordantes}"
	else:
		motivo = (
			f"as fontes divergem em {dispersao:.0f} ms (tolerância {dispersao_maxima_ms:.0f} ms): "
			f"só {len(concordantes)} concordam, são necessárias {minimo_concordantes}"
		)

	return Medicao(mediana, False, len(amostras), len(concordantes), dispersao, motivo)
