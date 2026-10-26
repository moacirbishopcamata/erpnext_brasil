# Reanálise — arquitetura, CI e documentação

Reanálise de **2026-10-26**, versão `0.228.0`. **Cobertura parcial**: leitura de `tests/test_arquitetura.py`, de `.github/workflows/ci.yml` e varredura mecânica de `docs/` por afirmações datadas. **Não revisados** nesta passagem: `docs/README.md` arquivo a arquivo contra os documentos novos desde `c1ef23d`, e o item "regressão indireta" (pontos de entrada novos).

## Achados

### RA-01 — `test_docker` falha no Windows sem modo UTF-8 — **Baixo**

`erpnext_brasil/tests/test_docker.py:430-437` chama `subprocess.run([...], capture_output=True, text=True, ...)` sem `encoding`. No Windows o padrão é `cp1252`, e a saída UTF-8 de `docker compose config` vira `'NF-e em homologa��o'`. Resultado reproduzido duas vezes: `python -m unittest erpnext_brasil.tests.test_docker` → `FAILED (failures=7, skipped=1)`; com `python -X utf8` → `OK`. São 7 falhas de **um** teste (`test_os_rotulos_de_instancia_chegam_aos_servicos_de_aplicacao`, uma por serviço). O CI (Ubuntu, UTF-8) não vê isso, então a suíte "verde no CI" convive com vermelha na máquina do desenvolvedor. Correção de uma linha (`encoding="utf-8"`), não aplicada: a reanálise é somente leitura.

### RA-02 — pilha do bench com 7 CVE críticos — **Alto → tratado em 2026-10-26**

`auditar_pilha.py` no bench-16 às 08:59: 40 falhas, 7 críticas (Pillow 12.3.0 ×5, `certifi` 2026.7.22, `brotli` 1.2.0). Na auditoria de 2026-10-09 só o `pdfkit` falhava; tudo isso é novo. Depois da atualização do bench (Pillow 13.0.0 e demais): **5 falhas, nenhuma crítica**. Detalhe e o que sobrou, por pin do Frappe: [`../atualizacao-do-bench-2026-10-26.md`](../atualizacao-do-bench-2026-10-26.md).

### RA-03 — pureza de `contabil/` e `folha/` só por convenção — **Baixo**

`test_arquitetura.py:19` define `PURO = RAIZ / "fiscal"`; só ele é checado contra `frappe` e `integracao`. `PACOTES_PUROS_DAS_FERRAMENTAS` cobre `persistencia`, `sistema`, `bancos`, `soda`, `chantilly`. `contabil/` (40 módulos) e `folha/` (21) não entram. Varredura mecânica hoje: nenhum importa `frappe` nem `erpnext_brasil.integracao` (`grep -rlE "^\s*(import|from) frappe|erpnext_brasil\.integracao"` sem resultado). A regra vale, mas nada a defende: um `import frappe` em `contabil/` passaria na suíte. O `CLAUDE.md` passou a declarar isso.

### RA-04 — documentação com `version-15` e contagens velhas — **Médio → corrigido nesta reanálise**

Varredura (`docs_defasados.py`: versão do app, versões `16.x`, "N testes", `version-15`) achou 19 arquivos com afirmações datadas. Corrigidos: `docs/versoes-frappe-erpnext.md`, `docs/instalacao.md`, `docs/ambiente-dev-bench.md`, `pyproject.toml` (comentário), `README.md` (1.670 → 3.956 testes), `docs/estado-da-tropicalizacao.md`, `docs/gaps.md`, `docs/revisao-total.md`, `docs/auditoria-da-pilha.md`, `docs/healthcare-estado.md`, `docs/ged-viabilidade.md`, `docs/nfse-estado.md` (link quebrado para `../MEMORY.md`, RT-09). **Mantidos como histórico datado**, sem reescrever: `docs/avaliacao-tropicalizacao.md` ("2851 testes"), `docs/integracao-party-bench.md` ("1731 testes"), `docs/docker-compose.md` ("1671 testes"), `docs/banco-do-bench-v16.md`, `docs/estoque-estado.md` e `docs/postgresql.md` (Frappe 16.31/16.33), `docs/proposta-de-melhorias.md`.

### RA-05 — clone do app no bench com trabalho local não versionado — **Médio (a verificar com o dono)**

`~/frappe-bench-16/apps/erpnext_brasil`: branch `bench-main` no commit `07f2701`, com **19 arquivos alterados** (ignorando fim de linha e modo) e **47 não rastreados**, incluindo `hooks.py`, `integracao/party.py`, `setup/campos_documento.py`. Nada disso está em nenhum remoto conhecido. Dois efeitos: risco de perda do trabalho local e impossibilidade de provar em bench a correção da `0.228.0` sem sobrescrevê-lo. Nenhum arquivo foi tocado.

### RA-06 — `bench backup` não funciona nos sites PostgreSQL — **Médio**

`bench --site v16pg.localhost backup` → `pg_dump: error: aborting because of server version mismatch (server 18.6; pg_dump 16.15)`. O WSL tem o cliente 16 (`postgresql-client` do apt, ver memória do PostgreSQL local). Falha alto, mas significa que **nenhuma rotina de backup do bench cobre os três sites PostgreSQL**. Contornado em 2026-10-26 com o `pg_dump` 18.6 do Windows. Correção durável: instalar `postgresql-client-18` no WSL (não feito).

### RA-07 — relatórios padrão removidos como órfãos no `migrate` — **a verificar**

"Lotes por Validade" e "Itens em LIFO" foram apagados em `v16.localhost` e `v16pg.localhost`. Não estão em `apps/`, em `sus_brasil` nem no histórico do `erpnext_brasil`. Origem desconhecida (possivelmente um app removido do bench). As linhas de papéis estão no backup `20261026_184600-v16_localhost-database.sql.gz`; o registro do próprio Report não foi localizado nele.

### RA-08 — realtime novo do Frappe 16.53 não exercitado — **a verificar**

A 16.53.0 trocou o servidor de tempo real por Python (`python-socketio`, `uvicorn`, `a2wsgi`, `httpx`). Os pacotes foram instalados e importam; o `bench start` não foi subido.

## O que está bem

- `ci.yml` bate com o que o `CLAUDE.md` descreve: suíte pura, `ruff check`/`format` em `erpnext_brasil/` e `scripts/`, job do Cherry com dois pisos (95% núcleo, 89% interface) e passo que falha se não houver Docker.
- Sem `ruff` pendente: `All checks passed`, `519 files already formatted`.
- Testes do Cherry: 157, cobertura 100% no núcleo e 91% em `app.py`.
