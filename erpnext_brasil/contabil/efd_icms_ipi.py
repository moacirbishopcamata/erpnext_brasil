# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Registro E110 do EFD-ICMS/IPI (SPED Fiscal) — apuração do ICMS.

Por que EFD, não o "Registro de Entradas e Saídas" em papel
------------------------------------------------------------
O roteiro deste bloco pedia "apuração e livros (Registro de Entradas e Saídas, Apuração
de ICMS e de IPI)". Investigando antes de implementar: o **Ajuste SINIEF 02/2009**
dispensou, para quem é obrigado ao EFD-ICMS/IPI, a emissão e autenticação dos livros em
papel — Registro de Entradas, Registro de Saídas, Registro de Inventário, Registro de
Apuração do IPI e Registro de Apuração do ICMS. Hoje esse é o caso da esmagadora maioria
das empresas. Implementar o livro de papel seria construir um artefato que a lei já
tornou dispensável para quem mais importa — o alvo real é o **registro digital do EFD**
que o substitui, não a forma antiga.

O registro E110 traz exatamente o que `contabil/apuracao_periodo.ApuracaoPeriodo` (ICMS)
já calcula: débito bruto, crédito bruto, saldo credor anterior, saldo apurado, valor a
recolher, saldo credor a transportar. Por isso este módulo é um **conversor**, não uma
nova apuração — a conta já foi feita, aqui só se organiza no formato que o Fisco espera.

Escopo desta primeira versão: só o caso sem ajuste de apuração
-------------------------------------------------------------------
O registro E110 tem 13 campos de valor; só 6 correspondem ao que `ApuracaoPeriodo`
calcula. Os outros 7 — `VL_AJ_DEBITOS`, `VL_TOT_AJ_DEBITOS`, `VL_ESTORNOS_CRED`,
`VL_AJ_CREDITOS`, `VL_TOT_AJ_CREDITOS`, `VL_ESTORNOS_DEB`, `VL_TOT_DED` — são **ajustes
de apuração**: cada um discriminado, no registro E111 do mesmo bloco, contra uma tabela
de códigos própria (Tabela 5.3 do Guia Prático EFD) que este app não modela ainda.

`montar_e110` zera os sete campos de ajuste. Isto está **correto** para uma apuração sem
nenhum ajuste (o caso comum — nenhuma glosa, nenhum estorno, nenhuma dedução do período).
Não está correto para uma apuração que precise de ajuste real: usar esta função nesse
caso produziria um registro estruturalmente válido, mas que subestimaria ou
superestimaria o que é devido — silenciosamente. Por isso não há, hoje, nenhum ponto de
entrada que descubra sozinho "este período teve ajuste" e ainda assim chame esta função;
isso fica para quando o registro E111 for implementado.

Formato de saída: dict de campo → valor, não a linha de texto do EFD
------------------------------------------------------------------------
O layout de texto do SPED (campos separados por `|`, decimal com vírgula, escapes
próprios, um registro por linha dentro de um bloco) é uma preocupação de serialização
separada de "quais valores vão em quais campos". Resolver as duas juntas arriscaria
acertar o valor e errar o formato, ou vice-versa, sem teste dedicado para cada
responsabilidade — a mesma razão de `fiscal/documento/serializacao.py` separar a árvore
de dados do XML final. Este módulo só resolve a primeira.

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import Decimal

from erpnext_brasil.contabil.apuracao_periodo import ApuracaoPeriodo

__all__ = ["montar_e110"]

ZERO = Decimal("0.00")


def montar_e110(apuracao: ApuracaoPeriodo) -> dict:
	"""Campos do registro E110, na ordem oficial do Guia Prático EFD-ICMS/IPI.

	Pré-condição: `apuracao.tributo` precisa ser `"ICMS"` — E110 é o registro de
	apuração do ICMS; IPI tem registro próprio (E200), layout diferente, não coberto
	aqui.
	"""
	if apuracao.tributo != "ICMS":
		raise ValueError(f"E110 é o registro de apuração do ICMS, recebido tributo={apuracao.tributo!r}")

	return {
		"REG": "E110",
		"VL_TOT_DEBITOS": apuracao.debitos,
		"VL_AJ_DEBITOS": ZERO,
		"VL_TOT_AJ_DEBITOS": ZERO,
		"VL_ESTORNOS_CRED": ZERO,
		"VL_TOT_CREDITOS": apuracao.creditos,
		"VL_AJ_CREDITOS": ZERO,
		"VL_TOT_AJ_CREDITOS": ZERO,
		"VL_ESTORNOS_DEB": ZERO,
		"VL_SLD_CREDOR_ANT": apuracao.saldo_credor_anterior,
		"VL_SLD_APURADO": apuracao.a_recolher,
		"VL_TOT_DED": ZERO,
		"VL_ICMS_RECOLHER": apuracao.a_recolher,
		"VL_SLD_CREDOR_TRANSPORTAR": apuracao.saldo_credor_a_transportar,
		"DEB_ESP": ZERO,
	}
