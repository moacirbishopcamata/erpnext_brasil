# CT-e — Prestação em Desacordo (`tpEvento` 610110) e seu Cancelamento (`tpEvento` 610111)

## Achado real: primeiro `tpEvento` fora da família `110xxx`

Todos os oito eventos anteriores desta frente (cancelamento, CC-e, comprovante de entrega,
EPEC, cancelamento do comprovante de entrega, insucesso na entrega, cancelamento do insucesso na
entrega, GTV) têm `tpEvento` no padrão `110xxx`. Estes dois são os primeiros no padrão
**`610xxx`** — `"610110"` e `"610111"`. Não muda nada na composição do `@Id` (ainda são 6
dígitos), mas é um lembrete direto de que não dá para supor a faixa de código de um evento pelo
padrão dos anteriores — cada tipo de evento do CT-e tem seu próprio código.

Fonte: `evPrestDesacordo_v4.00.xsd` (49 linhas, lido inteiro) e
`evCancPrestDesacordo_v4.00.xsd` (32 linhas, lido inteiro).

## `evPrestDesacordo` — o tomador reporta desacordo com a prestação

`descEvento` tem as duas grafias já vistas em `evGTV` (`"Prestação"`/`"Prestacao"`) — grava-se a
acentuada. `indDesacordoOper` é uma **enumeração de um único valor** (`"1"`) no XSD — mantido por
fidelidade ao schema, mesmo parecendo supérfluo (`INDICADOR_DESACORDO_OPERACAO`, não é parâmetro
da função, sempre gravado). `xObs` (observações do tomador) segue o mesmo intervalo 15-255 já
visto no cancelamento/EPEC (`TJust`-like, mas aqui é uma restrição inline, não um tipo nomeado).

## `evCancPrestDesacordo` — achado real: forma diferente dos cancelamentos anteriores

`evCancCECTe`/`evCancIECTe` carregam **dois** protocolos: `nProt` do CT-e e o protocolo do
evento cancelado. Este cancelamento carrega **só um**, `nProtEvPrestDes` — sem `nProt` do CT-e.
Por isso não reaproveita `_montar_evento_cancelamento_protocolo` (que exige os dois protocolos);
ganhou função própria, `montar_evento_cancelamento_prestacao_desacordo_cte`.

## Testes

11 testes novos, incluindo a confirmação de que `tpEvento` não começa com `"110"` (achado
real do prefixo diferente) e que o cancelamento não carrega `nProt` (achado real da forma
diferente).
