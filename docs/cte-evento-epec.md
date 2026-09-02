# CT-e — EPEC (`tpEvento` 110113, `evEPECCTe`)

## O que é

EPEC (Evento Prévio de Emissão em Contingência) é o mecanismo de contingência do CT-e: quando o
emitente não consegue autorização de verdade da SEFAZ no momento da emissão, ele transmite um
**resumo** do documento como evento — carga tributária, tomador, modal, origem/destino — e emite o
CT-e em papel, regularizando depois. É estruturalmente análogo ao EPEC da NF-e, mas o corpo do
evento é específico do CT-e.

Fonte: `evEPECCTe_v4.00.xsd` (161 linhas, lido inteiro, via `curl` direto — não `WebFetch`).

## Estrutura confirmada

`descEvento`="EPEC", depois, nesta ordem: `xJust` (mesmo `TJust` do cancelamento, 15-255
caracteres), `vICMS`, `vICMSST` (opcional), `vTPrest` (pode ser zero — CT-e de complemento de
valores), `vCarga`, `toma4` (ver achado abaixo), `modal` (as mesmas seis opções de
`fiscal.cte.MODAL_*`), `UFIni`, `UFFim`, `tpCTe` e `dhEmi`.

## Achado real: o `toma4` do EPEC não é o `toma4` da `ide`

Mesmo nome de grupo, forma parecida, semântica diferente. O `toma4` real (`fiscal.cte.montar_toma4`
/ `TomadorOutros`) serve só para o papel "Outros" (`toma` fixo em `"4"`) e carrega `xNome`,
`enderToma`, `email`. O `toma4` do EPEC é uma versão resumida e genérica:

- `toma` aceita `"0"` a `"4"` — qualquer papel (remetente/expedidor/recebedor/destinatário/outros),
  não só "Outros".
- Só tem `toma`, `UF`, `CNPJ`|`CPF` (exclusivo) e `IE` (opcional) — sem nome, sem endereço, sem
  e-mail.

Reaproveitar `TomadorOutros`/`montar_toma4` exigiria inventar dados que o EPEC não pede, ou fixar
`papel="4"` quando o XSD permite qualquer um — por isso este incremento criou um tipo à parte,
`TomadorEpec`/`montar_tomador_epec`, em vez de forçar reuso por analogia de nome.

## Achado real: `tpCTe` do EPEC é fixo em `"0"` — não é o mesmo domínio do `ide/tpCTe`

O XSD restringe: `xs:length value="1"` combinado com uma única `xs:enumeration value="0"`. Só
aceita CT-e Normal. Isso diverge do `tpCTe` da `ide` (`fiscal.cte.IdentificacaoCte`), que aceita
`"0"` (Normal), `"1"` (Complemento) e `"3"` (Substituto) — CT-e de Complemento e Substituto não
podem ser emitidos via EPEC. Por isso `tpCTe` não é parâmetro de `montar_evento_epec_cte`: a
função sempre grava `TIPO_CTE_NORMAL` (reaproveitado de `fiscal.cte`, já existia e já era
exportado), fechando a porta para alguém tentar passar `"1"`/`"3"` por engano.

## Reuso

- `MODAL_RODOVIARIO`/`MODAL_AEREO`/`MODAL_AQUAVIARIO`/`MODAL_FERROVIARIO`/`MODAL_DUTOVIARIO`/
  `MODAL_MULTIMODAL` e `TIPO_CTE_NORMAL`, de `fiscal.cte` — já existiam, sem nenhuma mudança.
- `validar_cpf_cnpj` (não `validar_cnpj` sozinho, como o autor do evento usa) — porque o tomador do
  EPEC aceita CNPJ **ou** CPF, diferente do autor do evento (sempre CNPJ).
- `JUSTIFICATIVA_MINIMA_CTE`/`JUSTIFICATIVA_MAXIMA_CTE` (255, não 256 — mesmo achado do
  cancelamento) e `_formatar_id_cte` (`@Id` de 53 dígitos), sem alteração.

## Testes

25 testes novos (`TestTomadorEpec`, `TestMontarTomadorEpec`, `TestMontarEventoEpecCte`), incluindo:
os cinco papéis do `toma4` aceitos (diferente do `toma4` real), `tpCTe` sempre `"0"` mesmo não
sendo parâmetro, `vTPrest` podendo ser zero, `vICMSST` opcional, CNPJ/CPF exclusivo no tomador, e
um round-trip assinatura+serialização confirmando `<tpCTe>0</tpCTe>` e `<toma4>` no XML final.
