# Reanálise — situação dos achados da revisão total

Reanálise de **2026-10-26**, versão `0.228.0`, contra a revisão total de 2026-10-11 (`c1ef23d`, `0.227.0`). A revisão total tem **19** achados (RT-01 a RT-19; a tabela da síntese lista RT-19 na última linha).

Estados (decisão 3 do design): **provado** (resolvido, com teste executado que falha sem a correção) · **sem prova** (resolvido no código; a prova no ambiente que importa não rodou) · **aberto** · **severidade mudou** · **não reproduz**.

Arquivos citados nos RT que mudaram desde `c1ef23d` (`git diff --name-only c1ef23d 4e2e93f -- <arquivos citados>`): só `integracao/{alerta_fiscal,folha,geracao_efd,navegador_estoque,pix}.py`, todos no commit de correção `b08beb7`. Os demais arquivos citados estão idênticos ao que a revisão total leu.

## Quadro

| ID | Sev. original | Estado | Evidência |
|---|---|---|---|
| RT-01 | Crítico (latente até 01/01/2027) | **sem prova** | `folha/periodo.py` (`ano_do_periodo`) e `integracao/folha.py:96-103` passam `ano=` às duas funções e recusam ano sem tabela. Guarda por `ast` em `tests/test_periodo_folha.py`, verde. Os casos de bench (`tests_bench/test_folha.py`, 2026 e 2027) não rodaram: ver "Bench" abaixo. Tabela de 2027 ainda inexistente (bloqueada até a Portaria de janeiro de 2027, tarefa 2.1 de `corrigir-ano-da-folha`) |
| RT-02 | Alto | **sem prova** | `integracao/geracao_efd.py:100-101` checa `Company`/read e `Arquivo SPED`/create antes de ler; `insert()` sem `ignore_permissions`. Guarda estática em `tests/test_whitelist_com_permissao.py`, verde. Falta o teste de bench de permissão (tarefa 1.1 de `proteger-gerar-efd`, não escrita) |
| RT-03 | Médio | **sem prova** | `navegador_estoque.py:48-65` (`_empresa`, `_exigir_leitura`), `alerta_fiscal.py:98-99`, `pix.py` com `has_permission`. Mesma guarda estática. Falta o teste de bench "usuário restrito a uma empresa" (tarefa 2.1 de `proteger-gerar-efd`, não escrita) |
| RT-04 | Médio | **aberto** | `fiscal/impostos/` não mudou desde `c1ef23d`; nenhuma change foi criada para conferir a fonte |
| RT-05 | Médio | **aberto** | 14 `etree.fromstring` fora de `tests/` (`grep -rn "etree.fromstring" erpnext_brasil --include=*.py`), nenhum `XMLParser(` endurecido |
| RT-06 | Médio (a verificar em bench) | **aberto** | `integracao/eventos_cte.py:80` e `eventos_mdfe.py:74` ainda usam `datetime.now().astimezone()` (fuso do servidor) |
| RT-07 | Médio | **aberto, reproduzido** | `scripts/auditar_pilha.py:463-465` ordena `glob("mariadb-*")` como texto. Rodado em 2026-10-26 no WSL2: há `mariadb-10.11.19-…` e `mariadb-10.11.9-…` em `~`, e o script relata `instalada=10.11.9` (ver "Pilha") |
| RT-08 | Médio | **parcial** | Metade de permissão resolvida: `importar_codigos.importar_classificacao_ibs_cbs` e `importar_arquivo` (`whitelist`) passam na guarda de `test_whitelist_com_permissao.py`. Metade de teste **aberta**: os mesmos nove módulos seguem sem referência em `tests/` nem `tests_bench/` — `cobranca_documento`, `ecf_dados_empresa`, `efd_dados_cadastrais`, `eventos_sefaz_mdfe`, `importar_codigos`, `inutilizacao_sefaz`, `repositorio_frappe`, `seed_codigos`, `transporte_pagamento` (script que procura o nome do módulo no texto dos testes) |
| RT-09 | Médio | **aberto** (link corrigido nesta reanálise) | `docs/nfse-estado.md:33` apontava para `../MEMORY.md`, que não existe no repositório; corrigido em [arquitetura-ci-docs](arquitetura-ci-docs.md). `estado-da-tropicalizacao.md` continua com o aviso de defasagem e números da `0.133.0` |
| RT-10 | Médio (a verificar) | **aberto** | `docs/healthcare-estado.md:13` registra GPL-3.0 × MIT; nenhuma decisão registrada |
| RT-11 | Baixo (a verificar) | **aberto** | `tests/` não foi reconferido; fora do escopo por diferença |
| RT-12 | Médio (declarado) | **aberto** | Tarefas 3.1 e 5.1 de `openspec/changes/fechar-laco-cte-mdfe/tasks.md` (linhas 92 e 210) seguem `- [ ]` |
| RT-13 | Médio (declarado) | **aberto** | `docs/gaps.md:819` ainda declara os cinco montadores de evento do MDF-e com a forma da NF-e |
| RT-14 | Baixo | **provado** | Docstring de `gerar_efd` (`geracao_efd.py:95-96`) agora diz que só falta o Bloco D; conferido por leitura (o achado era o texto) |
| RT-15 | Baixo | **aberto** | `setup/install.py:21-37`: `after_install` e `after_migrate` seguem com corpo idêntico |
| RT-16 | Médio (declarado) | **aberto** | `.github/workflows/ci.yml` não tem job de bench |
| RT-17 | Baixo (declarado) | **aberto** | Healthcare só no site `hc16pg.localhost` (PostgreSQL), visto na sonda do bench |
| RT-18 | Baixo | **aberto** | `tests_bench/test_consulta_cep.py` não mudou |
| RT-19 | Baixo | **provado** | `tests/test_whitelist_com_permissao.py` falha se um `@frappe.whitelist()` de `integracao/` ficar sem checagem e se uma exceção de `EXCECOES` deixar de ser necessária; executado na suíte (verde). `ignore_permissions` em `integracao/`: 28 → 24 |

