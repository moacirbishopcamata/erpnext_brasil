# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Recusa a emissão fiscal quando o relógio do servidor está comprovadamente errado.

Tarefa 4.1 de `fonte-de-tempo-ntp-br`. Irmã de `consumo_indevido.garantir_liberado` no espírito —
"recusar antes de chamar a SEFAZ" —, mas com um lugar diferente na cadeia: roda como **primeira
instrução** de cada `emitir_*`, antes de alocar número. A guarda de consumo indevido é injetada no
`TransporteSefaz`, que só nasce depois da alocação; pendurar esta ali queimaria um número da série
a cada recusa (`design.md`, decisão 6).

O que cada veredito faz
-----------------------
- `critico`: `throw` com o desvio medido — nada é alocado, nada é enviado.
- `aviso`: a emissão segue, e o usuário vê o desvio (`msgprint`, não `throw`: mesma distinção que o
  app faz com o ambiente de homologação).
- `sem_medicao` (ausente, vencida, não medida, não confiável): **não bloqueia**. Fica um registro no
  log do app dizendo que a guarda não pôde verificar — registro, e não `Error Log`, porque acontece
  a cada emissão enquanto durar e inundaria a tela de erros.
- Guarda desligada (`brasil_ntp_guarda: false`): nem consulta a medição. O alerta periódico segue.

Lê o cache; **nunca** abre socket. A sonda leva segundos quando uma fonte não responde, e uma emissão
não pode esperar por um serviço público.
"""

import time
from collections.abc import Callable

import frappe
from frappe import _

from erpnext_brasil.fiscal.relogio_politica import (
	Veredito,
	avaliar,
	mensagem_de_alerta,
	mensagem_de_recusa,
)
from erpnext_brasil.integracao.medicao_do_relogio import configuracao, ler_ultima

__all__ = ["garantir_relogio_confiavel"]


def garantir_relogio_confiavel(
	agora: Callable[[], float] = time.time,
	avisar: Callable[..., None] = frappe.msgprint,
) -> Veredito | None:
	"""Levanta se o desvio medido passa do limite crítico; avisa se passa do de aviso.

	Devolve o veredito (para o chamador poder registrar), ou `None` com a guarda desligada.
	"""
	config = configuracao()

	if not config.guarda_ligada:
		return None

	veredito = avaliar(ler_ultima(), agora(), config)

	if veredito.nivel == "critico":
		frappe.throw(mensagem_de_recusa(veredito, config), title=_("Relógio fora da Hora Legal"))

	if veredito.nivel == "aviso":
		avisar(mensagem_de_alerta(veredito, config)[1], title=_("Atenção ao relógio"), indicator="orange")

	if veredito.nivel == "sem_medicao":
		frappe.logger("erpnext_brasil").warning(
			f"Guarda de relógio sem medição utilizável: {veredito.motivo}"
		)

	return veredito
