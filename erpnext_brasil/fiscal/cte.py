# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CT-e (Conhecimento de Transporte Eletrônico, modelo 57): montagem de grupos do XML.

Por que existe
--------------
Primeira peça de código do CT-e, depois do levantamento em `docs/cte-estado.md`. Escopo
deliberadamente estreito: só o grupo `ICMSUFFim` (partilha do ICMS entre UF de origem e UF de
término da prestação, para tomador consumidor final não contribuinte — Art. 155 §2º VII/VIII
CF, EC 87/2015), porque é o único ponto do levantamento já verificado byte a byte contra o XSD
oficial (`cte_v4.00.xsd`, `nfephp-org/sped-cte`, grupo `imp/ICMSUFFim`, linha 3960).

O que fica de fora, e por quê
------------------------------
A tabela de CFOP para prestação de serviço de transporte (grupo `5.35x`/`6.35x`/`6.36x` do
Convênio SINIEF 6/89) **não** está aqui: não foi verificada contra fonte primária nesta
investigação (o levantamento em `docs/cte-estado.md` confirmou que `ide.CFOP` usa o mesmo tipo
`TCfop` de 4 dígitos já implementado em `fiscal/cfop.py`, mas não os valores específicos de
transporte). Adicionar esses códigos de memória, sem checar a fonte, é exatamente o tipo de erro
silencioso que este projeto existe para evitar (ver `docs/cfop.md` sobre o bug de dígito faltante
pego pelo teste, e `docs/pcp-estado.md` sobre o campo quase reaproveitado errado) — fica para um
incremento futuro, com fonte citada.

Reuso deliberado
----------------
`montar_icms_uf_fim` não recalcula DIFAL — delega inteiramente a
`fiscal.impostos.icms.calcular_difal`, que já implementa a partilha de base dupla/única e o FCP.
A única coisa nova aqui é o **nome dos campos** no grupo `ICMSUFFim` do CT-e, que diverge do
`ICMSUFDest` da NF-e (`vBCUFFim` em vez de `vBCUFDest`, `pICMSUFFim` em vez de `pICMSUFDest`) —
confirmado por leitura direta do XSD, não suposto por analogia.
"""

from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import calcular_difal

__all__ = ["montar_icms_uf_fim"]


def montar_icms_uf_fim(
	valor_prestacao: Decimal,
	aliquota_interestadual: Decimal,
	aliquota_interna_destino: Decimal,
	aliquota_fcp: Decimal = Decimal(0),
	base_dupla: bool = True,
) -> dict:
	"""Monta o grupo `ICMSUFFim` (`imp/ICMSUFFim` do XSD do CT-e).

	Só se aplica a prestações interestaduais de transporte para consumidor final não
	contribuinte do ICMS — mesma condição de aplicabilidade do `ICMSUFDest` na NF-e.
	Devolve os nomes de campo exatos do XSD (`vBCUFFim`, `pFCPUFFim`, `pICMSUFFim`,
	`pICMSInter`, `vFCPUFFim`, `vICMSUFFim`, `vICMSUFIni` — este último é o ICMS que fica
	com a UF de início da prestação, equivalente ao `icms_origem` do cálculo).
	"""
	resultado = calcular_difal(
		valor_operacao=valor_prestacao,
		aliquota_interestadual=aliquota_interestadual,
		aliquota_interna_destino=aliquota_interna_destino,
		base_dupla=base_dupla,
		aliquota_fcp=aliquota_fcp,
	)

	grupo = {
		"vBCUFFim": str(resultado["base_destino"]),
		"pFCPUFFim": str(aliquota_fcp),
		"pICMSUFFim": str(aliquota_interna_destino),
		"pICMSInter": str(aliquota_interestadual),
		"vFCPUFFim": str(resultado["fcp"]),
		"vICMSUFFim": str(resultado["difal"]),
		"vICMSUFIni": str(resultado["icms_origem"]),
	}

	return grupo
