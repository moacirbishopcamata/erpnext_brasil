# Atualização do bench-16 — 2026-10-26

Pedido do usuário: "atualizar o Frappe e/ou ERPNext para versões mais estáveis LTS sem CVE críticos". O Frappe/ERPNext **não usa o rótulo LTS**: o critério adotado (ver `docs/auditoria-da-pilha.md`) é a série estável mais recente (`version-16`) no último patch dela, nunca `develop`.

## Antes → depois

| Componente | Antes | Depois | Fonte da "última" |
|---|---|---|---|
| Frappe | `16.51.0` (branch `frappe-v16-pg-patches`) | **`16.53.0`** (branch `frappe-v16.53-pg-patches`) | tag `v16.53.0`, 2026-10-22 (API de releases do GitHub) |
| ERPNext | `16.50.0` | **`16.52.1`** | tag `v16.52.1`, 2026-10-22 |
| HRMS | `16.50.0` | **`16.52.0`** | tag `v16.52.0`, 2026-10-22 |
| Healthcare (Marley) | `16.6.1` | `16.6.1` (não tocado) | — |
| Pillow | `12.3.0` | **`13.0.0`** | PyPI; fecha 5 CVE críticos e 23 altos |
| certifi / brotli / virtualenv / filelock | `2026.7.22` / `1.2.0` / `21.14.6` / `4.1.0` | `≥ 2026.10.19` / `≥ 1.2.1` / `≥ 21.14.9` / `4.2.4` | pip |
| Babel | `2.16.0` | `2.18.0` (pin do Frappe 16.53) | — |
| Python, Node, MariaDB, Redis, bench | `3.14.8`, `24.21.0`, `10.11.9`, `7.2.16`, `5.31.0` | **não alterados** | ver "O que ficou de fora" |

`erpnext_brasil`, `sus_brasil` e `healthcare` não foram tocados.

## Vulnerabilidades

`python3 scripts/auditar_pilha.py --bench ~/frappe-bench-16` (2026-10-26, WSL2):

| | Antes (08:59) | Depois (~09:40) |
|---|---:|---:|
| Registros que afetam a versão instalada | 76 | **14** |
| Falhas do script (críticas + altas) | 40 | **5** |
| das quais críticas | 7 (Pillow ×5, certifi, brotli) | **0** |
| Componentes "em dia" | 1 (Redis) | 4 (Frappe, ERPNext, HRMS, Redis) |

As 5 falhas altas que sobram **não são escolha deste projeto**:

- `pypdf` 6.19.0 (3 altos, mais 7 moderados e 1 baixo, todos corrigidos em 6.21.2): o Frappe fixa `pypdf==6.19.0` no `pyproject.toml`. Subir por cima do pin é decisão do mantenedor do bench, não desta atualização.
- `GitPython` 3.1.62 (alto, RCE em submódulo, corrigido em 3.2.1): o Frappe fixa `GitPython~=3.1.45`; a 3.2.x está fora do pin. A auditoria de 2026-10-09 já tinha recusado a 3.2.0 pelo mesmo motivo.
- `pdfkit` 1.0.0 (CVE-2025-26240): sem versão corrigida; já aceito em `docs/auditoria-da-pilha.md`, e o app não usa `pdfkit`.

Avisos do Frappe sem faixa nem correção (`tbd` na API de advisories, conferido em 2026-10-26): CVE-2026-63654 (baixo), CVE-2026-62315 e CVE-2026-53569 (médios). Continuam indeterminados.

## O que mudou no Frappe 16.53 e exigiu ação

A comparação de `pyproject.toml` entre `v16.51.0` e `v16.53.0` mostrou **dependências novas**: o servidor de tempo real passou a ser Python (`python-socketio`, `python-engineio`, `uvicorn`, `a2wsgi`, `httpx`), mais `tzdata` e `Babel` 2.18. O primeiro passo do script usou `pip install --no-deps` e deixou isso de fora; o `pip check` acusou, e os pacotes foram instalados em seguida com os pins do Frappe. **Ainda não se subiu o servidor (`bench start`) com o realtime novo**: `Procfile` e `socketio.js` continuam no bench, mas nada foi exercitado.

