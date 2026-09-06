# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Liga `contabil/perdas.py` às telas de estoque do ERPNext.

O gap que este módulo paga
---------------------------------
`contabil/perdas.py` existia com o cálculo completo, testado, e **nenhum módulo de
integração o importava** — só uma docstring do Bloco K o citava. É o mesmo formato de gap
que a depreciação teve antes de `depreciacao_ativo.py`: código correto e inalcançável do
Desk, que é pior que um bug, porque um bug aparece.

Descoberto na varredura da frente de Estoque, e não estava em `docs/gaps.md`.

As duas telas, e por que a leitura do valor difere
-------------------------------------------------------------
| DocType | Campo do valor | O que significa |
|---|---|---|
| `Stock Entry` | `total_outgoing_value` | o que saiu do estoque na baixa |
| `Stock Reconciliation` | `difference_amount` | a diferença apurada — **com sinal** |

⚠️ **Sinal não é classificação.** No `Stock Reconciliation`, diferença negativa é falta
(perda); positiva é **sobra**, que não estorna crédito nenhum — a mercadoria não deixou de
existir, ela apareceu. Tratar as duas pelo módulo de perdas produziria um estorno em cima
de um ganho: passivo fiscal criado do nada. Por isso a sobra é recusada alto, e não
ignorada em silêncio.

O que se recusa, e por quê
---------------------------------
1. **Tipo de perda num `Stock Entry` que não é `Material Issue`.** Uma transferência ou uma
   requisição para produção não é perda; classificá-la como tal estornaria crédito de
   mercadoria que continua na empresa.
2. **Tipo de perda numa sobra de inventário.** Ver acima.

Nenhuma das duas levanta erro no ERPNext sozinho: são preenchimentos válidos de campos
válidos. É exatamente por isso que a guarda existe.

O que **não** se faz aqui, declarado
-------------------------------------------
- **Lançar o estorno no livro fiscal.** O valor apurado fica no documento; o registro no
  `E111` da EFD é do Bloco E, e está na lista de `docs/sped-fiscal.md`. Escrever o
  lançamento daqui puliria a apuração do período.
- **Derivar o crédito tomado.** Ver a docstring de `setup/campos_estoque.py`: o crédito é
  o daquela entrada, não a alíquota de hoje, e inventá-lo seria lançamento sem origem.

Estado de verificação
----------------------------
Conferido em site **v16 real** (`v16.localhost`, frappe 16.31.0 / erpnext 16.33.0): os sete
campos de dado têm coluna, os dois breaks corretamente não têm, as opções do `Select`
gravadas batem com `TIPOS_DE_PERDA`, e o hook aparece no `doc_events` do Frappe **ao lado**
dos hooks do próprio ERPNext em `Stock Entry` — o framework funde por app, não sobrescreve.

⚠️ O que **não** foi exercitado é a execução: nenhum `Stock Entry` foi gravado no site para
ver `validate` rodar. As recusas (sobra, finalidade incompatível) estão provadas por forma,
não por comportamento.
"""

from decimal import Decimal

import frappe
from frappe import _

from erpnext_brasil.contabil.perdas import TipoDePerda, apurar_perda

__all__ = [
	"CAMPOS_DE_CREDITO",
	"CAMPO_TIPO",
	"PROPOSITO_DE_BAIXA",
	"apurar_perda_do_documento",
	"creditos_informados",
	"valor_da_perda",
]

CAMPO_TIPO = "br_tipo_de_perda"
"""O campo que decide se este documento é uma perda. Vazio: não é."""

PROPOSITO_DE_BAIXA = "Material Issue"
"""O único `Stock Entry.purpose` em que uma perda cabe.

