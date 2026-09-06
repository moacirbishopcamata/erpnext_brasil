# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Depreciação fiscal brasileira: quota dedutível, turnos, bens usados e o teto.

Fecha o gap 3 de `docs/tropicalizacao-por-area.md`. O ERPNext traz Asset Register e três
métodos (linear, saldo decrescente, duplo decrescente); o Brasil usa **um** — quota sobre o
**custo de aquisição** —, com taxas por espécie de bem e um punhado de regras que não se
deduzem de nenhum dos três.

Fonte
--------
**RIR/2018 — Decreto nº 9.580/2018, arts. 317 a 323**, baixado do Planalto e lido
localmente. Cada regra abaixo cita o artigo. As taxas vêm do **Anexo III da IN RFB nº
1.700/2017**.

As cinco regras que um método linear genérico erra
---------------------------------------------------------

**1. A base é sempre o custo de aquisição, nunca o saldo residual** (art. 319). Não existe
"saldo decrescente" na quota fiscal brasileira: a quota do último ano é igual à do
primeiro. Aplicar taxa sobre valor contábil residual — o que o ERPNext chama de *Written
Down Value* — produz um número que não é o dedutível.

**2. O mês conta inteiro; não há rateio por dias** (art. 319, § 2º): *"dispensado o ajuste
da taxa para os bens postos em funcionamento ou baixados no curso do mês"*. Um bem que
entrou em serviço no dia 28 deprecia o mês todo. Quem faz *pro rata die* deduz a menos, e
a diferença atravessa toda a vida do bem.

**3. Bens usados usam o MAIOR dos dois prazos** (art. 322): metade da vida útil do bem
novo, **ou** o restante da vida útil — o que for maior. Parece que seria o menor, e não é.
Errar aqui deduz depressa demais, que é o lado que o Fisco glosa.

**4. O acumulado nunca passa do custo de aquisição** (art. 317, § 3º): *"Em qualquer
hipótese"* — inclusive somando a depreciação acelerada. É teto, não meta.

**5. A depreciação começa quando o bem entra em serviço, não quando é comprado**
(art. 317, § 2º): *"a partir da época em que o bem é instalado, posto em serviço ou em
condições de produzir"*. Para edificação, a partir da conclusão e do início da utilização
(art. 318, I).

O que este módulo **não** faz
-----------------------------------
- **Não reproduz o Anexo III inteiro.** São centenas de linhas por NCM. `TAXAS_ANUAIS`
  traz um **núcleo** das espécies mais comuns, declarado como tal — e a lei assegura ao
  contribuinte usar taxa diferente desde que prove a adequação (art. 320, § 1º), então uma
  tabela fechada seria falsa de qualquer modo.
- **Não decide se um bem é depreciável.** `BENS_NAO_DEPRECIAVEIS` documenta as quatro
  vedações do art. 318, parágrafo único, para quem precise consultar; classificar o bem é
  do usuário.
- **Não faz o LALUR.** O art. 321 permite excluir do lucro líquido a diferença entre a
  depreciação contábil e a fiscal, e manda adicioná-la de volta quando o acumulado atinge o
  teto. Isso é controle de Parte B, domínio que o projeto ainda não tem — ver
  `docs/ecf-blocos-l-m-n.md`.
- **Não trata depreciação acelerada incentivada** (art. 324), que é benefício por indústria
  e prazo certo, com exclusão direta no Lalur.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

__all__ = [
	"BENS_NAO_DEPRECIAVEIS",
	"COEFICIENTE_POR_TURNOS",
	"TAXAS_ANUAIS",
	"DepreciacaoInvalida",
	"QuotaDepreciacao",
	"coeficiente_de_turnos",
	"depreciar",
	"quota_anual",
	"quota_mensal",
	"taxa_de_bem_usado",
]

ZERO = Decimal("0")
_CENTAVO = Decimal("0.01")

