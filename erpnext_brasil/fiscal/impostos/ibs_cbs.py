# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""IBS e CBS — os tributos da reforma (EC 132/2023), e o cronograma de transição.

Isto não é preparação para o futuro: **já está em vigor**. Desde 3 de agosto de 2026,
encerrado o período de tolerância do Ato Conjunto RFB/CGIBS nº 1/2025, documento fiscal
eletrônico sem os campos de IBS e CBS **é rejeitado pelo autorizador** para empresas do
regime regular. A Nota Técnica 2025.002 rege NF-e e NFC-e.

Consequência para quem integra: emitir NF-e sem estes campos não gera nota com imposto
errado — gera nota que não existe.

Diferença estrutural em relação ao que veio antes
-------------------------------------------------
O ICMS é calculado **por dentro**: integra a própria base, e por isso `icms.py` precisa
do gross-up por `(1 - alíquota)`. IBS e CBS são **por fora**: não integram a própria base
nem a base um do outro. É uma escolha deliberada da reforma, em nome da transparência —
o valor destacado é o que se paga, sem embutimento.

Portanto **não reutilize `base_por_dentro` aqui**. Se alguém "unificar" os dois cálculos
numa refatoração futura, o imposto sai errado nos dois.

Cronograma
----------
- **2026** — alíquota-teste de 1% no total (0,9% CBS + 0,1% IBS). A apuração é
  *meramente informativa*: não há recolhimento, desde que cumpridas as obrigações
  acessórias. Os campos, porém, são obrigatórios no documento.
- **2027** — CBS plena; PIS e COFINS extintos; IPI reduzido a zero (salvo Zona Franca
  de Manaus); entra o Imposto Seletivo.
- **2029 a 2032** — IBS sobe gradualmente enquanto ICMS e ISS descem.
- **2033** — ICMS e ISS extintos; IBS pleno.

As alíquotas de 2027 em diante dependem de lei ainda por fixar, então este módulo
**não as inventa**: elas entram por parâmetro, e o único ano com valores embutidos é
2026, cuja alíquota-teste está definida.

Funções puras, `Decimal`, alíquota como fração — mesmas regras de `icms.py`.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = [
	"ALIQUOTA_TESTE_CBS_2026",
	"ALIQUOTA_TESTE_IBS_2026",
	"ANO_TESTE",
	"ResultadoIBSCBS",
	"aliquotas_do_ano",
	"calcular_ibs_cbs",
	"exige_campos_no_documento",
]

ANO_TESTE = 2026

ALIQUOTA_TESTE_CBS_2026 = Decimal("0.009")
ALIQUOTA_TESTE_IBS_2026 = Decimal("0.001")

# Data em que terminou a tolerância e o autorizador passou a rejeitar documento sem os
# campos de IBS e CBS (Ato Técnico Conjunto RFB/CGIBS, NT 2025.002).
INICIO_OBRIGATORIEDADE = (2026, 8, 3)


@dataclass(frozen=True)
class ResultadoIBSCBS:
	base: Decimal
	aliquota_ibs: Decimal
	aliquota_cbs: Decimal
	ibs: Decimal
	cbs: Decimal
	informativo: bool
	"""True enquanto a apuração não gera recolhimento (ano-teste)."""

	@property
	def total(self) -> Decimal:
		return self.ibs + self.cbs


def aliquotas_do_ano(ano: int) -> tuple[Decimal, Decimal]:
	"""Devolve (IBS, CBS) para o ano, quando fixadas em norma.

	Só 2026 tem valores embutidos — é o único ano cuja alíquota está definida como
	alíquota-teste. Para 2027 em diante as alíquotas dependem de lei ainda por fixar, e
	inventar um número aqui seria pior que exigir que o usuário informe o vigente.
	"""
	if ano == ANO_TESTE:
		return ALIQUOTA_TESTE_IBS_2026, ALIQUOTA_TESTE_CBS_2026

	raise ValueError(
		f"As alíquotas de IBS/CBS para {ano} não estão embutidas: só {ANO_TESTE} tem "
		"alíquota-teste fixada em norma. Informe aliquota_ibs e aliquota_cbs vigentes."
	)


def exige_campos_no_documento(ano: int, mes: int, dia: int) -> bool:
	"""Indica se o documento fiscal já precisa trazer os campos de IBS e CBS.

	Antes de 3 de agosto de 2026 a ausência era tolerada; a partir dela, o autorizador
	rejeita o documento.
	"""
	return (ano, mes, dia) >= INICIO_OBRIGATORIEDADE


def calcular_ibs_cbs(
	base: Decimal,
	ano: int = ANO_TESTE,
	aliquota_ibs: Decimal | None = None,
	aliquota_cbs: Decimal | None = None,
	imposto_seletivo: Decimal = Decimal(0),
) -> ResultadoIBSCBS:
	"""Calcula IBS e CBS **por fora** sobre a base da operação.

	O Imposto Seletivo, quando incidir, integra a base de IBS e CBS — por isso entra
	como parcela somada, e não como tributo calculado à parte e ignorado aqui.

	Nenhum dos dois integra a própria base nem a base do outro: é aplicação direta da
	alíquota, sem o gross-up que o ICMS exige.
	"""
	if aliquota_ibs is None or aliquota_cbs is None:
		padrao_ibs, padrao_cbs = aliquotas_do_ano(ano)
		aliquota_ibs = padrao_ibs if aliquota_ibs is None else aliquota_ibs
		aliquota_cbs = padrao_cbs if aliquota_cbs is None else aliquota_cbs

	for nome, valor in (("aliquota_ibs", aliquota_ibs), ("aliquota_cbs", aliquota_cbs)):
		if not (Decimal(0) <= valor < Decimal(1)):
			raise ValueError(f"{nome} deve ser fração entre 0 e 1, recebido {valor}")

	if imposto_seletivo < 0:
		raise ValueError("imposto_seletivo não pode ser negativo")

	base_final = arredondar(base + imposto_seletivo)

	if base_final < 0:
		raise ValueError("A base de IBS/CBS ficou negativa")

	return ResultadoIBSCBS(
		base=base_final,
		aliquota_ibs=aliquota_ibs,
		aliquota_cbs=aliquota_cbs,
		ibs=arredondar(base_final * aliquota_ibs),
		cbs=arredondar(base_final * aliquota_cbs),
		informativo=ano == ANO_TESTE,
	)
