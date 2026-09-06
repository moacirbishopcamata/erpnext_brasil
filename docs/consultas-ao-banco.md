# Consultas ao banco: o que o Frappe decide, e o que dá para otimizar

Resposta a uma pergunta que vale registro: *"todas as buscas em banco são feitas pelo
Frappe? Não temos como interferir e até otimizar?"*

## ⚠️ A resposta curta

**Não é uma camada só, e dá para interferir em todos os níveis.** O Frappe oferece quatro
caminhos ao banco, do mais protegido ao mais cru — e o app escolhe qual usar em cada ponto.

| Caminho | O que dá | O que custa |
|---|---|---|
| `frappe.get_all` / `get_list` | permissões, filtros, ordenação, paginação | não faz `JOIN` complexo nem agregação livre |
| `frappe.qb` (Query Builder) | SQL montado programaticamente, com `JOIN` e agregação | não aplica permissão sozinho |
| `frappe.db.sql` | **tudo** — SQL cru | **nenhuma permissão**, e o SQL é seu |
| Índice no DocField / `add_index` | o plano de execução | migração |

## Onde este app está

- **`frappe.get_all` em quase tudo** — 15 chamadas espalhadas pela integração.
- **`frappe.db.sql` uma única vez**, em `efd_inventario.py`: a apuração do Bloco H precisa
  de agregação por item e depósito num intervalo, e montar isso com `get_all` seria trazer
  linhas demais para somar em Python.
- **`frappe.qb` nenhuma vez.**

Ou seja: **a escolha já é nossa**, e foi feita pelo lado conservador de propósito — o que
`get_all` dá de graça (permissão, `ignore_permissions` explícito, compatibilidade com
Postgres) vale mais que o ganho de SQL manual na maioria dos pontos.

## As quatro formas de interferir

### 1. Índice — o que quase sempre resolve

O jeito declarativo é `search_index: 1` no DocField, que o `frappe/database/schema.py`
traduz em índice na migração. O jeito programático é `frappe.db.add_index(doctype, fields)`
num patch.

⚠️ **É aqui que está o ganho real deste app.** As consultas que crescem sem limite são as
de `Transmissao Fiscal` filtrando por `documento_tipo` + `documento` — o painel de situação
fiscal faz uma **a cada abertura de formulário**. Sem índice nesse par, é varredura de
tabela numa tabela que cresce com cada nota emitida.

**Isso ainda não foi feito.** Está declarado abaixo, em "o que falta".

### 2. `permission_query_conditions` — injetar `WHERE` do lado de fora

Hook do Frappe (`frappe/hooks.py`) que permite acrescentar condição a **toda** listagem de
um DocType, sem tocar em quem consulta. É como o ERPNext restringe registros por empresa.

Serve para: um `Transmissao Fiscal` que só apareça para quem pode ver a `Company` dele.
Também não implementado.

### 3. `frappe.qb` — SQL programático sem string

Construtor sobre *pypika* (`frappe.qb`), com `JOIN` e agregação, e ainda portátil entre
MariaDB e Postgres. É a saída quando `get_all` não basta e SQL cru é demais.

### 4. `frappe.db.sql` — quando nada mais serve

Dá controle total e **não aplica permissão nenhuma**. O único uso do app está declarado na
docstring do módulo que o usa.

⚠️ Duas armadilhas, as duas já registradas em outros documentos:

- **SQL de escrita não passa pelo `Document`** e portanto **não gera `Version`** — some da
  trilha de auditoria (ver [logs-e-auditoria.md](logs-e-auditoria.md)). É a razão de este
  app usar `db_set`/`get_doc` para escrever, e SQL só para ler.
- **Portabilidade**: o ERPNext mantém compatibilidade com Postgres, e funções como `IF`,
  `DATE_FORMAT` e `GROUP_CONCAT` são só de MySQL.

## O que falta, declarado

1. **Índice em `Transmissao Fiscal (documento_tipo, documento)`.** A consulta mais quente
   do app, executada a cada `refresh` de `Sales Invoice`. É um patch curto e o ganho é
   estrutural — não uma micro-otimização.
2. **Índice em `Numeracao Fiscal`** pelo par que o `SELECT ... FOR UPDATE` usa: ali o
   índice não é só velocidade, é **tamanho do lock**. Sem índice, a trava pode escalar da
   linha para mais do que se quer.
3. **`permission_query_conditions`** nos DocTypes fiscais, para que um site multiempresa
   não mostre transmissão de outra `Company`.

Os três são gap declarado, não desenho final — e o primeiro é o mais barato dos três.

## O que **não** vale a pena

- **Trocar `get_all` por SQL cru para "ganhar desempenho"** onde a consulta traz poucas
  linhas: perde-se permissão e portabilidade por ganho que não se mede.
- **Cache próprio.** O Frappe já tem `frappe.cache` e o cache de documento; um terceiro
  nível só acrescenta um lugar onde invalidar errado.

## Fontes

- `frappe/database/database.py` — `add_index`, `add_unique`.
- `frappe/database/schema.py` — `search_index` do DocField virando índice.
- `frappe/hooks.py` — `permission_query_conditions`.
- `frappe/__init__.py` — `frappe.qb`.
- `erpnext_brasil/integracao/efd_inventario.py` — o único `frappe.db.sql` do app.
