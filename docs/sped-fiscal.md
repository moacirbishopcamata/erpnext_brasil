# SPED Fiscal (EFD-ICMS/IPI): registros E110, E111 e E520

Quarto incremento do bloco contábil, sobre
[apuracao-periodica.md](apuracao-periodica.md) — primeiro passo em "obrigações
acessórias" do roteiro.

## Por que EFD, não o "Registro de Entradas e Saídas" em papel

O roteiro deste bloco pedia "apuração e livros (Registro de Entradas e Saídas, Apuração
de ICMS e de IPI)". Investigando antes de implementar: o **Ajuste SINIEF 02/2009**
dispensou, para quem é obrigado ao EFD-ICMS/IPI, a emissão e autenticação dos livros em
papel — Registro de Entradas, Registro de Saídas, Registro de Inventário, Registro de
Apuração do IPI e Registro de Apuração do ICMS. Hoje esse é o caso da esmagadora maioria
das empresas brasileiras.

Consequência prática para este projeto: implementar o livro de papel seria construir um
artefato que a lei já tornou dispensável para quem mais importa. O alvo real —
"apuração e livros" no sentido em que ainda importa hoje — é o **registro digital do
EFD** que substitui esses livros, não a forma antiga. Por isso este incremento pula
direto para o SPED Fiscal, em vez de modelar o livro de papel primeiro.

## E110 (ICMS) e E520 (IPI) são conversores, não uma nova apuração

O registro E110 ("Apuração do ICMS — Operações Próprias") traz exatamente o que
`contabil/apuracao_periodo.ApuracaoPeriodo` (para ICMS) já calcula: débito bruto,
crédito bruto, saldo credor anterior, saldo apurado, valor a recolher, saldo credor a
transportar. `contabil/efd_icms_ipi.montar_e110` só organiza esses seis valores no
formato de campo que o Fisco espera — a conta já foi feita em `apuracao_periodo.py`.

O registro **E520** ("Apuração do IPI") faz o mesmo para IPI — layout mais enxuto (8
campos, não 15: sem equivalente a `VL_TOT_DED`), mesma mecânica de saldo mutuamente
exclusivo. **E110 não é o registro de IPI** — cheguei a cogitar "E200" antes de conferir
a fonte, o que estava errado: E200/E210 são de ICMS-Substituição Tributária, E300/E310
são de ICMS-DIFAL (EC 87/2015, o "Diferencial de Alíquota" interestadual — ver
`docs/README.md` para outros gaps deliberados envolvendo DIFAL). A apuração do IPI vive
no bloco E500-E530, numeração completamente separada da do ICMS.

## Layout confirmado (ordem oficial do Guia Prático EFD-ICMS/IPI)

### E110 — Apuração do ICMS

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"E110"` |
| 2 | `VL_TOT_DEBITOS` | Total de débitos do ICMS (saídas) |
| 3 | `VL_AJ_DEBITOS` | Ajustes a débito do documento fiscal |
| 4 | `VL_TOT_AJ_DEBITOS` | Total de ajustes a débito |
| 5 | `VL_ESTORNOS_CRED` | Estornos de crédito |
| 6 | `VL_TOT_CREDITOS` | Total de créditos do ICMS (entradas) |
| 7 | `VL_AJ_CREDITOS` | Ajustes a crédito do documento fiscal |
| 8 | `VL_TOT_AJ_CREDITOS` | Total de ajustes a crédito |
| 9 | `VL_ESTORNOS_DEB` | Estornos de débito |
| 10 | `VL_SLD_CREDOR_ANT` | Saldo credor do período anterior |
| 11 | `VL_SLD_APURADO` | Débitos + ajustes + estornos, menos créditos |
| 12 | `VL_TOT_DED` | Deduções previstas na legislação estadual |
| 13 | `VL_ICMS_RECOLHER` | `VL_SLD_APURADO` menos `VL_TOT_DED` |
| 14 | `VL_SLD_CREDOR_TRANSPORTAR` | Excedente de crédito para o próximo período |
| 15 | `DEB_ESP` | Débitos especiais (extemporâneos) |

### E520 — Apuração do IPI

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"E520"` |
| 2 | `VL_SD_ANT_IPI` | Saldo credor do período anterior |
| 3 | `VL_DEB_IPI` | Total de débitos do IPI (saídas) |
| 4 | `VL_CRED_IPI` | Total de créditos do IPI (entradas) |
| 5 | `VL_OD_IPI` | Outros débitos (inclui estornos de crédito) |
| 6 | `VL_OC_IPI` | Outros créditos (inclui estornos de débito) |
| 7 | `VL_SC_IPI` | Saldo credor a transportar para o próximo período |
| 8 | `VL_SD_IPI` | Saldo devedor (valor a recolher) |

`sped.rfb.gov.br` (fonte oficial, o Guia Prático em si) ficou inacessível às ferramentas
de busca no momento da implementação — mesma limitação já registrada para outras fontes
governamentais neste projeto. As duas tabelas acima foram confirmadas num guia técnico
especializado (vriconsulting.com.br) com descrição campo a campo, corroborado por um
segundo agregador (busca cruzada) que reproduziu a mesma lista de nomes de campo na
mesma ordem. Para o E520, a mesma fonte confirma explicitamente que `VL_SC_IPI` e
`VL_SD_IPI` são mutuamente exclusivos — a mesma regra que `ApuracaoPeriodo` já
implementava antes de eu ler essa confirmação, não o contrário.