Resumo: **2 provados** (RT-14, RT-19), **3 sem prova** (RT-01, RT-02, RT-03), **1 parcial** (RT-08), **13 abertos**. Nenhum mudou de severidade; nenhum deixou de reproduzir.

## Bench (tarefas 2.2 e 2.3): não executado

Sonda somente leitura do bench-16 em 2026-10-26 (`sonda_bench.sh` e `sonda_clone.sh`, script em arquivo disparado por PowerShell, log lido depois):

- Sites: `v16.localhost` (MariaDB, `allow_tests`), `v16pg.localhost` e `fr16pg.localhost` (PostgreSQL, `allow_tests`), `hc16pg.localhost` (PostgreSQL, healthcare) e `v16.localhost.orfao-1788733657`. Nenhum serviço ouvindo (MariaDB, Redis e servidor parados).
- O clone do app em `~/frappe-bench-16/apps/erpnext_brasil` está na branch **`bench-main`, commit `07f2701`** (PR #5, autorização do CT-e), muito atrás da `main`. A referência `upstream/main` do clone também para em `07f2701` (nunca atualizada).
- Alterações locais **reais**: com `core.fileMode=false` e ignorando espaço e fim de linha, `19 files changed, 373 insertions(+), 52 deletions(-)` — entre eles `hooks.py`, `integracao/folha.py`, `integracao/party.py`, `setup/campos_documento.py`, `fiscal/documento/evento_mdfe.py` —, mais **47 arquivos não rastreados**. (Sem `fileMode=false`, `git status` mostra 490 linhas: o resto é bit de permissão.)
- O `tests_bench/test_folha.py` do clone é a versão antiga: nenhum caso de 2027.

Rodar `test_folha` ali provaria o código de `07f2701` com alterações locais, não a correção de `0.228.0`. Pôr o código da `main` no clone sobrescreveria trabalho local não versionado — fora do que uma reanálise somente leitura pode fazer. **Decisão: não tocar o bench**; RT-01, RT-02 e RT-03 ficam "sem prova". Caminhos para fechar a prova, a decidir pelo dono do bench: (a) versionar ou guardar o trabalho local do clone e atualizá-lo para a `main`; (b) um segundo clone/bench só para teste, com `bench get-app` do repositório.

## Testes de bench que faltam (tarefa 2.4)

Não escritos nesta reanálise (são código e pertencem às changes donas):

- `proteger-gerar-efd` 1.1 — usuário sem papel contábil chama `gerar_efd` e recebe `PermissionError`, sem `Arquivo SPED` criado (RT-02).
- `proteger-gerar-efd` 2.1 — usuário restrito a uma empresa não lê armazéns, saldos nem prontidão de outra (RT-03).
- `corrigir-ano-da-folha` 1.1/1.2 — escritos em `tests_bench/test_folha.py`, falta só executar (RT-01).

## Pilha (tarefa 2.5)

`python3 scripts/auditar_pilha.py --bench ~/frappe-bench-16` (script desta worktree, WSL2, 2026-10-26T08:59-04:00), **saída 1, 40 falhas**:

| Componente | Instalada | Última | |
|---|---|---|---|
| frappe | 16.51.0 | 16.53.0 | atrás |
| erpnext | 16.50.0 | 16.52.1 | atrás |
| hrms | 16.50.0 | 16.52.0 | atrás |
| bench | 5.31.0 | 5.31.1 | atrás |
| python | 3.14.8 | 3.14.10 | atrás (suporte até 2030-10-31) |
| nodejs | 24.21.0 | 24.22.1 | atrás (até 2028-04-30) |
| mariadb | 10.11.9 *(leitura errada, RT-07)* | 10.11.19 | `mariadb-10.11.19` existe em `~` |
| redis | 7.2.16 | 7.2.16 | em dia |

Vulnerabilidades que afetam a instalação: 76 registros; **7 críticas** (pillow 12.3.0 ×5, corrigidas em 13.0.0; `certifi` 2026.7.22 com CA emSign comprometida, corrigida em 2026.10.19; `brotli` 1.2.0, corrigida em 1.2.1) e altas em pillow, `pypdf` 6.19.0 (→ 6.21.2), `virtualenv` 21.14.6 (→ 21.14.9), `filelock` 4.1.0 (→ 4.2.1), `GitPython` 3.1.62 (→ 3.2.1, **fora do pin `~=3.1.45` do Frappe**) e `pdfkit` (sem correção, já aceito). Na auditoria de 2026-10-09 (`docs/auditoria-da-pilha.md`) só `pdfkit` falhava: todo o resto é **novo** — registrado como **RA-02**.

Avisos do Frappe sem versão corrigida, conferidos na API pública em 2026-10-26 (`GET api.github.com/repos/frappe/frappe/security-advisories`): CVE-2026-63654 (low, [GHSA-cgwf-xgph-hxgm](https://github.com/frappe/frappe/security/advisories/GHSA-cgwf-xgph-hxgm)), CVE-2026-62315 (medium, [GHSA-2c6h-wv85-fxvj](https://github.com/frappe/frappe/security/advisories/GHSA-2c6h-wv85-fxvj)), CVE-2026-53569 (medium, [GHSA-rx6h-4p83-m76x](https://github.com/frappe/frappe/security/advisories/GHSA-rx6h-4p83-m76x)) — faixa e correção ainda `tbd`; já registrados em `docs/auditoria-da-pilha.md:52`, sem mudança.
