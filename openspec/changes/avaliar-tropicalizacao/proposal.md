## Why

A tropicalização do ERPNext tem progresso significativo (101 módulos de regra pura, 30 de integração, ~35.300 linhas), mas `docs/gaps.md` e `docs/estado-da-tropicalizacao.md` documentam lacunas que impedem uso real. Os documents estão parcialmente desatualizados e dispersos — não há uma visão consolidada do que falta, priorizado por impacto no negócio. Esta avaliação consolida o estado atual em um único documento de referência.

## What Changes

- Criar `docs/avaliacao-tropicalizacao.md` com inventário consolidado de todo o que falta para terminar a tropicalização, priorizado por impacto
- Atualizar `docs/gaps.md` se necessário para refletir números e estado atual
- Registrar decisões de priorização que não existem em nenhum document

## Capabilities

### New Capabilities

Nenhuma — esta é uma avaliação de documentação, não uma mudança de comportamento. O change usa `skip_specs: true`.

### Modified Capabilities

Nenhuma.

## Impact

- Afeta apenas `docs/` — nenhum código, API ou dependência extern
- Consolida informações de `gaps.md`, `estado-da-tropicalizacao.md`, `sped-fiscal.md`, `ecf-estado.md`, `rh-estado-esocial.md` e outros docs de estado
- Serviço de referência para priorização de changes futuros
