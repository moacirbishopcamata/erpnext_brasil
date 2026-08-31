# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CFOP de prestação de serviço de transporte (grupos 5.35x/6.35x) — o CFOP do CT-e.

Por que existe, separado de `fiscal/cfop.py`
---------------------------------------------
`fiscal/cfop.py` cobre CFOP de **mercadoria** (compra/venda/devolução). O CFOP que vai em
`ide.CFOP` do CT-e (ver `docs/cte-estado.md`) é de **prestação de serviço**, com uma tabela
paralela e semanticamente diferente — o critério não é finalidade de industrialização/
comercialização, é o **perfil de quem contrata o transporte** (estabelecimento industrial,
comercial, prestador de comunicação, gerador/distribuidor de energia, produtor rural, não
contribuinte, ou dispensa de nota fiscal pela carga transportada). Por isso é um módulo à
parte, não uma extensão do que já existe.

Fonte e nível de confiança — divergente do resto do projeto, declarado
------------------------------------------------------------------------------
O texto oficial do Convênio SINIEF s/nº de 1970 (com os ajustes que criaram os códigos do
grupo 5.35x/6.35x) não foi acessível nesta investigação (`confaz.fazenda.gov.br` devolveu 404
para o Ajuste consultado). Diferente do restante deste projeto — onde a fonte primária é a
regra —, esta tabela foi verificada cruzando **três fontes secundárias independentes que
concordam integralmente** entre si nos oito códigos e nas descrições (Cosmos/Bluesoft, portal
Contadores.cnt.br, base de conhecimento Una Sistemas para CT-e — a última é particularmente
relevante por ser documentação voltada a emissão de CT-e, não a um catálogo genérico de CFOP).
Tratado aqui como confiável o suficiente para implementar, mas com o nível de confiança
explicitamente mais baixo que os módulos com fonte primária — revisar se/quando o texto do
Ajuste SINIEF for localizado.

Escopo: nove códigos por perfil de tomador — não a tabela inteira do grupo 5.35x/6.35x
------------------------------------------------------------------------------------------
**Cobertos** — `cfop_prestacao_transporte`:

| Perfil do tomador | Mesmo estado | Outro estado |
|---|---|---|
| Estabelecimento industrial | `5352` | `6352` |
| Estabelecimento comercial | `5353` | `6353` |
| Prestador de serviço de comunicação | `5354` | `6354` |
| Geradora/distribuidora de energia elétrica | `5355` | `6355` |
| Produtor rural | `5356` | `6356` |
| Não contribuinte do ICMS | `5357` | `6357` |
| Carga dispensada de nota fiscal | `5359` | `6359` |
| Contribuinte substituto tributário do serviço | `5360` | `6360` |

**Coberto** — `cfop_subcontratacao_transporte`: `5351`/`6351`, prestação de serviço de
transporte para execução de serviço da mesma natureza (redespacho/subcontratação entre
transportadoras) — código distinto por não caber no critério "perfil do tomador" acima (o
tomador aqui é outra transportadora, contratando para a mesma finalidade).

**Fora de escopo, documentado, não implementado**: `5932`/`6932` (prestação iniciada em UF
diversa daquela onde inscrito o prestador — caso de redespacho intermediário mais raro);
qualquer CFOP do grupo `1.35x`/`2.35x` (entrada — usado por quem *contrata* o transporte para
registrar a aquisição do serviço em sua própria escrituração, não pelo emitente do CT-e); CFOP
de transporte internacional (`7.35x`, exportação de serviço) — não pesquisado.
"""

from erpnext_brasil.fiscal.cfop import CfopInvalido

__all__ = [
	"FINALIDADE_COMERCIAL",
	"FINALIDADE_COMUNICACAO",
	"FINALIDADE_DISPENSADO_NF",
	"FINALIDADE_ENERGIA",
	"FINALIDADE_INDUSTRIAL",
	"FINALIDADE_NAO_CONTRIBUINTE",
	"FINALIDADE_PRODUTOR_RURAL",
	"FINALIDADE_SUBSTITUTO_TRIBUTARIO",
	"cfop_prestacao_transporte",
	"cfop_subcontratacao_transporte",
]

FINALIDADE_INDUSTRIAL = "industrial"
FINALIDADE_COMERCIAL = "comercial"
FINALIDADE_COMUNICACAO = "comunicacao"
FINALIDADE_ENERGIA = "energia"
FINALIDADE_PRODUTOR_RURAL = "produtor_rural"
FINALIDADE_NAO_CONTRIBUINTE = "nao_contribuinte"
FINALIDADE_DISPENSADO_NF = "dispensado_nf"
FINALIDADE_SUBSTITUTO_TRIBUTARIO = "substituto_tributario"

_SUFIXO_POR_FINALIDADE = {
	FINALIDADE_INDUSTRIAL: "352",
	FINALIDADE_COMERCIAL: "353",
	FINALIDADE_COMUNICACAO: "354",
	FINALIDADE_ENERGIA: "355",
	FINALIDADE_PRODUTOR_RURAL: "356",
	FINALIDADE_NAO_CONTRIBUINTE: "357",
	FINALIDADE_DISPENSADO_NF: "359",
	FINALIDADE_SUBSTITUTO_TRIBUTARIO: "360",
}


def cfop_prestacao_transporte(mesmo_estado: bool, finalidade: str) -> str:
	"""CFOP da prestação de serviço de transporte, pelo perfil de quem contrata (tomador).

	`mesmo_estado` compara a UF do prestador (emitente do CT-e) com a UF de início da
	prestação — mesmo critério de âmbito usado em `fiscal/cfop.py`, só que aqui não há
	terceiro dígito de exterior verificado (fora de escopo, ver docstring do módulo).
	"""
	if finalidade not in _SUFIXO_POR_FINALIDADE:
		raise CfopInvalido(
			f"finalidade de prestação de transporte desconhecida: {finalidade!r}; "
			f"esperado uma de {sorted(_SUFIXO_POR_FINALIDADE)}"
		)

	primeiro_digito = "5" if mesmo_estado else "6"

	return f"{primeiro_digito}{_SUFIXO_POR_FINALIDADE[finalidade]}"


def cfop_subcontratacao_transporte(mesmo_estado: bool) -> str:
	"""CFOP `5351`/`6351` — redespacho/subcontratação entre transportadoras."""
	return "5351" if mesmo_estado else "6351"
