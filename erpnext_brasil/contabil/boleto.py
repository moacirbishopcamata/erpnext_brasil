# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Código de barras e linha digitável de boleto bancário (padrão FEBRABAN).

Primeiro incremento de "boleto bancário" no roteiro contábil — item que, apesar de ser
integração bancária de contas a receber, não documento fiscal, pertence a este bloco
por lidar com título e conciliação (mesma nota já registrada na memória do projeto).

O fator de vencimento mudou de base em 2025 — isto não é teoria, é o presente
------------------------------------------------------------------------------------
O "fator de vencimento" é um número de 4 dígitos que conta os dias entre uma data-base
e o vencimento do boleto. A base original, `07/10/1997`, **esgotou em 21/02/2025**
(chegou ao limite de 9999 dígitos representáveis). A partir de **22/02/2025**, o
FEBRABAN (Comunicado FB-009/2023) reiniciou a contagem: `22/02/2025 = 1000`,
`23/02/2025 = 1001`, e assim por diante — nunca mais a base de 1997.

Isto importa **hoje**, não como nota de rodapé histórica: qualquer boleto com
vencimento a partir de 2025-02-22 (ou seja, todo boleto emitido de agora em diante)
usa a base nova. Implementar só a base de 1997 produziria um fator de vencimento
estruturalmente inválido para 100% dos boletos emitidos por este app — o próprio
propósito de existir do módulo. `calcular_fator_vencimento` escolhe a base pela data de
vencimento recebida, não por uma constante fixa no código.

Estrutura do código de barras (44 posições)
--------------------------------------------------
Confirmada em múltiplas fontes técnicas consistentes (a fonte primária, o PDF de layout
da FEBRABAN, é digitalizado como imagem e não pôde ser lido por texto):

```
1-3    banco (3)
4      moeda ("9" para Real)
5      DV geral (módulo 11)
6-9    fator de vencimento (4)
10-19  valor, em centavos, 8 inteiros + 2 decimais (10)
20-44  campo livre, definido por cada banco (25)
```

`campo_livre` **não é modelado aqui** — cada banco tem seu próprio layout interno para
essas 25 posições (nosso número, agência, carteira, etc.), e um layout genérico
"correto" para todos os bancos não existe (mesma razão de `gerar_lancamentos_compra`
receber `creditos_tributarios` já decidido em vez de inferir elegibilidade: a
informação que falta é responsabilidade de quem conhece o banco específico, não deste
módulo). `montar_codigo_barras` recebe `campo_livre` já pronto (25 caracteres).

DV geral: módulo 11, pesos 2 a 9 cíclicos, caso especial 0/1/10 → 1
-------------------------------------------------------------------------
Calculado sobre as 43 posições do código **exceto** a própria posição do DV (1-4 e
6-44, concatenadas nessa ordem) — pesos 2, 3, 4, ..., 9, voltando a 2, aplicados da
direita para a esquerda. `resto = soma % 11`; se `resto` for 0, 1 ou 10, o DV é `1`
(não `11-resto`, que daria 11 ou 10, dígitos que não existem) — senão, DV `= 11 - resto`.

Linha digitável: os mesmos 44 dígitos, reorganizados em 5 campos com DV próprio
------------------------------------------------------------------------------------
```
Campo 1 = banco(3) + moeda(1) + campo_livre[0:5]   (9 dígitos) + DV1 (módulo 10)
Campo 2 = campo_livre[5:15]                        (10 dígitos) + DV2 (módulo 10)
Campo 3 = campo_livre[15:25]                       (10 dígitos) + DV3 (módulo 10)
Campo 4 = DV geral (1 dígito, o mesmo da posição 5 do código de barras)
Campo 5 = fator de vencimento (4) + valor (10)     (14 dígitos, sem DV próprio)
```
Confirmada a composição (banco+moeda+5 do campo livre / próximos 10 / últimos 10) em
três fontes técnicas independentes e consistentes entre si — nenhuma delas publicou a
tabela de posições literal, mas todas descrevem exatamente a mesma divisão 9+10+10 do
campo livre de 25 posições, o que já fecha a conta sem ambiguidade.

Módulo 10 (DV de cada campo): pesos 2/1 alternados, da direita para a esquerda; produto
maior que 9 soma os próprios algarismos (`14 → 1+4 → 5`); `DV = (10 - soma % 10) % 10`
(o `% 10` extra cobre o caso `soma % 10 == 0`, em que o dígito correto é `0`, não `10`).

