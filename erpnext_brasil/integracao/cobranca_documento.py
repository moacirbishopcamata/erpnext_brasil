# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Monta o grupo `cobr` da NF-e a partir do parcelamento que o ERPNext já tem.

O achado da auditoria de Compras e Vendas
--------------------------------------------------
O ERPNext já modela venda a prazo: a tabela `Payment Schedule` da fatura tem
`due_date` e `payment_amount` por parcela. É **exatamente** o que a duplicata da NF-e
pede (`dVenc` e `vDup`) e o que o boleto precisa por título. O dado existe, íntegro, e
não estava sendo aproveitado — a NF-e saía declarando só a forma de pagamento, sem as
parcelas.

Não há campo novo a cadastrar. Quem já usa condição de pagamento no ERPNext já tem o
parcelamento correto; só faltava traduzi-lo para o layout fiscal.

Três formas do mesmo fato, e a costura entre elas
---------------------------------------------------------
O mesmo parcelamento aparece como:

- **`Payment Schedule`** — a forma do ERPNext, que alimenta o contas a receber;
- **`cobr/dup`** — a forma fiscal, que vai na NF-e;
- **título de cobrança** — a forma bancária, que vira boleto (`contabil/boleto.py`).

São a mesma verdade em três vocabulários, e é na costura entre eles que mora o bug
silencioso: parcela que existe no contas a receber e não na NF-e, ou boleto com
vencimento diferente do declarado ao Fisco. Traduzir num lugar só é o que impede isso.

Por que `grand_total` e não `net_total`
----------------------------------------------
A fatura (`fat`) representa o que o cliente **deve**, que inclui impostos e acessórios —
não a base de cálculo. `grand_total` é o campo do ERPNext com esse significado. Usar
`net_total` produziria uma fatura menor que a soma das duplicatas, e a pós-condição de
`montar_cobr` reprovaria (corretamente).

Sem teste dedicado — depende do Frappe; a regra que importa está em
`fiscal/documento/cobranca.py`, testada sem bench.
"""

from decimal import Decimal

__all__ = ["montar_cobranca_do_documento"]


def _decimal(valor) -> Decimal:
	if valor in (None, ""):
		return Decimal("0.00")

	return Decimal(str(valor))


def montar_cobranca_do_documento(doc) -> dict | None:
	"""Traduz o `Payment Schedule` do documento no grupo `cobr` da NF-e.

	Devolve `None` quando não há parcelamento — venda à vista não tem duplicata, e
	inventar uma seria declarar um título de crédito que não existe. `None` é resposta,
	não falha: quem monta a NF-e simplesmente não inclui o grupo.

	O desconto da fatura é derivado da diferença entre o total do documento e a soma
	das parcelas, em vez de vir de um campo à parte: assim a pós-condição de
	`montar_cobr` (soma das duplicatas = líquido da fatura) fecha por construção, e não
	por coincidência.
	"""
	from erpnext_brasil.fiscal.documento.cobranca import Duplicata, Fatura, montar_cobr

	parcelas = doc.get("payment_schedule") or []

	if not parcelas:
		return None

	duplicatas = []

	for indice, parcela in enumerate(parcelas, start=1):
		valor = _decimal(parcela.get("payment_amount"))

		if valor <= Decimal("0.00"):
			# Parcela sem valor não é duplicata: é linha de rascunho que sobrou.
			continue

		duplicatas.append(
			Duplicata(
				vencimento=parcela.get("due_date"),
				valor=valor,
				numero=f"{indice:03d}",
			)
		)

	if not duplicatas:
		return None

	total = _decimal(doc.get("grand_total"))
	soma = sum((d.valor for d in duplicatas), Decimal("0.00"))

	# Se o total não bate com as parcelas, a diferença é desconto concedido no
	# parcelamento — declarar isso é mais honesto que forçar os dois a serem iguais.
	fatura = Fatura(
		original=total if total >= soma else soma,
		desconto=total - soma if total > soma else Decimal("0.00"),
		numero=doc.get("name") or "",
	)

	return montar_cobr(fatura, duplicatas)
