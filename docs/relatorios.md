# Relatórios no Frappe/ERPNext

Os quatro tipos de relatório, qual escolher, e as armadilhas que só aparecem depois.

Verificado no código do Frappe em 2026-09-05 (`frappe/core/doctype/report/report.py`).

## Os quatro tipos

Todo relatório é um documento do DocType **`Report`**, com o campo `report_type`:

| Tipo | Como se escreve | Quem pode criar | Para quê |
|---|---|---|---|
| **Report Builder** | apontando e clicando | qualquer usuário com acesso ao DocType | listagem com filtro, agrupamento e total |
| **Query Report** | SQL | só papel **Script Manager** | consulta que junta tabelas, sem lógica |
| **Script Report** | Python | só papel **Script Manager** | cálculo, condicional, colunas derivadas |
| **Custom Report** | variação de outro relatório | qualquer usuário | mesmo relatório com filtros/colunas salvos |

A regra de quem pode criar vem de `frappe.only_for("Script Manager", True)` no `validate`:
Query e Script Report exigem o papel; Report Builder e Custom Report, não.

---

## Report Builder — o que resolve 80% dos pedidos

É a própria visão de lista, salva. Não escreve código nenhum.

1. Abra a lista do DocType (ex.: **Sales Invoice**).
2. Alterne para a visão **Report** (canto superior direito da lista).
3. Escolha colunas, filtros, ordenação; agrupe por um campo se quiser.
4. **Menu → Save As** e dê um nome.

O que fica salvo é o campo `json` do `Report`. O resultado aparece no menu de relatórios e
pode ser compartilhado por papel.

**Vale para**: "quero ver as notas do mês por cliente com o total". Se o pedido cabe em
colunas de um DocType e seus links, é aqui — e não custa manutenção.

---

## Query Report — SQL, com três regras rígidas

O campo `query` recebe SQL. O Frappe executa assim
(`Report.execute_query_report`):

```python
check_safe_sql_query(self.query)
frappe.db.begin(read_only=True)
result = [list(t) for t in frappe.db.sql(self.query, filters)]
frappe.db.rollback()
```

### 1. Só leitura, e a checagem é literal

`check_safe_sql_query` (`frappe/utils/safe_exec.py`) aceita a consulta apenas se o texto,
depois de `strip().lower()`, **começar** com `select` ou `explain` — e recusa qualquer
`INTO OUTFILE`/`DUMPFILE`.

⚠️ **Consequência que surpreende**: uma consulta com CTE (`WITH ... AS (...) SELECT ...`) é
**recusada**, porque não começa com `select`. Não é o SQL que é inválido — é a checagem que
olha só a primeira palavra. Contorne com subconsulta em vez de CTE.

⚠️ E um comentário antes do `SELECT` também derruba a consulta, pelo mesmo motivo.

### 2. Filtros são parâmetros, nunca concatenação

Os filtros chegam como segundo argumento do `frappe.db.sql`, então use placeholders
nomeados:

```sql
SELECT
    si.name AS "Nota:Link/Sales Invoice:120",
    si.customer AS "Cliente:Link/Customer:200",
    si.grand_total AS "Total:Currency:120"
FROM `tabSales Invoice` si
WHERE si.docstatus = 1
  AND si.company = %(company)s
  AND si.posting_date BETWEEN %(de)s AND %(ate)s
```

Montar a string com f-string é injeção de SQL — e num relatório o usuário controla o
filtro.

O apelido da coluna carrega rótulo, tipo e largura: `"Rótulo:Tipo/Opções:Largura"`.
Alternativamente, preencha a tabela filha **Report Column**.

### 3. ⚠️ SQL bruto **ignora as permissões de registro**

Esta é a armadilha séria. O Frappe verifica se o usuário tem permissão `report` sobre o
`ref_doctype` (`frappe/desk/query_report.py`, linhas 50 e 264) — ou seja, **se ele pode
abrir o relatório**. Não há nenhuma filtragem linha a linha depois disso: o `SELECT`
devolve o que devolver.

