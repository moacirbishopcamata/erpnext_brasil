## Why

O app chegou à `0.227.0` com ~91 mil linhas em `erpnext_brasil/`, 308 commits, 184 módulos de teste da suíte pura e 29 de bench. As auditorias feitas até aqui foram **pontuais**: `docs/gaps.md` (costura, 2026-09-04), `docs/auditoria-padroes.md` (lint e SOLID), `docs/auditoria-da-pilha.md` (versões e CVE, 2026-10-09) e `docs/estado-da-tropicalizacao.md` (panorama de 2026-09-03, versão `0.133.0`, hoje defasado). Ninguém olhou o app **inteiro de uma vez**, contra o estado atual, com a mesma régua. Duas frentes cresceram depois da última varredura geral (MDF-e operacional e saúde), e o CI não tem job de bench: "verde no CI" não prova nada sobre Custom Field, hook ou DocType.

## What Changes

- Executar uma **revisão total, somente leitura**, em nove frentes (fiscal documental, fiscal tributário, contábil, folha/RH, integração Frappe, setup/instalação, saúde/estoque, testes, segurança), mais pilha/CVE/CI e documentação, todas com a mesma escala de severidade e a mesma exigência de evidência.
- Produzir `docs/revisao-total.md` (síntese priorizada) e um anexo por frente em `docs/revisao-total/`, com o inventário de números atualizado.
- Reconciliar `docs/gaps.md` e `docs/estado-da-tropicalizacao.md` com o que a revisão encontrar (números, itens resolvidos, itens novos).
- Para cada achado Crítico ou Alto, **propor** (não implementar) o change de correção; erro factual simples em documentação é corrigido na própria revisão.
- **Não** altera código, Custom Fields, hooks, DocTypes nem dependências.

## Capabilities

### New Capabilities

Nenhuma. A revisão não muda comportamento do sistema; o change usa `skip_specs: true`.

### Modified Capabilities

Nenhuma.

## Impact

- Escreve apenas em `docs/` e em `openspec/changes/` (novas propostas de correção).
- Lê `erpnext_brasil/` inteiro, `tests/`, `tests_bench/`, `.github/workflows/ci.yml`, `scripts/`, `openspec/` e `docs/`.
- Consulta externa (autorização permanente de verificar na fonte): endoflife.date, GitHub releases/advisories, PyPI, OSV/NVD e a fonte normativa de cada regra fiscal revisada. Fonte só secundária vira aviso, não bloqueio.
- Roda a suíte pura e o `ruff`; bench só em WSL2/Linux, com `git pull` de frappe/erpnext/hrms antes e backup, se o bench for tocado.
