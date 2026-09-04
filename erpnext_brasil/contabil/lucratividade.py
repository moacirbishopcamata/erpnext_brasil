# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lucratividade pela cadeia da DRE — Art. 187 da Lei 6.404/76.

Por que "lucro" precisa de definição legal, e não de opinião
--------------------------------------------------------------------
"Quanto lucrei?" tem várias respostas certas, e trocá-las é como se compara margem de
empresas diferentes e se conclui besteira. O Art. 187 fixa a ordem:

```
    Receita Bruta
(−) Deduções (devoluções, abatimentos, impostos sobre vendas)
=   Receita Líquida
(−) Custo das Mercadorias e Serviços Vendidos
=   Lucro Bruto
(−) Despesas operacionais
=   Resultado Operacional
```

`plano_de_contas.py` já modela essas contas e registra que **Receita Líquida e Lucro
Bruto são subtotais calculados, não contas próprias**. Este módulo é o cálculo que faltava
para transformá-las em número.

O erro que a cadeia evita: dividir pela receita errada
---------------------------------------------------------------
Margem bruta calculada sobre a **receita bruta** dá um número maior e falso — os impostos
sobre vendas ainda estão lá dentro, e eles não são receita de ninguém: são repasse. A
margem tem de sair sobre a **receita líquida**, e é por isso que a dedução vem antes na
ordem legal.

Uma empresa que fatura R$ 1.000 com R$ 265 de impostos e R$ 600 de custo tem margem bruta
de **18,4%** (135 ÷ 735), não de 13,5% (135 ÷ 1.000) nem de 40% (400 ÷ 1.000). Os três
números aparecem em planilha por aí; só o primeiro responde à pergunta.

Relação com `fiscal/precificacao.py`
-------------------------------------------
Aquele módulo olha **um item**, antes da venda: que preço entrega a margem desejada. Este
olha o **período**, depois: que resultado a operação de fato entregou. Os dois usam a
mesma ideia de margem sobre a receita, e é por isso que fecham — há teste provando que
precificar com margem de 20% e apurar o período dá 20%.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import Decimal

__all__ = ["LucratividadeInvalida", "ResultadoLucratividade", "apurar_lucratividade"]

ZERO = Decimal("0.00")


class LucratividadeInvalida(ValueError):
	"""Composição de resultado que não fecha com a estrutura do Art. 187."""


@dataclass(frozen=True)
class ResultadoLucratividade:
	"""A DRE em números, com cada subtotal na ordem legal.

	Cada margem é fração da **receita líquida**, não da bruta — ver docstring do módulo
	sobre por que essa escolha não é estilística.
	"""

	receita_bruta: Decimal
	deducoes: Decimal
	custo: Decimal
	despesas_operacionais: Decimal

	@property
	def receita_liquida(self) -> Decimal:
		return self.receita_bruta - self.deducoes

	@property
	def lucro_bruto(self) -> Decimal:
		return self.receita_liquida - self.custo

	@property
	def resultado_operacional(self) -> Decimal:
		return self.lucro_bruto - self.despesas_operacionais

	@property
	def margem_bruta(self) -> Decimal:
		"""Lucro bruto sobre a receita **líquida**."""
		return self._sobre_liquida(self.lucro_bruto)

	@property
	def margem_operacional(self) -> Decimal:
		return self._sobre_liquida(self.resultado_operacional)

	@property
	def margem_bruta_sobre_faturamento(self) -> Decimal:
		"""Lucro bruto sobre a receita **bruta** — a terceira definição de margem.

		Existe porque é a que `fiscal/precificacao.py` usa: lá a margem é fração do
		**preço**, que é receita bruta. As duas são corretas e **não são o mesmo
		número**: precificar com 20% sobre o preço produz 24,4% sobre a receita líquida
		quando o imposto é 18%, porque o denominador encolheu.

		Descoberta por um teste de costura entre os dois módulos, que "falhou" apontando
		para uma diferença conceitual real, não para um erro. Ter as duas nomeadas
		impede a comparação errada — que é como se conclui que a margem melhorou quando
		só mudou a régua.
		"""
		if self.receita_bruta == ZERO:
			return ZERO

		return self.lucro_bruto / self.receita_bruta

	@property
	def carga_sobre_faturamento(self) -> Decimal:
		"""Quanto do faturamento bruto virou dedução.

		Não é margem: é o tamanho do repasse. Útil porque é o número que o empresário
		costuma chamar de "imposto que pago", e vê-lo separado da margem evita a confusão
		entre os dois.
		"""
		if self.receita_bruta == ZERO:
			return ZERO

		return self.deducoes / self.receita_bruta

	def _sobre_liquida(self, valor: Decimal) -> Decimal:
		if self.receita_liquida == ZERO:
			return ZERO

		return valor / self.receita_liquida


def apurar_lucratividade(
	receita_bruta: Decimal,
	deducoes: Decimal = ZERO,
	custo: Decimal = ZERO,
	despesas_operacionais: Decimal = ZERO,
) -> ResultadoLucratividade:
	"""Apura o resultado na ordem do Art. 187.

	Prejuízo é resultado válido: lucro bruto e operacional podem ser negativos, e
	esconder isso seria o oposto do que uma apuração serve. O que **não** é válido é
	dedução maior que a receita bruta — receita líquida negativa não descreve nenhuma
	operação real, e sim erro de lançamento.
	"""
	for nome, valor in (
		("receita_bruta", receita_bruta),
		("deducoes", deducoes),
		("custo", custo),
		("despesas_operacionais", despesas_operacionais),
	):
		if not isinstance(valor, Decimal):
			raise LucratividadeInvalida(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

		if valor < ZERO:
			raise LucratividadeInvalida(f"{nome} não pode ser negativo, recebido {valor}")

	if deducoes > receita_bruta:
		raise LucratividadeInvalida(
			f"as deduções ({deducoes}) superam a receita bruta ({receita_bruta}): receita "
			"líquida negativa não descreve operação real, é erro de lançamento"
		)

	return ResultadoLucratividade(
		receita_bruta=receita_bruta,
		deducoes=deducoes,
		custo=custo,
		despesas_operacionais=despesas_operacionais,
	)
