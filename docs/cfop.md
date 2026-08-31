# CFOP: determinação, não só validação de formato

Até este incremento, `fiscal/documento/produto.py` recebia o CFOP como string
pronta — validado só por formato (4 dígitos), nunca calculado. A tabela completa
(~600 códigos) já tinha infraestrutura de importação genérica
(`integracao/importar_codigos.py`, reaproveitando `Code List`/`Common Code` do
próprio Frappe) — o que faltava era a regra de **qual** código usar.

## A estrutura do código

Quatro dígitos: o **primeiro** indica direção e âmbito —
`1`/`2`/`3` = entrada (mesmo estado / outro estado / exterior),
`5`/`6`/`7` = saída (mesmo estado / outro estado / exterior). Os **três últimos**
detalham a natureza específica, e mantêm o mesmo significado trocando só o primeiro
dígito conforme o âmbito — confirmado cruzando várias fontes concordantes para os
pares `1101`/`2101`, `5101`/`6101`, `1202`/`2202`, não suposto por padrão isolado.

## Escopo: dezesseis códigos, o núcleo mais comum

| Operação | Mesmo estado | Outro estado | Finalidade |
|---|---|---|---|
| Compra | `1101` | `2101` | industrialização/produção rural |
| Compra | `1102` | `2102` | comercialização |
| Venda | `5101` | `6101` | produção própria |
| Venda | `5102` | `6102` | mercadoria de terceiros |
| Devolução de venda | `1201` | `2201` | produção própria devolvida pelo cliente |
| Devolução de venda | `1202` | `2202` | mercadoria de terceiros devolvida pelo cliente |
| Devolução de compra | `5201` | `6201` | industrialização, devolvida ao fornecedor |
| Devolução de compra | `5202` | `6202` | comercialização, devolvida ao fornecedor |

**Fora do escopo, e não finja que está coberto**: operação com o exterior (`3`/`7`),
transferência entre estabelecimentos, remessa/retorno de industrialização por conta
de terceiros, bonificação/doação/brinde, consignação, ativo imobilizado/uso e
consumo, substituição tributária, prestação de serviço de transporte. `determinar_cfop`
levanta erro explícito para qualquer combinação não coberta.

## Devolução não é o espelho direto de direção — só de finalidade

Um erro fácil de cometer: pensar que "devolução de venda" usa o mesmo primeiro
dígito da venda original. Não usa — a venda é **saída** (`5`/`6`), a devolução dela
é **entrada** (`1`/`2`, o cliente devolve para nós). O que se mantém é só a
correspondência mesmo-estado↔mesmo-estado (`5`→`1`, `6`→`2`) e os dois últimos
dígitos (a finalidade). Um teste (`test_devolucao_de_venda_espelha_venda`) provou
isso o jeito difícil — a primeira versão do teste assumia primeiro dígito igual e
falhou, corrigida antes do commit.

## Este módulo não decide industrialização × comercialização, nem mesmo/outro estado

Essas decisões dependem de dado que o módulo não tem (a UF do fornecedor/cliente, a
que a mercadoria se destina) — mesma disciplina de `imposto_item.py` não inferir
natureza de operação a partir de dado incompleto. Quem chama informa
`mesmo_estado`/`finalidade` já decididos.

## Arquivos

- `fiscal/cfop.py` — `cfop_compra`, `cfop_venda`, `cfop_devolucao_venda`,
  `cfop_devolucao_compra`; camada pura, sem Frappe, testável sem bench.

## Fontes

- Busca agregada, cruzando múltiplas fontes concordantes para cada par de código
  (não uma fonte isolada por código) — nenhuma leitura direta do Convênio SINIEF
  s/nº de 15/12/1970 (texto original) nem do Ajuste SINIEF que consolidou a tabela
  vigente nesta rodada. Consultado em 2026-08-31.
