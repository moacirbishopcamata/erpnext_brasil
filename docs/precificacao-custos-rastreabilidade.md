# Precificação, custos, lucratividade, perdas e rastreabilidade

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

**Implementado** em `contabil/custo_aquisicao.py`, com fonte verificada: **RIR/2018, art.
301, §3º** — "os impostos recuperáveis por meio de créditos na escrita fiscal não
integram o custo de aquisição".

`custo_de_aquisicao(valor_mercadoria, tributos, frete, seguro, outras_despesas,
descontos)` devolve `ResultadoCusto` com `custo`, `creditos` e `creditos_por_tributo`.
Cada tributo entra como `TributoDaAquisicao(nome, valor, recuperavel, por_dentro)`.

Duas decisões que o teste-âncora prova:

- **`recuperavel` é informado, não deduzido do nome.** O mesmo ICMS é recuperável para
  uma empresa e não para outra; deduzir aqui exigiria conhecer regime e destinação, que
  são decisão da camada de integração.
- **`por_dentro` muda o sinal da conta.** ICMS/PIS/COFINS já estão no valor da
  mercadoria — somá-los dobraria o imposto. **IPI é por fora** e soma ao total pago.
  Tratar os dois igual erra o custo nos dois sentidos, e foi exatamente o erro que a
  primeira versão deste módulo cometeu antes do teste pegá-lo.

Pós-condição verificada em teste: `custo + créditos == total pago`. Se não fechasse,
algum valor teria sumido ou sido contado duas vezes — e um erro assim se propaga para a
margem e para o preço sem dar sinal nenhum.

**Atecnia declarada**: o §3º fala em *impostos*; PIS e COFINS são tecnicamente
*contribuições*. O módulo segue a interpretação sistemática (inclui as contribuições,
porque a razão da regra vale igualmente), e registra na própria docstring que a letra do
dispositivo é mais estreita. Divergência declarada, não silenciosa.

## Lucratividade: "quanto lucrei?" tem três respostas, e duas estão erradas

`contabil/lucratividade.py`, fonte: **Art. 187 da Lei 6.404/76**, que fixa a ordem da DRE:

```
    Receita Bruta
(−) Deduções (devoluções, abatimentos, impostos sobre vendas)
=   Receita Líquida
(−) Custo das Mercadorias e Serviços Vendidos
=   Lucro Bruto
(−) Despesas operacionais
=   Resultado Operacional
```

`plano_de_contas.py` já registrava que **Receita Líquida e Lucro Bruto são subtotais
calculados, não contas próprias**; este módulo é o cálculo que faltava.

O erro que a ordem legal evita: **margem calculada sobre a receita bruta dá número maior
e falso**, porque os impostos sobre vendas ainda estão lá dentro e não são receita de
ninguém — são repasse. Empresa que fatura R$ 1.000 com R$ 265 de imposto e R$ 600 de
custo tem margem bruta de **18,4%** (135 ÷ 735), não 13,5% (135 ÷ 1.000) nem 40%.

### O achado do teste de costura

Escrever o teste que ligava `precificacao` a `lucratividade` "falhou" — e a falha era um
achado conceitual, não um bug: **precificar com margem de 20% produz 24,4% de margem
bruta apurada** quando o imposto é 18%. As duas estão certas; o denominador é que muda
(preço/receita bruta lá, receita líquida aqui).

A resposta não foi escolher uma: foi **nomear as duas**. `margem_bruta` (sobre a líquida,
a do Art. 187) e `margem_bruta_sobre_faturamento` (sobre a bruta, a que a precificação
usa). Ter as duas nomeadas impede a comparação errada — que é como se conclui que a
margem melhorou quando só mudou a régua. `carga_sobre_faturamento` fica separada de
ambas: é o tamanho do repasse, o número que o empresário chama de "imposto que pago", e
não é margem nenhuma.

Prejuízo é resultado válido (lucro pode ser negativo). Dedução maior que a receita bruta
**não é**: receita líquida negativa não descreve operação real, é erro de lançamento, e
falha alto.

## Gestão de perdas: uma perda de R$ 1.000 não custa R$ 1.000

`contabil/perdas.py`, fonte: **LC 87/1996 (Lei Kandir), art. 21** — manda estornar o
crédito de ICMS quando a mercadoria "vier a perecer, deteriorar-se ou extraviar-se".

Quem compra credita porque vai tributar a saída. Quando a mercadoria **não sai**, o
pressuposto do crédito deixa de existir e o crédito tomado tem de ser **estornado**.
Consequência: o custo real da perda é o valor do estoque **mais** o crédito devolvido.
Sistema que só dá baixa contábil subestima o prejuízo e deixa passivo fiscal para trás —
R$ 1.000 de estoque com R$ 272,50 de crédito tomado custa R$ 1.272,50.

`apurar_perda(valor_do_estoque, tipo, creditos_tomados)` devolve `ResultadoPerda` com as
duas parcelas separadas e `estornos_por_tributo` discriminado (quem lança precisa saber
qual crédito devolver, não só o total).

### A exceção que muda o número

**Quebra normal do processo** — evaporação, aparagem, resíduo previsível — **não estorna**:
a mercadoria não deixou de ser usada na atividade tributada, ela foi consumida por ela.
Integra o custo de produção.

A distinção **não é de tamanho, é de natureza**, e por isso a classificação não é feita
pelo módulo: depende do processo de cada empresa e, em dúvida, do Fisco estadual. Dos
seis tipos declarados (`TIPO_QUEBRA_NORMAL`, `TIPO_VENCIMENTO`, `TIPO_DETERIORACAO`,
`TIPO_FURTO_OU_ROUBO`, `TIPO_SINISTRO`, `TIPO_INVENTARIO`), só o primeiro preserva o
crédito — e há teste que falha se alguém acrescentar outro sem pensar.

### A simetria compra ↔ perda

Estorna-se **exatamente** o que se creditou. `creditos_tomados` recebe o
`creditos_por_tributo` que `custo_de_aquisicao` devolveu, e há teste de costura provando
que `custo_total_da_perda == total_pago` da compra original. Não é coincidência: é a
mesma nota vista pelos dois lados.

### Fora de escopo, declarado

- **Percentuais de quebra tolerada por UF ou produto** — alguns regulamentos estaduais
  fixam limites; variam por estado e produto, e inventar número seria criar regra fiscal
  sem fonte.
- **Dedutibilidade da perda no IRPJ** — matéria de apuração de lucro real (laudo,
  comunicação), não desta baixa.
- **Registro da perda no Bloco K da EFD** — consumidor natural disto, já na lista de
  pendências de `docs/sped-fiscal.md`.

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
