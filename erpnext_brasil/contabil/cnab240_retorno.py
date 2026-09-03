# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura dos Segmentos T e U do arquivo de retorno CNAB 240 (cobrança bancária).

O sucessor do CNAB 400 já modelado
------------------------------------------
`cnab400_retorno.py` já cobre o formato antigo (400 posições, um banco com dialeto
próprio). O CNAB 240 é o formato federado pela FEBRABAN — mais recente, mais
uniforme entre bancos — e cada título de cobrança no retorno vira **dois**
registros consecutivos: **Segmento T** (identificação do título) seguido de
**Segmento U** (valores e data da ocorrência), não um registro só como no CNAB 400.

Posições confirmadas contra dois bancos independentes, concordantes
------------------------------------------------------------------------------
Diferente do CNAB 400 (uma única fonte técnica, sem segunda fonte para cruzar —
ver `cnab400_retorno.py`), aqui as posições foram lidas nas configurações CNAB 240
de **dois bancos diferentes** (Banco do Brasil e Bradesco,
`glauberportella/cnab-layouts`, projeto open-source de parsing bancário) e batem
posição a posição: `codigo_movimento` em `[16,17]` (presente nos dois segmentos),
`identificacao_titulo` em `[38,57]` (Segmento T), `valor_pago` em `[78,92]` e
`data_ocorrencia` em `[138,145]` (Segmento U). Concordância entre dois bancos
independentes é mais forte que a fonte única do CNAB 400, mas ainda não é a
especificação oficial FEBRABAN lida diretamente (o PDF oficial, como a maioria das
fontes bancárias grandes deste projeto, veio como imagem/fonte codificada,
ilegível às ferramentas de busca).

`codigo_movimento`: hipótese de trabalho, não confirmada como a mesma tabela do CNAB 400
------------------------------------------------------------------------------------------------
O CNAB 240 unificou boa parte do que divergia entre bancos no CNAB 400 — é razoável
supor que a tabela de código de movimento/ocorrência da cobrança seja a mesma
tabela nacional já usada em `cnab400_retorno.CODIGOS_OCORRENCIA`/`FOI_PAGO` (os
valores comuns — `02`, `03`, `06`, `09`, `17` — aparecem exatamente com o mesmo
significado nas fontes consultadas para os dois formatos). Mas isso é uma hipótese
de trabalho, **não uma confirmação de que as duas tabelas são idênticas campo a
campo** — este módulo reaproveita `foi_pago`/`CODIGOS_OCORRENCIA` do CNAB 400
explicitamente marcado como tal, para quem for usar contra um banco real conferir
antes de confiar cegamente.

`identificacao_titulo` não é chamado "nosso número" nas fontes usadas
------------------------------------------------------------------------------------
As duas fontes usam `identificacao_titulo` (Segmento T, 20 posições) para o que
seria o equivalente ao `nosso_numero` do CNAB 400 — mantido com esse nome aqui de
propósito, para não presumir que os dois formatos usam exatamente o mesmo conceito
de identificação por trás de nomes diferentes.

`data_ocorrencia` tem 8 posições aqui (DDMMAAAA), não 6 como no CNAB 400 (DDMMAA)
------------------------------------------------------------------------------------------------
Ano completo, não 2 dígitos — evita a suposição de século que `cnab400_retorno.
_data_ddmmaa` precisa fazer.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.cnab400_retorno import CODIGOS_OCORRENCIA, foi_pago

__all__ = [
	"CODIGOS_OCORRENCIA",
	"RetornoCnab240Invalido",
	"SegmentoT",
	"SegmentoU",
	"foi_pago",
	"ler_segmento_t",
	"ler_segmento_u",
]

_TAMANHO_REGISTRO = 240


class RetornoCnab240Invalido(ValueError):
	"""Linha do arquivo de retorno CNAB 240 não tem o formato esperado."""


@dataclass(frozen=True)
class SegmentoT:
	"""Segmento T — identifica o título e traz o código de movimento (a mesma
	`codigo_movimento` também aparece, repetida, no Segmento U seguinte)."""

	identificacao_titulo: str
	codigo_movimento: str


@dataclass(frozen=True)
class SegmentoU:
	"""Segmento U — valores e data da ocorrência do mesmo título do Segmento T
	imediatamente anterior no arquivo (a relação entre os dois não é verificada
	por este módulo — quem lê o arquivo linha a linha garante o pareamento)."""

	codigo_movimento: str
	valor_pago: Decimal
	data_ocorrencia: date


def _validar_tamanho(linha: str) -> None:
	if len(linha) != _TAMANHO_REGISTRO:
		raise RetornoCnab240Invalido(
			f"Registro CNAB 240 deve ter {_TAMANHO_REGISTRO} posições, recebeu {len(linha)}"
		)


def _data_ddmmaaaa(bruto: str) -> date:
	if len(bruto) != 8 or not bruto.isdigit():
		raise RetornoCnab240Invalido(f"Data de ocorrência deve ter 8 dígitos (DDMMAAAA), recebido {bruto!r}")

	dia, mes, ano = int(bruto[0:2]), int(bruto[2:4]), int(bruto[4:8])

	try:
		return date(ano, mes, dia)
	except ValueError as e:
		raise RetornoCnab240Invalido(f"Data de ocorrência inválida: {bruto!r} ({e})") from e


def ler_segmento_t(linha: str) -> SegmentoT:
	"""Lê `identificacao_titulo` (posições 38-57) e `codigo_movimento`
	(posições 16-17) de uma linha de Segmento T."""
	_validar_tamanho(linha)

	return SegmentoT(
		identificacao_titulo=linha[37:57].strip(),
		codigo_movimento=linha[15:17],
	)


def ler_segmento_u(linha: str) -> SegmentoU:
	"""Lê `codigo_movimento` (16-17), `valor_pago` (78-92, 13 inteiros + 2 decimais
	implícitos) e `data_ocorrencia` (138-145, DDMMAAAA) de uma linha de Segmento U."""
	_validar_tamanho(linha)

	codigo_movimento = linha[15:17]
	valor_bruto = linha[77:92]

	if not valor_bruto.isdigit():
		raise RetornoCnab240Invalido(f"valor_pago deve ser numérico, recebido {valor_bruto!r}")

	valor_pago = Decimal(valor_bruto) / 100
	data_ocorrencia = _data_ddmmaaaa(linha[137:145])

	return SegmentoU(
		codigo_movimento=codigo_movimento, valor_pago=valor_pago, data_ocorrencia=data_ocorrencia
	)
