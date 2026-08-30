# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Registros I200/I250 da ECD — lançamento contábil e suas partidas.

Sétimo incremento do bloco contábil, sobre `ecd_i050.py` (que declara o plano) e
`lancamento.py` (que já gera os `Lancamento` de venda/compra). Este módulo converte um
`Lancamento` — já balanceado por construção, um débito e um crédito do mesmo valor — no
par de registros que a ECD exige: **I200** (cabeçalho do lançamento: número, data,
valor) e **I250** (uma linha por partida — aqui sempre duas, a de débito e a de
crédito).

Por que dois registros para um `Lancamento`
------------------------------------------------
A ECD não modela "débito e crédito" como dois campos do mesmo registro (como
`Lancamento` faz) — modela o lançamento como cabeçalho (I200, com o valor total) mais
uma lista de partidas (I250, cada uma com sua própria conta e um indicador `D`/`C`). Um
`Lancamento` — sempre um débito, um crédito, o mesmo valor — vira exatamente um I200 e
duas linhas I250: nunca mais que duas partidas, porque `Lancamento` não modela
lançamento com mais de duas pontas (um rateio entre três contas, por exemplo, precisaria
de um tipo mais rico que `Lancamento` ainda não é).

`COD_CTA` vem de `plano_de_contas.montar_codigos()`
--------------------------------------------------------
`Lancamento.conta_debito`/`conta_credito` são nomes (`"Clientes"`, `"ICMS a
Recolher"`), o mesmo vocabulário de `plano_de_contas.ARVORE` — não código. A conversão
usa a numeração-padrão de `montar_codigos()` (ver `docs/ecd.md`: convenção deste app,
não exigência legal) para resolver nome → código. Um nome que não exista na árvore
levanta erro explícito, nunca um `COD_CTA` vazio ou inventado.

`montar_i200_i250_multiplo` faz o mesmo para `LancamentoMultiplo`
------------------------------------------------------------------------
Um rateio (`LancamentoMultiplo`, mais de uma conta de cada lado) vira o mesmo I200 —
`VL_LCTO` é `valor_total`, já garantido igual dos dois lados pela invariante do próprio
tipo — mais uma linha I250 **por partida**, não só duas. A conversão de nome de conta
para `COD_CTA` é a mesma função, compartilhada entre as duas versões.

Fora de escopo desta primeira versão
----------------------------------------
- **`IND_LCTO`** sempre `"N"` (lançamento normal) — `"E"` (encerramento de contas de
  resultado, lançamento de fim de exercício) e `"X"` (lançamento extemporâneo) não são
  produzidos por `lancamento.py` hoje.
- **`COD_CCUS`** (centro de custo), **`COD_HIST_PAD`** (histórico padronizado, tabela
  I075) e **`COD_PART`** (participante, tabela 0150) ficam em branco — nenhuma dessas
  três tabelas auxiliares existe neste app ainda.
- **`NUM_ARQ`** (referência a documento anexado) também em branco — `Lancamento` não
  carrega essa informação.
- **`DT_LCTO_EXT`** (data de ocorrência, só para lançamento extemporâneo `"X"`) — não
  se aplica, já que este módulo só produz `"N"`.

Formato de saída: dict, não a linha de texto do SPED — mesma decisão já registrada em
`docs/sped-fiscal.md` e `docs/ecd.md`.

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.contabil.lancamento import Lancamento, LancamentoMultiplo
from erpnext_brasil.contabil.plano_de_contas import montar_codigos

__all__ = ["ContaDesconhecida", "montar_i200_i250", "montar_i200_i250_multiplo"]


class ContaDesconhecida(ValueError):
	"""Lançamento referencia uma conta que não existe em `plano_de_contas.ARVORE`."""


def _codigo_ou_erro(codigos: dict[str, str], nome: str) -> str:
	if nome not in codigos:
		raise ContaDesconhecida(f"Conta {nome!r} não existe em plano_de_contas.ARVORE")

	return codigos[nome]


def _linha_i250(codigos: dict[str, str], conta: str, valor, indicador: str, historico: str) -> dict:
	return {
		"REG": "I250",
		"COD_CTA": _codigo_ou_erro(codigos, conta),
		"COD_CCUS": "",
		"VL_DC": valor,
		"IND_DC": indicador,
		"NUM_ARQ": "",
		"COD_HIST_PAD": "",
		"HIST": historico,
		"COD_PART": "",
	}


def _linha_i200(num_lcto: str, data_lancamento: str, valor) -> dict:
	return {
		"REG": "I200",
		"NUM_LCTO": num_lcto,
		"DT_LCTO": data_lancamento,
		"VL_LCTO": valor,
		"IND_LCTO": "N",
	}


def montar_i200_i250(
	lancamentos: list[Lancamento], data_lancamento: str, *, numero_inicial: int = 1
) -> list[tuple[dict, list[dict]]]:
	"""Um par `(I200, [I250_débito, I250_crédito])` por `Lancamento`, nessa ordem.

	`data_lancamento` é única para todo o lote (mesma razão de `ecd_i050.montar_i050`
	receber `data_alteracao` como parâmetro: este módulo não decide "hoje" sozinho).
	`numero_inicial` numera `NUM_LCTO` sequencialmente a partir daí — a chave só precisa
	ser única dentro do arquivo, não um código com significado próprio.
	"""
	codigos = montar_codigos()
	pares: list[tuple[dict, list[dict]]] = []

	for indice, lancamento in enumerate(lancamentos, start=numero_inicial):
		i200 = _linha_i200(str(indice), data_lancamento, lancamento.valor)
		partidas = [
			_linha_i250(codigos, lancamento.conta_debito, lancamento.valor, "D", lancamento.historico),
			_linha_i250(codigos, lancamento.conta_credito, lancamento.valor, "C", lancamento.historico),
		]

		pares.append((i200, partidas))

	return pares


def montar_i200_i250_multiplo(
	lancamentos: list[LancamentoMultiplo], data_lancamento: str, *, numero_inicial: int = 1
) -> list[tuple[dict, list[dict]]]:
	"""Mesma ideia de `montar_i200_i250`, para rateio: uma linha I250 **por partida**,
	não só duas — `VL_LCTO` é `LancamentoMultiplo.valor_total`, já garantido igual nos
	dois lados pela invariante do próprio tipo (ver `lancamento.py`)."""
	codigos = montar_codigos()
	pares: list[tuple[dict, list[dict]]] = []

	for indice, lancamento in enumerate(lancamentos, start=numero_inicial):
		i200 = _linha_i200(str(indice), data_lancamento, lancamento.valor_total)
		partidas = [
			_linha_i250(codigos, partida.conta, partida.valor, "D", lancamento.historico)
			for partida in lancamento.debitos
		] + [
			_linha_i250(codigos, partida.conta, partida.valor, "C", lancamento.historico)
			for partida in lancamento.creditos
		]

		pares.append((i200, partidas))

	return pares
