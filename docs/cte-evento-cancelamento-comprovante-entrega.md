# CT-e — Cancelamento do Comprovante de Entrega (`tpEvento` 110181, `evCancCECTe`)

## Achado real: "CE" é Comprovante de Entrega, não Carta de Correção

O nome do arquivo (`evCancCECTe_v4.00.xsd`) sugere, por analogia solta com `evCancCTe`
(cancelamento do CT-e) e `evCCeCTe` (carta de correção), que seria o "cancelamento da carta de
correção". **Não é.** O próprio texto do XSD (`xs:documentation`) descreve o evento como:

> "Schema XML de validação do evento cancelamento do comprovante de entrega eletrônico do CT-e
> 110181"

A sigla `CE` aqui é **Comprovante de Entrega** — o evento `evCECTe` (`tpEvento` 110180,
implementado anteriormente nesta mesma frente), não a Carta de Correção (que tem sigla própria,
`CCe`, sem ambiguidade — `evCCeCTe`). Mais um exemplo, na mesma frente, de que nome de arquivo
por analogia não é fonte confiável — só a leitura do conteúdo confirma.

Fonte: `evCancCECTe_v4.00.xsd` (36 linhas, lido inteiro).

## Estrutura

Simples: `descEvento` (string fixa, "Cancelamento do Comprovante de Entrega do CT-e"), `nProt`
(protocolo de autorização do próprio CT-e, tipo `TProt`) e `nProtCE` (protocolo do evento de
comprovante de entrega que está sendo cancelado, também `TProt`) — dois protocolos distintos, não
o mesmo valor repetido: um autoriza o CT-e, o outro autorizou o evento de entrega que agora está
sendo desfeito.

## Implementação

`montar_evento_cancelamento_comprovante_entrega_cte(chave_acesso, protocolo,
protocolo_comprovante_entrega, cnpj_autor, data_evento, numero_sequencia=1, ambiente="2")` —
mesma costura dos demais eventos do CT-e (`_formatar_id_cte`, `@Id` de 53 dígitos, `EventoInvalido`
para ambos os protocolos vazios). Nenhum campo novo reaproveitado além do que já existia
(`validar_chave`/`ler_chave`/`validar_cnpj`).

## Testes

6 testes novos, incluindo a confirmação de que `tpEvento` é `"110181"` (não `"110110"`, o da
CC-e) e que os dois protocolos (`nProt`/`nProtCE`) chegam distintos no XML final.
