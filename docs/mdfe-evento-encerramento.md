# MDF-e — Evento de Encerramento (`tpEvento` 110112, `evEncMDFe`)

## O que é

Fecha a viagem do MDF-e — o momento em que o transportador confirma que a carga chegou ao
destino final e o manifesto não vale mais. Fonte: `evEncMDFe_v3.00.xsd` (59 linhas, lido
inteiro).

## Estrutura

`descEvento` fixo ("Encerramento"), `nProt`, `dtEnc` (`TData` — só data, sem hora, diferente
do `dhEvento` do `infEvento`, que é `TDateTimeUTC`), `cUF` (UF de encerramento), `cMun`
(código IBGE do município, `[0-9]{7}`) e `indEncPorTerceiro` (opcional, `"1"` — só quando quem
encerra é um transportador terceiro, diferente do emitente do MDF-e).

## Achado real: `cUF` aceita `"99"` para operações no Exterior

`cUF` usa o tipo `TCodUfIBGE_EX` — **não** o `TCodUfIBGE` simples usado em outros pontos do
MDF-e. A própria documentação do tipo diz "Tipo Código da UF da tabela do IBGE **+ 99 para
Exterior**" — confirmado na enumeração (as 27 UFs brasileiras mais `"99"`). Faz sentido: uma
viagem de MDF-e pode terminar fora do Brasil (ex. transporte Mercosul). Este módulo valida
`codigo_uf` contra essa lista estendida de 28 valores (`_UFS_VALIDAS_ENCERRAMENTO_MDFE`), não
contra uma tabela comum de 27 UFs.

## Reuso

`EventoInvalido`/`assinar_evento`/`_formatar_id_mdfe` de `evento_mdfe.py` — sem alteração,
mesmo padrão já usado pelo cancelamento.

## Testes

8 testes novos, incluindo a aceitação de `"99"` (Exterior) e a rejeição de UF fora da lista
estendida, a validação do código de município (7 dígitos), e o indicador de terceiro só
aparecendo quando explicitamente solicitado.
