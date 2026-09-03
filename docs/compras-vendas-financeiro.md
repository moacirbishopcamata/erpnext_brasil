# Auditoria: Compras, Vendas, contas a pagar/receber e livro caixa

Pedido do usuário, em três mensagens seguidas: "analise Compras e Vendas
(Pedidos/Boletos e etc...)", "contas a pagar e a receber", "livro caixa
(Entrada/Saída/Resultado)". São a mesma cadeia vista em pontos diferentes, e por isso o
levantamento é um só.

## O achado principal: faltava o elo entre venda parcelada, NF-e e boleto

O grupo `pag` da NF-e (formas de pagamento) estava modelado. O grupo **`cobr`** (fatura e
duplicatas) **não** — e é justamente onde três coisas se encontram:

1. a **venda parcelada** — no ERPNext, a tabela `Payment Schedule` da fatura;
2. o **documento fiscal**, que precisa declarar cada duplicata;
3. o **boleto**, emitido por parcela, com o mesmo vencimento e o mesmo valor.

Sem `cobr`, uma NF-e de venda a prazo saía declarando só *como* se paga, sem dizer
*quando e quanto* de cada parcela. E a duplicata não é detalhe de layout: é **título de
crédito** (Lei 5.474/68), a base do que vira contas a receber e do que se leva a protesto.

Implementado em `fiscal/documento/cobranca.py` (regra pura) e
`integracao/cobranca_documento.py` (a leitura do `Payment Schedule`).

### `pag` e `cobr` respondem perguntas diferentes

Fácil confundir, e o XSD os separa de propósito: `pag` diz **como** se paga; `cobr` diz
**quando e quanto**. Uma venda em 3x no boleto tem *um* `pag` e *três* `dup`.

### Divergência deliberada: exigimos mais que o XSD

Confirmado no `leiauteNFe_v4.00.xsd`: **todos** os campos de `fat` e `dup` são
`minOccurs="0"` — o schema aceita uma duplicata sem número, sem vencimento e sem valor.
Aceitar isso produziria documento tecnicamente válido e inútil: parcela sem valor não
cobra nada, sem vencimento não vence. O módulo exige os dois, e registra a divergência
como escolha, não como descuido. O limite de **120** duplicatas, esse sim, é do XSD.

### A pós-condição que o XSD não tem

Quando há fatura e duplicatas, a soma das parcelas **tem** de fechar com o líquido da
fatura. Parcelar R$ 1.000 em três de R$ 300 passa no schema e só aparece na conciliação
do contas a receber, muito depois. `montar_cobr` recusa.

## Contas a receber: o dado já existia, íntegro

O ERPNext modela venda a prazo em `Payment Schedule` (`due_date`, `payment_amount`), que é
o que alimenta o contas a receber. **Nenhum campo novo foi preciso** — quem já usa
condição de pagamento no ERPNext já tem o parcelamento correto; faltava traduzi-lo para o
layout fiscal.

A tradução mora num lugar só (`montar_cobranca_do_documento`), porque é aí que o bug
silencioso nasceria: parcela que existe no contas a receber e não na NF-e, ou boleto com
vencimento diferente do declarado ao Fisco. Três vocabulários, uma verdade.

Detalhe registrado: a fatura usa `grand_total`, não `net_total` — o que o cliente **deve**
inclui impostos e acessórios. Usar a base de cálculo produziria uma fatura menor que a
soma das parcelas, e a pós-condição reprovaria (corretamente).

## Contas a pagar: simétrico, e sem lacuna nova

O lado da compra usa a mesma mecânica do ERPNext (`Payment Schedule` na Purchase Invoice),
e o documento fiscal que interessa é o **do fornecedor** — recebido, não emitido. O que o
app precisa dali é a chave de acesso, que já tem campo (`br_chave_acesso`) com validação e
leitura por código de barras (`docs/leitor-codigo-e-alertas.md`).

Não há grupo `cobr` a montar numa compra: quem monta a NF-e é o fornecedor.

## Boleto: o que existe e o que falta

`contabil/boleto.py` calcula código de barras e linha digitável FEBRABAN, verificados
contra exemplo real. O que **não** existe é o `campo_livre` — os 25 caracteres cujo layout
**cada banco define do seu jeito** (agência, conta, carteira, nosso número, em ordens
diferentes). O módulo recebe o campo pronto.

Isso é limite declarado, não esquecimento: implementar o `campo_livre` exige o manual de
cada banco, e errá-lo produz um boleto que o banco recusa ou credita na conta errada.
Enquanto não houver um gerador por banco, os campos de cadastro bancário (carteira,
convênio, código do cedente) também não entram — campo de configuração sem código que o
leia é estrutura sem uso, o mesmo critério de `docs/efd-configuracoes.md`.

**Com `cobr` implementado, a ponte ficou meio caminho andada**: as parcelas que viram
duplicata são exatamente os títulos que virariam boleto.

## Pedidos de compra e venda: já cobertos

`Sales Order` e `Purchase Order` já recebem sugestão de CFOP (`hooks.py` →
`cfop_sugestao.sugerir_cfop_compra_venda`), com os quatro códigos a mais que cobrem os
dois papéis da operação (`docs/cfop-sugestao.md`). Pedido não é documento fiscal — não tem
chave, não é transmitido —, então não há mais o que tropicalizar ali além do CFOP que ele
sugere para quando virar nota.

## Livro caixa: por que não é um gap

O livro caixa (entradas, saídas, resultado) **não é obrigação acessória separada** para
quem escritura contabilidade — é uma **visão** do que os lançamentos contábeis já contêm.
O projeto já tem:

- `contabil/lancamento.py` — partidas dobradas de compra e venda, com as contas certas
  (Caixa/Bancos, Clientes, Fornecedores, Receita, Custo);
- `contabil/plano_de_contas.py` — as contas do Art. 178/187 da Lei 6.404/76;
- `contabil/apuracao_periodo.py` — o fechamento do período;
- **ECD** (`docs/ecd.md`) — a escrituração que substitui os livros em papel, incluindo o
  Diário e o Razão.

Onde o livro caixa **é** obrigação própria — Lucro Presumido dispensado de escrituração
contábil, e o Livro Caixa Digital do Produtor Rural (LCDPR) — trata-se de **layout de
arquivo específico**, não de um cálculo novo. O LCDPR é candidato real a incremento
futuro, com a mesma disciplina dos demais: levantar o layout em fonte antes de escrever
código.

Registrado como pendência com escopo definido, não como "falta livro caixa" — o dado
existe; o que faltaria é o formato de entrega para esses dois regimes específicos.

## Resumo

| Frente | Estado |
|---|---|
| Pedido de compra/venda | Coberto (CFOP sugerido) |
| Venda parcelada → NF-e | **Fechado nesta rodada** (`cobr`/`dup`) |
| Contas a receber | Dado do ERPNext aproveitado, sem campo novo |
| Contas a pagar | Simétrico, sem lacuna nova |
| Boleto | Cálculo pronto; `campo_livre` por banco é limite declarado |
| Livro caixa | Não é gap: os lançamentos existem. LCDPR fica como pendência de layout |
