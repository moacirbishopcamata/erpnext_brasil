# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consumo indevido: o erro da SEFAZ em que **tentar de novo é a pior ação possível**.

A regra
-------
`cStat 656 — Consumo indevido pelo aplicativo da empresa` é a resposta da SEFAZ a um
aplicativo que usa os web services fora do padrão dos Manuais de Orientação do
Contribuinte. O efeito: o **CNPJ fica bloqueado por uma hora**, e o desbloqueio é
automático.

O gatilho mais comum é reconsultar um documento depois de um `cStat 137` (*"Nenhum
documento localizado"*) sem esperar o intervalo — o aplicativo interpreta "não achei" como
"tente de novo", e a SEFAZ interpreta a insistência como abuso.

⚠️ A armadilha que inverte o reflexo natural
--------------------------------------------------
Da orientação oficial: *"se retomar a consulta antes de completar 1 (uma) hora, o tempo é
zerado e a contagem reiniciará"*.

Ou seja: **cada tentativa dentro da janela empurra o fim do bloqueio uma hora para a
frente.** Um laço de retentativa — o reflexo de qualquer sistema diante de erro de
transmissão — mantém a empresa bloqueada **indefinidamente**, e quanto mais o operador
insiste, pior fica. É o caso raro em que a resposta certa a um erro é **não fazer nada**.

Por isso a guarda deste módulo é **preventiva, e não de recuperação**: ela existe para
impedir que a requisição saia, não para tratar a resposta depois que saiu. Uma requisição
recusada localmente **não** reinicia o relógio, porque nunca chegou à SEFAZ — e é
exatamente essa diferença que faz a espera terminar.

O que este módulo **não** decide
--------------------------------------
- **Onde o bloqueio é guardado.** É `integracao/consumo_indevido.py` quem persiste, por
  `(CNPJ, ambiente)`. Aqui só existe a aritmética do tempo.
- **Se houve consumo indevido.** Quem diz é a SEFAZ, no `cStat`. Adivinhar por heurística
  local ("consultei demais") criaria um bloqueio que a SEFAZ não impôs.

Vale para NF-e, NFC-e, CT-e e MDF-e: os web services e os MOC são os mesmos.

Funções puras: nenhuma dependência do Frappe, e o "agora" é sempre um parâmetro — data que
o módulo lê do relógio não se testa.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

__all__ = [
	"CARENCIA",
	"CSTAT_CONSUMO_INDEVIDO",
	"CSTAT_NENHUM_DOCUMENTO_LOCALIZADO",
	"Bloqueio",
	"e_consumo_indevido",
	"iniciar_bloqueio",
]

CSTAT_CONSUMO_INDEVIDO = "656"
"""`Rejeição: Consumo indevido pelo aplicativo da empresa`."""

CSTAT_NENHUM_DOCUMENTO_LOCALIZADO = "137"
"""`Nenhum documento localizado`.

Não é rejeição de consumo indevido — é o **gatilho** mais comum dele. Está declarado aqui
para que quem escrever um caminho de reconsulta veja o nome e lembre por quê.
"""

CARENCIA = timedelta(hours=1)
"""Uma hora, com desbloqueio automático.

Não é configurável de propósito: é prazo da SEFAZ, não parâmetro deste app. Um campo
"tempo de espera" convidaria alguém a diminuí-lo, e diminuir é exatamente o que reinicia a
contagem.
"""


def e_consumo_indevido(codigo_status) -> bool:
	"""O `cStat` da resposta é o 656?

	Aceita `str` e `int` porque o `cStat` chega como texto do XML e como número de um
	campo do Desk — comparar tipos diferentes devolveria `False` em silêncio, que aqui
	significa transmitir de novo e estender o bloqueio.
	"""
	if codigo_status is None:
		return False

	return str(codigo_status).strip().lstrip("0") == CSTAT_CONSUMO_INDEVIDO.lstrip("0")


@dataclass(frozen=True)
class Bloqueio:
	"""Uma janela de bloqueio, com início e fim explícitos.

	Guardar o **início** e derivar o fim, em vez de guardar só o fim, é o que permite dizer
	*quando* o bloqueio começou quando alguém perguntar por que a emissão parou.
	"""

	inicio: datetime

	@property
	def liberado_em(self) -> datetime:
		return self.inicio + CARENCIA

	def ativo_em(self, agora: datetime) -> bool:
		"""Ainda bloqueado neste instante?

		Fronteira **inclusiva no fim**: exatamente em `liberado_em` já está liberado. A
		SEFAZ desbloqueia automaticamente ao completar a hora, e esperar um segundo a mais
		não custa nada — mas transmitir um segundo antes custa outra hora.
		"""
		return agora < self.liberado_em

	def restante(self, agora: datetime) -> timedelta:
		"""Quanto falta. Nunca negativo: liberado devolve zero, não tempo passado."""
		falta = self.liberado_em - agora

		return falta if falta > timedelta(0) else timedelta(0)


def iniciar_bloqueio(agora: datetime, anterior: Bloqueio | None = None) -> Bloqueio:
	"""Cria — ou **reinicia** — a janela de bloqueio.

	⚠️ `anterior` existe para tornar visível o que a regra faz: um novo 656 recebido
	**dentro** de uma janela ativa não estende a antiga, **começa outra** a partir de agora.
	O resultado é o mesmo de ignorar `anterior`, e é por isso que o parâmetro parece inútil
	— ele existe para que quem leia o código encontre esta explicação em vez de deduzir
	errado que a janela é fixa desde a primeira rejeição.

	Receber um segundo 656 é sinal de que **alguma requisição escapou da guarda**: se nada
	tivesse saído, a SEFAZ não teria o que rejeitar.
	"""
	del anterior  # documentado acima: a janela nova sempre parte de `agora`

	return Bloqueio(inicio=agora)
