# MDF-e — Evento de Inclusão de DF-e (`tpEvento` 110115, `evIncDFeMDFe`)

## O que é

Acrescenta uma NF-e ao manifesto já autorizado (ex.: uma nota que ficou de fora na
emissão original). Fonte: `evInclusaoDFeMDFe_v3.00.xsd` (81 linhas, lido inteiro).

## Achado real: nome do arquivo diverge do nome do elemento raiz

O arquivo se chama `evInclusaoDFeMDFe_v3.00.xsd`, mas o elemento que ele declara é
`evIncDFeMDFe` — nomes diferentes. Mesma classe de achado já registrada antes neste
projeto (`cteTiposBasico_v4.00.xsd` do CT-e também não refletia seu conteúdo pelo nome).
Reforça a disciplina de sempre ler o conteúdo do XSD, nunca confiar no nome do arquivo.

## Estrutura

`descEvento` com as duas grafias já vistas em outros eventos (`"Inclusão DF-e"`/
`"Inclusao DF-e"`); `cMunCarrega`/`xMunCarrega` (município de carregamento, um só, fora da
lista); `infDoc` (lista, `maxOccurs="unbounded"`) — cada item tem `cMunDescarga`/
`xMunDescarga` (um município de descarregamento) e **um único** `chNFe`.

## Achado real: este evento só aceita NF-e, nunca CT-e

Diferente do `infDoc` da orquestração principal do MDF-e (`fiscal.mdfe.montar_infdoc`, que
agrupa `infCTe`/`infNFe` dentro de cada município), o `infDoc` deste evento tem só `chNFe`
(tipo `TChNFe`) — nenhum campo equivalente para CT-e. `chNFe` é validado com `ler_chave`,
recusando qualquer chave que não seja modelo 55 — mesma defesa em profundidade já aplicada
em `fiscal.cte.montar_infnfe` e em `_montar_inf_entrega_nfe` do CT-e.

## Testes

7 testes novos, incluindo a rejeição de uma chave de MDF-e/CT-e passada como se fosse
NF-e, e a validação de que `infDoc` precisa de ao menos um documento.
