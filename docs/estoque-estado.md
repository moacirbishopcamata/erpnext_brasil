# Estoque: o que o ERPNext anuncia, o que já está tropicalizado, e o que falta

Varredura da página oficial de estoque do ERPNext
(`frappe.io/erpnext/open-source-inventory-management-system`) contra o que este app tem,
no mesmo método de `tropicalizacao-por-area.md`: cada recurso anunciado é classificado em
**neutro** (funciona no Brasil sem alteração), **pronto** (já tropicalizado) ou **gap**.

O achado desta varredura não estava em nenhuma das três colunas: era um módulo **completo e
inalcançável**. Ver "O gap que a varredura encontrou", abaixo.

## Os oito recursos anunciados

| Recurso | Situação | Por quê |
|---|---|---|
| **Centralized Item Master** | ✅ pronto | `Item` já recebe `br_ncm`, `br_cest`, `br_origem_mercadoria` e a classificação fiscal; o `validate` recusa NCM inválido |
| **Flexible Warehouses** | ⚪ neutro | a árvore de `Warehouse` é layout físico, sem consequência fiscal própria. ⚠️ A ressalva está abaixo, em "Transferência entre estabelecimentos" |
| **Stock Replenishment** | ⚪ neutro | ponto de reposição e `Material Request` automática não têm regra brasileira |
| **Stock Reservation** | ⚪ neutro | reserva é controle interno; não gera documento fiscal |
| **Stock Reconciliation** | ✅ pronto **neste incremento** | a falta apurada no inventário é perda e estorna crédito — ver abaixo |
| **Putaway and Pick List** | ⚪ neutro | organização de armazém |
| **Serialised and Batched Inventory** | ✅ pronto | `integracao/rastreabilidade.py` traduz lote e validade para o grupo `rastro` da NF-e |
| **Stock Reports** | ⚪ neutro | *aging*, *balance* e *ledger* são gerenciais. O relatório **fiscal** de estoque é outro: é o Bloco H da EFD, e já existe |

O que já existia e a página não anuncia, porque é exigência brasileira e não recurso do
produto:

- **Bloco H da EFD Fiscal** — o inventário declarado ao Fisco (`contabil/efd_bloco_h.py`),
  inclusive item em poder de terceiro: `IND_PROP` 1 ou 2 exige `COD_PART`, e o módulo
  recusa a omissão.
- **Bloco K** — controle da produção e do estoque (`contabil/efd_bloco_k.py`).

## O gap que a varredura encontrou

`contabil/perdas.py` existia desde antes, com o cálculo completo e testado do estorno de
crédito — e **nenhum módulo de integração o importava**. A única citação em todo o app era
uma docstring do Bloco K.

É o gap de costura na sua forma mais cara: **código correto e inalcançável**. Um bug
aparece; isto não aparece. E não estava em `docs/gaps.md`, o que quer dizer que a varredura
por área encontra o que o inventário de gaps não encontra — os dois métodos não se
substituem.

### O que a perda significa no Brasil, e por que o ERPNext não resolve sozinho

Quem compra mercadoria credita ICMS (e PIS/COFINS no não cumulativo) porque vai tributar a
saída. Quando a mercadoria **não sai** — quebrou, venceu, foi furtada —, o pressuposto do
crédito deixa de existir e o crédito tem de ser **estornado** (LC 87/1996, art. 21).

Consequência prática: **uma perda de R$ 1.000 não custa R$ 1.000.** Custa o estoque mais o
crédito devolvido. Sistema que só dá a baixa contábil subestima a perda e deixa passivo
fiscal para trás.

A exceção que muda tudo é a **quebra normal do processo** — evaporação, aparagem, resíduo
previsível. Ela integra o custo de produção e **não** estorna: a mercadoria não deixou de
ser usada na atividade tributada, foi consumida por ela. A distinção não é de tamanho, é de
natureza.

O `Stock Entry` sabe **quanto** saiu e **para onde** foi o custo. O que ele não tem, e não
teria por que ter, é o **motivo** — e é o motivo que decide o estorno. Sem ele, uma quebra
de processo e um furto produzem lançamentos idênticos.

### As duas telas, e a diferença que quase passou

| DocType | Campo do valor | O que significa |
|---|---|---|
| `Stock Entry` | `total_outgoing_value` | o que saiu na baixa |
| `Stock Reconciliation` | `difference_amount` | a diferença apurada, **com sinal** |

⚠️ **Sinal não é classificação fiscal.** Na reconciliação, diferença negativa é falta
(perda); positiva é **sobra**, e sobra não estorna nada — a mercadoria não deixou de
existir, ela apareceu. Passar as duas pelo módulo de perdas calcularia estorno em cima de um
ganho: passivo fiscal criado do nada, sem que o ERPNext levantasse um único erro.