COEFICIENTE_POR_TURNOS = {
	1: Decimal("1.0"),
	2: Decimal("1.5"),
	3: Decimal("2.0"),
}
"""Coeficientes de depreciação acelerada por turnos — RIR/2018, art. 323.

Citação literal: *"I - um turno de oito horas - um inteiro; II - dois turnos de oito horas
- um inteiro e cinco décimos; e III - três turnos de oito horas - dois inteiros"*.

⚠️ Vale só para **bens móveis** — o artigo diz "Em relação aos bens móveis". Aplicá-lo a
uma edificação seria acelerar o que a lei não acelera.

⚠️ E exige prova do regime de turnos. O coeficiente é direito do contribuinte que opera
naquele regime, não escolha livre.
"""

TAXAS_ANUAIS = {
	"edificacoes": (Decimal("4"), 25),
	"instalacoes": (Decimal("10"), 10),
	"moveis_e_utensilios": (Decimal("10"), 10),
	"maquinas_e_equipamentos": (Decimal("10"), 10),
	"computadores_e_perifericos": (Decimal("20"), 5),
	"veiculos_de_passageiros": (Decimal("20"), 5),
	"veiculos_de_carga": (Decimal("25"), 4),
	"tratores": (Decimal("25"), 4),
	"motocicletas": (Decimal("25"), 4),
	"ferramentas": (Decimal("20"), 5),
}
"""Núcleo do Anexo III da IN RFB 1.700/2017: `(taxa anual em %, vida útil em anos)`.

**Núcleo, não a tabela.** O Anexo III tem centenas de linhas por NCM, e o art. 320, § 1º
assegura ao contribuinte computar quota diferente desde que prove a adequação — uma tabela
fechada aqui seria falsa mesmo se completa.

As chaves são deste projeto, não da norma: a norma classifica por NCM. Servem para dar um
padrão razoável, e quem tem o NCM do bem deve usar a taxa que o Anexo III lhe atribui.
"""

BENS_NAO_DEPRECIAVEIS = (
	"terrenos, exceto melhoramentos e construções",
	"prédios ou construções não alugados nem usados na produção, ou destinados à revenda",
	"bens que normalmente aumentam de valor com o tempo, como obras de arte e antiguidades",
	"bens para os quais seja registrada quota de exaustão",
)
"""As quatro vedações do art. 318, parágrafo único, para consulta.

Classificar o bem é do usuário — este módulo não adivinha que um imóvel é terreno.
"""


class DepreciacaoInvalida(ValueError):
	"""Parâmetro que produziria quota indedutível."""

	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


@dataclass(frozen=True)
class QuotaDepreciacao:
	"""O resultado de um período de depreciação."""

	quota: Decimal
	acumulado: Decimal
	custo: Decimal

	@property
	def valor_residual(self) -> Decimal:
		"""O que falta depreciar. Zero quando o bem chegou ao teto."""
		return self.custo - self.acumulado

	@property
	def totalmente_depreciado(self) -> bool:
		return self.acumulado >= self.custo


def _arredondar(valor: Decimal) -> Decimal:
	"""Duas casas, meio para cima — a moeda do país."""
	return valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def _exigir(condicao: bool, mensagem: str, campo: str) -> None:
	if not condicao:
		raise DepreciacaoInvalida(mensagem, campo)


def coeficiente_de_turnos(turnos: int) -> Decimal:
	"""O coeficiente do art. 323 para 1, 2 ou 3 turnos de oito horas.

	Recusa qualquer outro número: a lei enumera três casos, e interpolar um quarto (meio
	turno, quatro turnos) seria inventar direito que ela não dá.
	"""
	coeficiente = COEFICIENTE_POR_TURNOS.get(turnos)

	_exigir(
		coeficiente is not None,
		f"o art. 323 prevê 1, 2 ou 3 turnos de oito horas; recebido {turnos!r}",
		"turnos",
	)

	return coeficiente


