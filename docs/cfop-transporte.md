# CFOP de prestação de serviço de transporte (`ide.CFOP` do CT-e)

Fecha a lacuna deixada deliberadamente aberta em `docs/cte-icms-uf-fim.md`: o CFOP que vai no
grupo `ide` do CT-e (ver `docs/cte-estado.md`) não é o de mercadoria de `fiscal/cfop.py` — é uma
tabela paralela, indexada pelo **perfil de quem contrata o transporte**, não por
industrialização/comercialização.

## Nível de confiança, declarado — diferente do resto do projeto

O texto do Ajuste SINIEF que criou o grupo 5.35x/6.35x não foi localizado nesta investigação
(`confaz.fazenda.gov.br` devolveu 404 para a URL tentada). A tabela implementada foi verificada
cruzando **três fontes secundárias independentes que concordam integralmente**: Cosmos/Bluesoft,
Contadores.cnt.br e a base de conhecimento da Una Sistemas especificamente para emissão de CT-e
(a mais relevante das três, por ser documentação de domínio, não catálogo genérico). Registrado
aqui como nível de confiança mais baixo que o normal deste projeto — não escondido, para ser
revisado se/quando o texto oficial for localizado.

## O que foi implementado

`fiscal/cfop_transporte.py`:

- `cfop_prestacao_transporte(mesmo_estado, finalidade)` — oito perfis de tomador
  (`FINALIDADE_INDUSTRIAL`, `FINALIDADE_COMERCIAL`, `FINALIDADE_COMUNICACAO`,
  `FINALIDADE_ENERGIA`, `FINALIDADE_PRODUTOR_RURAL`, `FINALIDADE_NAO_CONTRIBUINTE`,
  `FINALIDADE_DISPENSADO_NF`, `FINALIDADE_SUBSTITUTO_TRIBUTARIO`) → `5352`–`5360`/`6352`–`6360`.
- `cfop_subcontratacao_transporte(mesmo_estado)` → `5351`/`6351` — redespacho entre
  transportadoras, código à parte por não caber no critério "perfil do tomador".

`CfopInvalido` é **reaproveitado** de `fiscal/cfop.py` (importado, não redefinido) — um só tipo
de exceção para erro de determinação de CFOP, seja de mercadoria ou de serviço. Testado
explicitamente (`test_reusa_a_mesma_excecao_de_fiscal_cfop`) para não virar duas exceções
parecidas por acidente numa refatoração futura.

## O que ficou de fora, documentado como decisão

- `5932`/`6932` — prestação iniciada em UF diversa daquela onde o prestador é inscrito
  (redespacho intermediário mais raro).
- Grupo `1.35x`/`2.35x` (entrada) — usado por quem **contrata** o transporte para registrar a
  aquisição do serviço na própria escrituração; não é o CFOP que o emitente do CT-e usa.
- CFOP de transporte internacional (`7.35x`) — não pesquisado.

## Arquivos

- `erpnext_brasil/fiscal/cfop_transporte.py`.
- `erpnext_brasil/tests/test_cfop_transporte.py` — 6 testes.

## Fontes

- `cosmos.bluesoft.com.br/tabelas/cfop/` (páginas 5350/5351/5352/5353/6351), consultado via
  busca em 2026-08-31.
- `contadores.cnt.br/cfop/` (mesmas páginas), consultado em 2026-08-31.
- `suporte.unasistemas.com.br/una-cte/codigos-cfop-para-prestacao-de-servico-de-transporte/`,
  consultado em 2026-08-31 — lista completa dos códigos 5352–5360/6352–6360/5932/6932, usada
  como a fonte mais próxima do domínio (CT-e) entre as três.
