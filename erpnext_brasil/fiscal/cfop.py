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

**Industrialização por encomenda** (achado ao levantar o estado do módulo de
Subcontratação do ERPNext, `Subcontracting Order`/`Subcontracting Receipt` — hoje
sem tratamento fiscal nenhum, mesmo gap já registrado para Sales Order/Purchase
Order): quatro códigos a mais, cobrindo os dois papéis da operação —

| Papel | Operação | Mesmo estado | Outro estado |
|---|---|---|---|
| Dono do material | Remessa para industrialização (saída) | `5901` | `6901` |
| Industrializador | Entrada do insumo recebido (entrada) | `1901` | `2901` |
| Dono do material | Retorno recebido de volta (entrada) | `1902` | `2902` |
| Industrializador | Retorno do que industrializou (saída) | `5902` | `6902` |

`Subcontracting Order` (remessa) e `Subcontracting Receipt` (retorno) do ERPNext
modelam o papel de **dono do material** — por isso só `5901`/`6901` e `1902`/`2902`
importam para esse fluxo específico; os outros dois (`1901`/`2901`, `5902`/`6902`)
são fornecidos para quem usa este app do lado do industrializador.

**Fora do escopo, e não finja que está coberto**: operação com o exterior (`3`/`7`),
bonificação/doação/brinde, consignação, substituição tributária, prestação de
serviço de transporte, e qualquer código fora deste núcleo. `CfopInvalido` é
levantado para qualquer combinação não coberta — nunca um código plausível
inventado.

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
	"cfop_entrada_para_industrializacao",
	"cfop_remessa_para_industrializacao",
	"cfop_retorno_da_industrializacao_realizada",
	"cfop_retorno_de_industrializacao",
	"cfop_transferencia_ativo_imobilizado",
	"cfop_transferencia_entrada",
	"cfop_transferencia_saida",
	"cfop_transferencia_uso_e_consumo",
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


def cfop_compra(mesmo_estado: bool, finalidade: str, exterior: bool = False) -> str:
	"""`1101`/`2101` (industrialização) ou `1102`/`2102` (comercialização) —
	entrada de mercadoria comprada de terceiros. `exterior=True` monta `3101`/`3102`
	(compra do exterior/importação) em vez disso — `mesmo_estado` é ignorado nesse
	caso, importação não distingue UF de origem. Confirmado que o segundo e os dois
	últimos dígitos mantêm o mesmo significado entre operação doméstica e com o
	exterior — só o primeiro dígito muda (`1`/`2` → `3`)."""
	_validar_finalidade(finalidade)

	sufixo = "01" if finalidade == FINALIDADE_INDUSTRIALIZACAO else "02"

	if exterior:
		return f"31{sufixo}"

	prefixo = "1" if mesmo_estado else "2"

	return f"{prefixo}1{sufixo}"


def cfop_venda(mesmo_estado: bool, producao_propria: bool, exterior: bool = False) -> str:
	"""`5101`/`6101` (produção própria do estabelecimento) ou `5102`/`6102`
	(mercadoria adquirida/recebida de terceiros) — saída por venda. `exterior=True`
	monta `7101`/`7102` (venda para o exterior/exportação) em vez disso —
	`mesmo_estado` é ignorado, exportação não distingue UF de destino."""
	sufixo = "01" if producao_propria else "02"

	if exterior:
		return f"71{sufixo}"

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


def cfop_remessa_para_industrializacao(mesmo_estado: bool) -> str:
	"""`5901`/`6901` — saída do **dono do material**, enviando insumo para um
	terceiro industrializar por encomenda. Equivalente ao `Subcontracting Order`
	do ERPNext (envio de matéria-prima ao subcontratado)."""
	return "5901" if mesmo_estado else "6901"


def cfop_entrada_para_industrializacao(mesmo_estado: bool) -> str:
	"""`1901`/`2901` — entrada no **industrializador**, recebendo o insumo que vai
	processar por encomenda de terceiro."""
	return "1901" if mesmo_estado else "2901"


def cfop_retorno_de_industrializacao(mesmo_estado: bool) -> str:
	"""`1902`/`2902` — entrada no **dono do material**, recebendo de volta a
	mercadoria que tinha remetido para industrializar. Equivalente ao
	`Subcontracting Receipt` do ERPNext (recebimento do produto processado)."""
	return "1902" if mesmo_estado else "2902"


