# MDF-e — Evento de Cancelamento (`tpEvento` 110111, `evCancMDFe`)

## O que é

Primeira peça da frente de eventos do MDF-e, aberta depois que os onze eventos do CT-e foram
concluídos (ver `docs/cte-estado.md`). Fonte: `evCancMDFe_v3.00.xsd` (38 linhas, lido inteiro)
e `eventoMDFeTiposBasico_v3.00.xsd` (300 linhas, lido inteiro), ambos de
`nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b`.

## `TEvento` do MDF-e converge com o CT-e, diverge da NF-e

`infEvento`: `cOrgao`, `tpAmb`, `(CNPJ|CPF)`, `chMDFe`, `dhEvento`, `tpEvento`, `nSeqEvento`,
`detEvento` (com `@versaoEvento` como **atributo**, não elemento `verEvento`). No nível do
`evento` inteiro, `@versao` fixo em `"3.00"`. Isso é idêntico à forma do CT-e (que também usa
`@versaoEvento` em `detEvento`, sem elemento `verEvento` próprio) e diferente da NF-e (que tem
`verEvento` como elemento, fixo em `"1.00"`, independente da versão do leiaute).

## Achado real: `tpEvento` do cancelamento é o mesmo número em NF-e, CT-e e MDF-e

`"110111"` — confirmado, não coincidência aparente: os três documentos reaproveitam a mesma
faixa de código para cancelamento, mesmo cada um tendo XSD próprio e (como a frente do CT-e
mostrou) outros eventos com códigos exclusivos por documento.

## `TJust` do MDF-e é 15-255 — verificado à parte, não suposto igual ao do CT-e

Numericamente idêntico ao `TJust` do CT-e, mas são tipos diferentes de schemas diferentes —
confirmado por leitura direta de `tiposGeralMDFe_v3.00.xsd`, não presumido pela "mesma família
de documentos" (a lição que motivou verificar cada documento individualmente desde o início
desta frente inteira). Por isso `JUSTIFICATIVA_MINIMA_MDFE`/`JUSTIFICATIVA_MAXIMA_MDFE` são
constantes próprias, não um import das constantes do CT-e.

## Achado real: `@Id` — a mesma composição do CT-e, mas o schema tolera duas larguras

O padrão confirmado é `ID[0-9]{12}[A-Z0-9]{12}[0-9]{28}|ID[0-9]{12}[A-Z0-9]{12}[0-9]{29}`. À
primeira vista parece divergir da regra documentada ("ID + tpEvento + chave + nSeqEvento"), mas
bate exatamente ao decompor: `TChMDFe` (a chave) já é `[0-9]{6}[A-Z0-9]{12}[0-9]{26}` — suporte
ao CNPJ alfanumérico, mesmo tratamento já implementado em `fiscal/documento/chave_acesso.py`.
Somando os 6 dígitos do `tpEvento` aos 6 primeiros da chave dá os `[0-9]{12}` do início; o
`[A-Z0-9]{12}` do meio é a raiz alfanumérica do CNPJ dentro da própria chave; o
`[0-9]{28}`/`[0-9]{29}` final é o resto da chave (26 dígitos) mais `nSeqEvento` — que pode ter
**2 ou 3 dígitos** (52 ou 53 de comprimento total). Diferente do CT-e (onde só 3 dígitos é
válido no XSD), o MDF-e tolera as duas larguras — este módulo grava sempre com 3, a mesma
convenção já usada para o CT-e.

## Reuso

`EventoInvalido`/`assinar_evento` de `fiscal.documento.evento` — ambos já genéricos, sem
alteração, mesmo padrão do reuso já feito para o CT-e.

## Testes

13 testes novos, incluindo a confirmação de que `chMDFe` é o campo correto (não `chNFe`/
`chCTe`), que `tpEvento` é o mesmo `"110111"` de NF-e/CT-e, e o round-trip
assinatura+serialização.
