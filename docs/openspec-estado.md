# Estado do OpenSpec — 2026-09-15

## Estrutura

- Root: `G:\PROJECTS\erpnext_brasil`
- Schema: `spec-driven`
- `openspec/specs/`: vazio (contém apenas `.gitkeep`)
- `openspec/changes/`: 3 changes ativos

## Decision: openspec/specs/ fica vazio até primeiro archive

`openspec/specs/` é o local de **capacidades duráveis** — specs que sobrevivem ao archive
de um change. Nenhum change foi archivado ainda, então o diretório fica vazio.

**Quando popular:** no archive do primeiro change (`emitir-nfce-do-pos` ou
`fechar-laco-cte-mdfe`). Cada capability declarada no `proposal.md` do change será
"synced" para `openspec/specs/<capability-path>/spec.md`.

**Por que não agora:** sincronizar specs de changes em andamento criaria specs parciais
que seriam atualizados a cada iteração — trabalho duplicado sem ganho.

## Changes ativos

| Change | Schema | Progresso | Specs |
|---|---|---|---|
| `fechar-laco-cte-mdfe` | spec-driven | 3/30 tasks | fiscal/cte-operacional, fiscal/mdfe-operacional |
| `emitir-nfce-do-pos` | spec-driven | 6/30 tasks | fiscal/nfce-pos, fiscal/contingencia-offline |
| `resolver-3-criticos` | spec-driven | 5/8 tasks | skip_specs: true |
| `resolver-media-criticity` | spec-driven | 0/8 tasks | skip_specs: true |

## Convenções

- Artefatos em pt-BR
- Títulos estruturais e SHALL/MUST em inglês
- Specs começam com `## Purpose` + `## ADDED Requirements`
- `skip_specs: true` para changes de docs/planejamento (sem delta de comportamento)
