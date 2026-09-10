# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Contingência off-line da NFC-e: **decidir** o que fazer quando a transmissão não deu certo.

Por que a decisão é um módulo puro
----------------------------------
Três situações chegam parecidas ao mesmo `except` da chamada HTTP, e exigem respostas
**opostas**:

| O que aconteceu | Resposta certa | Por quê |
|---|---|---|
| A SEFAZ **não respondeu** | entrar em contingência | a venda não pode parar |
| A SEFAZ **rejeitou** | recusar | o documento está errado; contingenciar só adia a recusa |
| Guarda local do **656** barrou | recusar | tentar de novo estende o bloqueio |

Decidir dentro do `try/except` da requisição confunde as três — e só é testável com bench e
com a SEFAZ simulada. Aqui a decisão recebe **o que aconteceu** e devolve **o que fazer**,
sem rede, sem relógio e sem Frappe: cada confusão vira um teste de uma linha.

Quem *age* é `integracao/`. Este módulo não emite, não grava e não espera.

A diferença que justifica existir
---------------------------------
A NFC-e admite emissão off-line (`tpEmis = 9`): imprime o cupom sem autorização e transmite
depois, no prazo do Manual. A NF-e modelo 55 **não** admite — a contingência dela é outro
autorizador (SVC), o que é um problema diferente e não passa por aqui.

⚠️ Retransmitir **não é emitir de novo**: a NFC-e em contingência mantém a **mesma chave de
acesso e o mesmo código numérico** da emissão. Chave nova produziria documento diferente do
cupom que o consumidor já levou. Este módulo não gera chave — o aviso está aqui porque é
aqui que alguém decide "vamos contingenciar" e pode supor o contrário.

O que este módulo **não** decide
--------------------------------
- **Quando o prazo venceu.** É aritmética de tempo sobre o registro persistido, e mora com a
  fila, em `integracao/`.
- **Se a SEFAZ respondeu.** Quem sabe é quem fez a chamada. Aqui só se classifica o que ela
  informou.

Fonte: `docs/nfce-contingencia.md` — `tpEmis = 9`, prazo de 24 horas, mesma chave, sem série
distinta, e a expressão obrigatória no cupom.
"""

from enum import Enum

__all__ = [
	"Acao",
	"Resultado",
	"decidir",
	"pode_emitir_em_contingencia",
]


class Resultado(Enum):
	"""O que a tentativa de transmissão produziu, do ponto de vista de quem chamou.

	Não são `cStat`. O `cStat` só existe quando **houve** resposta — e a indisponibilidade,
	que é o caso que motiva a contingência, é justamente a ausência dele. Classificar por
	`cStat` deixaria o caso principal sem nome.
	"""

	AUTORIZADA = "autorizada"
	"""A SEFAZ respondeu e autorizou."""

	REJEITADA = "rejeitada"
	"""A SEFAZ respondeu e recusou. **Houve** resposta: o documento é que está errado."""

	SEM_RESPOSTA = "sem_resposta"
	"""Nenhuma resposta conclusiva — indisponibilidade, tempo esgotado, falha de rede.

	É o único caso de contingência. Note que "demorou e depois rejeitou" **não** é isto.
	"""

	BLOQUEADO = "bloqueado"
	"""A guarda local do consumo indevido (`cStat 656`) impediu a requisição de sair.

	Nada chegou à SEFAZ — e é essa a diferença que faz a espera terminar. Ver
	`fiscal/consumo_indevido.py`.
	"""


class Acao(Enum):
	"""O que fazer com a venda, decidido a partir do `Resultado`."""

	CONCLUIR = "concluir"
	"""Documento autorizado: seguir o fluxo normal."""

	CONTINGENCIAR = "contingenciar"
	"""Emitir off-line, entregar o cupom, transmitir depois."""

	RECUSAR = "recusar"
	"""Não concluir a venda como documento fiscal. O motivo vem de quem chamou."""


def pode_emitir_em_contingencia(emitente_pessoa_fisica: bool) -> bool:
	"""A contingência off-line está disponível para este emitente?

	⚠️ **Não** para emitente Pessoa Física (Produtor Rural, identificado por CPF). O QR Code
	da NFC-e em contingência é o ponto: a versão 2 (hash com CSC) é **rejeição 444** para
	Pessoa Física, e a versão 3 (assinatura), que seria o caminho dela, não está
	implementada — a NT 2025.001 remete o algoritmo a um manual que o portal oficial não
	entrega. Ver `docs/nfce-qrcode.md`.

	Recusar aqui é deliberado, e é o oposto de degradar: emitir mesmo assim produziria um
	cupom **já entregue ao consumidor** que a SEFAZ nunca vai aceitar. Entre não vender e
	vender com documento irrecuperável, não vender é o dano menor — e é o único reversível.
	"""
	return not emitente_pessoa_fisica


def decidir(resultado: Resultado, *, emitente_pessoa_fisica: bool = False) -> Acao:
	"""O que fazer, dado o que a transmissão produziu.

	`emitente_pessoa_fisica` é keyword-only de propósito: é uma condição do **cadastro**, não
	da transmissão, e um booleano posicional ao lado de um `Resultado` seria lido errado na
	chamada.
	"""
	if resultado is Resultado.AUTORIZADA:
		return Acao.CONCLUIR

	if resultado is not Resultado.SEM_RESPOSTA:
		# Rejeitada e bloqueada compartilham a resposta, por motivos diferentes: uma porque o
		# documento está errado, outra porque nada saiu e insistir estende o bloqueio.
		# Contingenciar qualquer uma das duas seria transformar recusa em cupom entregue.
		return Acao.RECUSAR

	if not pode_emitir_em_contingencia(emitente_pessoa_fisica):
		return Acao.RECUSAR

	return Acao.CONTINGENCIAR
