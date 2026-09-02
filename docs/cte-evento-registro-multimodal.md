# CT-e — Registro Multimodal (`tpEvento` 110160, `evRegMultimodal`)

## O último dos onze eventos do CT-e v4.00

Fonte: `evRegMultimodal_v4.00.xsd` (51 linhas, lido inteiro). Com este, os onze eventos
listados em `schemes/PL_CTe_400` do `nfephp-org/sped-cte` estão todos implementados.

## Achado real: volta ao padrão `110xxx`

O evento anterior (prestação em desacordo) foi o primeiro fora do padrão `110xxx`
(`610110`/`610111`). Este volta ao padrão — `"110160"` — confirmando de novo que não dá
para prever o código de um evento pelo padrão do vizinho na mesma frente: cada evento tem seu
próprio código, sem relação sequencial garantida.

## Estrutura

`descEvento` tem **uma única** grafia válida ("Registro Multimodal") — diferente de `evGTV`/
`evPrestDesacordo`, que aceitavam duas (acentuada/sem acento). `xRegistro` (texto livre sobre o
registro no multimodal) vai até **1000** caracteres — o maior limite de texto livre entre os
eventos do CT-e nesta frente (os demais ficam em 255/256). `nDoc` (opcional) é o "número do
documento lançado no CT-e Multimodal".

## Achado real: `nDoc` não é uma chave de acesso, apesar do comprimento coincidir

`nDoc` tem 1-44 dígitos — o mesmo comprimento de uma chave de acesso (`chNFe`/`chCTe`, sempre
44 posições). Mas o XSD tipa como `[0-9]{1,44}` solto (`xs:pattern`), **não** como `TChDFe` (o
tipo usado em todo lugar que é de fato uma chave, com dígito verificador e estrutura
decomponível). Este módulo não trata `nDoc` como chave — não chama `ler_chave`/`validar_chave`
nele — só confere que é uma string numérica de até 44 dígitos, fiel ao que o schema realmente
pede, sem inventar uma validação mais forte que o próprio schema não exige.

## Testes

10 testes novos, incluindo a confirmação de que `tpEvento` volta ao padrão `110xxx`, que
`nDoc` aceita qualquer numérico de até 44 dígitos (mas rejeita não-numérico) sem validação de
chave de acesso, e o limite de 1000 caracteres de `xRegistro`.
