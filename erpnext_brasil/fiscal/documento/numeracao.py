# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Numeração de documento fiscal: as regras do leiaute, sem o problema de concorrência.

Este módulo é a **regra**; alocar o próximo número com segurança sob concorrência é
trabalho de `integracao/numeracao_fiscal.py`, que precisa de transação e trava de linha.
Separados porque são problemas diferentes: aqui não há nada que dependa do banco, e a
aritmética se testa sem bench.

O que o XSD exige, lido no arquivo oficial
--------------------------------------------------
`tiposBasico_v4.00.xsd` da NF-e, lido localmente:

```xml
<xs:simpleType name="TNF">      <xs:pattern value="[1-9]{1}[0-9]{0,8}"/>
<xs:simpleType name="TSerie">   <xs:pattern value="0|[1-9]{1}[0-9]{0,2}"/>
```

Duas consequências que não são óbvias e que um sistema costuma errar:

- **`nNF` não admite zero à esquerda nem o valor zero.** O primeiro dígito é `[1-9]`, o
  que descarta `"0"`, `"007"` e `"0"`-preenchido de qualquer forma. A faixa útil é
  1 a 999.999.999.
- **`serie` admite `"0"`, mas não `"00"` nem `"000"`.** O padrão é `0` **ou** um número de
  1 a 999 sem zero à frente.

Esse segundo ponto contraria o hábito adquirido no EFD: o registro `D100` do SPED exige
`SER` com **três posições**, informando `"000"` quando não há série (ver
`contabil/efd_bloco_d.py`). São artefatos diferentes — o XML do documento e o arquivo da
escrituração — e o mesmo conceito tem formato diferente em cada um. Mais um caso de nunca
transportar formato entre documentos irmãos.

A regra que o XSD **não** diz
--------------------------------------
Sequência **sem lacuna** por série é exigência da legislação, não do schema: um número
pulado precisa ser justificado (inutilização de faixa, que este projeto já implementa em
`fiscal/documento/inutilizacao.py`). Por isso `proximo_numero` só sabe somar um — nunca
"pular para o próximo livre", que esconderia a lacuna em vez de tratá-la.

Funções puras: nenhuma dependência do Frappe.
"""

import re

__all__ = [
	"NUMERO_MAXIMO",
	"NUMERO_MINIMO",
	"SERIE_MAXIMA",
	"NumeracaoInvalida",
	"primeiro_numero",
	"proximo_numero",
	"validar_numero",
	"validar_serie",
]

NUMERO_MINIMO = 1
NUMERO_MAXIMO = 999_999_999
SERIE_MAXIMA = 999

_PADRAO_NUMERO = re.compile(r"^[1-9][0-9]{0,8}$")
_PADRAO_SERIE = re.compile(r"^(0|[1-9][0-9]{0,2})$")


class NumeracaoInvalida(ValueError):
	"""Número ou série que o leiaute não aceita, ou faixa esgotada."""


def validar_numero(numero) -> str:
	"""Devolve o `nNF` normalizado, ou levanta.

	Aceita `int` e `str` porque o número vive como inteiro no banco e como texto no XML —
	converter aqui, num lugar só, evita que cada chamador invente sua própria conversão e
	uma delas acabe com zero à esquerda, que o padrão recusa.
	"""
	texto = str(numero).strip()

	if not _PADRAO_NUMERO.match(texto):
		raise NumeracaoInvalida(
			f"nNF deve ser um número de {NUMERO_MINIMO} a {NUMERO_MAXIMO} sem zero à "
			f"esquerda (TNF do XSD: [1-9][0-9]{{0,8}}), recebido {texto!r}"
		)

	return texto


def validar_serie(serie) -> str:
	"""Devolve a `serie` normalizada, ou levanta.

	`"0"` é válido; `"00"` e `"000"` não são — ao contrário do `SER` do registro `D100` do
	SPED, que exige três posições. Ver docstring do módulo.
	"""
	texto = str(serie).strip()

	if not _PADRAO_SERIE.match(texto):
		raise NumeracaoInvalida(
			f"serie deve ser '0' ou um número de 1 a {SERIE_MAXIMA} sem zero à esquerda "
			f"(TSerie do XSD: 0|[1-9][0-9]{{0,2}}), recebido {texto!r} — note que '000' vale "
			"no registro D100 do SPED, mas não no XML"
		)

	return texto


def primeiro_numero() -> str:
	"""O número inicial de uma série nova."""
	return str(NUMERO_MINIMO)


def proximo_numero(atual) -> str:
	"""O sucessor imediato — nunca "o próximo livre".

	Pular um número esconderia uma lacuna que a legislação manda justificar por
	inutilização de faixa. Se a faixa acabou, isso é fato a tratar (série nova), não a
	contornar: por isso esgotamento levanta erro em vez de reiniciar em 1.
	"""
	valor = int(validar_numero(atual))

	if valor >= NUMERO_MAXIMO:
		raise NumeracaoInvalida(
			f"a série chegou ao número máximo ({NUMERO_MAXIMO}); a continuação é abrir uma "
			"série nova, não reiniciar a contagem"
		)

	return str(valor + 1)
