# CT-e — Insucesso na Entrega (`tpEvento` 110190, `evIECTe`)

## O que é

Quase gêmeo do comprovante de entrega (`evCECTe`, `tpEvento` 110180): em vez de confirmar que a
carga chegou, registra que uma **tentativa** de entrega falhou. Fonte: `evIECTe_v4.00.xsd` (126
linhas, lido inteiro).

## Estrutura

`descEvento` fixo ("Insucesso na Entrega do CT-e"), `nProt`, `dhTentativaEntrega`
(obrigatório), `nTentativa` (opcional, `[0-9]{3}` — número da tentativa que falhou), `tpMotivo`
(enum "1"-"4": recebedor não encontrado / recusa do recebedor / endereço inexistente / outros),
`xJustMotivo` (obrigatório **só** quando `tpMotivo="4"`, proibido nos demais — regra de negócio
do próprio texto do XSD, não decorrente do `minOccurs` sozinho, que é opcional em qualquer caso),
`latitude`/`longitude` opcionais (mesmo formato string de 6 casas do comprovante de entrega),
`hashTentativaEntrega`/`dhHashTentativaEntrega` (opcionais), `infEntrega` (mesma forma do
comprovante de entrega — lista de `chNFe`, até 2000, só para CT-e Normal).

## Achado real 1: `xJustMotivo` usa `TString` (15-256), não `TJust` (15-255)

O cancelamento e o EPEC deste mesmo documento usam `TJust` para seus textos livres — limite
máximo **255** caracteres (`JUSTIFICATIVA_MAXIMA_CTE`). `xJustMotivo` do `evIECTe` usa um tipo
diferente, `TString`, cujo limite máximo é **256** — igual ao da NF-e, não ao do próprio CT-e.
Reaproveitar a constante do cancelamento teria rejeitado, por engano, um texto de 256 caracteres
que o XSD aceita. Por isso este evento define sua própria constante,
`XJUSTMOTIVO_MAXIMO_IE_CTE = 256`, em vez de reusar `JUSTIFICATIVA_MAXIMA_CTE`.

## Achado real 2: o hash é opcional aqui, obrigatório no comprovante de entrega

`hashEntrega` (no `evCECTe`) é obrigatório — faz sentido, é a prova de que a entrega aconteceu.
`hashTentativaEntrega` (aqui) é opcional (`minOccurs="0"`) — uma tentativa malsucedida pode não
ter conseguido capturar nenhuma imagem do local (recebedor não encontrado, endereço
inexistente). O cálculo, quando informado, é o mesmo SHA-1+Base64 de `calcular_hash_entrega` —
reaproveitado sem alteração nenhuma (só muda o nome do campo no XML final, não o algoritmo).

## Reuso: `_montar_inf_entrega_nfe` extraído

Antes deste incremento, a validação de `infEntrega` (até 2000 chaves, só NF-e modelo 55) estava
inline dentro de `montar_evento_comprovante_entrega_cte`. Como `evIECTe` precisa exatamente da
mesma lógica, foi extraída para `_montar_inf_entrega_nfe`, reaproveitada pelos dois eventos —
evita duplicar a mesma regra de negócio (SRP: a regra de "o que é um `infEntrega` válido" mora
num lugar só).

## Testes

12 testes novos, incluindo: `xJustMotivo` obrigatório só para `tpMotivo="4"` e proibido nos
demais, o limite de 256 (não 255) confirmado, hash calculado só quando a imagem é informada,
`nTentativa` formatado com 3 dígitos, e reuso confirmado da validação de `infEntrega`.
