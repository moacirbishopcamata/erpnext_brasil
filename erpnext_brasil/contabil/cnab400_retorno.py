# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura do registro detalhe do arquivo de retorno CNAB 400 (cobrança bancária).

Continua "boleto bancário" no roteiro contábil: depois de montar código de
barras/linha digitável (`boleto.py`), este módulo lê o **arquivo de retorno** que o
banco devolve informando o que aconteceu com cada título — a metade que fecha o
ciclo de conciliação.

Por que só o registro detalhe, e por que a cautela nos códigos
--------------------------------------------------------------------
O CNAB 400 tem cabeçalho (registro tipo `0`), detalhe (tipo `1`, um por título) e
trailer (tipo `9`) — só o detalhe importa para conciliação, por isso é só ele que este
módulo lê. **Cada banco tem seu próprio dialeto de CNAB 400** — confirmado em múltiplas
fontes ao pesquisar: existe uma tabela "padrão" de código de ocorrência, mas bancos
divergem em detalhe. Por isso as posições de byte e a tabela de códigos aqui vêm de uma
única fonte técnica consistente (um provedor de banking-as-a-service regulado, não um
banco específico) — **não foi possível cruzar contra uma segunda fonte posição a
posição**, diferente do rigor que `boleto.py` conseguiu (validado contra exemplo real
publicado). Os quatro códigos mais comuns (`02`, `03`, `06`, `09`) foram corroborados
por busca cruzada independente; os demais da tabela, não — dito explicitamente aqui
para quem for usar isto contra um banco real conferir antes.

O que cada código de ocorrência realmente significa para conciliação
--------------------------------------------------------------------------
Nem todo código representa "o título foi pago". `02` (entrada confirmada) é só a
confirmação de que o banco recebeu o registro do título — não fecha nada.
`FOI_PAGO` cobre só os códigos que representam liquidação de fato (`06` — liquidação
normal; `17` — liquidação após baixa ou título não registrado, o caso de um boleto pago
depois de já ter sido baixado). Tratar `02` como "pago" seria o erro que motivou
separar essa lista — confirmação de entrada não é dinheiro na conta.

Posições do registro detalhe (fonte única, ver cautela acima)
-------------------------------------------------------------------
```
71-82    nosso número (nosso identificador do título, 12 posições)
109-110  código de ocorrência (2 posições)
147-152  data de ocorrência, formato DDMMAA (6 posições)
254-266  valor pago/recebido, 11 inteiros + 2 decimais implícitos (13 posições)
```

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

__all__ = [
	"CODIGOS_OCORRENCIA",
	"CODIGOS_OCORRENCIA_CORROBORADOS",
	"FOI_PAGO",
	"RegistroDetalhe",
	"RetornoCnabInvalido",
	"foi_pago",
	"ler_registro_detalhe",
]

_TAMANHO_REGISTRO = 400

# Confirmado em fonte técnica única (banking-as-a-service regulado) — ver a cautela na
# docstring do módulo. Não é a tabela completa oficial de nenhum banco específico.
CODIGOS_OCORRENCIA = {
	"02": "Entrada confirmada",
	"03": "Entrada rejeitada",
	"06": "Liquidação normal",
	"09": "Baixado automaticamente via arquivo",
	"10": "Baixado conforme instruções da agência",
	"11": "Em ser — arquivo de títulos pendentes",
	"12": "Abatimento concedido",
	"13": "Abatimento cancelado",
	"14": "Protesto do título",
	"16": "Protesto do título rejeitado",
	"17": "Liquidação após baixa ou título não registrado",
	"18": "Acerto de depositária",
	"21": "Acerto do controle do participante",
	"22": "Título com pagamento cancelado",
	"24": "Entrada rejeitada por CEP irregular",
	"27": "Baixa rejeitada",
	"28": "Débito de tarifas/custas",
	"29": "Ocorrências do pagador",
	"32": "Instrução rejeitada",
	"40": "Estorno de pagamento",
}

# Só estes quatro foram corroborados por busca cruzada independente da fonte principal.
CODIGOS_OCORRENCIA_CORROBORADOS = frozenset({"02", "03", "06", "09"})

# Códigos que representam dinheiro de fato recebido — "02" (confirmação de entrada) não
# entra aqui de propósito, é o erro que este conjunto existe para evitar.
FOI_PAGO = frozenset({"06", "17"})


class RetornoCnabInvalido(ValueError):
	"""Linha do arquivo de retorno não tem o formato esperado."""


@dataclass(frozen=True)
class RegistroDetalhe:
	nosso_numero: str
	codigo_ocorrencia: str
	data_ocorrencia: date
	valor: Decimal


def foi_pago(codigo_ocorrencia: str) -> bool:
	"""`True` só para código que representa liquidação de fato — nunca confirmação de
	entrada, mesmo que pareça "positivo" à primeira vista."""
	return codigo_ocorrencia in FOI_PAGO


def _data_ddmmaa(bruto: str) -> date:
	"""`DDMMAA` (2 dígitos de ano) — assume sempre século XXI, não há registro anterior
	a 2000 relevante para conciliação de boleto emitido por este app."""
	if len(bruto) != 6 or not bruto.isdigit():
		raise RetornoCnabInvalido(f"Data de ocorrência deve ter 6 dígitos (DDMMAA), recebido {bruto!r}")

	dia, mes, ano = int(bruto[0:2]), int(bruto[2:4]), int(bruto[4:6])

	try:
		return date(2000 + ano, mes, dia)
	except ValueError as e:
		raise RetornoCnabInvalido(f"Data de ocorrência inválida: {bruto!r} ({e})") from e


def ler_registro_detalhe(linha: str) -> RegistroDetalhe:
	"""Lê os quatro campos relevantes para conciliação de uma linha de 400 posições.

	Não valida o registro inteiro (não confere `codigo_registro` na posição 1, nem
	nenhum outro campo fora dos quatro que a conciliação usa) — só o suficiente para
	responder "este título foi pago, e quando/quanto".
	"""
	if len(linha) != _TAMANHO_REGISTRO:
		raise RetornoCnabInvalido(
			f"Registro de retorno deve ter {_TAMANHO_REGISTRO} posições, recebeu {len(linha)}"
		)

	nosso_numero = linha[70:82].strip()
	codigo_ocorrencia = linha[108:110]
	data_ocorrencia = _data_ddmmaa(linha[146:152])
	valor_bruto = linha[253:266]

	if not valor_bruto.isdigit():
		raise RetornoCnabInvalido(f"Valor deve ser numérico, recebido {valor_bruto!r}")

	valor = Decimal(valor_bruto) / 100

	return RegistroDetalhe(
		nosso_numero=nosso_numero,
		codigo_ocorrencia=codigo_ocorrencia,
		data_ocorrencia=data_ocorrencia,
		valor=valor,
	)