Funções puras: nenhuma dependência do Frappe.
"""

from datetime import date
from decimal import Decimal

__all__ = [
	"DATA_BASE_ANTIGA",
	"DATA_BASE_NOVA",
	"BoletoInvalido",
	"calcular_dv_barra",
	"calcular_dv_campo",
	"calcular_fator_vencimento",
	"montar_codigo_barras",
	"montar_linha_digitavel",
]

DATA_BASE_ANTIGA = date(1997, 10, 7)
DATA_BASE_NOVA = date(2025, 2, 22)
_FATOR_INICIAL_NOVO = 1000


class BoletoInvalido(ValueError):
	"""Dado que impediria a montagem correta do código de barras/linha digitável."""


def calcular_fator_vencimento(data_vencimento: date) -> int:
	"""Dias entre a data-base vigente e `data_vencimento`, na base correta.

	Base antiga (`07/10/1997`) para vencimento anterior a `22/02/2025`; base nova
	(`1000` em `22/02/2025`, incrementando um por dia) a partir daí — ver a docstring do
	módulo sobre por que a base nova é a que importa para qualquer boleto emitido hoje.
	"""
	if data_vencimento < DATA_BASE_ANTIGA:
		raise BoletoInvalido(f"Vencimento {data_vencimento} anterior à data-base ({DATA_BASE_ANTIGA})")

	if data_vencimento < DATA_BASE_NOVA:
		return (data_vencimento - DATA_BASE_ANTIGA).days

	return _FATOR_INICIAL_NOVO + (data_vencimento - DATA_BASE_NOVA).days


def calcular_dv_barra(codigo_sem_dv: str) -> str:
	"""DV geral do código de barras — módulo 11, pesos 2 a 9 cíclicos.

	`codigo_sem_dv` são as 43 posições do código **exceto** o DV (posições 1-4 e 6-44,
	já concatenadas nessa ordem pelo chamador) — este função não sabe montar código de
	barras, só calcular o dígito de uma sequência já pronta.
	"""
	soma = 0
	peso = 2

	for digito in reversed(codigo_sem_dv):
		soma += int(digito) * peso
		peso = peso + 1 if peso < 9 else 2

	resto = soma % 11

	if resto in (0, 1, 10):
		return "1"

	return str(11 - resto)


def calcular_dv_campo(campo: str) -> str:
	"""DV de um campo da linha digitável — módulo 10, pesos 2/1 alternados.

	Produto maior que 9 soma os próprios algarismos (`14` → `1+4` → `5`) antes de somar
	ao total — a pegadinha clássica do módulo 10 que um `* 2` sem essa correção erra.
	"""
	soma = 0
	peso = 2

	for digito in reversed(campo):
		produto = int(digito) * peso
		soma += produto if produto <= 9 else (produto // 10) + (produto % 10)
		peso = 1 if peso == 2 else 2

	return str((10 - soma % 10) % 10)


def montar_codigo_barras(codigo_banco: str, valor: Decimal, data_vencimento: date, campo_livre: str) -> str:
	"""Monta o código de barras completo (44 posições).

	`codigo_banco` são 3 dígitos (tabela de bancos do Bacen/FEBRABAN, não reproduzida
	aqui — cada instalação sabe o seu). `campo_livre` são exatamente 25 caracteres
	(dígitos), já no layout interno do banco — ver docstring do módulo.
	"""
	if len(codigo_banco) != 3 or not codigo_banco.isdigit():
		raise BoletoInvalido(f"codigo_banco deve ter 3 dígitos, recebido {codigo_banco!r}")

	if len(campo_livre) != 25 or not campo_livre.isdigit():
		raise BoletoInvalido(f"campo_livre deve ter 25 dígitos, recebido {campo_livre!r}")

	if valor <= 0:
		raise BoletoInvalido(f"valor deve ser positivo, recebido {valor}")

	moeda = "9"  # Real — único valor que este módulo produz.
	fator = str(calcular_fator_vencimento(data_vencimento)).rjust(4, "0")
	valor_em_centavos = str(int((valor * 100).to_integral_value())).rjust(10, "0")

	sem_dv = f"{codigo_banco}{moeda}{fator}{valor_em_centavos}{campo_livre}"
	dv = calcular_dv_barra(sem_dv)

	return f"{codigo_banco}{moeda}{dv}{fator}{valor_em_centavos}{campo_livre}"


def montar_linha_digitavel(codigo_barras: str) -> str:
	"""Reorganiza o código de barras (44 posições) nos 5 campos da linha digitável.

	Pré-condição: `codigo_barras` já é válido (44 dígitos) — este módulo não recalcula
	o DV geral, só o lê da posição 5 e reparte o resto conforme a docstring do módulo.
	"""
	if len(codigo_barras) != 44 or not codigo_barras.isdigit():
		raise BoletoInvalido(f"código de barras deve ter 44 dígitos, recebido {codigo_barras!r}")

	banco_moeda = codigo_barras[0:4]
	dv_geral = codigo_barras[4]
	fator_valor = codigo_barras[5:19]
	campo_livre = codigo_barras[19:44]

	campo1_sem_dv = banco_moeda + campo_livre[0:5]
	campo2_sem_dv = campo_livre[5:15]
	campo3_sem_dv = campo_livre[15:25]

	campo1 = campo1_sem_dv + calcular_dv_campo(campo1_sem_dv)
	campo2 = campo2_sem_dv + calcular_dv_campo(campo2_sem_dv)
	campo3 = campo3_sem_dv + calcular_dv_campo(campo3_sem_dv)

	return f"{campo1}{campo2}{campo3}{dv_geral}{fator_valor}"
