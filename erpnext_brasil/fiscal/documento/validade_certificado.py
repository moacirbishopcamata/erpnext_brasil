# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Decide **quando** avisar que o certificado A1 está para vencer.

O problema real: o A1 vale um ano, e quando vence a emissão simplesmente para
------------------------------------------------------------------------------------------
`assinador_local.carregar_certificado` já recusa certificado vencido — mas na hora de
emitir, que é o pior momento possível para descobrir. Este módulo é a metade que faltava:
a regra de antecedência, para avisar antes.

Por que a regra não é "avisar todo dia nos últimos 30"
--------------------------------------------------------------
Aviso diário por trinta dias vira ruído, e ruído é ignorado — o alerta perderia
exatamente a função que justifica existir. A regra aqui distingue dois regimes:

- **Marcos** (30, 15 e 7 dias): um aviso em cada, e só nesses dias. Tempo de sobra para
  providenciar a renovação sem incomodar todo dia.
- **Urgência** (3 dias ou menos, e depois de vencido): aviso **todos os dias**, porque
  aí já não há folga e cada dia importa.

Vencido também alerta, e é o caso mais importante — quem deixou passar é justamente
quem mais precisa ser avisado, e é por isso que a leitura da validade
(`assinador_local.expiracao_do_certificado`) foi separada da que recusa vencido.

Puro de propósito: nem criptografia, nem Frappe
------------------------------------------------------
Recebe a data de expiração já lida por quem abriu o arquivo, e o "hoje" por parâmetro —
nada de `date.today()` escondido dentro, que tornaria o comportamento impossível de
testar em qualquer data que não a de hoje.
"""

from dataclasses import dataclass
from datetime import date

__all__ = [
	"DIAS_DE_MARCO",
	"DIAS_DE_URGENCIA",
	"NIVEL_ATENCAO",
	"NIVEL_CRITICO",
	"NIVEL_VENCIDO",
	"AvaliacaoValidade",
	"avaliar_validade",
]

DIAS_DE_MARCO = (30, 15, 7)
"""Dias exatos que geram um aviso pontual — ver docstring do módulo."""

DIAS_DE_URGENCIA = 3
"""A partir daqui (inclusive) o aviso passa a ser diário."""

NIVEL_ATENCAO = "atencao"
NIVEL_CRITICO = "critico"
NIVEL_VENCIDO = "vencido"


@dataclass(frozen=True)
class AvaliacaoValidade:
	"""O resultado da análise: quantos dias faltam e se hoje é dia de avisar.

	`deve_alertar` é separado de `dias_restantes` de propósito: quem chama não precisa
	reimplementar a regra de marcos/urgência para decidir se envia a notificação, e
	assim a regra fica num lugar só.
	"""

	dias_restantes: int
	deve_alertar: bool
	nivel: str = ""

	@property
	def vencido(self) -> bool:
		return self.dias_restantes < 0


def avaliar_validade(expira_em: date, hoje: date) -> AvaliacaoValidade:
	"""Avalia a validade do certificado em relação a `hoje`.

	`dias_restantes` é `0` no próprio dia do vencimento (o certificado ainda vale) e
	negativo depois — a contagem não "pula" o dia do vencimento, que é um dia útil
	inteiro de emissão.
	"""
	dias = (expira_em - hoje).days

	if dias < 0:
		return AvaliacaoValidade(dias_restantes=dias, deve_alertar=True, nivel=NIVEL_VENCIDO)

	if dias <= DIAS_DE_URGENCIA:
		return AvaliacaoValidade(dias_restantes=dias, deve_alertar=True, nivel=NIVEL_CRITICO)

	if dias in DIAS_DE_MARCO:
		return AvaliacaoValidade(dias_restantes=dias, deve_alertar=True, nivel=NIVEL_ATENCAO)

	return AvaliacaoValidade(dias_restantes=dias, deve_alertar=False)


def mensagem(avaliacao: AvaliacaoValidade, empresa: str, expira_em: date) -> str:
	"""Texto do aviso, em português e sem jargão — quem lê é quem vai renovar, não
	quem escreveu o código."""
	quando = expira_em.strftime("%d/%m/%Y")

	if avaliacao.vencido:
		return (
			f"O certificado digital A1 de {empresa} venceu em {quando} "
			f"(há {abs(avaliacao.dias_restantes)} dia(s)). A emissão de documentos "
			"fiscais está bloqueada até a renovação."
		)

	if avaliacao.dias_restantes == 0:
		return (
			f"O certificado digital A1 de {empresa} vence hoje ({quando}). "
			"Depois de hoje, a emissão de documentos fiscais para."
		)

	return (
		f"O certificado digital A1 de {empresa} vence em {avaliacao.dias_restantes} "
		f"dia(s), em {quando}. Providencie a renovação — sem certificado válido a "
		"emissão de documentos fiscais para."
	)