Também: o pin `filelock~=3.20.1` do Frappe conflita com o `filelock 4.2.4` instalado. O conflito é anterior a esta atualização (estava em 4.1.0) e foi mantido de propósito, porque a série 4.x é a que traz a correção de CVE.

## Patches locais do Frappe

Os dois commits de PostgreSQL (`fix(doctype): accept already-decoded link_filters on PostgreSQL`, `fix(query): do not apply default ORDER BY to aggregate-only queries on PostgreSQL`) **não foram absorvidos pelo upstream** (`git cherry` os marcou `+` contra `version-16`) e foram reaplicados sobre a 16.53.0 sem conflito. O terceiro commit local (`chore(deps): bump pypdf, Werkzeug, PyJWT, oauthlib and WeasyPrint`) deixou de ser necessário: a 16.53.0 já traz esses pins. O commit novo `chore(deps): Pillow 13.0.0…` é só local; o upstream segue em `Pillow~=12.3.0`.

## Backup e como voltar

- `v16.localhost` (MariaDB): `bench backup --with-files`, em `sites/v16.localhost/private/backups/20261026_184600-*`.
- Sites PostgreSQL (`v16pg`, `fr16pg`, `hc16pg`): o `pg_dump` do Ubuntu (16.15) **recusa o servidor 18.6**, então o `bench backup` falha neles. Os dumps foram feitos com o `pg_dump` 18.6 do Windows, validados com `pg_restore -l` (3.265, 1.007 e 3.210 entradas; 918, 274 e 881 tabelas de dados) e ficam em `C:\Users\ninte\frappe-backups-20261026` e em `sites/<site>/private/backups/20261026-*`.
- Cada app (`frappe`, `erpnext`, `hrms`) tem a tag git `antes-da-atualizacao-20261026` no estado anterior.

## Migração e testes

`bench migrate` rodou nos quatro sites sem erro. Duas consequências:

- O `migrate` removeu como órfãos os Reports **"Lotes por Validade"** e **"Itens em LIFO"** em `v16.localhost` e `v16pg.localhost`. Nenhum app nem repositório conhecido os contém (busca em `apps/`, em `sus_brasil` e no histórico do `erpnext_brasil`); as linhas de papéis deles estão no backup de hoje. **A origem é desconhecida**, registrada como a verificar.
- Testes do Frappe depois da atualização:

| Módulo | Site | Resultado |
|---|---|---|
| `frappe.tests.test_query` | `fr16pg` (PostgreSQL) | **64 testes, OK** (3 pulados). Cobre o patch de `ORDER BY` |
| `frappe.core.doctype.doctype.test_doctype` | `fr16pg` | 42 testes, **1 falha e 2 erros** (`test_no_delete_doc`, `test_change_field_type_with_incompatible_values`, `test_delete_orphaned_doctypes`) |
| `frappe.core.doctype.file.test_file` | `fr16pg` | 73 testes, **1 falha e 3 erros** |
| `frappe.core.doctype.file.test_file` | `v16.localhost` (MariaDB) | `Ran 1 test … OK`; o processo não encerrou e foi interrompido (saída 143) |

Das falhas, quatro são `OutgoingEmailError: Please setup default outgoing Email Account` (site sem conta de e-mail) e uma é timeout de `rq_job`: aparentam ser de ambiente. As outras duas (`test_no_delete_doc` e `test_make_thumbnail`) **não foram explicadas**. Descartei o Pillow 13 como causa da miniatura: a geração de miniatura isolada dá o mesmo resultado com 12.3.0 e 13.0.0. **Não rodei estes testes antes da atualização**, então não sei se as falhas são anteriores a ela.

## O que ficou de fora, e por quê

- **MariaDB `10.11.9` → `10.11.19`**: o binário novo já existe em `~` (o `auditar_pilha.py` lê o errado, RT-07), mas trocar o servidor sobre o `mariadb-data` existente é outra operação e não foi pedida.
- **Python 3.14.8 → .10, Node 24.21 → 24.22, bench 5.31.0 → .1**: patches menores sem CVE crítico; fora do pedido.
- **`erpnext_brasil` no bench**: o clone segue na branch `bench-main` (`07f2701`) com 19 arquivos alterados e 47 não rastreados. Por isso a prova em bench das correções da `0.228.0` continua pendente (ver `docs/reanalise/situacao-rt.md`).
- **`bench start` e a interface web**: não foram subidos.
