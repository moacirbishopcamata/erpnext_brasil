## Context

Bugs e gaps de média criticidade identificados na varredura de 2026-09-15. Alguns são
de planejamento (docs desatualizados), outros de costura (módulos sem chamador) e
outros de operação (funcionalidade ausente). Nenhum é silencioso nem bloqueante.

## Goals / Non-Goals

**Goals:**

- Atualizar documentação com números corretos.
- Marcar tasks completadas mas desmarcadas.
- Documentar dependências de módulos futuros.
- Registrar gaps de operação como pendentes declarados.

**Non-Goals:**

- Não implementar funcionalidade nova (G5, G6, G7, G12 dependem de changes futuros).
- Não conectar módulos órfãos (G1 depende do change `fechar-laco-cte-mdfe`).
- Não alterar specs ou comportamento.

## Decisions

### 1. B2: Tasks 1.4 e 1.5 marcadas

`docs/mdfe-estado.md` já tem a seção de levantamento dos campos de Shipment (tarefa 1.4).
`docs/cte-estado.md` já tem a seção de serviços por família (tarefa 1.1). Ambas as tasks
devem ser marcadas `[x]` no `tasks.md` do `fechar-laco-cte-mdfe`.

### 2. B3: openspec/specs/ fica vazio

Nenhum change foi archivado ainda. Specs ficam em `changes/<name>/specs/` até o primeiro
archive. Não popular `openspec/specs/` agora — decidir no archive do primeiro change.

### 3. B4: Diff do emitir-nfce documentado

O diff em `setup/custom_fields.py` e `tests/test_costura_campos_e_hooks.py` é trabalho
em andamento do change `emitir-nfce-do-pos`. Registrar no `tasks.md` desse change que
o diff existe e não deve ser commitado até a tarefa correspondente.

### 4. B5: Números atualizados em gaps.md

A cobertura de bench cresceu (perda_estoque, sobra_inventario, party, party_bench,
consumo_indevido). Atualizar "28 de 31" para o número correto.

### 5. G1-G4: Módulos órfãos documentados

`cte_extracao`, `ecf_dados_empresa`, `efd_dados_cadastrais` e `conta_bancaria` dependem
de módulos futuros. Registrar em `docs/gaps.md` como pendentes declarados.

### 6. G5-G7, G12: Gaps de operação documentados

Transferência, estorno EFD, quebra tolerada e NFC-e do POS dependem de decisions
futuras. Registrar em `docs/gaps.md` como pendentes declarados.
