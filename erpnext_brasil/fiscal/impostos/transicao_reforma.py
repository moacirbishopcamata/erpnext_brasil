# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Avisa quando as alíquotas embutidas da reforma tributária ficam para trás.

O risco real, encontrado numa auditoria de alertas
----------------------------------------------------------
`ibs_cbs.py` embute alíquotas de **um único ano**: 2026, o ano-teste (0,9% CBS + 0,1%
IBS, total de 1%, sem recolhimento). Isso está certo — as alíquotas de 2027 em diante
dependem de lei ainda por fixar, e inventá-las seria pior.

O perigo não é o cálculo: é o **padrão**. `Operacao.ano` nasce valendo `ANO_TESTE`, e
`integracao/mapeamento.operacao_de_documento` usava esse padrão quando o documento não
tinha ano de competência preenchido. Em 2027, um documento sem aquele campo cairia em
2026 e seria apurado com **1%** — enquanto a CBS plena já vale e PIS/COFINS já foram
extintos. Erro silencioso, de valor grande, e para menos: o tipo que só aparece numa
fiscalização.

Duas correções, e esta é a metade que avisa
----------------------------------------------------
1. `operacao_de_documento` passou a usar o **ano do próprio documento** quando o campo
   está vazio, em vez do ano-teste fixo. Com isso, um documento de 2027 pede as
   alíquotas de 2027 e `aliquotas_do_ano` **falha alto** ("não estão embutidas: informe
   as alíquotas vigentes") em vez de calcular errado em silêncio. Em 2026 nada muda: o
   ano do documento **é** o ano-teste.
2. Este módulo, que avisa **antes** de o usuário esbarrar no erro — na virada do ano,
   não na primeira nota que ele tentar emitir.

Puro: recebe o ano, não o consulta
------------------------------------------
`date.today()` ficaria escondido aqui dentro e tornaria impossível testar qualquer ano
que não o de hoje — o mesmo cuidado de `validade_certificado.py`.
"""

from dataclasses import dataclass

from erpnext_brasil.fiscal.impostos.ibs_cbs import ANO_TESTE

__all__ = ["SituacaoTransicao", "avaliar_transicao"]


@dataclass(frozen=True)
class SituacaoTransicao:
	"""Como o ano avaliado se relaciona com o único ano de alíquotas embutidas."""

	ano: int
	aliquotas_embutidas: bool
	deve_alertar: bool
	mensagem: str = ""


def avaliar_transicao(ano: int) -> SituacaoTransicao:
	"""Avalia se `ano` ainda é coberto pelas alíquotas embutidas no app.

	Alerta em dois casos, por motivos opostos:

	- **ano posterior** ao ano-teste: as alíquotas embutidas não valem mais, e qualquer
	  apuração que dependa delas está errada;
	- **ano anterior**: apuração de período em que IBS/CBS ainda nem existiam, sinal de
	  que o ano de competência foi digitado errado.
	"""
	if ano == ANO_TESTE:
		return SituacaoTransicao(ano=ano, aliquotas_embutidas=True, deve_alertar=False)

	if ano > ANO_TESTE:
		return SituacaoTransicao(
			ano=ano,
			aliquotas_embutidas=False,
			deve_alertar=True,
			mensagem=(
				f"Estamos em {ano}, mas este sistema só tem embutidas as alíquotas de "
				f"IBS/CBS de {ANO_TESTE} (a alíquota-teste de 1%). A partir de "
				f"{ANO_TESTE + 1} a CBS passa a ser plena e PIS/COFINS são extintos — "
				"as alíquotas vigentes precisam ser informadas no cadastro do item ou no "
				"documento, senão a apuração é recusada. Isso é proposital: apurar com a "
				"alíquota de teste seria recolher a menos."
			),
		)

	return SituacaoTransicao(
		ano=ano,
		aliquotas_embutidas=False,
		deve_alertar=True,
		mensagem=(
			f"O ano de competência {ano} é anterior a {ANO_TESTE}, quando IBS e CBS "
			"ainda não existiam. Confira se o ano foi digitado corretamente."
		),
	)