## E111: ajuste de apuração do ICMS, agora coberto

O registro E111 discrimina, um a um, cada ajuste que compõe os 7 campos de ajuste do
E110 — `VL_TOT_AJ_DEBITOS`, `VL_ESTORNOS_CRED`, `VL_TOT_AJ_CREDITOS`,
`VL_ESTORNOS_DEB`, `VL_TOT_DED`, `DEB_ESP` (`VL_AJ_DEBITOS`/`VL_AJ_CREDITOS` são
ajuste vinculado a documento fiscal específico, categoria diferente, continuam fora de
escopo). Layout (4 campos, ordem oficial):

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"E111"` |
| 2 | `COD_AJ_APUR` | Código do ajuste (4 caracteres) |
| 3 | `DESCR_COMPL_AJ` | Descrição complementar |
| 4 | `VL_AJ_APUR` | Valor do ajuste |

`COD_AJ_APUR` **não tem tabela nacional única** — cada UF mantém sua própria tabela de
códigos (Ato COTEPE/ICMS 09/2008, item 5.1.1, usado como *fallback* só quando o estado
não tem tabela própria) — mesma variação por UF já vista em `boleto.py`
(`campo_livre`)/`cnab400_retorno.py` (dialeto por banco). Por isso `Ajuste.codigo` vem
pronto de quem chama; este módulo só lê o **4º caractere**, que decide o tipo (e,
portanto, para qual campo do E110 o valor soma):

| 4º caractere | Tipo | Campo do E110 |
|---|---|---|
| `0` | Outros débitos | `VL_TOT_AJ_DEBITOS` |
| `1` | Estornos de crédito | `VL_ESTORNOS_CRED` |
| `2` | Outros créditos | `VL_TOT_AJ_CREDITOS` |
| `3` | Estornos de débito | `VL_ESTORNOS_DEB` |
| `4` | Deduções | `VL_TOT_DED` |
| `5` | Débitos especiais (extemporâneos) | `DEB_ESP` |

`montar_e110(apuracao, ajustes)` recalcula `VL_SLD_APURADO`/`VL_ICMS_RECOLHER`/
`VL_SLD_CREDOR_TRANSPORTAR` somando os ajustes à fórmula — não reaproveita
`ApuracaoPeriodo.a_recolher`/`saldo_credor_a_transportar` direto, porque esses dois não
sabem de ajuste algum (escopo de débito/crédito bruto só). `DEB_ESP` fica de fora da
fórmula — confirmado na fonte como valor informativo (débito extemporâneo), não algo
que altera o saldo apurado. Dedução maior que o saldo devedor apurado levanta erro
explícito (`EfdInvalido`) — caso não coberto, sem fonte confirmada para o tratamento
correto.

## E520 (IPI) continua sem ajuste — E530 ainda não levantado

Diferente do par E110/E111, o par E520/E530 do IPI não teve seu registro de ajuste
(E530) pesquisado ainda — `montar_e520` continua zerando `VL_OD_IPI`/`VL_OC_IPI` como
antes, com a mesma ressalva: correto sem ajuste real, não correto com ajuste.

## Formato de saída: dict, não a linha de texto do EFD

O layout de texto do SPED (campos separados por `|`, decimal com vírgula, escapes
próprios, um registro por linha dentro de um bloco) é uma preocupação de serialização
separada de "quais valores vão em quais campos". `montar_e110`/`montar_e520` devolvem
um `dict` (campo → `Decimal`), não a linha pronta — resolver as duas coisas juntas
arriscaria acertar o valor e errar o formato, ou vice-versa, sem teste dedicado para
cada responsabilidade (mesma separação de `fiscal/documento/serializacao.py`: a árvore
de dados primeiro, o formato de texto depois, como camada própria).

## Ainda por implementar

- **Registro E530** (ajuste de apuração do IPI) — equivalente do E111 para IPI.
- **Registros E200/E210 (ICMS-ST) e E300/E310 (ICMS-DIFAL)** — apurações distintas de
  E110, não cobertas; DIFAL em particular já é gap deliberado desde `imposto_item.py`.
- **Serialização para o formato de texto do EFD** (pipe-delimited, decimal com
  vírgula) — ver seção acima.
- **Blocos 0, C, D, H, K, 1, 9** do EFD (identificação, documentos fiscais, inventário,
  totalizadores) — o arquivo completo tem muito mais que o bloco E de apuração; este
  incremento cobre só três registros de um bloco.
- **Tabela de códigos de ajuste por UF** — `Ajuste.codigo` vem pronto de quem chama;
  nenhuma das 27 tabelas estaduais (nem a federal de fallback) foi modelada aqui.

## Arquivos

- `contabil/efd_icms_ipi.py` — `Ajuste`, `montar_e110`, `montar_e111`, `montar_e520`;
  camada pura, sem Frappe, testável sem bench.

## Fontes

- Ajuste SINIEF 02/2009 (dispensa dos livros em papel) — confirmado em fontes
  secundárias consistentes (`sped.rfb.gov.br`, `sefaz.pe.gov.br`) — consultado em
  2026-08-30.
- Guia Prático EFD-ICMS/IPI, layout dos registros E110, E111 e E520 — fonte oficial
  (`sped.rfb.gov.br`) inacessível às ferramentas de busca no momento; confirmado em
  guia técnico especializado (`vriconsulting.com.br`) com descrição campo a campo,
  corroborado por busca cruzada — consultado em 2026-08-30.
