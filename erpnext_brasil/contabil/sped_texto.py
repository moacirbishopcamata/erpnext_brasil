# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Serialização de um registro SPED (linha pipe-delimited) a partir do `dict` que os
`montar_*` deste bloco já produzem.

Por que separado dos módulos que montam cada registro
-----------------------------------------------------------
"Quais valores vão em quais campos" (`efd_icms_ipi.py`, `ecd_i050.py`, `ecd_i150.py`,
`ecd_i200.py`) e "como formatar isso como texto" são responsabilidades diferentes —
resolver as duas juntas arriscaria acertar o valor e errar o formato, ou vice-versa,
sem teste dedicado para cada uma (mesma separação de `fiscal/documento/
serializacao.py`: a árvore de dados primeiro, o formato de texto depois). Esta é a
camada de formato: recebe qualquer um dos `dict`s que este bloco já produz — todos têm
a mesma forma, `{"REG": "...", campo: valor, ...}` — e devolve a linha de texto.

Formato confirmado
-----------------------
- Campos separados por `|`; a linha **começa e termina** com `|`.
- Data: `DDMMAAAA`, **sem separador** (nunca `/` nem `-`) — confirmado explicitamente
  contra uma fonte que chegou a afirmar o contrário (`DD/MM/AAAA`) antes de uma segunda
  busca, com exemplo literal de arquivo real, corrigir isso.
- Numérico: vírgula como separador decimal (`1234,56`, nunca `1234.56`).
- Campo vazio (texto ou data): string vazia entre os dois `|` — nunca preenchido com
  máscara nem `None`/`"None"`.
- Campo de texto **não pode conter `|`** — é o próprio caractere delimitador; um valor
  com `|` dentro seria ambiguidade estrutural, não escapada de nenhum jeito no leiaute.

Funções puras: nenhuma dependência do Frappe.
"""

from datetime import date
from decimal import Decimal

__all__ = ["SpedTextoInvalido", "formatar_campo", "montar_linha"]


class SpedTextoInvalido(ValueError):
	"""Um campo não pode ser representado no formato de texto do SPED."""


def formatar_campo(valor: object) -> str:
	"""Um valor de campo já resolvido (`Decimal`, `date`, `str`, ou vazio) para o texto
	que entra entre dois `|` na linha do SPED.

	`None` e string vazia viram campo vazio — a mesma representação, porque o leiaute
	não distingue "não informado" de "informado como vazio" (não há máscara nem
	sentinela própria para isso).
	"""
	if valor is None or valor == "":
		return ""

	if isinstance(valor, Decimal):
		return str(valor).replace(".", ",")

	if isinstance(valor, date):
		return valor.strftime("%d%m%Y")

	texto = str(valor)

	if "|" in texto:
		raise SpedTextoInvalido(
			f"Campo de texto não pode conter '|' (é o delimitador do próprio formato): {texto!r}"
		)

	return texto


def montar_linha(campos: dict) -> str:
	"""A linha de texto completa de um registro — um `|` antes do primeiro campo, um
	entre cada par, um depois do último.

	Recebe o `dict` que qualquer `montar_*` deste bloco já produz (`REG` incluso como
	primeiro campo) — não conhece o significado de nenhum campo específico, só formata
	na ordem em que o `dict` já os tem (a ordem correta é responsabilidade de quem
	montou o `dict`, não desta função).
	"""
	return "|" + "|".join(formatar_campo(valor) for valor in campos.values()) + "|"