Lido do `stock_entry.json` do erpnext v16, não suposto: `purpose` é um `Select` cujas
opções incluem `Material Receipt`, `Material Transfer`, `Manufacture` e `Repack` — e em
nenhuma delas a mercadoria deixa de existir.
"""

CAMPOS_DE_CREDITO = {
	"ICMS": "br_credito_icms_tomado",
	"PIS": "br_credito_pis_tomado",
	"COFINS": "br_credito_cofins_tomado",
}
"""`{nome do tributo: campo}`. Os nomes são os de `custo_aquisicao.creditos_por_tributo` —
estorna-se exatamente o que se creditou, e o vocabulário acompanha.
"""

ZERO = Decimal("0.00")


def _decimal(valor) -> Decimal:
	"""Converte um número do Frappe (float) para `Decimal` **pela string**.

	`Decimal(0.1)` carrega o ruído binário do float; `Decimal("0.1")` não. Em dinheiro a
	diferença chega ao centavo depois de somar.
	"""
	return Decimal(str(valor or 0))


def valor_da_perda(doc) -> Decimal:
	"""O valor baixado, lido do campo que cada DocType usa.

	Levanta quando a reconciliação acusa **sobra** — ver a nota de sinal na docstring do
	módulo.
	"""
	if doc.doctype == "Stock Reconciliation":
		diferenca = _decimal(doc.get("difference_amount"))

		if diferenca >= ZERO:
			frappe.throw(
				_(
					"A diferença apurada é de {0}, ou seja, sobra de inventário — e sobra não é "
					"perda: não há crédito a estornar sobre mercadoria que apareceu. Deixe o "
					"tipo de perda em branco."
				).format(diferenca),
				title=_("Sobra de inventário classificada como perda"),
			)

		# Falta vem negativa; o módulo de perdas trabalha com valor positivo.
		return -diferenca

	return _decimal(doc.get("total_outgoing_value"))


def creditos_informados(doc) -> dict[str, Decimal]:
	"""`{tributo: valor}` a partir dos três campos, omitindo os vazios.

	Campo vazio é **ausência de crédito**, não erro: é o caso real do Simples Nacional.
	"""
	creditos = {}

	for tributo, campo in CAMPOS_DE_CREDITO.items():
		valor = _decimal(doc.get(campo))

		if valor > ZERO:
			creditos[tributo] = valor

	return creditos


def _limpar(doc) -> None:
	"""Zera o resultado quando o documento não é (ou deixou de ser) uma perda.

	Sem isto, apagar o tipo deixaria para trás um "crédito a estornar" de uma classificação
	que não existe mais — número órfão na tela, que ninguém sabe de onde veio.
	"""
	doc.br_perda_estorna_credito = 0
	doc.br_credito_estornado = 0
	doc.br_custo_total_da_perda = 0


def apurar_perda_do_documento(doc, method=None) -> None:
	"""Hook de `validate` do `Stock Entry` e do `Stock Reconciliation`."""
	nome_do_tipo = (doc.get(CAMPO_TIPO) or "").strip()

	if not nome_do_tipo:
		_limpar(doc)
		return

	if doc.doctype == "Stock Entry" and doc.get("purpose") != PROPOSITO_DE_BAIXA:
		frappe.throw(
			_(
				"Tipo de perda preenchido num lançamento cuja finalidade é {0}. Perda só cabe "
				"em {1}: nas demais finalidades a mercadoria continua na empresa, e estornar o "
				"crédito dela criaria passivo fiscal sem fato gerador."
			).format(doc.get("purpose"), PROPOSITO_DE_BAIXA),
			title=_("Finalidade incompatível com perda"),
		)

	valor = valor_da_perda(doc)

	if valor <= ZERO:
		frappe.throw(
			_(
				"Perda classificada como {0}, mas o valor baixado é {1}. Baixa de valor zero "
				"não é perda — é lançamento sem efeito."
			).format(nome_do_tipo, valor),
			title=_("Perda sem valor"),
		)

	resultado = apurar_perda(valor, TipoDePerda(nome_do_tipo), creditos_informados(doc))

	doc.br_perda_estorna_credito = 1 if resultado.estorna else 0
	doc.br_credito_estornado = resultado.creditos_estornados
	doc.br_custo_total_da_perda = resultado.custo_total_da_perda
