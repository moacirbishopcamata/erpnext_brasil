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

# O IBS é dual: parte estadual e parte municipal, destacadas separadamente no XML
# (`pIBSUF`/`vIBSUF` e `pIBSMun`/`vIBSMun`). Tratá-lo como alíquota única é o erro que a
# rejeição 1026 acusa.
#
# Para 2026, a regra UB18-10 da NT 2025.002 exige `pIBSUF` igual a 0,1% — ou seja, toda a
# alíquota-teste do IBS está na parcela estadual. A parcela municipal em zero é inferência
# nossa, e não leitura direta da norma: se ela fosse positiva, o IBS total superaria os
# 0,1% que compõem o teste de 1%. Confirmar contra a NT antes de emitir em produção.
ALIQUOTA_TESTE_IBS_UF_2026 = Decimal("0.001")
ALIQUOTA_TESTE_IBS_MUN_2026 = Decimal("0")

# Data em que terminou a tolerância e o autorizador passou a rejeitar documento sem os
# campos de IBS e CBS (Ato Técnico Conjunto RFB/CGIBS, NT 2025.002).
INICIO_OBRIGATORIEDADE = (2026, 8, 3)


@dataclass(frozen=True)
class ResultadoIBSCBS:
	base: Decimal
	aliquota_ibs_uf: Decimal
	aliquota_ibs_mun: Decimal
	aliquota_cbs: Decimal
	ibs_uf: Decimal
	ibs_mun: Decimal
	cbs: Decimal
	informativo: bool
	"""True enquanto a apuração não gera recolhimento (ano-teste)."""

	@property
	def aliquota_ibs(self) -> Decimal:
		"""Alíquota consolidada do IBS. O XML destaca as parcelas, nunca esta soma."""
		return self.aliquota_ibs_uf + self.aliquota_ibs_mun

	@property
	def ibs(self) -> Decimal:
		"""Valor consolidado do IBS — corresponde a `vIBS` no XML."""
		return self.ibs_uf + self.ibs_mun

	@property
	def total(self) -> Decimal:
		return self.ibs + self.cbs


def aliquotas_do_ano(ano: int) -> tuple[Decimal, Decimal, Decimal]:
	"""Devolve (IBS UF, IBS município, CBS) para o ano, quando fixadas em norma.

	Só 2026 tem valores embutidos — é o único ano cuja alíquota está definida como
	alíquota-teste. Para 2027 em diante as alíquotas dependem de lei ainda por fixar, e
	inventar um número aqui seria pior que exigir que o usuário informe o vigente.
	"""
	if ano == ANO_TESTE:
		return (
			ALIQUOTA_TESTE_IBS_UF_2026,
			ALIQUOTA_TESTE_IBS_MUN_2026,
			ALIQUOTA_TESTE_CBS_2026,
		)

	raise ValueError(
		f"As alíquotas de IBS/CBS para {ano} não estão embutidas: só {ANO_TESTE} tem "
		"alíquota-teste fixada em norma. Informe as alíquotas vigentes."
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
	aliquota_ibs_uf: Decimal | None = None,
	aliquota_ibs_mun: Decimal | None = None,
	aliquota_cbs: Decimal | None = None,
	imposto_seletivo: Decimal = Decimal(0),
) -> ResultadoIBSCBS:
	"""Calcula IBS e CBS **por fora** sobre a base da operação.

	As parcelas estadual e municipal do IBS são calculadas em separado porque é assim
	que o XML as exige (`vIBSUF` e `vIBSMun`); somá-las antes perderia a informação que
	o documento precisa destacar.

	O Imposto Seletivo, quando incidir, integra a base de IBS e CBS — por isso entra
	como parcela somada, e não como tributo calculado à parte e ignorado aqui.

	Nenhum dos dois integra a própria base nem a base do outro: é aplicação direta da
	alíquota, sem o gross-up que o ICMS exige.
	"""
	if aliquota_ibs_uf is None or aliquota_ibs_mun is None or aliquota_cbs is None:
		padrao_uf, padrao_mun, padrao_cbs = aliquotas_do_ano(ano)
		aliquota_ibs_uf = padrao_uf if aliquota_ibs_uf is None else aliquota_ibs_uf
		aliquota_ibs_mun = padrao_mun if aliquota_ibs_mun is None else aliquota_ibs_mun
		aliquota_cbs = padrao_cbs if aliquota_cbs is None else aliquota_cbs

	aliquotas = (
		("aliquota_ibs_uf", aliquota_ibs_uf),
		("aliquota_ibs_mun", aliquota_ibs_mun),
		("aliquota_cbs", aliquota_cbs),
	)

	for nome, valor in aliquotas:
		if not (Decimal(0) <= valor < Decimal(1)):
			raise ValueError(f"{nome} deve ser fração entre 0 e 1, recebido {valor}")

	if imposto_seletivo < 0:
		raise ValueError("imposto_seletivo não pode ser negativo")

	base_final = arredondar(base + imposto_seletivo)

	if base_final < 0:
		raise ValueError("A base de IBS/CBS ficou negativa")

	return ResultadoIBSCBS(
		base=base_final,
		aliquota_ibs_uf=aliquota_ibs_uf,
		aliquota_ibs_mun=aliquota_ibs_mun,
		aliquota_cbs=aliquota_cbs,
		ibs_uf=arredondar(base_final * aliquota_ibs_uf),
		ibs_mun=arredondar(base_final * aliquota_ibs_mun),
		cbs=arredondar(base_final * aliquota_cbs),
		informativo=ano == ANO_TESTE,
	)