def taxa_de_bem_usado(vida_util_nova: int, vida_util_restante: int) -> int:
	"""A vida útil de um bem adquirido usado — art. 322.

	*"a taxa anual de depreciação de bens adquiridos usados será fixada tendo em vista o
	**maior** dos seguintes prazos: I - a metade da vida útil admissível para o bem
	adquirido novo; ou II - o restante da vida útil"*.

	O **maior**, não o menor — é o ponto em que a intuição erra, e errar aqui deduz depressa
	demais, que é o lado glosado.

	A metade é arredondada para cima: meia vida útil de 5 anos são 3, não 2. A norma não
	trata do ímpar, e arredondar para baixo deduziria mais rápido, na direção da glosa.
	"""
	_exigir(vida_util_nova > 0, "vida útil do bem novo deve ser positiva", "vida_util_nova")
	_exigir(vida_util_restante >= 0, "vida útil restante não pode ser negativa", "vida_util_restante")

	metade = -(-vida_util_nova // 2)

	return max(metade, vida_util_restante)


def quota_anual(custo: Decimal, taxa_anual: Decimal, turnos: int = 1) -> Decimal:
	"""A quota anual dedutível — art. 319, com o coeficiente do art. 323.

	`taxa_anual` em pontos percentuais (10 para 10%), como o Anexo III a publica.

	⚠️ A base é o **custo de aquisição**, não o saldo residual. Ver a nota 1 no topo.
	"""
	_exigir(custo > ZERO, f"custo deve ser positivo, recebido {custo}", "custo")
	_exigir(taxa_anual > ZERO, f"taxa anual deve ser positiva, recebida {taxa_anual}", "taxa_anual")

	return _arredondar(custo * taxa_anual / Decimal("100") * coeficiente_de_turnos(turnos))


def quota_mensal(custo: Decimal, taxa_anual: Decimal, turnos: int = 1) -> Decimal:
	"""A quota de um mês — art. 319, § 2º.

	Um mês é um mês: o bem posto em funcionamento no dia 28 deprecia igual ao posto no dia
	1º, porque o § 2º dispensa o ajuste da taxa nesse caso. **Não há rateio por dias.**

	O arredondamento é do resultado mensal, não da quota anual dividida — dividir uma quota
	já arredondada por 12 espalha o resto do arredondamento por todos os meses.
	"""
	_exigir(custo > ZERO, f"custo deve ser positivo, recebido {custo}", "custo")
	_exigir(taxa_anual > ZERO, f"taxa anual deve ser positiva, recebida {taxa_anual}", "taxa_anual")

	bruta = custo * taxa_anual / Decimal("100") * coeficiente_de_turnos(turnos) / Decimal("12")

	return _arredondar(bruta)


def depreciar(
	custo: Decimal,
	taxa_anual: Decimal,
	meses: int = 1,
	acumulado: Decimal = ZERO,
	turnos: int = 1,
) -> QuotaDepreciacao:
	"""Deprecia `meses` meses e devolve a quota do período mais o novo acumulado.

	⚠️ **O acumulado nunca passa do custo** (art. 317, § 3º: *"Em qualquer hipótese"*). Se o
	período calculado ultrapassaria o teto, a quota é reduzida ao que falta — e o excedente
	simplesmente não existe, não é diferido para depois.

	É esse corte que faz a aceleração por turnos **encurtar** a vida do bem em vez de
	aumentar a dedução total: dois turnos deduzem em dois terços do tempo o mesmo valor.
	"""
	_exigir(meses >= 0, f"meses não pode ser negativo, recebido {meses}", "meses")
	_exigir(acumulado >= ZERO, f"acumulado não pode ser negativo, recebido {acumulado}", "acumulado")
	_exigir(
		acumulado <= custo,
		f"acumulado ({acumulado}) já ultrapassa o custo ({custo}) — art. 317, § 3º",
		"acumulado",
	)

	bruta = quota_mensal(custo, taxa_anual, turnos) * meses
	falta = custo - acumulado
	quota = min(bruta, falta)

	return QuotaDepreciacao(
		quota=_arredondar(quota),
		acumulado=_arredondar(acumulado + quota),
		custo=custo,
	)
