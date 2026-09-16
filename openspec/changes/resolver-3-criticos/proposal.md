## Why

Três bugs críticos foram encontrados na varredura de 2026-09-15. Dois são silenciosos
(documento de referência contradiz o design; numeração não alocada mas campo existe) e um
é de validação (a cadeia de emissão da NF-e nunca rodou contra a SEFAZ real). Todos
comprometem a produção: o primeiro engana quem implementa, o segundo gera rejeição em
concorrência, o terceiro pode ter toda a assinatura/ envelope errado sem ninguém saber.

## What Changes

- **B1**: Corrigir `proposal.md` do change `fechar-laco-cte-mdfe` — alinhar a descrição
  dos serviços de autorização com a decisão 3 do `design.md` (CT-e síncrono, MDF-e lote+recibo).
- **G8**: Implementar alocação de numeração sequencial por série antes da transmissão —
  `numero_do_documento(doc, modelo, serie)` já existe mas não é chamado; dois usuários
  emitindo ao mesmo tempo produziriam número repetido.
- **G9**: Validar a cadeia de emissão da NF-e contra a SEFAZ de homologação com certificado
  A1 real — a assinatura, o envelope e a chave de acesso nunca foram testados fora de mock.

## Capabilities

### New Capabilities
<!-- Nenhuma: o change corrige bugs, não adiciona comportamento novo. -->

### Modified Capabilities
<!-- Nenhuma: o change não altera requisitos de specs. -->

## Impact

- **Arquivos afetados**: `openspec/changes/fechar-laco-cte-mdfe/proposal.md` (B1),
  `integracao/emissao_nfe.py` (G8), `tests/test_emissao_nfe.py` (G8), possivelmente
  `integracao/numeros_fiscais.py` (G8).
- **Infraestrutura**: G9 exige certificado A1 real e acesso ao ambiente de homologação
  da SEFAZ (qualquer UF).
- **Risco**: G8 muda o fluxo de emissão — inserir alocação antes da transmissão pode
  expor falhas de concorrência que antes eram silenciosas.
