# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Retenções na fonte sobre serviços: IRRF, CSRF (CSLL/PIS/COFINS), INSS e ISS.

Categoria diferente dos demais tributos
---------------------------------------
ICMS, IPI e PIS/COFINS incidem *sobre a operação* e são somados ou embutidos no preço.
Retenção é outra coisa: o tomador **desconta do que vai pagar** e recolhe no lugar do
prestador. O valor da nota não muda; muda quem entrega o dinheiro a quem. Errar para
menos gera responsabilidade solidária do tomador — não é problema do prestador.

O que realmente dá trabalho aqui não é a multiplicação, é o **limite de dispensa**: cada
retenção tem um piso abaixo do qual não se retém, e as regras diferem entre si.

Limites como parâmetro, não como constante
------------------------------------------
Os valores padrão abaixo são os usualmente praticados, mas mudam por lei ordinária e o
ISS varia por município. Por isso todos entram como parâmetro com padrão explícito: o
código não deve afirmar com mais certeza do que tem. **Confirme os limites vigentes com
a contabilidade antes de usar em produção.**

Funções puras, `Decimal`, alíquota como fração — mesmas regras de `icms.py`.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = [
	"ALIQUOTA_COFINS",
	"ALIQUOTA_CCSL",
	"ALIQUOTA_CSRF",
	"ALIQUOTA_INSS",
	"ALIQUOTA_IRRF_SERVICOS",
	"ALIQUOTA_PIS",
	"MINIMO_CSRF",
	"MINIMO_IRRF",
	"Retencao",
	"calcular_csrf",
	"calcular_inss",
	"calcular_irrf",
	"calcular_iss_retido",
	"total_retido",
]

# Serviços profissionais prestados por pessoa jurídica.
ALIQUOTA_IRRF_SERVICOS = Decimal("0.015")

# CSRF: a soma das três contribuições retidas em conjunto.
ALIQUOTA_CCSL = Decimal("0.01")
ALIQUOTA_PIS = Decimal("0.0065")
ALIQUOTA_COFINS = Decimal("0.03")
ALIQUOTA_CSRF = ALIQUOTA_CCSL + ALIQUOTA_PIS + ALIQUOTA_COFINS  # 4,65%

ALIQUOTA_INSS = Decimal("0.11")

# Dispensa: não se retém quando o valor calculado (IRRF) ou a base (CSRF) fica abaixo.
# Os dois pisos se correspondem: 215,05 x 4,65% = 10,00.
MINIMO_IRRF = Decimal("10.00")
MINIMO_CSRF = Decimal("215.05")


@dataclass(frozen=True)
class Retencao:
	tributo: str
	base: Decimal
	aliquota: Decimal
	valor: Decimal
	dispensada: bool = False
	motivo: str = ""

	@property
	def retido(self) -> Decimal:
		"""Valor efetivamente retido — zero quando dispensada."""
		return Decimal("0.00") if self.dispensada else self.valor


def _validar(base: Decimal, aliquota: Decimal) -> None:
	if base < 0:
		raise ValueError(f"A base não pode ser negativa, recebido {base}")

	if not (Decimal(0) <= aliquota < Decimal(1)):
		raise ValueError(f"A alíquota deve ser fração entre 0 e 1, recebido {aliquota}")


def calcular_irrf(
	base: Decimal,
	aliquota: Decimal = ALIQUOTA_IRRF_SERVICOS,
	minimo: Decimal = MINIMO_IRRF,
) -> Retencao:
	"""IRRF sobre serviços prestados por pessoa jurídica.

	A dispensa do IRRF olha o **imposto calculado**, não a base: não se retém quando o
	valor apurado fica igual ou abaixo do mínimo. É diferente da CSRF, que olha a base —
	confundir as duas é o erro mais comum nesta área.
	"""
	_validar(base, aliquota)

	valor = arredondar(base * aliquota)
	dispensada = valor <= minimo

	return Retencao(
		tributo="IRRF",
		base=arredondar(base),
		aliquota=aliquota,
		valor=valor,
		dispensada=dispensada,
		motivo=f"valor calculado ({valor}) não supera o mínimo de {minimo}" if dispensada else "",
	)


def calcular_csrf(
	base: Decimal,
	aliquota: Decimal = ALIQUOTA_CSRF,
	minimo: Decimal = MINIMO_CSRF,
) -> Retencao:
	"""CSLL, PIS e COFINS retidos em conjunto (CSRF), à alíquota somada de 4,65%.

	Aqui a dispensa olha a **base do pagamento**, não o valor apurado. As três
	contribuições são retidas juntas, mas recolhidas em códigos distintos — por isso
	`decompor_csrf` existe.
	"""
	_validar(base, aliquota)

	dispensada = base <= minimo

	return Retencao(
		tributo="CSRF",
		base=arredondar(base),
		aliquota=aliquota,
		valor=arredondar(base * aliquota),
		dispensada=dispensada,
		motivo=f"base ({arredondar(base)}) não supera o mínimo de {minimo}" if dispensada else "",
	)


def decompor_csrf(retencao: Retencao) -> dict[str, Decimal]:
	"""Separa a CSRF nas três contribuições, para o recolhimento em códigos distintos.

	A soma das partes pode diferir do total em um centavo por arredondamento; o
	componente maior (COFINS) absorve a diferença, de modo que a soma sempre bate com o
	valor retido.
	"""
	if retencao.dispensada:
		return {"CSLL": Decimal("0.00"), "PIS": Decimal("0.00"), "COFINS": Decimal("0.00")}

	csll = arredondar(retencao.base * ALIQUOTA_CCSL)
	pis = arredondar(retencao.base * ALIQUOTA_PIS)
	cofins = retencao.valor - csll - pis

	return {"CSLL": csll, "PIS": pis, "COFINS": cofins}


def calcular_inss(base: Decimal, aliquota: Decimal = ALIQUOTA_INSS) -> Retencao:
	"""INSS retido sobre cessão de mão de obra e empreitada.

	Não tem limite de dispensa por valor: incide desde o primeiro real.
	"""
	_validar(base, aliquota)

	return Retencao(
		tributo="INSS",
		base=arredondar(base),
		aliquota=aliquota,
		valor=arredondar(base * aliquota),
	)


def calcular_iss_retido(base: Decimal, aliquota: Decimal) -> Retencao:
	"""ISS retido pelo tomador.

	A alíquota **não tem padrão** e é obrigatória: o ISS é municipal e varia de 2% a 5%
	conforme o município e o item da lista de serviços. Assumir um valor aqui seria
	inventar tributo.
	"""
	_validar(base, aliquota)

	if aliquota == 0:
		raise ValueError(
			"A alíquota do ISS é obrigatória: varia por município e por item da lista "
			"de serviços, e não há padrão nacional a assumir"
		)

	return Retencao(
		tributo="ISS",
		base=arredondar(base),
		aliquota=aliquota,
		valor=arredondar(base * aliquota),
	)


def total_retido(retencoes: list[Retencao]) -> Decimal:
	"""Soma o que será efetivamente descontado do pagamento ao prestador."""
	return sum((r.retido for r in retencoes), Decimal("0.00"))
