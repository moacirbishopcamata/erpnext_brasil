# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O que este app **lê** do ERPNext sem acrescentar campo nem ligar hook.

A superfície que nenhum inventário mostrava
----------------------------------------------------
O contato deste app com o ERPNext tinha três formas visíveis e uma invisível:

| Forma | Onde estava declarada |
|---|---|
| campo acrescentado | `setup/campos*.py` — 24 DocTypes |
| comportamento ligado | `hooks.py` — 17 DocTypes |
| DocType próprio | `registros_fiscais/doctype/` — 6 |
| **leitura** | **em lugar nenhum** — 13 DocTypes |

⚠️ **A invisível é a mais frágil**, e por um motivo simples: campo e hook são coisas que
*nós* criamos, e mudam quando nós mudamos. Leitura é dependência de estrutura **alheia**,
que muda quando o ERPNext muda — e aí nada aqui acusa.

O caso concreto que mostrou o problema: `contabil/efd_bloco_k.py` monta o Bloco K da EFD a
partir de `Work Order`, do módulo `manufacturing`. Esse módulo não recebe **um único campo
nosso e nenhum hook** — ele existe no app só por esta leitura. Se o ERPNext renomear
`actual_start_date`, a EFD sai errada, o SPED é entregue errado, e a suíte pura continua
verde: ela não conhece o ERPNext.

Para que serve esta declaração
--------------------------------------
1. Torna a dependência **visível** — é a lista de tudo que uma atualização do ERPNext pode
   quebrar sem aviso.
2. Dá ao teste de bench o que conferir: cada DocType existe, cada campo é coluna.
   `tests_bench/test_leituras_do_erpnext.py` roda essa conferência num site real.
3. Trava a entrada de leitura nova sem declaração — `tests/test_leituras_do_erpnext.py`
   reprova qualquer DocType citado no app que não esteja em uma das quatro formas.

⚠️ **A contagem começou errada, e o teste é que corrigiu.** Uma varredura escrita à mão
achou onze; o teste achou **treze** — `Dynamic Link` e `Has Role` escaparam porque a
varredura procurava numa lista de nomes que ela mesma tinha montado. É a diferença entre
procurar o que se espera e conferir o que existe, e vale a pena estar escrito aqui.

Declaração, e não inferência
-----------------------------------
A lista é escrita à mão, como `MAPAS` em `setup/campos.py`. Derivá-la varrendo o código
pareceria mais esperto e seria pior: a varredura concordaria com o código por construção, e
uma leitura errada passaria nos dois lados. Aqui a lista é a **afirmação** de quem escreveu
o código, e o teste confere se o código a respeita.

Sem dependência do Frappe: é dado.
"""

__all__ = ["LEITURAS", "NOMES_USADOS_COMO_CHAVE", "todos_os_doctypes_lidos"]

LEITURAS: dict[str, tuple[str, ...]] = {
	# ------------------------------------------------------------------ assets
	"Asset Shift Factor": ("shift_factor",),
	# `instalar_turnos` cria os três turnos do art. 323 do RIR e grava o coeficiente
	# aqui. Se o campo mudar de nome, os fatores 1,0/1,5/2,0 param de ser aplicados e a
	# depreciação sai menor — sem erro.
	# --------------------------------------------------------------- accounts
	"Finance Book": (),
	# Só existência: o livro `Fiscal (Brasil)` é criado e referenciado pelo nome. Não se lê
	# campo nenhum dele.
	# -------------------------------------------------------------------- edi
	"Code List": ("version",),
	"Common Code": ("additional_data", "common_code", "name", "title"),
	# As tabelas de código fiscal (CFOP, NCM, CST) são importadas para os DocTypes de EDI
	# **do próprio Frappe/ERPNext**, em vez de um DocType nosso — decisão de não duplicar
	# estrutura que já existe. O preço é esta dependência.
	# ------------------------------------------------------- manufacturing
	"Work Order": ("actual_end_date", "actual_start_date"),
	# ⚠️ O módulo `manufacturing` existe no app **só por esta leitura**. É a dependência
	# mais silenciosa do projeto: alimenta o Bloco K da EFD, que é entregue ao Fisco.
	# ------------------------------------------------------------------ stock
	"Batch": ("batch_id", "expiry_date", "manufacturing_date"),
	# Vira o grupo `rastro` da NF-e (`nLote`, `dVal`, `dFab`). Campo renomeado = nota
	# emitida sem rastreabilidade, que é rejeição na origem para quem é obrigado a ela.
	"Bin": ("actual_qty", "company", "item_code", "stock_uom", "warehouse"),
	# Saldo por item e armazém, já materializado. É a fonte do Navegador de Estoque.
	"Item Barcode": ("barcode", "parent", "uom"),
	# ⚠️ `parent` é lido com alias (`parent as item_code`) — o campo real é `parent`, e é
	# ele que precisa existir. Declarar o alias esconderia a dependência verdadeira.
	"Stock Ledger Entry": (
		"creation",
		"item_code",
		"name",
		"posting_date",
		"posting_time",
		"qty_after_transaction",
		"stock_value",
		"warehouse",
	),
	# Bloco H da EFD — o inventário declarado ao Fisco. Mesma gravidade do `Work Order`.
	"Warehouse": ("is_group", "lft", "name", "rgt", "warehouse_name", "warehouse_type"),
	# `lft`/`rgt` são o *nested set*: se o ERPNext trocar a implementação da árvore, o
	# total por endereço do Navegador para de somar os descendentes.
	# ----------------------------------------------------------------- frappe
	"Dynamic Link": ("parent",),
	# A ligação entre `Address` e a parte (Company/Customer/Supplier). É por ela que se
	# descobre a UF de quem emite e de quem recebe — e a UF decide CFOP, alíquota
	# interestadual e validação de Inscrição Estadual.
	"Has Role": ("parent",),
	# Quem recebe o alerta de vencimento do certificado A1. Sem esta leitura o alerta é
	# calculado e não vai a ninguém: o pior desfecho, porque parece funcionar.
}
"""`{DocType: campos que lemos}`. Tupla vazia = só a existência importa.

⚠️ Inclui dois DocTypes do **Frappe** (`Dynamic Link`, `Has Role`), e não só do ERPNext. O
nome do módulo é histórico — a fragilidade é a mesma, e separá-los em duas listas faria
alguém conferir uma e esquecer a outra. O núcleo do Frappe muda menos, o que reduz a
probabilidade, não a consequência.
"""

NOMES_USADOS_COMO_CHAVE: frozenset[str] = frozenset()
"""DocTypes citados só como **chave de decisão**, sem leitura de campo.

Vazio hoje. `POS Invoice` morava aqui: o nome dele era comparado em
`validacao_fiscal.INDICADOR_POR_DOCUMENTO` e nada era lido dele. Saiu quando o cupom passou
a receber campos fiscais e a ser ligado no `hooks.py` — deixou de ser estrutura **alheia**
para virar estrutura que nós declaramos, e a conferência dele passou a ser a de campo.

⚠️ Foi o teste que exigiu esta remoção, não a leitura do código: um DocType não pode estar
nos dois lugares, porque a pergunta que cada lado faz é diferente. Manter a estrutura vazia
preserva a distinção — a fragilidade aqui é outra. Um campo renomeado quebra uma leitura de
forma detectável; um **DocType** renomeado faz a chave simplesmente não casar, e o mapa cai
no padrão, em silêncio.
"""


def todos_os_doctypes_lidos() -> frozenset[str]:
	"""Tudo o que este app depende do ERPNext sem declarar campo nem hook."""
	return frozenset(LEITURAS) | NOMES_USADOS_COMO_CHAVE