Por isso a sobra é **recusada alto**, e é o teste-âncora da suíte.

### As duas recusas, e por que precisam existir

Nenhuma das duas levanta erro no ERPNext sozinha — são preenchimentos válidos de campos
válidos, que é exatamente o motivo da guarda:

1. **Tipo de perda num `Stock Entry` que não é `Material Issue`.** Uma transferência ou uma
   requisição para produção não é perda; classificá-la como tal estornaria o crédito de
   mercadoria que continua na empresa.
2. **Tipo de perda numa sobra de inventário.** Ver acima.

### Por que os créditos são informados, e não calculados

Seria cômodo derivar o crédito da alíquota do item, e estaria **errado**. O crédito a
estornar é o que foi tomado **naquela entrada** — com a alíquota daquele fornecedor, daquele
estado, daquela data —, não a alíquota que o item tem hoje. Ligar a saída à entrada exige
lote ou série, e nem todo estoque tem.

Inventar o número seria pior que pedir: um estorno calculado por analogia vira lançamento
fiscal com valor sem origem. São três campos que o usuário preenche, e a apuração usa
exatamente o que ele informou.

**Campo vazio significa "não houve crédito"**, e não erro — é o caso real do Simples
Nacional, que não credita.

## Validação em bench v16

Conferido em `v16.localhost` (frappe 16.31.0, erpnext 16.33.0) depois do `migrate`:

```
Stock Entry / Stock Reconciliation
    br_secao_perda_br        coluna: False   CustomField: True   (break, correto)
    br_tipo_de_perda         coluna: True    CustomField: True
    br_credito_icms_tomado   coluna: True    CustomField: True
    ... 7 campos de dado com coluna, 2 breaks sem

opções do Select, uma por linha (primeira vazia):
    Quebra normal do processo / Vencimento / Deterioração /
    Furto ou roubo / Sinistro / Ajuste de inventário

doc_events['Stock Entry'] = {
  'on_submit': ['erpnext...update_completed_and_requested_qty'],
  'validate':  ['erpnext_brasil.integracao.perda_estoque.apurar_perda_do_documento'],
}
```

A última linha é a que valia confirmar: nosso `doc_events["Stock Entry"] = {...}` **não
apagou** os hooks que o próprio ERPNext registra no mesmo DocType. O Frappe funde os
`doc_events` de todos os apps; cada app declara o seu dicionário inteiro sem pisar no do
vizinho. Se sobrescrevesse, teríamos quebrado o `Material Request` do ERPNext sem que
nenhum teste nosso percebesse.

⚠️ **O que ainda não foi exercitado é a execução.** Nenhum `Stock Entry` foi gravado para
ver o `validate` rodar: as duas recusas estão provadas por forma, não por comportamento.

## Gaps que ficam declarados

### 1. Transferência entre estabelecimentos não emite NF-e

Este é o furo mais relevante que sobra na frente de estoque.

Mover mercadoria entre dois estabelecimentos **da mesma empresa** mas com **CNPJ
diferentes** é fato gerador de NF-e (CFOP 5152/6152, transferência de mercadoria). No
ERPNext isso é um `Stock Entry` com `purpose = "Material Transfer"` — e a emissão de NF-e
deste app está ligada a `Sales Invoice`, `Delivery Note`, `Purchase Invoice` e
`Purchase Receipt`. **`Stock Entry` não está na lista.**

Consequência: a transferência acontece no estoque e **nenhum documento fiscal nasce**.

Não se resolveu aqui porque a decisão anterior é de modelagem, não de código: um
estabelecimento com CNPJ próprio é uma `Company` separada no ERPNext ou um `Warehouse` com
CNPJ? A resposta muda o que é "transferência" e o que é "venda entre empresas", e escolher
sem o desenho seria construir sobre suposição.

### 2. O estorno apurado não vira lançamento na EFD

O valor fica no documento; o registro do estorno é um ajuste de apuração no `E111` do Bloco
E. Está na lista de pendências de `sped-fiscal.md`. Escrever o lançamento a partir da baixa
puliria a apuração do período.

### 3. Percentual de quebra tolerada por UF

Alguns regulamentos estaduais fixam limites de perda técnica aceita sem estorno. Não estão
implementados: variam por estado e por produto, e inventar um número seria criar regra
fiscal sem fonte. A classificação entre quebra normal e perda que estorna continua sendo do
usuário — o app calcula a consequência dela.

## Fonte

- Lei Complementar 87/1996, art. 21 — estorno do crédito quando a mercadoria "vier a
  perecer, deteriorar-se ou extraviar-se".
- `stock_entry.json` e `stock_reconciliation.json` do erpnext **v16** — nomes de campo e
  opções de `purpose` lidos no JSON, não supostos.
- `frappe.io/erpnext/open-source-inventory-management-system` — a lista dos oito recursos.
