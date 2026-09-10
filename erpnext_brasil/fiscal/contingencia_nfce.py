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

from datetime import datetime, timedelta
from enum import Enum

__all__ = [
	"PRAZO_TRANSMISSAO",
	"Acao",
	"Resultado",
	"SituacaoDaPendencia",
	"classificar_resposta",
	"decidir",
	"deve_tentar_autorizar",
	"exige_tratamento_humano",
	"pode_emitir_em_contingencia",
	"transmitir_ate",
	"venceu_o_prazo",
]

PRAZO_TRANSMISSAO = timedelta(hours=24)
"""Prazo para transmitir a NFC-e emitida em contingência, contado da **emissão**.

Não é configurável: é prazo do Manual de Orientação do Contribuinte, não parâmetro deste
app. Ver `docs/nfce-contingencia.md` — e a ressalva registrada lá, de que as 24 horas foram
confirmadas em portal estadual da SEFAZ, com o portal nacional inacessível às ferramentas.
"""


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


class SituacaoDaPendencia(Enum):
	"""Em que pé está a autorização de um documento emitido em contingência.

	⚠️ Os valores são exatamente as opções do `Select` do DocType `Pendencia Nfce`, e
	`tests/test_pendencia_nfce.py` compara os dois lendo o JSON. Redigitar rótulo bonito de
	um lado é como o Select e o domínio divergem — e `frappe.db.set_value` **não valida
	opções de Select**, então a divergência grava sem erro.
	"""

	PENDENTE = "Pendente"
	"""Emitido em contingência, ainda não transmitido ou sem resposta conclusiva."""

	AUTORIZADA = "Autorizada"
	"""A SEFAZ autorizou depois. Fim de vida da pendência."""

	REJEITADA = "Rejeitada"
	"""A SEFAZ recusou — e o cupom **já está com o consumidor**."""

	DENEGADA = "Denegada"
	"""Denegada: a SEFAZ registrou o documento e proibiu a operação (irregularidade do
	participante). Não é o mesmo que rejeitada, e tratá-las como uma só apagaria o fato de
	que a denegada **fica registrada** no fisco."""


def exige_tratamento_humano(situacao: SituacaoDaPendencia) -> bool:
	"""Esta pendência precisa de alguém, e não de mais uma tentativa?

	Sim para rejeitada e denegada: em ambos os casos existe cupom entregue ao consumidor e
	nenhum documento válido — desfecho que nenhuma retentativa conserta. Deixar isso
	implícito faria a fila continuar tentando contra uma parede, e o problema ficaria
	invisível justamente onde é mais caro.
	"""
	return situacao in (SituacaoDaPendencia.REJEITADA, SituacaoDaPendencia.DENEGADA)


def deve_tentar_autorizar(situacao: SituacaoDaPendencia) -> bool:
	"""Vale gastar uma requisição com esta pendência agora?

	Só a pendente. As outras três já têm desfecho — e insistir sobre elas não é inofensivo:
	é requisição a mais à SEFAZ, que é exatamente o caminho do `cStat 656`.

	⚠️ A idempotência do reprocessamento depende disto **mais** de uma consulta pela chave
	antes de reemitir: a pendência pode ter sido autorizada por uma rodada anterior que não
	chegou a fechar o registro. Esta função sozinha não basta, e dizer que basta seria o
	erro que produz documento em duplicidade.
	"""
	return situacao is SituacaoDaPendencia.PENDENTE


def classificar_resposta(resultado: Resultado) -> SituacaoDaPendencia:
	"""Em que situação a pendência fica depois desta tentativa.

	`SEM_RESPOSTA` e `BLOQUEADO` mantêm **pendente**: nada se soube do documento, e mudar a
	situação por causa de uma falha nossa de transporte apagaria a diferença entre "a SEFAZ
	recusou" e "não conseguimos perguntar". A tentativa fica registrada no contador; a
	situação, não.

	⚠️ `DENEGADA` não sai daqui. Denegação chega como um `cStat` específico dentro de uma
	resposta — e este módulo classifica o **desfecho do transporte**, não o conteúdo dela.
	Quem lê o `cStat` é quem grava; forçar a denegada neste mapa exigiria trazer a tabela de
	`cStat` para cá e misturaria duas responsabilidades.
	"""
	if resultado is Resultado.AUTORIZADA:
		return SituacaoDaPendencia.AUTORIZADA

	if resultado is Resultado.REJEITADA:
		return SituacaoDaPendencia.REJEITADA

	return SituacaoDaPendencia.PENDENTE


def transmitir_ate(emitida_em: datetime) -> datetime:
	"""O instante em que o prazo de transmissão se esgota, derivado da emissão."""
	return emitida_em + PRAZO_TRANSMISSAO


def venceu_o_prazo(emitida_em: datetime, agora: datetime) -> bool:
	"""O prazo já passou?

	Fronteira: **exatamente no limite já venceu** — as 24 horas se completaram.

	⚠️ Não confundir com `consumo_indevido.Bloqueio.ativo_em`, que usa `<`. Parece a mesma
	fronteira e é a **complementar**: lá o estado (bloqueado) *termina* no limite; aqui o
	estado (vencido) *começa* nele. Escrever "igual ao bloqueio" custou um teste vermelho —
	a analogia entre dois prazos vizinhos é exatamente o tipo que engana.

	O "agora" é parâmetro: data que o módulo lê do relógio não se testa.
	"""
	return agora >= transmitir_ate(emitida_em)


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
