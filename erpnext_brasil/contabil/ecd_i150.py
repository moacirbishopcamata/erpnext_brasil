# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Registros I150/I155 da ECD — saldos periódicos por conta.

Oitavo incremento do bloco ECD, sobre `ecd_i050.py` (plano) e `ecd_i200.py`
(lançamento): I150 declara o período do fechamento (início/fim), I155 traz, para cada
conta analítica que teve movimento no período, o saldo inicial, o total de débitos e
créditos, e o saldo final.

`D`/`C`, não positivo/negativo — mas a aritmética é a mesma para qualquer conta
------------------------------------------------------------------------------------
`IND_DC_INI`/`IND_DC_FIN` dizem de que lado o saldo está (`"D"` devedor, `"C"` credor),
nunca em branco mesmo quando o saldo é zero. A conta de "que lado o saldo termina depois
de somar débitos e subtrair créditos" é **puramente mecânica** — não depende de a conta
ser "naturalmente devedora" (Ativo/Despesa) ou "naturalmente credora" (Passivo/PL/
Receita): registrar um débito sempre empurra o saldo para o lado D, um crédito sempre
empurra para o lado C, seja qual for a conta. Por isso este módulo converte
`(valor, indicador)` para um número com sinal (`D` positivo, `C` negativo), soma
débitos e subtrai créditos, e converte de volta — sem precisar saber `root_type` nem
consultar `plano_de_contas.py` para nada além do código da conta.

Quando o saldo dá exatamente zero, o indicador escolhido é `"D"` — convenção arbitrária
mas consistente (a fonte só exige não ficar em branco, não diz qual dos dois usar).

Só contas com movimento no período
----------------------------------------
Confirmado na fonte: o registro I155 só é apresentado para contas analíticas que
tiveram movimento (débito ou crédito) no período — uma conta sem lançamento nenhum não
gera linha, mesmo que tenha saldo inicial diferente de zero transportado do período
anterior.

Saldo inicial é parâmetro, não persistido
------------------------------------------------
Mesma disciplina de `apuracao_periodo.apurar_periodo` (`saldo_credor_anterior`): o saldo
inicial de cada conta vem de fora (`SaldoInicial`), porque nenhum mecanismo aqui guarda
o saldo final de um período para virar o inicial do seguinte automaticamente — isso
pertence à camada de negócio/doctype, quando existir.

`COD_CTA` resolvido pela mesma numeração-padrão de `plano_de_contas.montar_codigos()`
já usada por `ecd_i050.py`/`ecd_i200.py` — conta desconhecida levanta `ContaDesconhecida`
(reexportada de `ecd_i200.py`, não duplicada).

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.ecd_i200 import ContaDesconhecida
from erpnext_brasil.contabil.lancamento import Lancamento
from erpnext_brasil.contabil.plano_de_contas import montar_codigos

__all__ = ["ContaDesconhecida", "SaldoInicial", "montar_i150", "montar_i155"]

ZERO = Decimal("0.00")

_DEVEDOR = "D"
_CREDOR = "C"


@dataclass(frozen=True)
class SaldoInicial:
	"""Saldo de uma conta ao início do período — transportado de fora, não recalculado
	daqui (ver docstring do módulo)."""

	valor: Decimal
	indicador: str

	def __post_init__(self) -> None:
		if self.indicador not in (_DEVEDOR, _CREDOR):
			raise ValueError(f"indicador deve ser 'D' ou 'C', recebido {self.indicador!r}")

		if self.valor < ZERO:
			raise ValueError(f"valor não pode ser negativo, recebido {self.valor}")


def _assinado(valor: Decimal, indicador: str) -> Decimal:
	return valor if indicador == _DEVEDOR else -valor


def _valor_e_indicador(assinado: Decimal) -> tuple[Decimal, str]:
	if assinado >= ZERO:
		return assinado, _DEVEDOR

	return -assinado, _CREDOR


def montar_i150(data_inicio: date, data_fim: date) -> dict:
	"""Campos do registro I150 — identificação do período do fechamento."""
	return {"REG": "I150", "DT_INI": data_inicio, "DT_FIN": data_fim}


def montar_i155(
	lancamentos: list[Lancamento], saldos_iniciais: dict[str, SaldoInicial] | None = None
) -> list[dict]:
	"""Uma linha I155 por conta com movimento no período — só contas que aparecem em
	`lancamentos` (débito ou crédito), na ordem em que aparecem pela primeira vez.

	`saldos_iniciais` é `{nome_da_conta: SaldoInicial}` — conta sem entrada aqui começa
	do zero (`SaldoInicial(ZERO, "D")`), nunca erro: a maioria das contas de resultado
	(Receita/Despesa) realmente zera a cada período, só as patrimoniais carregam saldo.
	"""
	saldos_iniciais = saldos_iniciais or {}
	codigos = montar_codigos()
	contas_em_ordem: list[str] = []
	vistas: set[str] = set()

	for lancamento in lancamentos:
		for conta in (lancamento.conta_debito, lancamento.conta_credito):
			if conta not in vistas:
				vistas.add(conta)
				contas_em_ordem.append(conta)

	linhas: list[dict] = []

	for conta in contas_em_ordem:
		if conta not in codigos:
			raise ContaDesconhecida(f"Conta {conta!r} não existe em plano_de_contas.ARVORE")

		debitos = sum(
			(lancamento.valor for lancamento in lancamentos if lancamento.conta_debito == conta), ZERO
		)
		creditos = sum(
			(lancamento.valor for lancamento in lancamentos if lancamento.conta_credito == conta), ZERO
		)

		inicial = saldos_iniciais.get(conta, SaldoInicial(ZERO, _DEVEDOR))
		assinado_final = _assinado(inicial.valor, inicial.indicador) + debitos - creditos
		valor_final, indicador_final = _valor_e_indicador(assinado_final)

		linhas.append(
			{
				"REG": "I155",
				"COD_CTA": codigos[conta],
				"COD_CCUS": "",
				"VL_SLD_INI": inicial.valor,
				"IND_DC_INI": inicial.indicador,
				"VL_DEB": debitos,
				"VL_CRED": creditos,
				"VL_SLD_FIN": valor_final,
				"IND_DC_FIN": indicador_final,
			}
		)

	return linhas
