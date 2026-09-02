# MDF-e — Evento de Confirmação do Serviço (`tpEvento` 110117, `evConfirmaServMDFe`)

## O que é

O evento mais simples desta frente: confirma o serviço de transporte. Fonte:
`evConfirmaServMDFe_v3.00.xsd` (34 linhas, lido inteiro).

## Estrutura

`descEvento` (as duas grafias já vistas em outros eventos) e só `nProt` — nenhum outro
campo.

## Achado real: a numeração não é contígua nem segue a ordem alfabética dos arquivos

`tpEvento` é `"110117"`, não `"110116"` — esse número pertence ao evento de pagamento da
operação (`evPagtoOperMDFe`, ver `docs/mdfe-evento-pagamento-operacao.md`), que vem depois
na ordem alfabética do nome do arquivo mas tem código numérico **menor**. Mais um lembrete
de não presumir sequência de código a partir do nome ou da posição na listagem do
diretório.

## Testes

3 testes novos, incluindo a confirmação de que `detEvento` só tem `@versaoEvento`/
`descEvento`/`nProt` — nenhum campo a mais.
