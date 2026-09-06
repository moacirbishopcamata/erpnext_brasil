# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Campos que a baixa de estoque precisa para dizer se houve perda — e qual.

Por que o ERPNext não resolve isto sozinho
--------------------------------------------------
O `Stock Entry` com `purpose = "Material Issue"` sabe **quanto** saiu (`total_outgoing_value`)
e **para onde** foi o custo (`expense_account`). O que ele não tem, e não teria por que ter,
é o **motivo** — e no Brasil o motivo decide se há estorno de crédito de ICMS/PIS/COFINS
(LC 87/1996, art. 21). Sem o motivo declarado, uma quebra de processo e um furto produzem
lançamentos idênticos, e só um dos dois estorna.

O mesmo vale para o `Stock Reconciliation`: uma falta apurada no inventário é perda; uma
sobra não é. O ERPNext registra as duas no mesmo `difference_amount`, com o sinal
distinguindo — e sinal não é classificação fiscal.

Por que os créditos tomados são informados, e não calculados
---------------------------------------------------------------------
Seria cômodo derivar o crédito da alíquota do item, e estaria **errado**. O crédito a
estornar é o que foi tomado **naquela entrada**, com a alíquota daquele fornecedor, daquele
estado, daquela data — não a alíquota que o item tem hoje. Ligar a saída à entrada exige
lote ou série, e nem todo estoque tem.

Inventar o número seria pior que pedir: um estorno calculado por analogia vira lançamento
fiscal com valor sem origem. Por isso são três campos que o usuário preenche, e a apuração
usa exatamente o que ele informou. Campo vazio significa "não houve crédito" — que é o caso
real do Simples Nacional, e não pode ser tratado como erro.

⚠️ Nenhum campo repete o que o ERPNext já guarda
-------------------------------------------------------
Não há `br_valor_da_perda`: o valor é `total_outgoing_value` (ou `difference_amount`), e um
segundo campo criaria duas verdades sobre a mesma baixa — o erro que já se evitou no
`Bank Account` e no `Asset`.

Sem dependência do Frappe: é dado, e a suíte de costura o lê sem bench.
"""

from erpnext_brasil.contabil.perdas import TIPOS_DE_PERDA

__all__ = ["DOCTYPES_COM_PERDA", "OPCOES_DE_PERDA", "get_custom_fields"]

DOCTYPES_COM_PERDA = ("Stock Entry", "Stock Reconciliation")
"""As duas telas onde uma perda de estoque acontece no ERPNext.

`Stock Entry` é a baixa deliberada (quebrou, venceu, sumiu); `Stock Reconciliation` é a
falta que o inventário revelou. São documentos diferentes com a mesma consequência fiscal,
e por isso recebem o mesmo conjunto de campos — mas a leitura do valor difere, e isso fica
em `integracao/perda_estoque.py`, não aqui.
"""

OPCOES_DE_PERDA = "\n".join(("", *TIPOS_DE_PERDA))
"""Opções do `Select`, derivadas de `TIPOS_DE_PERDA`.

⚠️ Derivadas, nunca digitadas: uma segunda lista aqui divergiria da do domínio no dia em
que um tipo fosse acrescentado, e o sintoma seria um valor válido que o formulário recusa.

A primeira opção é **vazia** de propósito. Uma `Material Issue` costuma ser consumo, não
perda; obrigar a escolher um motivo transformaria toda requisição de material numa
declaração de sinistro.
"""

_ANCORAS = {
	"Stock Entry": "value_difference",
	"Stock Reconciliation": "difference_amount",
}
"""Onde a seção entra em cada formulário — conferido nos JSON do erpnext v16.

Âncora inexistente não levanta erro: só põe a seção no lugar errado da tela. Tem teste.
"""


def _campos(ancora: str) -> list[dict]:
	"""O mesmo bloco para os dois DocTypes, mudando só o campo de ancoragem."""
	return [
		{
			"fieldname": "br_secao_perda_br",
			"label": "Perda de Estoque (Brasil)",
			"fieldtype": "Section Break",
			"insert_after": ancora,
			"collapsible": 1,
		},
		{
			"fieldname": "br_tipo_de_perda",
			"label": "Tipo de Perda",
			"fieldtype": "Select",
			"options": OPCOES_DE_PERDA,
			"insert_after": "br_secao_perda_br",
			"description": (
				"Em branco quando a baixa não é perda — consumo, requisição, transferência. "
				"Preenchido, decide o estorno: quebra normal do processo preserva o crédito "
				"(a mercadoria foi consumida pela atividade tributada); as demais estornam, "
				"por força da LC 87/1996, art. 21."
			),
		},
		{
			"fieldname": "br_credito_icms_tomado",
			"label": "Crédito de ICMS Tomado na Entrada",
			"fieldtype": "Currency",
			"insert_after": "br_tipo_de_perda",
			"depends_on": "br_tipo_de_perda",
			"description": (
				"O que foi creditado quando esta mercadoria entrou — não a alíquota de hoje. "
				"Vazio significa que não houve crédito, e é o caso do Simples Nacional."
			),
		},
		{
			"fieldname": "br_coluna_perda_br",
			"fieldtype": "Column Break",
			"insert_after": "br_credito_icms_tomado",
		},
		{
			"fieldname": "br_credito_pis_tomado",
			"label": "Crédito de PIS Tomado na Entrada",
			"fieldtype": "Currency",
			"insert_after": "br_coluna_perda_br",
			"depends_on": "br_tipo_de_perda",
		},
		{
			"fieldname": "br_credito_cofins_tomado",
			"label": "Crédito de COFINS Tomado na Entrada",
			"fieldtype": "Currency",
			"insert_after": "br_credito_pis_tomado",
			"depends_on": "br_tipo_de_perda",
		},
		{
			"fieldname": "br_perda_estorna_credito",
			"label": "Estorna Crédito",
			"fieldtype": "Check",
			"read_only": 1,
			"insert_after": "br_credito_cofins_tomado",
			"depends_on": "br_tipo_de_perda",
			"description": "Decidido pelo tipo, não pelo usuário.",
		},
		{
			"fieldname": "br_credito_estornado",
			"label": "Crédito a Estornar",
			"fieldtype": "Currency",
			"read_only": 1,
			"insert_after": "br_perda_estorna_credito",
			"depends_on": "br_tipo_de_perda",
		},
		{
			"fieldname": "br_custo_total_da_perda",
			"label": "Custo Total da Perda",
			"fieldtype": "Currency",
			"read_only": 1,
			"insert_after": "br_credito_estornado",
			"depends_on": "br_tipo_de_perda",
			"description": (
				"Estoque baixado **mais** o crédito devolvido. É o número que a perda de fato "
				"custou — quem olha só o valor do estoque a subestima."
			),
		},
	]


def get_custom_fields() -> dict[str, list[dict]]:
	"""`{DocType: [definições]}`, no formato de `create_custom_fields`."""
	return {doctype: _campos(_ANCORAS[doctype]) for doctype in DOCTYPES_COM_PERDA}
