# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Apuração de um item: a ordem em que as bases se compõem.

O problema que este módulo resolve
----------------------------------
Cada módulo de tributo sabe calcular o seu imposto a partir de uma base. Nenhum deles
sabe **qual** base — e é aí que mora o erro, porque as bases dependem umas das outras:

1. o **IPI** entra na base do ICMS ou não, conforme a natureza da operação;
2. o **ICMS** é calculado sobre essa base composta;
3. o **ICMS destacado sai** da base de PIS/COFINS (RE 574.706);
4. **IBS e CBS** são por fora e não integram base nenhuma, mas o Imposto Seletivo
   integra a deles.

Calcular os quatro isoladamente e somar produz números plausíveis e errados. A ordem
acima é a regra, e ela fica escrita num lugar só — aqui.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.ibs_cbs import ANO_TESTE, ResultadoIBSCBS, calcular_ibs_cbs
from erpnext_brasil.fiscal.impostos.icms import ResultadoICMS, arredondar, calcular_icms
from erpnext_brasil.fiscal.impostos.ipi import ResultadoIPI, calcular_ipi
from erpnext_brasil.fiscal.impostos.pis_cofins import (
	ResultadoContribuicao,
	calcular_pis_cofins,
)

__all__ = ["ApuracaoItem", "ItemFiscal", "Operacao", "apurar", "apurar_documento"]

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class Operacao:
	"""Natureza da operação — o que decide as regras, não os valores."""

	destinatario_contribuinte: bool = True
	destinado_a_industrializacao_ou_comercio: bool = True
	regime_pis_cofins: str = "cumulativo"
	ano: int = ANO_TESTE
	excluir_icms_de_pis_cofins: bool = True


@dataclass(frozen=True)
class ItemFiscal:
	"""Valores e alíquotas de um item. Alíquotas sempre como fração."""

	valor_produtos: Decimal
	frete: Decimal = ZERO
	seguro: Decimal = ZERO
	outras_despesas: Decimal = ZERO
	descontos: Decimal = ZERO

	aliquota_icms: Decimal = ZERO
	reducao_icms: Decimal = ZERO
	aliquota_ipi: Decimal = ZERO
	imposto_seletivo: Decimal = ZERO

	aliquota_ibs_uf: Decimal | None = None
	aliquota_ibs_mun: Decimal | None = None
	aliquota_cbs: Decimal | None = None

	cst_ibs_cbs: str = ""
	classificacao_tributaria: str = ""

	@property
	def valor_liquido(self) -> Decimal:
		"""Valor da operação: produtos mais acessórios, menos descontos.

		É a base de partida de tudo. O IPI **não** entra aqui — ele é calculado sobre
		esta base e depois, conforme a operação, pode ou não se somar à do ICMS.
		"""
		return (
			self.valor_produtos
			+ self.frete
			+ self.seguro
			+ self.outras_despesas
			- self.descontos
		)


@dataclass(frozen=True)
class ApuracaoItem:
	item: ItemFiscal
	ipi: ResultadoIPI
	icms: ResultadoICMS
	pis_cofins: ResultadoContribuicao
	ibs_cbs: ResultadoIBSCBS
	base_icms: Decimal
	ipi_na_base_do_icms: bool

	@property
	def total_item(self) -> Decimal:
		"""Total do item com os tributos que se somam ao preço.

		Somam-se por fora: IPI, IBS, CBS e Imposto Seletivo. **Não** se soma o ICMS, que
		já está dentro do preço, nem PIS/COFINS, que também são por dentro. Somar o ICMS
		aqui dobraria o imposto — é o erro que a distinção por dentro/por fora existe
		para evitar.
		"""
		return arredondar(
			self.item.valor_liquido
			+ self.ipi.valor
			+ self.item.imposto_seletivo
			+ self.ibs_cbs.ibs
			+ self.ibs_cbs.cbs
		)


def apurar(item: ItemFiscal, operacao: Operacao | None = None) -> ApuracaoItem:
	"""Apura todos os tributos de um item, na ordem em que as bases se compõem."""
	operacao = operacao or Operacao()

	if item.valor_liquido < 0:
		raise ValueError("O valor líquido do item ficou negativo; verifique descontos")

	# 1. IPI sobre o valor da operação. O resultado carrega a decisão constitucional
	#    sobre entrar ou não na base do ICMS.
	ipi = calcular_ipi(
		item.valor_produtos,
		item.aliquota_ipi,
		frete=item.frete,
		seguro=item.seguro,
		outras_despesas=item.outras_despesas,
		descontos=item.descontos,
		destinatario_contribuinte=operacao.destinatario_contribuinte,
		destinado_a_industrializacao_ou_comercio=(
			operacao.destinado_a_industrializacao_ou_comercio
		),
	)

	# 2. Base do ICMS: o valor da operação, mais o IPI quando ele compõe.
	base_icms = item.valor_liquido + (ipi.valor if ipi.compoe_base_icms else ZERO)
	icms = calcular_icms(base_icms, item.aliquota_icms, item.reducao_icms)

	# 3. PIS/COFINS sobre a receita, com o ICMS destacado fora da base.
	pis_cofins = calcular_pis_cofins(
		item.valor_liquido,
		operacao.regime_pis_cofins,
		icms_destacado=icms.valor,
		excluir_icms=operacao.excluir_icms_de_pis_cofins,
	)

	# 4. IBS e CBS por fora, sobre o valor da operação acrescido do Imposto Seletivo.
	ibs_cbs = calcular_ibs_cbs(
		item.valor_liquido,
		ano=operacao.ano,
		aliquota_ibs_uf=item.aliquota_ibs_uf,
		aliquota_ibs_mun=item.aliquota_ibs_mun,
		aliquota_cbs=item.aliquota_cbs,
		imposto_seletivo=item.imposto_seletivo,
	)

	return ApuracaoItem(
		item=item,
		ipi=ipi,
		icms=icms,
		pis_cofins=pis_cofins,
		ibs_cbs=ibs_cbs,
		base_icms=arredondar(base_icms),
		ipi_na_base_do_icms=ipi.compoe_base_icms,
	)


@dataclass(frozen=True)
class ApuracaoDocumento:
	itens: list[ApuracaoItem] = field(default_factory=list)

	def _somar(self, extrair) -> Decimal:
		return sum((extrair(i) for i in self.itens), ZERO)

	@property
	def total_produtos(self) -> Decimal:
		return self._somar(lambda i: i.item.valor_liquido)

	@property
	def total_ipi(self) -> Decimal:
		return self._somar(lambda i: i.ipi.valor)

	@property
	def total_icms(self) -> Decimal:
		return self._somar(lambda i: i.icms.valor)

	@property
	def total_ibs(self) -> Decimal:
		return self._somar(lambda i: i.ibs_cbs.ibs)

	@property
	def total_cbs(self) -> Decimal:
		return self._somar(lambda i: i.ibs_cbs.cbs)

	@property
	def total_documento(self) -> Decimal:
		"""Soma dos totais de item — nunca recalculada sobre a base agregada.

		O validador confere o total contra a soma dos itens; recalcular divergiria em
		centavos e produziria rejeição.
		"""
		return self._somar(lambda i: i.total_item)


def apurar_documento(itens: list[ItemFiscal], operacao: Operacao | None = None) -> ApuracaoDocumento:
	"""Apura um documento inteiro, item a item."""
	if not itens:
		raise ValueError("Documento sem itens")

	return ApuracaoDocumento(itens=[apurar(item, operacao) for item in itens])
