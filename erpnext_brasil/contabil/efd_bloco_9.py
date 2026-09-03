# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Bloco 9 do EFD-ICMS/IPI — controle e encerramento do arquivo digital.

O que fecha o arquivo: `9001` (abertura), `9900` (uma linha por tipo de registro
existente, com a contagem de cada um), `9990` (encerramento do bloco) e `9999`
(encerramento do arquivo, com o total de linhas). Com este bloco, os registros já
implementados (Bloco 0, Bloco C, Bloco E) podem ser montados num arquivo EFD completo.

A sutileza real do `9900`: a contagem é auto-referente
--------------------------------------------------------------
O guia diz que "todos os registros referenciados neste arquivo, **inclusive os
posteriores a este registro**, devem ter uma linha totalizadora do seu número de
ocorrências". Ou seja, o `9900` precisa totalizar também o `9001`, o `9990`, o `9999` —
e o **próprio `9900`**. E a quantidade de linhas `9900` é exatamente o número de tipos
distintos de registro no arquivo, que inclui o `9900`. A contagem depende de si mesma.

Resolvido em `montar_bloco_9` de forma fechada, sem iterar até convergir: se o arquivo
tem `N` tipos distintos de registro fora do Bloco 9, o total de tipos é `N + 4` (os
quatro do Bloco 9, que não aparecem em nenhum outro lugar), e portanto:

- linhas `9900` = `N + 4`
- `QTD_LIN_9` (linhas do Bloco 9) = 1 (`9001`) + (`N + 4`) + 1 (`9990`) = `N + 6`
- `QTD_LIN` (linhas do arquivo) = linhas dos demais blocos + (`N + 6`) + 1 (`9999`)

O `9999` conta a si próprio ("a quantidade de linhas a ser informada deve considerar
também o próprio registro 9999" — texto literal do guia), e o `9990` segue a convenção
dos demais encerramentos de bloco (`0990`/`C990`), contando a si próprio.

Errar essa conta não produz um arquivo "quase certo": o PVA valida cada `QTD_` contra a
contagem real e rejeita o arquivo inteiro. É o tipo de aritmética chata que compensa
estar num só lugar, testada, em vez de espalhada por quem monta o arquivo.

Ordem das linhas `9900`
------------------------------
O guia não fixa uma ordem para as linhas `9900`. Este módulo emite em ordem alfabética
do código do registro — determinística (dois arquivos com o mesmo conteúdo saem
idênticos, o que torna diff e teste possíveis), sem alegar que a ordem é exigida.

Fonte: Guia Prático oficial EFD-ICMS/IPI versão 2.0.13 (cópia publicada pela SEFAZ-SP,
PDF baixado e lido localmente com `pdftotext`). Bloco 9 é estrutural e não mudou nas
versões seguintes — diferente do `0200`/`C100`, onde a versão antiga já se mostrou
desatualizada nesta mesma frente.

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

__all__ = [
	"REGISTROS_DO_BLOCO_9",
	"montar_9001",
	"montar_9900",
	"montar_9990",
	"montar_9999",
	"montar_bloco_9",
]

REGISTROS_DO_BLOCO_9 = ("9001", "9900", "9990", "9999")
"""Os quatro registros que só existem no Bloco 9 — a base da conta auto-referente."""


def montar_9001(tem_dados: bool = True) -> dict:
	"""Abertura do Bloco 9. Mesma convenção invertida de `0001`/`C001` (`0` = com
	dados). Na prática sempre tem dados: o `9900` é obrigatório."""
	return {"REG": "9001", "IND_MOV": "0" if tem_dados else "1"}


def montar_9900(registro: str, quantidade: int) -> dict:
	"""Uma linha `9900` — o código do registro totalizado e quantas vezes ele aparece
	no arquivo."""
	if not registro:
		raise EfdInvalido("REG_BLC não pode ser vazio")

	if quantidade < 1:
		raise EfdInvalido(
			f"não faz sentido totalizar {registro!r} com {quantidade} ocorrências — "
			"só entram no 9900 os registros que existem no arquivo"
		)

	return {"REG": "9900", "REG_BLC": registro, "QTD_REG_BLC": str(quantidade)}


def montar_9990(quantidade_linhas: int) -> dict:
	"""Encerramento do Bloco 9, contando a si próprio — mesma convenção de
	`0990`/`C990`."""
	if quantidade_linhas < 3:
		raise EfdInvalido(
			"o Bloco 9 tem no mínimo três linhas (9001, ao menos um 9900 e o próprio "
			f"9990), recebido {quantidade_linhas}"
		)

	return {"REG": "9990", "QTD_LIN_9": str(quantidade_linhas)}


def montar_9999(quantidade_linhas: int) -> dict:
	"""Encerramento do arquivo, contando a si próprio (texto literal do guia)."""
	if quantidade_linhas < 1:
		raise EfdInvalido(f"QTD_LIN deve ser positivo, recebido {quantidade_linhas}")

	return {"REG": "9999", "QTD_LIN": str(quantidade_linhas)}


def montar_bloco_9(contagem_por_registro: dict[str, int]) -> list[dict]:
	"""Monta o Bloco 9 inteiro a partir da contagem dos registros dos **demais** blocos.

	`contagem_por_registro` é `{código do registro: quantas vezes aparece}` para tudo
	que vem antes do Bloco 9 (Blocos 0, C, D, E, H, K, 1...). Os quatro registros do
	próprio Bloco 9 são acrescentados aqui — passá-los na entrada é erro, porque a
	quantidade deles é justamente o que esta função calcula.

	Devolve a lista de linhas na ordem do arquivo: `9001`, os `9900` (em ordem
	alfabética do código), `9990` e `9999`.
	"""
	intrusos = sorted(set(contagem_por_registro) & set(REGISTROS_DO_BLOCO_9))

	if intrusos:
		raise EfdInvalido(
			f"não informe os registros do próprio Bloco 9 na contagem de entrada ({intrusos}) — "
			"a quantidade deles é o que esta função calcula"
		)

	invalidos = sorted(reg for reg, qtd in contagem_por_registro.items() if qtd < 1)

	if invalidos:
		raise EfdInvalido(f"registros com contagem menor que 1 na entrada: {invalidos}")

	if not contagem_por_registro:
		raise EfdInvalido("a contagem de entrada está vazia — um arquivo EFD tem, no mínimo, o Bloco 0")

	linhas_dos_demais_blocos = sum(contagem_por_registro.values())
	tipos_fora_do_bloco_9 = len(contagem_por_registro)

	# A conta fechada, sem iterar até convergir — ver a docstring do módulo.
	linhas_9900 = tipos_fora_do_bloco_9 + len(REGISTROS_DO_BLOCO_9)
	linhas_do_bloco_9 = 1 + linhas_9900 + 1
	linhas_do_arquivo = linhas_dos_demais_blocos + linhas_do_bloco_9 + 1

	totais = dict(contagem_por_registro)
	totais["9001"] = 1
	totais["9900"] = linhas_9900
	totais["9990"] = 1
	totais["9999"] = 1

	linhas = [montar_9001()]
	linhas.extend(montar_9900(registro, totais[registro]) for registro in sorted(totais))
	linhas.append(montar_9990(linhas_do_bloco_9))
	linhas.append(montar_9999(linhas_do_arquivo))

	return linhas
