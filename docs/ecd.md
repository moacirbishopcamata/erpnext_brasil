# ECD (Escrituração Contábil Digital): registros I050, I200, I250, I150 e I155

Sexto incremento do bloco contábil, sobre
[plano-de-contas.md](plano-de-contas.md) — a ECD é o SPED Contábil: os livros Diário e
Razão em formato digital, obrigatório para a maioria das empresas tributadas pelo lucro
real/presumido.

## Decisão de design: numeração-padrão embutida, não código externo

O registro I050 exige um código por conta (`COD_CTA`) e a hierarquia via
`COD_CTA_SUP` — mas `plano_de_contas.py` foi desenhado deliberadamente **sem
códigos**, porque não existe codificação única obrigatória para empresa privada no
Brasil (ver `docs/plano-de-contas.md`).

Duas soluções possíveis: (a) `montar_i050` receber um plano de contas já codificado de
fora — mesmo padrão de `gerar_lancamentos_compra` recebendo `creditos_tributarios`
já decidido —, correto para uma empresa real com plano próprio, mas sem nada para
testar até existir esse chamador; ou (b) gerar uma numeração-padrão determinística
embutida em `plano_de_contas.montar_codigos`, documentada como convenção deste app, não
exigência legal — substituível por completo quando uma empresa real tiver seu próprio
plano.

**Decisão do usuário (2026-08-30): opção (b).** `montar_codigos()` numera cada raiz
`"1"`, `"2"`, `"3"`, `"4"` (na ordem de `ARVORE`: Ativo, Passivo, Receita, Despesa) e
cada filha como `"{código_do_pai}.{índice_de_nascimento}"` — puramente estrutural,
determinístico, sem julgamento de conteúdo.

## `COD_NAT`: Receita e Despesa compartilham o mesmo código

Confirmado em fonte técnica especializada, corroborada por busca cruzada: o campo
`COD_NAT` (natureza da conta) do registro I050 tem:

| Código | Natureza |
|---|---|
| `01` | Ativo |
| `02` | Passivo |
| `03` | Patrimônio Líquido |
| `04` | Contas de resultado (Receita **e** Despesa juntas) |
| `05` | Compensação (fora do balanço) |
| `09` | Outras |

Receita e Despesa **não** têm códigos separados — os dois caem em `"04"`. Isso
simplifica o mapeamento: não é preciso distinguir os dois `root_type` de resultado do
ERPNext (`Income`/`Expense`) neste campo específico.

## A pegadinha: Patrimônio Líquido não segue o `root_type` do pai

`plano_de_contas.py` modela `Patrimônio Líquido` como um grupo **dentro** de `Passivo`
(mesmo `root_type`, `Liability`, refletindo o Art. 178, § 2º da Lei 6.404/76, que lista
os três — Passivo Circulante, Passivo Não Circulante, Patrimônio Líquido — como
subgrupos do mesmo lado do balanço). O ERPNext não distingue os dois por `root_type`
porque não precisa; a ECD, por outro lado, **exige** `COD_NAT` distinto: `"02"` para o
resto do Passivo, `"03"` só para o subgrupo Patrimônio Líquido e tudo dentro dele.

`montar_i050` não deriva `COD_NAT` só do `root_type` — rastreia, durante o percurso da
árvore, se o nó atual (ou algum ancestral) é `"Patrimônio Líquido"`, e usa `"03"` nesse
caso, `"02"` no resto do Passivo. Testado explicitamente (`test_patrimonio_liquido_
usa_cod_nat_03_nao_02`), incluindo que uma folha **dentro** de Patrimônio Líquido (ex.:
`Capital Social`) herda o `"03"` do ancestral, não o `"02"` do avô `Passivo`.

