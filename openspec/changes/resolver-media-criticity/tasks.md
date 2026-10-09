## 1. B2: Marcar tasks 1.4 e 1.5 do fechar-laco-cte-mdfe

- [x] 1.1 Marcar `[x]` na task 1.4 de `openspec/changes/fechar-laco-cte-mdfe/tasks.md`
      (docs de Shipment já escritos)
- [x] 1.2 Marcar `[x]` na task 1.5 de `openspec/changes/fechar-laco-cte-mdfe/tasks.md`
      (verificação de tipo do Transmissao Fiscal já feita)

## 2. B3: Decisão sobre openspec/specs/

- [x] 2.1 Registrar em `docs/openspec-estado.md` que `openspec/specs/` fica vazio até
      o primeiro archive — decidir no archive do change `emitir-nfce-do-pos`

## 3. B4: Documentar diff do emitir-nfce

- [x] 3.1 Adicionar nota em `openspec/changes/emitir-nfce-do-pos/tasks.md` sobre o diff
      não commitado em `setup/custom_fields.py` e `tests/test_costura_campos_e_hooks.py`

## 4. B5: Atualizar gaps.md

- [x] 4.1 Atualizar a seção 2 de `docs/gaps.md` com o número correto de módulos sem
      bench (cobertura cresceu)
- [x] 4.2 Atualizar a seção 1.4 de `docs/gaps.md` com o estado atual dos módulos órfãos

## 5. G1-G4: Documentar módulos órfãos

- [x] 5.1 Atualizar `docs/gaps.md` seção 1.4 com: cte_extracao será desorfanado pelo
      change fechar-laco-cte-mdfe; ecf_dados_empresa e efd_dados_cadastrais dependem de
      geradores futuros; conta_bancaria depende de módulo de boleto

## 6. G5-G7, G12: Documentar gaps de operação

- [x] 6.1 Atualizar `docs/gaps.md` seção 5 com: transferência entre estabelecimentos
      depende de decisão de modelagem; estorno EFD listado em sped-fiscal.md; quebra
      tolerada depende de fonte única; NFC-e do POS depende do change emitir-nfce-do-pos
