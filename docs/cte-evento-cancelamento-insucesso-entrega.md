# CT-e — Cancelamento do Insucesso na Entrega (`tpEvento` 110191, `evCancIECTe`)

## Estrutura confirmada idêntica ao cancelamento do comprovante de entrega

`evCancIECTe_v4.00.xsd` (36 linhas, lido inteiro) tem exatamente a mesma forma de
`evCancCECTe_v4.00.xsd` (ver `docs/cte-evento-cancelamento-comprovante-entrega.md`): `descEvento`
fixo (texto diferente — "Cancelamento do Insucesso de Entrega do CT-e"), `nProt` (protocolo do
CT-e) e um segundo campo de protocolo (`nProtIE` aqui, `nProtCE` no outro) referenciando o evento
que está sendo cancelado — no caso, o insucesso na entrega (`evIECTe`, `tpEvento` 110190).

## Reuso: `_montar_evento_cancelamento_protocolo`

Diferente do EPEC (onde `TomadorEpec` foi deliberadamente criado como tipo à parte por o `toma4`
ter semântica genuinamente diferente), aqui os dois XSDs são **idênticos** na forma — só o nome
do campo do segundo protocolo e o texto de `descEvento` mudam. É um caso real (não especulativo)
de duplicação: a segunda instância confirmou que a primeira não era coincidência. Por isso
`montar_evento_cancelamento_comprovante_entrega_cte` foi refatorada para delegar a uma função
privada, `_montar_evento_cancelamento_protocolo(chave_acesso, protocolo,
protocolo_evento_cancelado, campo_protocolo_evento, desc_evento, tipo_evento, ...)`, e
`montar_evento_cancelamento_insucesso_entrega_cte` é a nova função pública que chama a mesma
privada com `campo_protocolo_evento="nProtIE"` e o `tpEvento`/`descEvento` corretos.

## Testes

5 testes novos, incluindo a confirmação de que o campo é `nProtIE` (não `nProtCE`) e que
`tpEvento` é `"110191"` (não `"110181"`, o do cancelamento do comprovante de entrega).
