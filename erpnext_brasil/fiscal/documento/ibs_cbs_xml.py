# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Grupos de IBS/CBS do layout da NF-e (NT 2025.002).

O que este módulo devolve — e por que não é XML
-----------------------------------------------
Devolve **dicionários com os nomes oficiais das tags**, não uma string de XML. O motivo
é a porta de transmissão: o ACBrLib consome INI, a ACBr API consome JSON, e um provedor
comercial pode querer outra coisa. Emitir XML aqui obrigaria todo adaptador a
desmontá-lo de volta. A árvore de dicionários serializa para qualquer um dos três, e é
o formato que se consegue testar por igualdade.

Percentual, não fração
----------------------
Dentro do app a alíquota é sempre fração (0.001). No XML ela é **percentual com quatro
casas** (`0.1000`), e valores monetários têm duas (`10.00`). A conversão acontece aqui,
num lugar só — é justamente a fronteira onde a regra "alíquota é fração" precisa ser
desfeita, e concentrá-la evita que alguém a desfaça no meio de um cálculo.

Estrutura (grupo UB, nível de item)
-----------------------------------
    IBSCBS
      CST
      cClassTrib
      gIBSCBS
        vBC
        gIBSUF   -> pIBSUF, vIBSUF
        gIBSMun  -> pIBSMun, vIBSMun
        vIBS
        gCBS     -> pCBS, vCBS

Totais (grupo W03): `IBSCBSTot`, com `vBCIBSCBS`, `gIBS` (contendo `gIBSUFTot`,
`gIBSMunTot` e `vIBS`) e `gCBS`.

Os nomes acima foram conferidos em duas fontes independentes que descrevem a NT
2025.002. **Antes de emitir em produção, valide contra o XSD oficial** — nome de tag
errado não gera imposto errado, gera documento rejeitado, e o XSD é a única fonte que
não interpreta.
"""

from decimal import Decimal

from erpnext_brasil.fiscal.codigos.classificacao import (
	formato_valido_cclasstrib,
	formato_valido_cst,
)
from erpnext_brasil.fiscal.impostos.ibs_cbs import ResultadoIBSCBS

__all__ = ["grupo_ibscbs_item", "grupo_totais_ibscbs", "percentual", "valor"]

# Casas decimais exigidas pelo layout.
_CASAS_ALIQUOTA = Decimal("0.0001")
_CASAS_VALOR = Decimal("0.01")


def percentual(fracao: Decimal) -> str:
	"""Converte fração interna em percentual do XML: 0.001 -> "0.1000"."""
	return str((fracao * 100).quantize(_CASAS_ALIQUOTA))


def valor(montante: Decimal) -> str:
	"""Formata valor monetário com as duas casas que o layout exige."""
	return str(montante.quantize(_CASAS_VALOR))


def grupo_ibscbs_item(
	resultado: ResultadoIBSCBS,
	cst: str,
	classificacao_tributaria: str,
) -> dict:
	"""Monta o grupo UB de um item da NF-e.

	`cst` e `classificacao_tributaria` (`cClassTrib`) vêm das tabelas de classificação do
	IBS e da CBS — são dados de cadastro do item e da operação, não algo derivável do
	cálculo, por isso entram como parâmetro.
	"""
	if not cst or not classificacao_tributaria:
		raise ValueError(
			"CST e cClassTrib são obrigatórios no grupo IBSCBS: sem eles o documento é "
			"rejeitado, e não há valor padrão seguro a assumir"
		)

	# Formatos fixados pelo XSD: TCST = \d{3}, TcClassTrib = \d{6}. Barrar aqui evita
	# montar um documento inteiro para descobrir na SEFAZ que o código tinha um dígito
	# a menos — erro comum quando o valor vem de planilha e perde o zero à esquerda.
	if not formato_valido_cst(cst):
		raise ValueError(f"CST do IBS/CBS deve ter exatamente 3 dígitos, recebido {cst!r}")

	if not formato_valido_cclasstrib(classificacao_tributaria):
		raise ValueError(
			f"cClassTrib deve ter exatamente 6 dígitos, recebido {classificacao_tributaria!r}"
		)

	return {
		"IBSCBS": {
			"CST": cst,
			"cClassTrib": classificacao_tributaria,
			"gIBSCBS": {
				"vBC": valor(resultado.base),
				"gIBSUF": {
					"pIBSUF": percentual(resultado.aliquota_ibs_uf),
					"vIBSUF": valor(resultado.ibs_uf),
				},
				"gIBSMun": {
					"pIBSMun": percentual(resultado.aliquota_ibs_mun),
					"vIBSMun": valor(resultado.ibs_mun),
				},
				"vIBS": valor(resultado.ibs),
				"gCBS": {
					"pCBS": percentual(resultado.aliquota_cbs),
					"vCBS": valor(resultado.cbs),
				},
			},
		}
	}


def grupo_totais_ibscbs(resultados: list[ResultadoIBSCBS]) -> dict:
	"""Monta o grupo de totais (`IBSCBSTot`, tipo `TIBSCBSMonoTot`) somando os itens.

	Os totais são somados a partir dos **valores já arredondados de cada item**, e não
	recalculados sobre a base total. As duas contas divergem em centavos, e o validador
	confere o total contra a soma dos itens — recalcular é como se produz a rejeição de
	"total diverge da soma dos itens".

	Atenção à assimetria com o nível de item: dentro de `gIBS`, os subgrupos repetem os
	nomes `gIBSUF` e `gIBSMun` (não existe sufixo `Tot`), e **todos os seus filhos são
	obrigatórios** quando o grupo é informado. Por isso `vDif`, `vDevTrib`, `vCredPres` e
	`vCredPresCondSus` saem zerados em vez de omitidos: diferimento, devolução de tributo
	e crédito presumido ainda não são calculados por este app, mas o layout exige o campo.
	"""
	if not resultados:
		raise ValueError("Não há itens para totalizar")

	base = sum((r.base for r in resultados), Decimal("0.00"))
	ibs_uf = sum((r.ibs_uf for r in resultados), Decimal("0.00"))
	ibs_mun = sum((r.ibs_mun for r in resultados), Decimal("0.00"))
	cbs = sum((r.cbs for r in resultados), Decimal("0.00"))

	zero = valor(Decimal("0.00"))

	return {
		"IBSCBSTot": {
			"vBCIBSCBS": valor(base),
			"gIBS": {
				"gIBSUF": {"vDif": zero, "vDevTrib": zero, "vIBSUF": valor(ibs_uf)},
				"gIBSMun": {"vDif": zero, "vDevTrib": zero, "vIBSMun": valor(ibs_mun)},
				"vIBS": valor(ibs_uf + ibs_mun),
				"vCredPres": zero,
				"vCredPresCondSus": zero,
			},
			"gCBS": {
				"vDif": zero,
				"vDevTrib": zero,
				"vCBS": valor(cbs),
				"vCredPres": zero,
				"vCredPresCondSus": zero,
			},
		}
	}
