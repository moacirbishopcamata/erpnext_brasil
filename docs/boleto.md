# Boleto bancário: código de barras e linha digitável

Oitavo incremento do bloco contábil — primeiro passo em "boleto bancário", item que a
memória do projeto já classificava como integração bancária de contas a receber (não
documento fiscal), mas pertencente a este bloco por lidar com título e conciliação.

## O fator de vencimento mudou de base em 2025 — isto não é nota histórica

O "fator de vencimento" é um número de 4 dígitos que conta os dias entre uma data-base
e o vencimento do boleto. A base original, `07/10/1997`, **esgotou em 21/02/2025**
(chegou ao limite de 9999). A partir de **22/02/2025**, o FEBRABAN (Comunicado
FB-009/2023) reiniciou a contagem: `22/02/2025 = 1000`, `23/02/2025 = 1001`, e assim
por diante — nunca mais a base de 1997.

Isto importa **hoje**: qualquer boleto com vencimento a partir de 2025-02-22 (ou seja,
todo boleto emitido de agora em diante, dado que hoje é 2026-08-30) usa a base nova.
Implementar só a base de 1997 produziria um fator estruturalmente inválido para 100%
dos boletos que este app algum dia emitir — não um problema teórico para 2033 como o
Y2038 de Unix, mas um bug ativo desde fevereiro de 2025. `calcular_fator_vencimento`
escolhe a base pela data de vencimento recebida, nunca uma constante fixa.

## Estrutura do código de barras (44 posições)

```
1-3    banco (3)
4      moeda ("9" para Real)
5      DV geral (módulo 11)
6-9    fator de vencimento (4)
10-19  valor, em centavos, 8 inteiros + 2 decimais (10)
20-44  campo livre, definido por cada banco (25)
```

Confirmada em múltiplas fontes técnicas consistentes. A fonte primária (o PDF de layout
da FEBRABAN, `cmsarquivos.febraban.org.br`) está digitalizado como imagem e não pôde
ser lido por texto pelas ferramentas de busca — dito explicitamente por ser a situação
que a política deste projeto pede para não esconder.

## `campo_livre` não é modelado — cada banco tem o seu

Cada banco define seu próprio layout interno para as 25 posições do campo livre (nosso
número, agência, carteira, etc.) — não existe um layout genérico "correto" para todos
os bancos. `montar_codigo_barras` recebe `campo_livre` já pronto (25 dígitos), mesma
disciplina de `gerar_lancamentos_compra` receber `creditos_tributarios` já decidido em
vez de inferir: a informação que falta é responsabilidade de quem conhece o banco
específico, não deste módulo.

## DV geral: módulo 11, pesos 2 a 9 cíclicos, caso especial 0/1/10 → 1

Calculado sobre as 43 posições do código **exceto** a própria posição do DV
(posições 1-4 e 6-44, concatenadas nessa ordem) — pesos 2, 3, 4, ..., 9, voltando a 2,
aplicados da direita para a esquerda. `resto = soma % 11`; se `resto` for 0, 1 ou 10, o
DV é `1` (não `11 - resto`, que daria 11 ou 10 — dígitos que não existem); senão,
DV `= 11 - resto`.

## Linha digitável: os mesmos 44 dígitos, em 5 campos com DV próprio

```
Campo 1 = banco(3) + moeda(1) + campo_livre[0:5]   (9) + DV1 (módulo 10)
Campo 2 = campo_livre[5:15]                        (10) + DV2 (módulo 10)
Campo 3 = campo_livre[15:25]                       (10) + DV3 (módulo 10)
Campo 4 = DV geral (1, o mesmo da posição 5 do código de barras)
Campo 5 = fator de vencimento (4) + valor (10)     (14, sem DV próprio)
```

Confirmada em três fontes técnicas independentes e consistentes entre si — nenhuma
publicou a tabela de posições literal, mas todas descrevem exatamente a mesma divisão
9+10+10 do campo livre de 25 posições, o que fecha a conta sem ambiguidade.

**Módulo 10** (DV de cada campo): pesos 2/1 alternados, da direita para a esquerda;
produto maior que 9 soma os próprios algarismos (`7*2=14` → `1+4` → `5`) — a pegadinha
clássica que um `*2` sem essa correção erra; `DV = (10 - soma % 10) % 10` (o `% 10`
extra cobre o caso `soma % 10 == 0`, em que o dígito correto é `0`, não `10`).

## Validado contra um exemplo real publicado

