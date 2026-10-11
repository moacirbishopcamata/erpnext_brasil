# Revisão total — documentação

Versão `0.227.0`, 2026-10-11. Cobre as tarefas 5.1 e 5.2 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Verificado por script:** todo arquivo de `docs/` contra o índice `docs/README.md`; todo link `.md` relativo em `docs/`.
- **Lido:** cabeçalhos de `estado-da-tropicalizacao.md`, `avaliacao-tropicalizacao.md`, `healthcare-estado.md`, `auditoria-da-pilha.md`, `gaps.md` (resumo) e os comentários de `ci.yml`.
- **Não conferido:** o conteúdo de cada `*-estado.md` contra o código. Os números do corpo de `gaps.md` não foram recontados.

## Achados

### RT-09 — documentos defasados ou fora do índice — **Médio**

| Item | Evidência | Situação |
|---|---|---|
| `estado-da-tropicalizacao.md` | cabeçalho: "Atualizado em 2026-09-03, versão `0.133.0`"; tabela com 1.955 testes e 102 documentos | defasado: a versão é `0.227.0`, são 3.490 testes e 142 documentos. O índice o chama de "panorama geral". **Reconciliado** com um aviso no topo (ver abaixo) |
| `avaliacao-tropicalizacao.md` | cabeçalho "versão `0.133.0+`" | defasado, e **fora do índice** |
| `nfce-contingencia.md` | arquivo existe | **fora do índice** |
| `openspec-estado.md` | "Estado do OpenSpec — 2026-09-15" | defasado e **fora do índice** |
| `nfse-estado.md:33` | link `../MEMORY.md` | quebrado: aponta para fora do repositório (a memória fica em `.claude/`, não em `docs/`) |
| `.github/workflows/ci.yml:3` | "a suíte pura (2.292 testes)" | defasado (3.490); não é doc, só relato |
| `CLAUDE.md` | "O CI roda só a suíte pura + `ruff`" | impreciso: há também o job do Cherry; **corrigido** |
| `integracao/geracao_efd.py:93-96` | docstring cita blocos D/H/K como ausentes | só D falta; ver RT-14 em [`contabil-obrigacoes.md`](contabil-obrigacoes.md) |

## O que foi corrigido na própria revisão

- `docs/README.md`: indexadas as três páginas que faltavam (`avaliacao-tropicalizacao.md`, `nfce-contingencia.md`, `openspec-estado.md`) e a nova revisão.
- `CLAUDE.md`: a linha do CI agora cita os três jobs.
- `docs/estado-da-tropicalizacao.md`: aviso no topo dizendo que o panorama é de `0.133.0` e apontando para esta revisão e para `gaps.md`; os números do corpo **não** foram reescritos, porque reescrevê-los é trabalho de frente por frente.
- `docs/gaps.md`: seção nova no resumo apontando as pendências desta revisão.

## Não corrigido, de propósito

- `nfse-estado.md:33`: o link da jurisdição aponta para uma memória pessoal do usuário. Trocar por texto exige saber o que o autor queria dizer (RO, Porto Velho); fica como pendência.
- `ci.yml:3`: comentário em arquivo de CI; vale corrigir junto com a proposta de job de bench.
