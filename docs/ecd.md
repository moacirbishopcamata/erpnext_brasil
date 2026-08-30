# ECD (Escrituração Contábil Digital): registro I050

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

## Ainda por implementar

- **Registro I051** (plano de contas referencial da RFB) — mapeamento entre o plano
  próprio e o plano referencial que a ECD também aceita, para quem usa o de terceiros.
- **Registros I150/I155/I200/I250** (saldos periódicos e lançamentos) — o I050 só
  declara o plano; os lançamentos de verdade (que `contabil/lancamento.py` já gera)
  ainda não têm conversor para o formato do bloco I da ECD.
- **Serialização para o formato de texto do SPED** — mesma decisão já registrada em
  `docs/sped-fiscal.md`: este módulo devolve `list[dict]`, não a linha de texto.

## Arquivos

- `contabil/ecd_i050.py` — `montar_i050`; camada pura, sem Frappe, testável sem bench.
- `contabil/plano_de_contas.montar_codigos` — a numeração-padrão que este módulo usa.

## Fontes

- Layout do registro I050 e tabela `COD_NAT` — fonte oficial (`sped.rfb.gov.br`, o
  Manual de Orientação da ECD) inacessível às ferramentas de busca no momento;
  confirmado em guia técnico especializado (`vriconsulting.com.br`), corroborado por
  busca cruzada que reproduziu a mesma tabela de códigos — consultado em 2026-08-30.
