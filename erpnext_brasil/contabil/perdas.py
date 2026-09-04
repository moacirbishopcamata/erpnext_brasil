# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Gestão de perdas: baixa de estoque e a consequência fiscal que ela dispara.

Perda não é só custo — é estorno de crédito
----------------------------------------------------
Quem compra mercadoria credita ICMS (e, no não cumulativo, PIS/COFINS) porque vai
tributar a saída. Quando a mercadoria **não sai** — quebra, vencimento, furto,
deterioração —, o pressuposto do crédito deixa de existir, e o crédito tomado tem de ser
**estornado**.

Base: Lei Complementar 87/1996 (Lei Kandir), art. 21, que manda estornar o crédito de
ICMS quando a mercadoria "for objeto de saída ou prestação não tributada ou isenta" ou
"vier a perecer, deteriorar-se ou extraviar-se".

Consequência prática: uma perda de R$ 1.000 em estoque **não custa R$ 1.000**. Custa o
valor do estoque mais o crédito que se devolve. Sistema que só dá baixa contábil e não
estorna o crédito subestima a perda e deixa passivo fiscal para trás.

A exceção que muda tudo: perda normal do processo
------------------------------------------------------------
Nem toda perda estorna. **Perda inerente ao processo produtivo** — a evaporação, a
aparagem, o resíduo previsível — integra o custo de produção e **não** exige estorno: a
mercadoria não deixou de ser usada na atividade tributada, ela foi consumida por ela.

A distinção não é de tamanho, é de natureza. Por isso `TipoDePerda` separa as duas, e a
decisão de qual é qual **não é feita aqui**: depende do processo de cada empresa e, em
caso de dúvida, de posicionamento do Fisco estadual. Este módulo calcula a consequência
de uma classificação que o usuário faz.

O que fica fora de escopo, declarado
--------------------------------------------
- **Percentuais de quebra tolerada por UF ou por produto.** Alguns regulamentos
  estaduais fixam limites (perda técnica aceita sem estorno). Não estão aqui: variam por
  estado e por produto, e inventar um número seria criar regra fiscal sem fonte.
- **Dedutibilidade da perda no IRPJ.** Perda de estoque é dedutível com laudo ou
  comunicação, conforme o caso; é matéria de apuração de lucro real, não desta baixa.
- **Bloco K / registro da perda na EFD.** É o consumidor natural disto, e está na lista
  de pendências de `docs/sped-fiscal.md`.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = [
	"TIPOS_QUE_ESTORNAM",
	"PerdaInvalida",
	"ResultadoPerda",
	"TipoDePerda",
	"apurar_perda",
]

ZERO = Decimal("0.00")

TIPO_QUEBRA_NORMAL = "Quebra normal do processo"
TIPO_VENCIMENTO = "Vencimento"
TIPO_DETERIORACAO = "Deterioração"
TIPO_FURTO_OU_ROUBO = "Furto ou roubo"
TIPO_SINISTRO = "Sinistro"
TIPO_INVENTARIO = "Ajuste de inventário"

TIPOS_DE_PERDA = (
	TIPO_QUEBRA_NORMAL,
	TIPO_VENCIMENTO,
	TIPO_DETERIORACAO,
	TIPO_FURTO_OU_ROUBO,
	TIPO_SINISTRO,
	TIPO_INVENTARIO,
)

TIPOS_QUE_ESTORNAM = (
	TIPO_VENCIMENTO,
	TIPO_DETERIORACAO,
	TIPO_FURTO_OU_ROUBO,
	TIPO_SINISTRO,
	TIPO_INVENTARIO,
)
"""Todos menos a quebra normal — ver docstring do módulo sobre por que ela é diferente."""


class PerdaInvalida(ValueError):
	"""Baixa de estoque que não descreve uma perda real."""


@dataclass(frozen=True)
class TipoDePerda:
	"""O motivo da baixa, que decide se há estorno de crédito."""

	nome: str

	def __post_init__(self) -> None:
		if self.nome not in TIPOS_DE_PERDA:
			raise PerdaInvalida(
				f"tipo de perda deve ser um de {list(TIPOS_DE_PERDA)}, recebido {self.nome!r}"
			)

	@property
	def estorna_credito(self) -> bool:
		return self.nome in TIPOS_QUE_ESTORNAM


@dataclass(frozen=True)
class ResultadoPerda:
	"""O custo real da perda: o estoque baixado mais o crédito devolvido.

	Separar as duas parcelas é o ponto. Quem vê só `valor_do_estoque` subestima a perda
	e não sabe que tem um estorno a lançar.
	"""

	valor_do_estoque: Decimal
	creditos_estornados: Decimal
	estornos_por_tributo: dict[str, Decimal] = field(default_factory=dict)
	estorna: bool = True

	@property
	def custo_total_da_perda(self) -> Decimal:
		"""O que a perda de fato custou."""
		return self.valor_do_estoque + self.creditos_estornados


def apurar_perda(
	valor_do_estoque: Decimal,
	tipo: TipoDePerda,
	creditos_tomados: dict[str, Decimal] | None = None,
) -> ResultadoPerda:
	"""Apura a perda e o estorno de crédito que ela dispara.

	`creditos_tomados` é `{tributo: valor}` — o que foi creditado na entrada daquela
	mercadoria, tipicamente o que `custo_aquisicao.custo_de_aquisicao` devolveu em
	`creditos_por_tributo`. A simetria não é coincidência: estorna-se exatamente o que
	se creditou.

	Na quebra normal do processo, os créditos são **preservados** e devolvidos zerados —
	não porque não existiram, mas porque continuam legítimos.
	"""
	if not isinstance(valor_do_estoque, Decimal):
		raise PerdaInvalida(f"valor_do_estoque deve ser Decimal, recebido {type(valor_do_estoque).__name__}")

	if valor_do_estoque <= ZERO:
		raise PerdaInvalida(
			f"perda precisa de valor positivo, recebido {valor_do_estoque} — "
			"baixa de valor zero não é perda, é lançamento sem efeito"
		)

	creditos_tomados = dict(creditos_tomados or {})

	for nome, valor in creditos_tomados.items():
		if not isinstance(valor, Decimal):
			raise PerdaInvalida(f"crédito de {nome} deve ser Decimal, recebido {type(valor).__name__}")

		if valor < ZERO:
			raise PerdaInvalida(f"crédito de {nome} não pode ser negativo, recebido {valor}")

	if not tipo.estorna_credito:
		return ResultadoPerda(
			valor_do_estoque=arredondar(valor_do_estoque),
			creditos_estornados=ZERO,
			estorna=False,
		)

	estornos = {nome: arredondar(valor) for nome, valor in creditos_tomados.items() if valor > ZERO}

	return ResultadoPerda(
		valor_do_estoque=arredondar(valor_do_estoque),
		creditos_estornados=arredondar(sum(estornos.values(), ZERO)),
		estornos_por_tributo=estornos,
		estorna=True,
	)
