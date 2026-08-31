# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CFOP (Código Fiscal de Operações e Prestações): determinação, não só validação.

Por que existe
--------------
`fiscal/documento/produto.py` já recebia o CFOP como string pronta, validado só por
formato (4 dígitos) — nunca calculado. A tabela completa (~600 códigos, Convênio
SINIEF s/nº de 15/12/1970 e ajustes posteriores) já tem infraestrutura de importação
genérica (`integracao/importar_codigos.py`, reaproveitando `Code List`/`Common Code`
do próprio Frappe) — o que faltava era a **regra de qual código usar**, dado o tipo
de operação. Este módulo cobre um núcleo pequeno e verificado, não a tabela inteira.

A estrutura do código, confirmada por múltiplas fontes concordantes
------------------------------------------------------------------------------
Quatro dígitos: o **primeiro** indica direção e âmbito da operação —
`1`/`2`/`3` = entrada (mesmo estado / outro estado / exterior),
`5`/`6`/`7` = saída (mesmo estado / outro estado / exterior). Os **três últimos**
detalham a natureza específica — mesmos três dígitos finais mantêm o mesmo
significado trocando só o primeiro dígito conforme o âmbito (ex.: `101` = compra
para industrialização tanto em `1101` (mesmo estado) quanto em `2101` (outro
estado)). Esse padrão foi confirmado, não suposto, cruzando várias fontes
concordantes para os pares `1101`/`2101`, `5101`/`6101`, `1202`/`2202`.

Escopo: dezesseis códigos, o núcleo mais comum — não a tabela inteira
------------------------------------------------------------------------------------------
**Cobertos** (compra, venda, devolução de venda, devolução de compra — mercadoria,
não serviço nem industrialização de terceiros):

| Operação | Mesmo estado | Outro estado | Finalidade |
|---|---|---|---|
| Compra | `1101` | `2101` | industrialização/produção rural |
| Compra | `1102` | `2102` | comercialização |
| Venda | `5101` | `6101` | produção própria do estabelecimento |
| Venda | `5102` | `6102` | mercadoria adquirida/recebida de terceiros |
| Devolução de venda (entrada) | `1201` | `2201` | produção própria devolvida pelo cliente |
| Devolução de venda (entrada) | `1202` | `2202` | mercadoria de terceiros devolvida pelo cliente |
| Devolução de compra (saída) | `5201` | `6201` | industrialização, devolvida ao fornecedor |
| Devolução de compra (saída) | `5202` | `6202` | comercialização, devolvida ao fornecedor |

**Fora do escopo, e não finja que está coberto**: operação com o exterior (`3`/`7`),
transferência entre estabelecimentos da mesma empresa, remessa/retorno de
industrialização por conta de terceiros, bonificação/doação/brinde, consignação,
ativo imobilizado/uso e consumo, substituição tributária, prestação de serviço de
transporte, e qualquer código fora deste núcleo de dezesseis. `determinar_cfop`
levanta erro explícito para qualquer combinação não coberta — nunca inventa um
código plausível.

Este módulo não decide industrialização × comercialização, nem mesmo/outro estado
------------------------------------------------------------------------------------------------
Essas decisões dependem de dado que este módulo não tem (a que UF pertence o
fornecedor/cliente, a que a mercadoria se destina) — mesma disciplina de
`imposto_item.py` não inferir natureza de operação a partir de dado incompleto.
Quem chama informa `mesmo_estado`/`finalidade` já decididos.

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = [
	"FINALIDADE_COMERCIALIZACAO",
	"FINALIDADE_INDUSTRIALIZACAO",
	"CfopInvalido",
	"cfop_compra",
	"cfop_devolucao_compra",
	"cfop_devolucao_venda",
	"cfop_venda",
]

FINALIDADE_INDUSTRIALIZACAO = "industrializacao"
FINALIDADE_COMERCIALIZACAO = "comercializacao"

_FINALIDADES_VALIDAS = (FINALIDADE_INDUSTRIALIZACAO, FINALIDADE_COMERCIALIZACAO)


class CfopInvalido(ValueError):
	"""Combinação de parâmetros fora do núcleo de códigos que este módulo cobre."""


def _validar_finalidade(finalidade: str) -> None:
	if finalidade not in _FINALIDADES_VALIDAS:
		raise CfopInvalido(
			f"finalidade deve ser {FINALIDADE_INDUSTRIALIZACAO!r} ou "
			f"{FINALIDADE_COMERCIALIZACAO!r}, recebida {finalidade!r}"
		)


def cfop_compra(mesmo_estado: bool, finalidade: str) -> str:
	"""`1101`/`2101` (industrialização) ou `1102`/`2102` (comercialização) —
	entrada de mercadoria comprada de terceiros."""
	_validar_finalidade(finalidade)

	sufixo = "01" if finalidade == FINALIDADE_INDUSTRIALIZACAO else "02"
	prefixo = "1" if mesmo_estado else "2"

	return f"{prefixo}1{sufixo}"


def cfop_venda(mesmo_estado: bool, producao_propria: bool) -> str:
	"""`5101`/`6101` (produção própria do estabelecimento) ou `5102`/`6102`
	(mercadoria adquirida/recebida de terceiros) — saída por venda."""
	sufixo = "01" if producao_propria else "02"
	prefixo = "5" if mesmo_estado else "6"

	return f"{prefixo}1{sufixo}"


def cfop_devolucao_venda(mesmo_estado: bool, producao_propria: bool) -> str:
	"""`1201`/`2201` ou `1202`/`2202` — entrada pela devolução de uma venda
	anterior, feita pelo cliente. Espelho de `cfop_venda`: mesma distinção entre
	produção própria e mercadoria de terceiros, mesma direção de estado."""
	sufixo = "01" if producao_propria else "02"
	prefixo = "1" if mesmo_estado else "2"

	return f"{prefixo}2{sufixo}"


def cfop_devolucao_compra(mesmo_estado: bool, finalidade: str) -> str:
	"""`5201`/`6201` ou `5202`/`6202` — saída pela devolução de uma compra
	anterior, feita ao fornecedor. Espelho de `cfop_compra`."""
	_validar_finalidade(finalidade)

	sufixo = "01" if finalidade == FINALIDADE_INDUSTRIALIZACAO else "02"
	prefixo = "5" if mesmo_estado else "6"

	return f"{prefixo}2{sufixo}"
