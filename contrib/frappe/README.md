# Correções para o Frappe — a devolver ao projeto

Patches feitos sobre o Frappe **16.31.0** (`version-16`, commit `6a329d0684`), no clone do
bench-16 (`~/frappe-bench-16/apps/frappe`, branch `fix/postgres-link-filters-already-decoded`),
provados no site PostgreSQL `v16pg.localhost`. O Frappe é MIT, como este app: a correção
volta para a comunidade, e enquanto o PR não entra, estes arquivos são a forma de reaplicá-la
em qualquer bench.

Histórico completo, sintoma a sintoma, em [`docs/postgresql.md`](../../docs/postgresql.md).

## Como aplicar num bench

```sh
cd ~/frappe-bench-16/apps/frappe
git pull --ff-only                      # regra do projeto: sempre atualizar antes de mexer
git am /caminho/para/erpnext_brasil/contrib/frappe/*.patch
```

`git am` falha se o upstream já tiver mudado o trecho — o que normalmente significa que a
correção entrou. Confira antes de forçar: `git log --oneline -20 -- frappe/database/query.py
frappe/core/doctype/doctype/doctype.py`.

## Os patches

| Arquivo | O que corrige | Prova |
|---|---|---|
| `0001-fix-doctype-accept-already-decoded-link_filters-on-P.patch` | `validate_link_filters` fazia `json.loads` num valor que a coluna `json` do Postgres já devolve decodificado → "Link Filters must be valid JSON" ao inserir **qualquer** Custom Field num DocType com `link_filters` (o ERPNext usa em `Company`). Passa a usar `frappe.parse_json`. Teste novo: `test_link_filters_already_decoded_are_accepted`. | `bench execute ...validate_fields_for_doctype --args '["Company"]'` — falhava, passa |
| `0002-fix-query-do-not-apply-default-ORDER-BY-to-aggregate.patch` | `get_value(dt, filtros, [{"MAX": campo}])` gerava `SELECT MAX(...) ... ORDER BY creation` — Postgres recusa ("creation must appear in the GROUP BY clause"). O motor passa a não aplicar ordenação a consulta só de agregados, como já faz com `DISTINCT`/`GROUP BY`. Teste novo: `test_aggregate_only_query_drops_default_order_by`. | `bench execute frappe.db.get_value --args '["User", {"enabled": 1}, [{"MAX": "creation"}]]'` — falhava, devolve o valor; e o caso real do ERPNext (`stock_closing_entry.py:31`) deixa de derrubar o `before_tests` |

## Texto sugerido para os PRs (em inglês, como o projeto pede)

### PR 1 — `fix(doctype): accept already-decoded link_filters on PostgreSQL`

> `link_filters` is a JSON field. MariaDB returns it as text, but PostgreSQL's `json` column
> comes back from psycopg2 already decoded (a list). `validate_link_filters` called
> `json.loads` on that list, raised `TypeError` and reported "Invalid Filters ... must be
> valid JSON" for a perfectly valid value.
>
> Any Custom Field inserted on a DocType whose fields carry `link_filters` (ERPNext sets it on
> `Company.default_wip_warehouse`) failed on PostgreSQL:
> `bench --site <pg-site> install-app <any app with custom fields on Company>`.
>
> Use `frappe.parse_json`, which parses strings and passes decoded values through
> (`orjson.JSONDecodeError` is a `ValueError`, so the existing `except` still catches bad
> JSON), and add a test for the decoded case.
>
> Reproduced on Frappe 16.31.0 / PostgreSQL 18.6; the same code is in `develop`.

### PR 2 — `fix(query): do not apply default ORDER BY to aggregate-only queries on PostgreSQL`

> `frappe.db.get_value(doctype, filters, [{"MAX": "field"}])` builds
> `SELECT MAX(field) FROM tab WHERE ... ORDER BY creation DESC`. MariaDB accepts it;
> PostgreSQL rejects it: "column creation must appear in the GROUP BY clause or be used in an
> aggregate function". ERPNext hits this on every site (e.g. `Stock Closing Entry` reading
> the last `Period Closing Voucher`), which breaks `bench run-tests` on PostgreSQL before any
> test runs.
>
> A query that only aggregates returns one row, so ordering carries no information: skip it
> on PostgreSQL, the same way DISTINCT/GROUP BY queries already skip it. Test added
> (`@run_only_if(db_type_is.POSTGRES)`).

## O que ainda não foi feito

- **Abrir os PRs.** Exige conta no GitHub com o fork do `frappe/frappe`; os patches estão
  prontos para `git am` num fork e `gh pr create`. Alvo: `develop` (o projeto faz backport
  para `version-16` por rótulo).
- ~~Rodar os testes dos trechos alterados~~ — **feito** em `fr16pg.localhost` (site só com
  Frappe, Postgres 18.6): `test_doctype` 5/5, `test_query` 1/1, em 2026-09-17.
- **Rodar a suíte inteira do Frappe em Postgres.** Só os testes dos dois trechos alterados
  foram executados; a suíte completa do Frappe/ERPNext em Postgres tem outros tropeços
  (`docs/postgresql.md`), e não é objetivo deste app corrigi-los todos.
