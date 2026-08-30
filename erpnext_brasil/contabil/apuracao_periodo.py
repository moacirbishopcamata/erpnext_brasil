# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Apuração periódica de ICMS e IPI: débitos das saídas menos créditos das entradas.

Diferente da apuração por documento (`fiscal/impostos/apuracao.py`, que calcula o
tributo de uma única NF-e), isto é o **livro de apuração** — o fechamento periódico
(normalmente mensal) que soma tudo que entrou como débito (`ICMS a Recolher`/`IPI a
Recolher`, gerado por `lancamento.gerar_lancamentos_venda`) contra tudo que entrou como
crédito (`ICMS a Recuperar`/`IPI a Recuperar`, gerado por
`lancamento.gerar_lancamentos_compra`), e decide se o resultado é imposto a pagar ou
saldo credor a carregar para o período seguinte.

Fundamento constitucional da não cumulatividade
--------------------------------------------------
Não é convenção de projeto — é o texto da Constituição:

- **ICMS** — Art. 155, § 2º, I: "será não-cumulativo, compensando-se o que for devido
  em cada operação (...) com o montante cobrado nas anteriores (...)".
- **IPI** — Art. 153, § 3º, II: "será não-cumulativo, compensando-se o que for devido em
  cada operação com o montante cobrado nas anteriores".

Os dois dispositivos usam a mesma redação ("compensando-se o que for devido... com o
montante cobrado nas anteriores") — por isso os dois tributos compartilham a mesma
mecânica de apuração aqui (`ApuracaoPeriodo` é genérico para ambos), em vez de duas
classes quase-iguais.

Por que só ICMS e IPI, não PIS/COFINS
------------------------------------------
O roteiro deste bloco pede explicitamente "Apuração de ICMS e de IPI" — escopo
deliberado, não esquecimento de PIS/COFINS. PIS/COFINS não-cumulativo também compensa
crédito e débito, mas por um regime de apuração federal distinto (Lei 10.637/2002 e
10.833/2003, com DCTF/EFD-Contribuições próprias) que não foi conferido nesta
implementação — estender `TRIBUTOS_APURAVEIS` para incluir "PIS"/"COFINS" sem antes ler
essas leis seria repetir o erro que este projeto existe para evitar.

Saldo credor nunca é negativo por engano
--------------------------------------------
`saldo` pode ser negativo (crédito supera débito) ou positivo (débito supera crédito).
`a_recolher` e `saldo_credor_a_transportar` nunca são os dois diferentes de zero ao
mesmo tempo — são mutuamente exclusivos por construção (`max(saldo, 0)` e
`max(-saldo, 0)`), nunca um `if/else` que poderia divergir se editado por engano.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.contabil.lancamento import Lancamento

__all__ = ["TRIBUTOS_APURAVEIS", "ApuracaoInvalida", "ApuracaoPeriodo", "apurar_periodo"]

ZERO = Decimal("0.00")

# Só os tributos cuja não cumulatividade tem base constitucional idêntica (Art. 155 § 2º
# I e Art. 153 § 3º II) e cujo roteiro deste bloco pede explicitamente — ver docstring.
TRIBUTOS_APURAVEIS = frozenset({"ICMS", "IPI"})


class ApuracaoInvalida(ValueError):
	"""Tributo fora de `TRIBUTOS_APURAVEIS`, ou dado que não fecha."""


@dataclass(frozen=True)
class ApuracaoPeriodo:
	"""Fechamento de um período: débitos das saídas contra créditos das entradas.

	`saldo_credor_anterior` é o crédito que sobrou do período anterior (Art. 155/153: o
	crédito não usado num período não se perde, transporta para o seguinte) — soma-se
	ao crédito do período corrente antes de comparar com o débito.
	"""

	tributo: str
	debitos: Decimal
	creditos: Decimal
	saldo_credor_anterior: Decimal = ZERO

	def __post_init__(self) -> None:
		if self.tributo not in TRIBUTOS_APURAVEIS:
			raise ApuracaoInvalida(
				f"Tributo {self.tributo!r} não tem apuração periódica implementada — "
				f"só {sorted(TRIBUTOS_APURAVEIS)} (ver docstring do módulo)"
			)

		for nome, valor in (
			("debitos", self.debitos),
			("creditos", self.creditos),
			("saldo_credor_anterior", self.saldo_credor_anterior),
		):
			if valor < ZERO:
				raise ApuracaoInvalida(f"{nome} não pode ser negativo, recebido {valor}")

	@property
	def saldo(self) -> Decimal:
		"""Positivo: imposto a recolher. Negativo: saldo credor a transportar."""
		return self.debitos - self.creditos - self.saldo_credor_anterior

	@property
	def a_recolher(self) -> Decimal:
		return max(self.saldo, ZERO)

	@property
	def saldo_credor_a_transportar(self) -> Decimal:
		return max(-self.saldo, ZERO)


def apurar_periodo(
	tributo: str, lancamentos: list[Lancamento], saldo_credor_anterior: Decimal = ZERO
) -> ApuracaoPeriodo:
	"""Soma `<tributo> a Recolher` (débitos) e `<tributo> a Recuperar` (créditos) numa
	lista de `Lancamento` já gerada por `lancamento.gerar_lancamentos_venda`/
	`gerar_lancamentos_compra` — normalmente o período inteiro (um mês), não um único
	documento.

	Lê pela conta de crédito/débito, não por metadado do `Lancamento` — a mesma conta
	nomeada em `plano_de_contas.py` é o único vocabulário compartilhado entre a geração
	do lançamento e a apuração do período, evitando um segundo jeito de identificar
	"isto é um lançamento de ICMS" que pudesse divergir do primeiro.
	"""
	debitos = sum((l.valor for l in lancamentos if l.conta_credito == f"{tributo} a Recolher"), ZERO)
	creditos = sum((l.valor for l in lancamentos if l.conta_debito == f"{tributo} a Recuperar"), ZERO)

	return ApuracaoPeriodo(
		tributo=tributo, debitos=debitos, creditos=creditos, saldo_credor_anterior=saldo_credor_anterior
	)