Diferente da maioria dos módulos deste app (onde a fonte primária governamental é
citada diretamente), aqui a validação mais forte veio de reconstituir um código de
barras/linha digitável **reais e publicados** (banco 001, fator 3026, valor R$ 32,80) a
partir dos parâmetros e comparar byte a byte com o resultado esperado — os três testes
de `TestExemploReal` fazem exatamente isso. Bateu exato: DV geral, os três DVs de
campo, a montagem inteira.

## Conciliação: leitura do arquivo de retorno CNAB 400

`contabil/cnab400_retorno.py` lê o registro detalhe do arquivo que o banco devolve
informando o que aconteceu com cada título — a metade que fecha o ciclo de
conciliação. Só o registro detalhe (tipo `1`) importa aqui; cabeçalho e trailer não são
lidos.

**Cada banco tem seu próprio dialeto de CNAB 400** — confirmado ao pesquisar: existe
uma tabela "padrão" de código de ocorrência, mas bancos divergem em detalhe. Por isso
as posições de byte e a tabela de códigos vêm de uma única fonte técnica consistente
(um provedor de banking-as-a-service regulado) — **não foi possível cruzar contra uma
segunda fonte posição a posição**, diferente do rigor que o código de barras conseguiu
(validado contra exemplo real). Os quatro códigos mais comuns (`02`, `03`, `06`, `09`)
foram corroborados por busca cruzada independente; os demais, não — `CODIGOS_
OCORRENCIA_CORROBORADOS` marca essa distinção explicitamente no próprio código.

### `FOI_PAGO`: nem todo código "positivo" é dinheiro recebido

`02` (entrada confirmada) é só a confirmação de que o banco recebeu o registro do
título — não fecha nada. `FOI_PAGO = {"06", "17"}` cobre só liquidação de fato: `06`
(liquidação normal) e `17` (liquidação após baixa ou título não registrado, o caso de
um boleto pago depois de já ter sido baixado). Tratar `02` como "pago" seria o erro
óbvio que motivou separar essa lista — testado explicitamente
(`test_confirmacao_de_entrada_nao_e_pago`).

### Posições do registro detalhe (fonte única, ver cautela acima)

| Campo | Posições (1-indexed) |
|---|---|
| Nosso número | 71-82 |
| Código de ocorrência | 109-110 |
| Data de ocorrência (`DDMMAA`) | 147-152 |
| Valor pago/recebido (11 inteiros + 2 decimais implícitos) | 254-266 |

## Ainda por implementar

- **Registro do título via API/CNAB do banco** — este módulo só calcula código de
  barras/linha digitável a partir de dados já decididos; não fala com nenhum banco.
- **CNAB 240** (layout mais novo, também usado por vários bancos) — só o 400 foi
  coberto.
- **Geração da imagem do código de barras** (padrão "2 de 5 intercalado") — este
  módulo produz a sequência de 44 dígitos, não a representação gráfica de barras.
- **Validação (não só geração)**: conferir um código de barras/linha digitável
  recebidos de fora contra os DVs esperados — hoje só monta, não audita.
- **Cabeçalho/trailer do CNAB 400** — só o registro detalhe é lido; nenhuma validação
  de que o arquivo inteiro está bem formado (contagem de registros, banco do trailer).

## Arquivos

- `contabil/boleto.py` — `calcular_fator_vencimento`, `calcular_dv_barra`,
  `calcular_dv_campo`, `montar_codigo_barras`, `montar_linha_digitavel`; camada pura,
  sem Frappe, testável sem bench.
- `contabil/cnab400_retorno.py` — `ler_registro_detalhe`, `foi_pago`; idem.

## Fontes

- Layout do código de barras (44 posições) e da linha digitável (5 campos) — fonte
  oficial (`cmsarquivos.febraban.org.br`, PDF digitalizado como imagem) ilegível às
  ferramentas de busca; confirmado em múltiplas fontes técnicas consistentes entre si
  — consultado em 2026-08-30.
- Mudança do fator de vencimento (Comunicado FEBRABAN FB-009/2023, base nova a partir
  de 22/02/2025) — confirmado em duas fontes secundárias consistentes — consultado em
  2026-08-30.
- Exemplo real de código de barras/linha digitável usado para validação byte a byte —
  consultado em 2026-08-30.
- Layout do registro detalhe do CNAB 400 de retorno e tabela de códigos de ocorrência —
  fonte técnica única (provedor de banking-as-a-service regulado); os quatro códigos
  mais comuns (`02`, `03`, `06`, `09`) corroborados por busca cruzada independente, os
  demais não — dito explicitamente na docstring do módulo — consultado em 2026-08-30.
