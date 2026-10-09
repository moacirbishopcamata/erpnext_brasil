# PostgreSQL como banco do bench: o que foi trocado, o que quebrou, o que foi corrigido

Pedido direto do usuário em 2026-09-17: *"Trocar banco para PostgreSQL"*, com o servidor
**PostgreSQL 18.6 instalado no Windows** (`postgres`/`postgres`, porta 5432) e o bench no
WSL2. Este documento registra a troca de ponta a ponta — o que o Frappe/ERPNext suportam de
verdade, os dois obstáculos reais, as três correções (uma no app, uma no próprio Frappe, uma
numa consulta nossa) e o que foi provado num site real.

## ⚠️ Nível de suporte, lido na fonte e não em blog

- **Frappe 16.31**: o próprio `bench new-site --db-type postgres` imprime
  *"PostgreSQL support is currently in development and considered experimental"*
  (`frappe/commands/site.py`). Suportado, mas experimental.
- **ERPNext**: não tem suporte oficial a Postgres — é pedido aberto há anos
  ([issue #24389](https://github.com/frappe/erpnext/issues/24389),
  [issue #38664](https://github.com/frappe/erpnext/issues/38664),
  [fórum](https://discuss.frappe.io/t/is-erpnext-officially-supported-with-postgresql/163329)).
  Existe um app de contorno da comunidade,
  [frappe_pg](https://discuss.frappe.io/t/postgresql-compatibility-for-erpnext-meet-frappe-pg/157807),
  **não usado aqui**.
- **Este app**: `docs/consultas-ao-banco.md` afirmava que "o ERPNext mantém compatibilidade
  com Postgres". Corrigido: quem mantém é o **Frappe**; o ERPNext instalou e migrou aqui
  (ver abaixo), mas isso é achado desta sessão, não garantia do projeto dele.

**Consequência honesta**: MariaDB continua sendo o banco de referência deste projeto
(`v16.localhost`, CI, `docs/banco-do-bench-v16.md`). PostgreSQL é um **segundo banco
provado** (`v16pg.localhost`), com as ressalvas desta página — não a substituição do primeiro.

## O ambiente

| Peça | Onde | Detalhe |
|---|---|---|
| PostgreSQL 18.6 | Windows, serviço | `listen_addresses = *`, superusuário `postgres` |
| bench-16 | WSL2 (`~/frappe-bench-16`) | frappe 16.31.0, erpnext 16.33.0, hrms 16.19.0, `psycopg2 2.9.12` já no venv |
| Rede | WSL2 → Windows | a porta 5432 do Windows **responde** em `127.0.0.1` dentro do WSL (rede espelhada) |
| Site novo | `v16pg.localhost` | `db_type: postgres`, banco `_e465c6f6052d07e5`; o site MariaDB `v16.localhost` ficou intocado |

⚠️ Diferente do caso do MariaDB nativo do Windows, que `docs/ambiente-dev-bench.md` registra como
inalcançável do WSL (Hyper-V Firewall), **o Postgres do Windows foi alcançado de primeira**. Não
se investigou por quê — provavelmente o instalador do PostgreSQL abre a regra de firewall que o
do MariaDB não abria. Registrado como fato observado, não explicado.

## A receita que funcionou, na ordem

```sh
# 1. cliente psql no WSL — o servidor fica no Windows (ver obstáculo 1)
apt-get install -y postgresql-client            # como root no WSL; sem sudo nesta máquina

# 2. Redis do bench-16 (o bench não sobe sem os dois)
redis-server --port 11001 --daemonize yes --dir ~/redis16 --dbfilename q.rdb --save ""
redis-server --port 13001 --daemonize yes --dir ~/redis16 --dbfilename c.rdb --save ""

# 3. apps.txt com \n final (armadilha 4b de banco-do-bench-v16.md — estava sem, de novo)
printf "frappe\nerpnext\nhrms\nerpnext_brasil\n" > sites/apps.txt

# 4. o site, explícito em tudo
bench new-site v16pg.localhost --db-type postgres --db-host 127.0.0.1 --db-port 5432 \
    --db-root-username postgres --db-root-password postgres --admin-password admin

# 5. apps, e migrate depois do último install-app (regra de banco-do-bench-v16.md, 4c)
bench --site v16pg.localhost install-app erpnext
bench --site v16pg.localhost install-app erpnext_brasil    # exige a correção 1, abaixo
bench --site v16pg.localhost install-app hrms
bench --site v16pg.localhost migrate
bench --site v16pg.localhost set-config allow_tests true
```

O [Cherry](cherry.md) gera o comando do passo 4 e grava `db_type`/`db_host`/`db_port`/
`root_login`/`root_password` no `common_site_config.json` — que é de onde o `new-site` os lê
quando não vêm na linha de comando (`frappe/installer.py::install_db`,
`frappe/database/postgres/setup_db.py::get_root_connection`).

## Obstáculo 1 — `psql not found in PATH`

**Sintoma.** `bench new-site` criava o banco e o usuário no Postgres e morria em
`frappe.exceptions.ExecutableNotFound: psql not found in PATH! This is required to restore
the database.` Tudo que vinha depois (`install-app`, `migrate`) falhava com
`relação "tabDefaultValue" não existe` — consequência, não causa.

**Causa.** O Frappe restaura o SQL-base do site (`framework_postgres.sql`) pelo **cliente**
`psql` (`frappe/database/db_manager.py::restore_database`), não pelo driver. O WSL não tinha
cliente Postgres nenhum: o servidor está no Windows.

**Correção.** `postgresql-client` no Ubuntu do WSL (psql 16.15). Cliente 16 contra servidor 18
restaura sem reclamar. O diretório `sites/v16pg.localhost` parcial precisou ser removido antes
de repetir: o script pula `new-site` quando o diretório existe.

## Obstáculo 2 — `Invalid Link Filters ... must be valid JSON` — bug do Frappe

**Sintoma.** `install-app erpnext_brasil` morria no primeiro Custom Field em `Company`:

```
An error occurred while installing erpnext_brasil: Invalid Link Filters for field
<strong> Default Work In Progress Warehouse </strong>. Link Filters must be valid JSON.
```

O campo citado é do **ERPNext** (`Company.default_wip_warehouse`), não nosso.

**Causa, lida na fonte.** Ao inserir qualquer Custom Field, o Frappe revalida todos os campos
do DocType (`custom_field.py::on_update` → `validate_fields_for_doctype`), e
`doctype.py::validate_link_filters` faz `json.loads(docfield.link_filters)`. `link_filters` é
`fieldtype: JSON`:

| Banco | Coluna | O que o driver devolve |
|---|---|---|
| MariaDB | texto | `'[["Warehouse","disabled","=",0]]'` — `json.loads` funciona |
| PostgreSQL | `json` (`postgres/database.py`, `"JSON": ("json", "")`) | `[['Warehouse','disabled','=',0]]` — **já decodificado**; `json.loads(lista)` levanta `TypeError` |

O `except (TypeError, ValueError)` traduz o `TypeError` em "must be valid JSON" — para um valor
perfeitamente válido. Confirmado o mesmo código em `version-16` e em `develop` do GitHub em
2026-09-17: o bug é upstream, ainda aberto.

### Correção 1 — no app (`setup/install.py::revalidacao_quebra_neste_banco`)

Em Postgres, `criar_campos_fiscais` chama `create_custom_fields(..., ignore_validate=True)`,
que é exatamente o que o **próprio Frappe** faz no assistente de configuração
(`create_custom_fields` liga `ignore_validate` quando `frappe.flags.in_setup_wizard`). A flag
desliga `validate()` e a revalidação do DocType para os nossos Custom Fields; o que ela
deixaria passar — conflito de nome, campo malformado — a suíte pura já confere sem banco
(`tests/test_costura_campos_e_hooks.py`, `tests/test_prefixo_dos_campos.py`). No MariaDB nada
muda.

É contorno, não conserto: fica **removível** quando a correção 2 estiver num Frappe publicado.

### Correção 2 — no Frappe (`contrib/frappe/0001-*.patch`)

`validate_link_filters` passa a usar `frappe.parse_json`, o utilitário do próprio Frappe que
faz `orjson.loads` em string e devolve intacto o que já veio decodificado (`utils/data.py`).
`orjson.JSONDecodeError` é `ValueError`, então o `except` existente continua pegando JSON
inválido de verdade, e os dois testes que já existiam (`test_link_filters_must_be_valid_json`,
`test_link_filters_must_be_list_of_filters`) seguem válidos. Um terceiro,
`test_link_filters_already_decoded_are_accepted`, fixa o caso Postgres.

Prova, no site `v16pg.localhost`:

```
antes:  bench execute frappe.core.doctype.doctype.doctype.validate_fields_for_doctype --args '["Company"]'
        Invalid Link Filters for field <strong> Default Work In Progress Warehouse </strong>. ...
depois: (silêncio — passou)
```

### Correção 2b — também no Frappe: `ORDER BY` padrão em consulta só de agregados

Apareceu ao tentar rodar os testes do Frappe no site: o `before_tests` do ERPNext morreu em
`coluna "tabPeriod Closing Voucher.creation" deve aparecer na cláusula GROUP BY`. A consulta é
`frappe.db.get_value("Period Closing Voucher", {...}, [{"MAX": "period_end_date"}])`
(`erpnext/stock/doctype/stock_closing_entry/stock_closing_entry.py:31`): o ERPNext pede só um
agregado e o **Frappe** acrescenta o `ORDER BY creation DESC` padrão. MariaDB aceita; Postgres
recusa. O motor de consultas (`frappe/database/query.py`) já pulava a ordenação em Postgres com
`DISTINCT`/`GROUP BY`; passou a pular também quando **todos** os campos são agregados
(`pypika.terms.AggregateFunction`) — uma consulta que devolve uma linha não tem ordem. Teste
novo `test_aggregate_only_query_drops_default_order_by`, só em Postgres.

Prova: `bench execute frappe.db.get_value --args '["User", {"enabled": 1}, [{"MAX": "creation"}]]'`
— falhava, devolve a data; e a chamada real do ERPNext deixa de derrubar o `before_tests`.

**Testes do Frappe rodados em Postgres**, num site só com Frappe (`fr16pg.localhost` — num
site com ERPNext o `before_tests` dele ainda tropeça em fixtures, `Could not find Warehouse:
_Test warehouse - _TC`, que não é alvo deste app): `test_doctype` 5/5 OK (os quatro que já
existiam sobre `link_filters` mais o novo), `test_query` 1/1 OK.

Os patches estão em `contrib/frappe/`, com o texto dos PRs e o histórico — ver o README de lá.
A regra de trabalho desde então (memória do projeto): **`git pull` do Frappe, ERPNext e hrms
antes de qualquer correção**, para não corrigir o que já foi corrigido nem retroceder.

## Correção 3 — a nossa única consulta SQL crua (`integracao/efd_inventario.py`)

Não quebrou; **podia quebrar**. `saldos_na_data` escolhia o lançamento mais recente por
item+depósito com `MAX(CONCAT(posting_date, posting_time, name))` — ordenação de **texto**.
No MariaDB a data vira texto sempre em ISO; no PostgreSQL a forma textual de `date` depende do
`DateStyle` da sessão, que o Frappe **não fixa** (`postgres/database.py` só faz
`SET search_path`). Com `DateStyle = 'SQL, DMY'` a concatenação ordenaria dia antes de ano, e
o saldo sairia de outra data — plausível e errado.

Reescrita com `ROW_NUMBER() OVER (PARTITION BY item_code, warehouse ORDER BY posting_date DESC,
posting_time DESC, creation DESC, name DESC)`: função de janela existe no MariaDB desde 10.2
(o Frappe exige ≥ 10.6) e no PostgreSQL. Os testes puros de inspeção
(`tests/test_efd_inventario.py`) continuam valendo, e nasceu o teste de bench
`tests_bench/test_efd_inventario.py`, que submete entradas em datas diferentes e lê o saldo
**na data intermediária** — o mesmo teste roda em `v16.localhost` (MariaDB) e em
`v16pg.localhost` (PostgreSQL).

Os outros dois `frappe.db.sql` do app (`navegador_estoque.py`) são `SELECT ... JOIN ... LIMIT`
sem função específica de banco; o Frappe traduz as crases e os `%(param)s` no driver Postgres.
Não há `LIKE` em filtro nenhum do app (Postgres distingue maiúsculas; MariaDB não), nem
`IFNULL`/`DATE_FORMAT`/`GROUP_CONCAT`.

## O que foi provado em `v16pg.localhost`

| Verificação | Resultado |
|---|---|
| `bench new-site --db-type postgres` | ✅ |
| `install-app erpnext` (16.33.0) | ✅ exit 0 — o ERPNext inteiro instalou sobre Postgres 18.6 |
| `install-app erpnext_brasil` | ✅ com a correção 1 (❌ sem ela — obstáculo 2) |
| `install-app hrms` (16.19.0) + `migrate` | ✅ |
| índice composto `documento_tipo_documento_index` em `tabTransmissao Fiscal` | ✅ criado, mesmo nome do MariaDB |
| colunas `br_*` em `tabCompany` / `tabSalary Component` | 29 / 2 — iguais ao MariaDB |
| Frappe corrigido: `validate_fields_for_doctype('Company')` | ✅ passa (falhava antes) |
| Frappe corrigido: `get_value(..., [{"MAX": ...}])` | ✅ devolve valor (falhava antes) |
| Testes do Frappe dos dois trechos, em `fr16pg.localhost` | ✅ 6/6 |

## O que **não** foi feito, declarado

- **Migrar o site MariaDB para Postgres.** Não existe migração de dados entre os dois no
  Frappe; a troca é criar site novo. O `v16.localhost` continua em MariaDB.
- **CI em Postgres.** A CI continua sem bench (`docs/gaps.md`, seção 2); o que se roda lá é a
  suíte pura, que não toca banco.
- **`scripts/subir.sh` para Postgres.** O script sobe o MariaDB em espaço de usuário; com o
  servidor no Windows não há o que subir do lado do WSL. Ganhou uma guarda: quando o
  `common_site_config.json` diz `postgres`, ele só confere que a porta responde e segue.
- **Docker Compose em Postgres.** `docker-compose.yml` continua com `mariadb`; um serviço
  `postgres` alternativo não foi escrito nem testado (o compose inteiro segue não
  build-testado — `docs/docker-compose.md`).

## Fontes

- `frappe/commands/site.py` (aviso de experimental), `frappe/installer.py::install_db`,
  `frappe/database/postgres/setup_db.py`, `frappe/database/postgres/database.py`
  (`"JSON": ("json", "")`, `SET search_path`), `frappe/database/db_manager.py::restore_database`,
  `frappe/core/doctype/doctype/doctype.py::validate_link_filters`,
  `frappe/custom/doctype/custom_field/custom_field.py` (`ignore_validate`, `in_setup_wizard`),
  `frappe/utils/data.py::parse_json` — lidos no clone do bench-16 (frappe 16.31.0) e
  conferidos contra `version-16` e `develop` em `raw.githubusercontent.com` em 2026-09-17.
- Estado do suporte do ERPNext: issues #24389 e #38664 do `frappe/erpnext`, fórum
  `discuss.frappe.io` — consultados em 2026-09-17.
- Funções de janela no MariaDB: disponíveis desde a 10.2 (documentação do MariaDB,
  `Window Functions`); o piso do Frappe 16 é 10.6 (`docs/banco-do-bench-v16.md`).
