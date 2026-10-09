# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O instante de emissão (`dhEmi`), com a correção pelo relógio oficial **se** o administrador a ligou.

Tarefa 5.1 de `fonte-de-tempo-ntp-br`. Por padrão devolve exatamente o que `agora_da_emissao()`
sempre devolveu — o relógio do servidor, com o fuso do sistema. Só com `brasil_ntp_corrigir_dhemi:
true` **e** uma medição confiável e recente soma o deslocamento medido.

O dado viaja, não se esconde
----------------------------
A função devolve o momento **e** o deslocamento aplicado (`InstanteDeEmissao`). Quem emite passa o
momento ao mapeador e o deslocamento ao registro do `Transmissao Fiscal`. A alternativa — gravar o
deslocamento num `frappe.flags` para o registrador ler depois — esconderia uma dependência entre
duas etapas que não se enxergam no código, e é o tipo de acoplamento invisível que este app evita.

Duas consequências de corrigir, que são o motivo de a opção nascer desligada
-----------------------------------------------------------------------------
- O documento passa a carregar uma hora **diferente da do banco e do sistema** (`creation`,
  `modified`). O deslocamento fica gravado para a diferença ser explicável.
- O `AAMM` da chave de acesso sai de `dhEmi`; perto da virada do mês a correção pode empurrá-lo para
  o mês seguinte. Chave e `dhEmi` continuam coerentes porque nascem do mesmo instante corrigido
  (travado em `tests/test_instante_de_emissao.py`).
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import frappe

from erpnext_brasil.fiscal.relogio_politica import deslocamento_a_aplicar
from erpnext_brasil.integracao.configuracao_fiscal import agora_da_emissao
from erpnext_brasil.integracao.medicao_do_relogio import configuracao, ler_ultima

__all__ = ["InstanteDeEmissao", "instante_de_emissao"]


@dataclass(frozen=True)
class InstanteDeEmissao:
	momento: datetime
	"""Com fuso: o XSD recusa `dhEmi` sem deslocamento."""
	deslocamento_ms: float | None = None
	"""O que foi somado ao relógio do servidor; `None` quando nada foi aplicado."""


def instante_de_emissao() -> InstanteDeEmissao:
	"""O momento da emissão e o deslocamento aplicado a ele (ou `None`)."""
	momento = agora_da_emissao()
	correcao = deslocamento_a_aplicar(ler_ultima(), time.time(), configuracao())

	if correcao.motivo:
		frappe.logger("erpnext_brasil").warning(correcao.motivo)

	if correcao.segundos is None:
		return InstanteDeEmissao(momento)

	return InstanteDeEmissao(momento + timedelta(seconds=correcao.segundos), correcao.segundos * 1000)
