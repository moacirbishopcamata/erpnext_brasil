# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Método de valoração de estoque: o que o Brasil admite, e o aviso para o que o ERPNext oferece a mais.

O ERPNext v16 permite três métodos de valoração — `FIFO`, `Moving Average` e `LIFO` — no `Item` e como padrão no
`Stock Settings`. O custo que sai da valoração é o custo da mercadoria vendida e, portanto, o que o fisco vê. O
ERPNext não sabe que, para o imposto de renda brasileiro, só dois desses três interessam.

⚠️ O que está comprovado, e o que não está
-------------------------------------------
Fontes **secundárias** (guias de contabilidade e de ERP) afirmam que o UEPS (LIFO) **não é aceito** para apurar o
imposto de renda; PEPS (FIFO) e custo médio são. A regra geral de custo está no art. 14 do Decreto-Lei 1.598/77,
confirmado em material de fornecedor de ERP. **O artigo do RIR/2018 (Decreto 9.580/2018) que veda o UEPS não foi
localizado** nas buscas desta verificação.

Por isso a regra devolve um **aviso**, e não um bloqueio, e o próprio texto declara a pendência. Promover a
bloqueio exige citar o dispositivo lido no texto oficial — a mesma disciplina de `integracao/alerta_fiscal.py`, que
recusa cravar data legal sem fonte.

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = ["METODOS_ADMITIDOS", "METODO_NAO_ADMITIDO", "aviso_de_valoracao"]

METODO_NAO_ADMITIDO = "LIFO"
"""`LIFO` (UEPS — último que entra, primeiro que sai), o valor que o ERPNext oferece e o fisco não aceita."""

METODOS_ADMITIDOS = ("FIFO", "Moving Average")
"""PEPS e custo médio, na grafia das opções do ERPNext."""


def aviso_de_valoracao(metodo: str | None) -> str | None:
	"""O texto do aviso para o método, ou `None` quando não há o que avisar (método admitido ou não definido)."""
	if metodo != METODO_NAO_ADMITIDO:
		return None

	return (
		"O método de valoração LIFO (UEPS) não é admitido para o imposto de renda, segundo as fontes consultadas: "
		"o custo apurado no ERPNext pode não ser o dedutível. Os métodos aceitos são PEPS (FIFO) e custo médio "
		"(Moving Average). Confirmação do dispositivo legal (RIR/2018) pendente — este é um aviso, não um bloqueio."
	)