def cfop_retorno_da_industrializacao_realizada(mesmo_estado: bool) -> str:
	"""`5902`/`6902` — saída do **industrializador**, devolvendo ao dono do
	material o que processou por encomenda."""
	return "5902" if mesmo_estado else "6902"


# --------------------------------------------------------------------------------------
# Transferência entre estabelecimentos da mesma empresa
#
# Entrou no escopo quando se decidiu que **cada estabelecimento é uma `Company` própria,
# com CNPJ próprio**. Com essa modelagem a transferência deixa de ser movimentação interna
# de estoque e passa a ser operação entre empresas — no ERPNext, um `Delivery Note` com
# `is_internal_customer`, que já é um documento que este app sabe emitir.
#
# ⚠️ **Entrada e saída NÃO são espelho, e a analogia com venda/devolução erraria.**
# Lido na tabela oficial da SEFAZ-PE, baixada e conferida linha a linha:
#
# | Código | Descrição oficial | Classifica por |
# |---|---|---|
# | `5.151`/`6.151` | "Transferência de produção do estabelecimento" | **origem** da mercadoria |
# | `5.152`/`6.152` | "Transferência de mercadoria adquirida ou recebida de terceiros" | **origem** |
# | `1.151`/`2.151` | "Transferência para industrialização ou produção rural" | **destino** |
# | `1.152`/`2.152` | "Transferência para comercialização" | **destino** |
#
# Ou seja: quem remete classifica pelo que a mercadoria **é** (produzi eu, ou comprei de
# terceiro); quem recebe classifica pelo que **vai fazer** com ela. Em `cfop_venda` e
# `cfop_devolucao_venda` os dois lados usam o mesmo par 01/02 — aqui não, e tratar igual
# produziria um código válido, existente, e errado.
# --------------------------------------------------------------------------------------


def cfop_transferencia_saida(mesmo_estado: bool, producao_propria: bool) -> str:
	"""`5151`/`6151` (produção do próprio estabelecimento) ou `5152`/`6152` (mercadoria
	adquirida ou recebida de terceiros) — saída em transferência para outro
	estabelecimento da mesma empresa.

	A distinção é de **origem** da mercadoria, igual à da venda — mas os três dígitos
	finais são `151`/`152`, não `101`/`102`.
	"""
	sufixo = "1" if producao_propria else "2"
	prefixo = "5" if mesmo_estado else "6"

	return f"{prefixo}15{sufixo}"


def cfop_transferencia_entrada(mesmo_estado: bool, finalidade: str) -> str:
	"""`1151`/`2151` (industrialização ou produção rural) ou `1152`/`2152`
	(comercialização) — entrada da mercadoria recebida em transferência.

	⚠️ O parâmetro é `finalidade`, **não** `producao_propria`: quem recebe classifica pelo
	destino que vai dar à mercadoria, não pela origem dela. Ver a nota acima.
	"""
	_validar_finalidade(finalidade)

	sufixo = "1" if finalidade == FINALIDADE_INDUSTRIALIZACAO else "2"
	prefixo = "1" if mesmo_estado else "2"

	return f"{prefixo}15{sufixo}"


def cfop_transferencia_uso_e_consumo(mesmo_estado: bool, entrada: bool = False) -> str:
	"""`5557`/`6557` na saída, `1557`/`2557` na entrada — transferência de material de uso
	ou consumo.

	Código próprio porque material de uso e consumo **não é mercadoria**: não gera crédito
	na entrada, e classificá-lo como `5152` daria a entender que gera.
	"""
	if entrada:
		return "1557" if mesmo_estado else "2557"

	return "5557" if mesmo_estado else "6557"


def cfop_transferencia_ativo_imobilizado(mesmo_estado: bool, entrada: bool = False) -> str:
	"""`5552`/`6552` na saída, `1552`/`2552` na entrada — transferência de bem do ativo
	imobilizado.

	Separado de uso e consumo porque o ativo imobilizado tem crédito de ICMS **apropriado
	em 48 parcelas** (LC 87/1996, art. 20, § 5º); uso e consumo não tem crédito nenhum. O
	mesmo código para os dois apagaria essa diferença.
	"""
	if entrada:
		return "1552" if mesmo_estado else "2552"

	return "5552" if mesmo_estado else "6552"
