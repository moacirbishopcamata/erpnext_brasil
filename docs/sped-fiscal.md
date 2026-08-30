# SPED Fiscal (EFD-ICMS/IPI): registro E110

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

## Registro E110 é um conversor, não uma nova apuração

O registro E110 ("Apuração do ICMS — Operações Próprias") traz exatamente o que
`contabil/apuracao_periodo.ApuracaoPeriodo` (para ICMS) já calcula: débito bruto,
crédito bruto, saldo credor anterior, saldo apurado, valor a recolher, saldo credor a
transportar. `contabil/efd_icms_ipi.montar_e110` só organiza esses seis valores no
formato de campo que o Fisco espera — a conta já foi feita em `apuracao_periodo.py`.

## Layout confirmado (ordem oficial do Guia Prático EFD-ICMS/IPI)

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

`sped.rfb.gov.br` (fonte oficial, o Guia Prático em si) ficou inacessível às ferramentas
de busca no momento da implementação — mesma limitação já registrada para outras fontes
governamentais neste projeto. A tabela acima foi confirmada num guia técnico
especializado (vriconsulting.com.br) com descrição campo a campo, corroborado por um
segundo agregador (busca cruzada) que reproduziu a mesma lista de nomes de campo na
mesma ordem.

## Escopo desta primeira versão: só o caso sem ajuste de apuração

Dos 13 campos de valor, só 6 correspondem ao que `ApuracaoPeriodo` calcula. Os outros 7
(`VL_AJ_DEBITOS`, `VL_TOT_AJ_DEBITOS`, `VL_ESTORNOS_CRED`, `VL_AJ_CREDITOS`,
`VL_TOT_AJ_CREDITOS`, `VL_ESTORNOS_DEB`, `VL_TOT_DED`) são **ajustes de apuração** —
cada um discriminado, no registro **E111** do mesmo bloco, contra uma tabela de códigos
própria (Tabela 5.3 do Guia Prático) que este app não modela ainda.

`montar_e110` zera os sete. Isso está **correto** para uma apuração sem nenhum ajuste
(nenhuma glosa, nenhum estorno, nenhuma dedução do período — o caso comum). **Não** está
correto para uma apuração que precise de ajuste real: usaria a função e produziria um
registro estruturalmente válido, mas que mentiria sobre o valor devido, silenciosamente.
Por isso não existe hoje nenhum ponto de entrada que decida sozinho "este período não
teve ajuste" e chame `montar_e110` — essa decisão continua sendo de quem chama, até o
registro E111 existir.

## Formato de saída: dict, não a linha de texto do EFD

O layout de texto do SPED (campos separados por `|`, decimal com vírgula, escapes
próprios, um registro por linha dentro de um bloco) é uma preocupação de serialização
separada de "quais valores vão em quais campos". `montar_e110` devolve um `dict`
(campo → `Decimal`), não a linha pronta — resolver as duas coisas juntas arriscaria
acertar o valor e errar o formato, ou vice-versa, sem teste dedicado para cada
responsabilidade (mesma separação de `fiscal/documento/serializacao.py`: a árvore de
dados primeiro, o formato de texto depois, como camada própria).

## Ainda por implementar

- **Registro E111** (discriminação de ajustes) — pré-requisito para `montar_e110`
  cobrir apuração com ajuste real.
- **Registro E200/E210** (apuração do IPI) — mesma ideia do E110, mas para IPI; layout
  ainda não levantado.
- **Serialização para o formato de texto do EFD** (pipe-delimited, decimal com
  vírgula) — ver seção acima.
- **Blocos 0, C, D, H, K, 1, 9** do EFD (identificação, documentos fiscais, inventário,
  totalizadores) — o arquivo completo tem muito mais que o bloco E de apuração; este
  incremento cobre só um registro de um bloco.

## Arquivos

- `contabil/efd_icms_ipi.py` — `montar_e110`; camada pura, sem Frappe, testável sem
  bench.

## Fontes

- Ajuste SINIEF 02/2009 (dispensa dos livros em papel) — confirmado em fontes
  secundárias consistentes (`sped.rfb.gov.br`, `sefaz.pe.gov.br`) — consultado em
  2026-08-30.
- Guia Prático EFD-ICMS/IPI, layout do registro E110 — fonte oficial
  (`sped.rfb.gov.br`) inacessível às ferramentas de busca no momento; confirmado em
  guia técnico especializado (`vriconsulting.com.br`) com descrição campo a campo,
  corroborado por busca cruzada — consultado em 2026-08-30.
