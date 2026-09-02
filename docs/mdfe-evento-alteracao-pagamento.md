# MDF-e — Evento de Alteração do Pagamento do Serviço (`tpEvento` 110118, `evAlteracaoPagtoServMDFe`)

## O que é

Corrige/atualiza informações de pagamento já registradas — último dos sete eventos do
MDF-e desta frente. Fonte: `evAlteracaoPagtoServMDFe_v3.00.xsd` (257 linhas, lido inteiro).

## Achado real: reuso direto, confirmado, do `infPag` do pagamento da operação

O `infPag` deste evento é **estruturalmente idêntico**, campo a campo, ao `infPag` do
`evPagtoOperMDFe` (ver `docs/mdfe-evento-pagamento-operacao.md`) — confirmado por leitura
direta dos dois XSDs, não suposto por analogia. A única diferença de forma entre os dois
eventos é que este **não tem** `infViagens` (faz sentido: alterar o pagamento de uma
operação já registrada não precisa repetir a contagem de viagens).

Por isso `ComponentePagamento`/`InfoBancaria`/`InfoPagamento` e as funções
`montar_componente_pagamento`/`montar_inf_banc`/`montar_inf_pag` — todas em
`fiscal/documento/evento_mdfe.py` — são compartilhadas entre os dois eventos. Só a
montagem do `evento` em si muda: `tpEvento`/`descEvento` diferentes, e a ausência de
`infViagens`.

## Testes

5 testes novos, incluindo a confirmação de que `infViagens` está ausente (diferente do
pagamento da operação) e que `infPag` reaproveita a mesma validação/forma.