## Layout do registro (ordem oficial)

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"I050"` |
| 2 | `DT_ALT` | Data de inclusão/alteração da conta no plano |
| 3 | `COD_NAT` | Natureza da conta (tabela acima) |
| 4 | `IND_CTA` | `"S"` sintética (grupo) / `"A"` analítica (folha) |
| 5 | `NIVEL` | Nível hierárquico (profundidade do código) |
| 6 | `COD_CTA` | Código da conta/grupo |
| 7 | `COD_CTA_SUP` | Código do grupo de nível imediatamente superior |
| 8 | `CTA` | Nome da conta/grupo |

`DT_ALT` é parâmetro, não `datetime.now()` embutido — mesma razão de
`ativar_contingencia_svc` receber `desde` como parâmetro: mantém a função determinística
e testável sem mockar tempo.

## I200/I250 — lançamento contábil e suas partidas

`contabil/ecd_i200.montar_i200_i250` converte uma lista de `Lancamento` (já gerada por
`lancamento.gerar_lancamentos_venda`/`gerar_lancamentos_compra`) num par de registros
por lançamento: **I200** (cabeçalho — número, data, valor) e **I250** (as partidas —
sempre duas, débito e crédito, porque `Lancamento` não modela lançamento com mais de
duas pontas).

### Por que dois registros para um `Lancamento`

A ECD não modela "débito e crédito" como dois campos do mesmo registro — modela o
lançamento como cabeçalho (I200, com o valor total) mais uma lista de partidas (I250,
cada uma com sua própria conta e um indicador `D`/`C`). Um rateio entre três contas
precisaria de um tipo mais rico que `Lancamento` ainda não é — fora de escopo.

### `COD_CTA` resolvido por `montar_codigos()`

`Lancamento.conta_debito`/`conta_credito` são nomes (`"Clientes"`, `"ICMS a
Recolher"`) — a conversão usa a mesma numeração-padrão de `plano_de_contas.
montar_codigos()` já usada pelo I050. Um nome que não exista na árvore levanta
`ContaDesconhecida`, nunca um `COD_CTA` vazio ou inventado.

### Layout dos dois registros

**I200:**

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"I200"` |
| 2 | `NUM_LCTO` | Identificador único do lançamento |
| 3 | `DT_LCTO` | Data do lançamento |
| 4 | `VL_LCTO` | Valor do lançamento |
| 5 | `IND_LCTO` | `"N"` normal / `"E"` encerramento de resultado / `"X"` extemporâneo |

**I250** (uma linha por partida):

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"I250"` |
| 2 | `COD_CTA` | Código da conta analítica debitada/creditada |
| 3 | `COD_CCUS` | Centro de custo (não modelado — sempre vazio) |
| 4 | `VL_DC` | Valor da partida (igual ao `VL_LCTO` do I200) |
| 5 | `IND_DC` | `"D"` débito / `"C"` crédito |
| 6 | `NUM_ARQ` | Referência a documento anexado (não modelado — vazio) |
| 7 | `COD_HIST_PAD` | Histórico padronizado, tabela I075 (não modelada — vazio) |
| 8 | `HIST` | Texto do histórico — vem de `Lancamento.historico` |
| 9 | `COD_PART` | Participante, tabela 0150 (não modelada — vazio) |

### Escopo desta versão

`IND_LCTO` sempre `"N"` — `lancamento.py` não produz lançamento de encerramento de
resultado (`"E"`) nem extemporâneo (`"X"`). `COD_CCUS`, `COD_HIST_PAD`, `COD_PART` e
`NUM_ARQ` ficam sempre em branco — as tabelas auxiliares correspondentes (centro de
custo, histórico padronizado, participante, documento anexado) não existem neste app.

## I150/I155 — saldos periódicos por conta

`contabil/ecd_i150.py` consolida os `Lancamento` de um período em saldo por conta: I150
identifica o período (início/fim); I155 traz, para cada conta **com movimento no
período** (confirmado na fonte: conta sem lançamento nenhum não gera linha, mesmo com
saldo transportado diferente de zero), o saldo inicial, o total de débitos e créditos, e
o saldo final.

### A aritmética D/C é mecânica, nunca condicionada à "natureza" da conta

`IND_DC_INI`/`IND_DC_FIN` dizem de que lado o saldo está (`"D"` devedor, `"C"` credor) —
nunca em branco, mesmo quando o saldo é zero (convenção deste módulo para o empate:
`"D"`, já que a fonte só exige não deixar em branco, sem dizer qual dos dois usar no
zero). A conta de "que lado o saldo termina" **não depende** de a conta ser
"naturalmente devedora" (Ativo/Despesa) ou "naturalmente credora" (Passivo/PL/Receita):
registrar um débito sempre empurra para o lado D, um crédito sempre empurra para o lado
C, seja qual for a conta — testado explicitamente
(`test_saldo_credor_recebendo_debito_pode_virar_devedor`, uma conta credora que vira
devedora depois de um débito grande o bastante). Por isso `ecd_i150.py` converte
`(valor, indicador)` para um número com sinal e soma/subtrai diretamente, sem consultar
`root_type` nem nada de `plano_de_contas.py` além do código da conta.

### Saldo inicial é parâmetro, não persistido

Mesma disciplina de `apuracao_periodo.apurar_periodo` (`saldo_credor_anterior`):
`SaldoInicial` vem de fora — nenhum mecanismo aqui guarda o saldo final de um período
para virar o inicial do seguinte automaticamente. Conta sem `SaldoInicial` informado
começa do zero devedor, não erro — a maioria das contas de resultado (Receita/Despesa)
realmente zera a cada período; só as patrimoniais carregam saldo de fato.

### Layout dos dois registros

**I150:**

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"I150"` |
| 2 | `DT_INI` | Data de início do período |
| 3 | `DT_FIN` | Data de fim do período |

