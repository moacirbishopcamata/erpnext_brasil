# Precificação, rastreabilidade e gestão de custos

Três pedidos do usuário em sequência: "analise Precificação", "rastreabilidade fiscal,
existe? senão implementar", "gestão de custos (fixos, temporais, móveis, por demanda
e etc.)". Os dois primeiros viraram código; o terceiro está levantado aqui, com o que é
gap real e o que o ERPNext já resolve.

## Precificação: o erro mais caro do Brasil cabe numa linha

**Somar a alíquota ao custo em vez de dividir.**

Um produto que custa R$ 100 com ICMS de 18% **não** é vendido a R$ 118. A R$ 118, o ICMS
— calculado *por dentro*, sobre o próprio preço — é R$ 21,24, e sobram R$ 96,76:
prejuízo de R$ 3,24 numa venda que parecia estar no custo. O preço correto é
R$ 100 ÷ (1 − 0,18) = **R$ 121,95**, onde o imposto é R$ 21,95 e sobram exatamente
R$ 100.

`icms.base_por_dentro` já fazia esse *gross-up* para **um** imposto. Faltava o cálculo
completo: vários impostos por dentro somados, mais a margem desejada, mais os impostos
por fora. Implementado em `fiscal/precificacao.py`.

### Por dentro e por fora não entram na mesma conta

Distinção que `ibs_cbs.py` já registrava e que aqui vira aritmética:

| | Quais | Onde entram |
|---|---|---|
| **Por dentro** | ICMS, PIS, COFINS, ISS | no **denominador** — dividem |
| **Por fora** | IBS, CBS (reforma) | **depois** — multiplicam |

```
preço       = custo ÷ (1 − Σ alíquotas por dentro − margem)
preço final = preço × (1 + Σ alíquotas por fora)
```

Isso muda a **fórmula**, não só o valor do imposto. Um sistema que trate os dois igual
acerta hoje e erra em 2027 — ou o contrário. Há teste provando que tratar um como o
outro dá preço diferente.

### Margem e markup não são a mesma coisa

Segundo erro mais comum. **Margem** é percentual do **preço**; **markup** é sobre o
**custo**. Markup de 30% sobre custo 100 dá preço 130 — cuja margem é 23,08%, não 30%.
`markup_para_margem` converte, porque a entrada costuma vir no formato errado (de
planilha, de fornecedor, de hábito).

### A pré-condição que impede o número absurdo

Se impostos por dentro + margem somarem 100% ou mais, **não existe preço**: o denominador
zera ou fica negativo. Implementação ingênua devolveria número enorme ou negativo, e o
usuário o cadastraria. Aqui falha alto, dizendo o que não fecha.

### `margem_efetiva`: o caminho inverso, e o mais útil

Descobrir o que um preço **já praticado** entrega. É como se descobre que a tabela
herdada dá 4% onde se acreditava dar 20% — ou que é negativa. Margem negativa é
resultado legítimo desta conta, não erro a esconder: é o diagnóstico.

## Rastreabilidade fiscal: existia pela metade

A resposta à pergunta era **meia**. A regra pura existia
(`fiscal/documento/produto.montar_rastro` — lote, quantidade, fabricação, validade, com
o limite de 500 lotes por item), mas **nada a alimentava**.

Mesmo achado do grupo `cobr`: o dado já está no ERPNext, íntegro, e não estava sendo
aproveitado. Os campos batem um a um — é tradução, não adaptação:

| ERPNext (`Batch`) | NF-e (`rastro`) |
|---|---|
| `batch_id` | `nLote` |
| `manufacturing_date` | `dFab` |
| `expiry_date` | `dVal` |
| quantidade da linha | `qLote` |

Implementado em `integracao/rastreabilidade.py`. **Nenhum campo novo**: quem já usa lote
no ERPNext já tem a rastreabilidade fiscal pronta.

### O que este módulo deliberadamente não decide

**Se o item precisa de `rastro`.** A obrigação vale para medicamentos (Lei 11.903/2009),
bebidas, água e produtos sob controle sanitário — e a lista muda por norma. O módulo
monta quando há lote e omite quando não há. Inventar aqui uma lista de NCM "que precisa
de rastro" seria criar regra fiscal sem fonte.

E `rastro` **não é** SNCM: o DataMatrix da caixa de remédio é outra obrigação, com dados
próprios, já registrado em `produto.py`.

## Gestão de custos: o que é gap e o que não é

Levantamento, sem código ainda — para não esquecer o que ficou pendente.

### O que o ERPNext já resolve, e bem

| Necessidade | Onde |
|---|---|
| Custo médio ponderado **móvel** | `Moving Average` (método de valoração) |
| Custo fixo/variável por centro | `Cost Center` |
| Custos de importação e frete rateados | `Landed Cost Voucher` |
| Custo de produção (materiais + operações) | `BOM` com `Operating Cost` |
| Custo por demanda / por projeto | `Project` e `Task`, com apontamento |

Nada disso é tropicalização: é contabilidade de custos genérica, e o ERPNext a
implementa. Reescrever seria duplicar.

### O gap brasileiro real: quais tributos integram o custo

Aqui sim há regra própria, e é a que produz erro caro:

- **ICMS recuperável não integra o custo** — é crédito, vai para "Impostos a Recuperar"
  (conta que `plano_de_contas.py` já tem). Somá-lo ao estoque infla o custo e derruba a
  margem calculada.
- **IPI recuperável** idem, para quem é industrial ou equiparado.
- **ICMS/IPI não recuperáveis integram** — Simples Nacional, uso e consumo, ativo
  imobilizado (com regra própria de crédito em 48 parcelas para o ICMS).
- **PIS/COFINS no regime não cumulativo** geram crédito e não integram; no cumulativo,
  integram.

Ou seja: **o custo de aquisição do mesmo produto muda conforme o regime tributário do
comprador e a destinação do item**. O projeto já tem as peças (`br_regime_pis_cofins`,
`finalidade_compra`, `origem_mercadoria`, apuração por item) — falta o módulo que
decide quanto do documento vira custo e quanto vira crédito.

**Pendência registrada com escopo definido**: `contabil/custo_aquisicao.py`, com fonte a
verificar (RIR/2018 e a legislação de PIS/COFINS não cumulativo) antes de escrever
código — mesma disciplina de sempre.

### Custeio por absorção não é escolha

Para fins fiscais, a legislação brasileira exige **custeio por absorção** (custos
indiretos de produção rateados ao produto). Custeio direto/variável é ferramenta
gerencial legítima, mas não serve de base para o resultado tributável. Se o projeto vier
a oferecer análise gerencial de custos, os dois números precisam coexistir sem se
confundir — registrado aqui para não virar surpresa.

### Bloco K da EFD

O controle de produção e estoque (Bloco K) é onde o Fisco cruza consumo, produção e
saldo. Já está na lista de pendências de `docs/sped-fiscal.md`; é o consumidor natural
de uma gestão de custos completa, e depende de `BOM` do ERPNext.
