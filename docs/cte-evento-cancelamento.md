# CT-e: evento de cancelamento (`evCancCTe`, `tpEvento` 110111)

Fecha mais uma peça de infraestrutura do CT-e — o evento mais universalmente necessário
(cancelar um documento emitido por engano), mesmo espírito de `fiscal/documento/evento.py`
para a NF-e.

## `tpEvento` e `detEvento` são idênticos à NF-e — confirmado, não copiado às cegas

O código `"110111"` e o corpo de `detEvento` (`descEvento`="Cancelamento", `nProt`, `xJust`)
batem exatamente com os da NF-e. Mas dois pontos genuinamente divergem — achados reais, cada
um verificado por leitura direta do XSD antes de assumir qualquer coisa por analogia (mesma
disciplina que já pegou divergências entre CT-e/MDF-e no `modal`, `procEmi`, `ideEvento`):

## Achado 1: limite da justificativa é 255, não 256

`TJust` do CT-e é `minLength=15, maxLength=255`. A NF-e usa `256`
(`evento.estado.JUSTIFICATIVA_MAXIMA`). Reaproveitar a constante da NF-e teria deixado passar
uma justificativa de exatamente 256 caracteres que a SEFAZ rejeitaria. `JUSTIFICATIVA_MAXIMA_CTE`
é uma constante nova, testada nos dois limites (255 válido, 256 inválido).

## Achado 2: a versão do evento mora em lugar diferente

A NF-e tem um elemento `verEvento` dentro de `infEvento`, fixo em `"1.00"` — numeração de
evento independente da versão do próprio leiaute da NF-e. O CT-e **não tem** esse elemento; a
versão vive só como atributo `detEvento/@versaoEvento` e, no nível do `evento` inteiro,
`@versao` (tipo `TVerEvento`, valor fixo confirmado `"4.00"`) — a mesma versão do leiaute do
CT-e, não uma numeração de evento à parte.

## Achado 3: `@Id` tem 53 dígitos, não 52 — `nSeqEvento` com 3 dígitos, não 2

O padrão confirmado é `ID[0-9]{53}` (contra `ID[0-9]{52}` da NF-e). A composição é a mesma
(`"ID" + tpEvento(6) + chave(44) + nSeqEvento`), mas `nSeqEvento` dentro do `@Id` do CT-e usa 3
dígitos com zero à esquerda (`"001"`), não 2 (`"01"`) — a diferença de um dígito no padrão bate
exatamente com essa mudança de largura.

## Reuso: `assinar_evento` e `EventoInvalido` da NF-e, sem alteração

`assinar_evento` já era genérica (nunca hardcodava `NAMESPACE_NFE`, só lê o que o dicionário
`evento` já tem) — reaproveitada direto, testado que assina o `@Id` certo e produz XML válido
com `chCTe`. `EventoInvalido` também reaproveitada — mensagem + campo, nenhuma lógica
específica de NF-e embutida.

## Arquivos

- `erpnext_brasil/fiscal/documento/evento_cte.py` — `montar_evento_cancelamento_cte`,
  `montar_env_evento_cte`, `JUSTIFICATIVA_MINIMA_CTE`/`JUSTIFICATIVA_MAXIMA_CTE`.
- `erpnext_brasil/tests/test_evento_cte.py` — 14 testes.

## O que ficou de fora

- Carta de correção do CT-e (CC-e) — a NF-e tem `evCCeNFe`; o CT-e tem `evCCeCTe.xsd` (visto
  na listagem do repositório em `docs/cte-estado.md`), ainda não lido.
- Outros eventos específicos do CT-e sem equivalente na NF-e: encerramento, registro de
  passagem, prestação em desacordo, EPEC — nenhum investigado ainda.

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/evCancCTe_v4.00.xsd` (36 linhas,
  lido inteiro) e `eventoCTeTiposBasico_v4.00.xsd` (`TEvento`, `TVerEvento`) e
  `tiposGeralCTe_v4.00.xsd` (`TJust`) — arquivos baixados e lidos localmente em 2026-08-31.