**I155** (uma linha por conta com movimento):

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"I155"` |
| 2 | `COD_CTA` | Código da conta analítica |
| 3 | `COD_CCUS` | Centro de custo (não modelado — sempre vazio) |
| 4 | `VL_SLD_INI` | Saldo inicial do período |
| 5 | `IND_DC_INI` | `"D"`/`"C"` do saldo inicial |
| 6 | `VL_DEB` | Total de débitos do período |
| 7 | `VL_CRED` | Total de créditos do período |
| 8 | `VL_SLD_FIN` | Saldo final do período |
| 9 | `IND_DC_FIN` | `"D"`/`"C"` do saldo final |

## Ainda por implementar

- **Registro I051** (plano de contas referencial da RFB) — mapeamento entre o plano
  próprio e o plano referencial que a ECD também aceita, para quem usa o de terceiros.
- **Lançamento com mais de duas pontas** (rateio entre três ou mais contas) — pede um
  tipo mais rico que `Lancamento`, hoje limitado a um débito e um crédito.
- **Serialização para o formato de texto do SPED** — mesma decisão já registrada em
  `docs/sped-fiscal.md`: este módulo devolve `list[dict]`/`list[tuple[dict, list[dict]]]`,
  não a linha de texto.
- **Persistência do saldo inicial entre períodos** — `SaldoInicial` é sempre parâmetro
  explícito; nenhum mecanismo guarda o saldo final de um mês para virar o inicial do
  seguinte automaticamente.

## Arquivos

- `contabil/ecd_i050.py` — `montar_i050`; camada pura, sem Frappe, testável sem bench.
- `contabil/ecd_i200.py` — `montar_i200_i250`; idem.
- `contabil/ecd_i150.py` — `montar_i150`, `montar_i155`, `SaldoInicial`; idem.
- `contabil/plano_de_contas.montar_codigos` — a numeração-padrão que os três usam.

## Fontes

- Layout dos registros I050, I200, I250, I150 e I155, e tabelas
  `COD_NAT`/`IND_LCTO`/`IND_DC` — fonte oficial (`sped.rfb.gov.br`, o Manual de
  Orientação da ECD) inacessível às ferramentas de busca no momento; confirmado em guia
  técnico especializado (`vriconsulting.com.br`), corroborado por busca cruzada que
  reproduziu a mesma tabela de códigos — consultado em 2026-08-30.
