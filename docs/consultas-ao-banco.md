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

⚠️ **É aqui que estava o ganho real deste app.** As consultas que crescem sem limite são as
de `Transmissao Fiscal` filtrando por `documento_tipo` + `documento` — o painel de situação
fiscal faz uma **a cada abertura de formulário**. Sem índice nesse par, é varredura de
tabela numa tabela que cresce com cada nota emitida.

✅ Feito — ver [O índice que faltava](#o-índice-que-faltava--feito) abaixo.

### 2. `permission_query_conditions` — injetar `WHERE` do lado de fora

Hook do Frappe (`frappe/hooks.py`) que acrescenta condição a **toda** listagem de um
DocType, sem tocar em quem consulta.

⚠️ **Não é preciso para restringir por empresa** — o Frappe já aplica User Permission a todo
campo Link sozinho. Ver a correção no fim deste documento. Serve para restrições que **não**
sejam por um campo Link: um filtro por período, por exemplo, ou por um cálculo.

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

## O índice que faltava — feito

`Transmissao Fiscal (documento_tipo, documento)`, criado por `setup/install.py` no
`after_install` **e** no `after_migrate`.

É a consulta mais quente do app: o painel de situação fiscal a executa a **cada `refresh` de
formulário**, numa tabela que cresce com toda nota emitida. Sem índice é varredura — e o
custo só aparece meses depois, quando ninguém mais associa a lentidão a esta consulta. É o
oposto de um erro alto, e por isso ganhou teste.

Três decisões:

- **Composto, não dois simples.** O banco usa um índice composto inteiro onde usaria só o
  primeiro de dois separados. Declarar dois pareceria equivalente e não seria.
- **No `after_migrate` também.** Só no `after_install` deixaria de fora todo site já
  existente — e é justamente o site com dados acumulados que precisa do índice.
- **`frappe.db.add_index`, não SQL.** Ele confere `has_index` antes de criar, então rodar a
  cada migração é barato e devolve o índice se alguma migração o tiver removido.

### ⚠️ Correção: `Numeracao Fiscal` **não** precisa de índice

A primeira redação deste documento listava um índice para ela, com o argumento de que ali
o índice não seria só velocidade, e sim **tamanho do lock**. O argumento é bom e o caso
estava errado.

O `SELECT ... FOR UPDATE` da alocação busca **pelo `name`**:

```python
frappe.db.get_value(DOCTYPE, nome, "ultimo_numero", for_update=True)
```

E o `autoname` daquele DocType é `format:{company}-{modelo}-{serie}` — **a chave primária já
é a combinação procurada**. Um índice sobre os três campos duplicaria a chave, custando
escrita sem ganhar leitura.

Foi erro de leitura: supus que a consulta filtrava por campos, e ela filtra por `name`. Dois
testes travam isso — um confere que o índice não existe, o outro confere que o `autoname`
continua sendo a combinação, porque o primeiro só vale enquanto o segundo for verdade.

## ⚠️ Segunda correção: `permission_query_conditions` **não** é necessário

Este documento afirmava que faltava um `permission_query_conditions` para que um site
multiempresa não mostrasse transmissão de outra `Company`. **O Frappe já faz isso.**

`frappe/model/db_query.py`, em `add_user_permissions`, percorre **todo campo Link** do
DocType (`doctype_meta.get_link_fields()`) e aplica a User Permission correspondente. O
campo `company` entra nessa varredura como qualquer outro — não há nada a acrescentar.

Escrever o hook teria produzido código redundante, que é pior que código faltando: alguém
depois teria de descobrir por que existem duas restrições fazendo a mesma coisa.

### O que **de fato** sustenta a proteção

Três condições, todas do lado do app, todas travadas por teste:

1. **O DocType tem campo `company`.** Sem ele não há por onde restringir.
2. **O campo é obrigatório.** Com `apply_strict_user_permissions` desligado — que é o
   **padrão** —, o Frappe deixa passar registro com o campo vazio (`ifnull(company,'')=''`).
   Campo obrigatório fecha esse buraco sem depender de configuração do site.
3. **O campo não tem `ignore_user_permissions`**, que desligaria a restrição para ele.

Os quatro DocTypes deste app cumprem as três. Se qualquer uma cair, a restrição para de
valer **sem erro nenhum** — as listagens simplesmente passam a mostrar mais.

### E nenhuma leitura contorna a permissão

`ignore_permissions` aparece 18 vezes na integração, **todas em escrita** (`insert`/`save`).
Isso é legítimo: gravar o registro de auditoria não deve depender de o usuário poder criar
um `Transmissao Fiscal` à mão. Em **leitura**, a marca desligaria a separação entre empresas
— e um teste varre as chamadas de `get_all`/`get_list`/`get_value` para garantir que não
aparece lá.

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
