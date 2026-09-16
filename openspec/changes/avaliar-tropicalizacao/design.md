## Context

A tropicalização do ERPNext acumulou 101 módulos de regra pura, 30 de integração, ~35.300 linhas de código e 2.851 testes. A documentação de estado está dispersa em `gaps.md` (732 linhas), `estado-da-tropicalizacao.md` (131 linhas), `sped-fiscal.md`, `ecf-estado.md`, `rh-estado-esocial.md` e outros. O `gaps.md` foi refeito em 2026-09-06 e 2026-09-15, mas ainda contém seções que referenciam trabalho já concluído (ex.: gap 1.1/1.2/1.2-bis — todos corrigidos). `estado-da-tropicalizacao.md` estava desatualizado em dois pontos até 2026-09-04.

## Goals / Non-Goals

**Goals:**
- Criar `docs/avaliacao-tropicalizacao.md` como referência consolidada e atualizada
- Categorizar gaps por: document fiscal, apuração/contabilidade, RH/eSocial, financeiro, infraestrutura
- Priorizar por impacto no negócio (o que impede uso real hoje)
- Referenciar changes ativos (`fechar-laco-cte-mdfe`, `emitir-nfce-do-pos`, `resolver-3-criticos`) e seus progressos
- Atualizar `gaps.md` com números corretos se necessário

**Non-Goals:**
- Implementar código ou criar novos DocTypes
- Alterar behavior de módulos existentes
- Atualizar docs de estado por frente (ex.: `mdfe-estado.md`, `ecf-estado.md`) — estes são mantidos por seus changes

## Decisions

### Estrutura do documento de avaliação

**Decisão**: Seção por domínio de negócio, com cada item classificado como `✅ Pronto`, `⚠️ Parcial`, `❌ Não iniciado` ou `🔧 Em andamento`.

**Alternativa considerada**: Ordem cronológica de implementação — rejeitada porque o usuário precisa de visão por impacto, não por data.

### Priorização

**Decisão**: Dois eixos — (1) o que impede uso real (bloqueio), e (2) o que destrava mais trabalho futuro (cascata). Itens de bloqueio vêm primeiro.

### Referência a changes ativos

**Decisão**: Cada item da avaliação referencia o change que o cobre (se existir) e o progresso (tasks completas / total). Items sem change são listados como "sem change — candidato a novo change".

## Risks / Trade-offs

- **[Documento envelhece]** → Registrar data de cada seção; reavaliar a cada archive de change
- **[Números ficam defasados]** → Referenciar `gaps.md` como fonte canônica de números; atualizar ambos ao mesmo tempo
- **[Escopo cresce]** → Manter foco em "o que impede uso real"; itens de melhoria ficam em `gaps.md` seção 5
