## Why

Bugs e gaps de média criticidade acumularam ao longo das iteracões. Alguns são de
planejamento (números defasados, tasks desmarcadas), outros de costura (módulos órfãos)
e outros de operação (funcionalidade ausente). Nenhum é silencioso nem bloqueante, mas
todos confundem quem implementa ou deixam funcionalidade parcial.

## What Changes

- **B2**: Marcar tasks 1.4 e 1.5 do change `fechar-laco-cte-mdfe` (docs escritos, tasks desmarcadas).
- **B3**: Decidir se `openspec/specs/` deve ser populado ou se fica vazio até primeiro archive.
- **B4**: Documentar o diff não commitado do `emitir-nfce-do-pos` como trabalho em andamento.
- **B5**: Atualizar `docs/gaps.md` com números corretos de cobertura de bench.
- **G1**: Conectar `cte_extracao` ao MDF-e (change `fechar-laco-cte-mdfe` já prevê isso).
- **G2-G4**: Documentar que ecf_dados_empresa, efd_dados_cadastrais e conta_bancaria dependem de módulos futuros.
- **G5**: Registrar que transferência entre estabelecimentos depende de decisão de modelagem.
- **G6**: Listar estorno EFD em `sped-fiscal.md` como pendente.
- **G7**: Documentar que quebra tolerada depende de fonte única.
- **G12**: Registrar que NFC-e do POS depende do change `emitir-nfce-do-pos`.

## Capabilities

### New Capabilities
<!-- Nenhuma: o change corrige documentação/planejamento, não comportamento. -->

### Modified Capabilities
<!-- Nenhuma: o change não altera requisitos de specs. -->

## Impact

- **Arquivos afetados**: `docs/gaps.md` (B5, G1-G7, G12), `tasks.md` do `fechar-laco-cte-mdfe` (B2),
  `openspec/changes/emitir-nfce-do-pos/tasks.md` (B4).
- **Risco**: baixo — são correções de documentação e planejamento.