Então um Query Report sobre `tabSales Invoice` mostra **todas** as notas, inclusive de
`Company` que o usuário não pode ver por permissão de usuário. Se o relatório precisa
respeitar restrição por empresa ou território, **o próprio SQL tem que filtrar** — o
framework não faz.

Num app fiscal isso importa: um relatório mal escrito vaza faturamento entre filiais.

---

## Script Report — Python

Um módulo com uma função `execute(filters)` que devolve `(columns, data)`:

```python
def execute(filters=None):
    filters = filters or {}
    colunas = [
        {"label": "Nota", "fieldname": "nota", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": "ICMS", "fieldname": "icms", "fieldtype": "Currency", "width": 120},
    ]
    dados = [...]
    return colunas, dados
```

Duas formas de existir:

- **Padrão (`is_standard: "Yes"`)** — vive em arquivos dentro do app, em
  `<app>/<módulo>/report/<nome>/`, com `.json`, `.py` e `.js`. É como o ERPNext distribui os
  seus (ex.: `erpnext/accounts/report/gross_profit/`). Versionado em git.
- **Não padrão** — o Python fica no campo `report_script`, executado por `safe_exec` (com
  ambiente restrito), definindo a variável `result`.

Para relatórios deste app, **a forma padrão em arquivo é a certa**: entra no repositório,
passa por revisão e por lint.

### ⚠️ Passou de 15 segundos, o Frappe muda a configuração sozinho

`execute_script_report` arma um temporizador de **15 segundos**; se o relatório demorar
mais, ele **liga o campo `prepared_report` no próprio documento `Report`**.

A partir daí o relatório deixa de rodar na hora e passa a ser enfileirado em segundo plano,
entregando o resultado depois (DocType `Prepared Report`). Não é defeito — mas é uma
mudança de comportamento **que ninguém pediu e que fica gravada**, e explica o "ontem abria
na hora, hoje diz que está sendo preparado". Para impedir, marque
`disable_prepared_report_automation`.

---

## ⚠️ `developer_mode` grava relatório no disco do app

No `on_update`, se `is_standard == "Yes"` **e** `frappe.conf.developer_mode` estiver ligado,
o Frappe **exporta o relatório para arquivos** dentro do app (`export_to_files`) e ainda gera
o esqueleto `.py`/`.js` no caso de Script Report.

E o `is_standard` vira `"Yes"` **automaticamente** quando quem salva é o `Administrator`
com `developer_mode` ligado (`validate`). Ou seja: **em ambiente de desenvolvimento, salvar
um relatório na interface cria arquivos não versionados dentro do app** — que aparecem no
`git status` sem que ninguém tenha editado código.

Não é bug; é o mecanismo com que os relatórios do ERPNext foram criados. Mas convém saber
antes de ver o `git status` sujo.

Relacionado: um relatório padrão **não pode ser editado** pela interface ("Cannot edit a
standard report. Please duplicate and create a new report") nem apagado fora de
`developer_mode`.

---

## Qual escolher

```
O pedido cabe em colunas de um DocType e seus links?
  └─ sim  → Report Builder            (custo zero, sem manutenção)
  └─ não  → precisa de cálculo, condicional ou coluna derivada?
              └─ não  → Query Report  (SQL; lembre do filtro de permissão)
              └─ sim  → Script Report em arquivo, versionado
```

**Comece sempre pelo Report Builder.** Um Query Report escrito por atalho vira dívida: não
tem teste, não passa por revisão e — pela regra de permissão acima — é onde vazamento de
dado aparece.

## Fontes

- `frappe/core/doctype/report/report.py` — `validate`, `execute_query_report`,
  `execute_script_report`, `export_doc`, o limite de 15 s.
- `frappe/utils/safe_exec.py` — `check_safe_sql_query`.
- `frappe/desk/query_report.py` — verificação de permissão (`report` sobre o `ref_doctype`).
- `frappe/core/doctype/report_column/`, `report_filter/`, `prepared_report/`.
- `erpnext/accounts/report/gross_profit/` — exemplo de Script Report padrão em arquivo.
