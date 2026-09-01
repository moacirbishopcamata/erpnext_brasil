# MDF-e: grupo `infDoc` (documentos vinculados, por município de descarga)

Primeiro código do MDF-e depois do levantamento em `docs/mdfe-estado.md`. Escopo deliberadamente
estreito, mesmo padrão do primeiro incremento do CT-e: só a peça mais barata e mais próxima de
já estar pronta.

## Por que não é cópia direta de `montar_infnfe` do CT-e

`fiscal/cte.py::montar_infnfe` monta uma lista plana de chaves de NF-e. O `infDoc` do MDF-e
organiza as referências **por município de descarregamento** — confirmado no XSD
(`infDoc/infMunDescarga/{infCTe,infNFe}`), não suposto por analogia. Copiar a forma do CT-e sem
verificar teria produzido uma lista plana onde o layout exige agrupamento — o mesmo tipo de erro
que a verificação do `modal` (CT-e `"01"`–`"06"` × MDF-e `"1"`–`"4"`, ver `docs/mdfe-estado.md`)
já pegou antes de chegar a implementar.

## Reuso

`montar_infdoc` reusa `ler_chave` de `fiscal/documento/chave_acesso.py` — a mesma função de
`montar_infnfe`. O layout de 44 posições é idêntico entre NF-e, CT-e e MDF-e; a única diferença
real é o dígito de modelo, e por isso `chave_acesso.MODELOS` ganhou `"57"`/`"58"` neste
incremento (antes só tinha `"55"`/`"65"`) — nomes de exibição corretos para os quatro modelos
que este projeto agora manipula.

A validação de modelo (`infCTe` só aceita `57`, `infNFe` só aceita `55`) é a mesma defesa em
profundidade de `montar_infnfe`: sem ela, colar a chave errada no grupo errado só falharia na
rejeição da SEFAZ.

## O que ficou de fora

- `infMDFeTransp` (referência a outro MDF-e — sub-manifesto de transferência multimodal) — caso
  menos comum, não implementado.
- Campos opcionais raros de `infCTe`/`infNFe` (`SegCodBarra`, `indReentrega`, `infUnidTransp`,
  `peri` para produtos perigosos) — não investigados a fundo.

## Arquivos

- `erpnext_brasil/fiscal/mdfe.py` — `MunicipioDescarga`, `montar_infdoc`.
- `erpnext_brasil/tests/test_mdfe.py` — 6 testes.
- `erpnext_brasil/fiscal/documento/chave_acesso.py` — `MODELOS` ganhou `"57"`/`"58"`.

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd`, grupo
  `infDoc` (a partir da linha 331 do arquivo baixado em 2026-08-31). Ver `docs/mdfe-estado.md`
  para o histórico da investigação.
