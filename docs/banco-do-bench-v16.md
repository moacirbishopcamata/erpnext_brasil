# Subir o banco do bench v16: quatro problemas e o que cada um ensinou

O bench v16 (`~/frappe-bench-16`, frappe 16.31.0, erpnext 16.33.0) tinha o código
completo e **nunca teve site** — `bench new-site v16.localhost` falhava. O sintoma
mais visível era um `Access denied` do MariaDB, e a leitura óbvia dele ("a senha do
root está errada") estava **errada**. Este documento registra os quatro obstáculos
reais, na ordem em que apareceram, porque nenhum deles é específico deste projeto:
são armadilhas de bench Frappe sobre um MariaDB que ninguém endureceu.

## 1. O Redis do bench não sobe sozinho

**Sintoma.** Antes de qualquer erro de banco, o `new-site` morria em
`redis.exceptions.TimeoutError: Timeout connecting to server`, com um traceback longo
que passa por `frappe/__init__.py::setup_redis_cache_connection`. O banco nem chegava
a ser tocado.

**Causa.** Cada bench tem o seu par de portas Redis no `common_site_config.json`. O
`~/frappe-bench` usa 11000 (fila) e 13000 (cache); o `~/frappe-bench-16` usa **11001 e
13001**. Só o primeiro par estava no ar. O diretório `config/` do bench-16 tinha apenas
`pids/` — nenhum `redis_*.conf` gerado.

**Saída.** Subir dois `redis-server` avulsos nessas portas, com `--dir` num caminho do
**Linux** e não em `/mnt/g`: volume `drvfs` não suporta os locks que o Redis usa para o
arquivo de dump (armadilha já registrada no ambiente).

> **A lição de ordem:** o erro de Redis mascarava tudo o que vinha depois. Um bench sem
> Redis nunca chega a mostrar o problema de banco — e é fácil concluir que "o
> `new-site` está quebrado" quando só falta um daemon.

## 2. `--no-mariadb-socket` cria o usuário em `'%'`, e aqui `'%'` não vale

**Sintoma.** Com o Redis no ar, o `new-site` avançou: criou o banco, criou o usuário, e
morreu na **restauração do SQL base** com

```
ERROR 1045 (28000): Access denied for user '_9874459769f52231'@'localhost' (using password: YES)
```

**O que a mensagem parece dizer, e não diz.** Parece senha errada. Não é. Duas provas:

1. Redefinir a senha como root (`SET PASSWORD FOR ...`) para exatamente o valor do
   `site_config.json` **não mudou nada** — continuou negando.
2. O usuário existia, com `plugin = mysql_native_password` e hash preenchido, idêntico
   em forma ao usuário do site v15 que **funciona**.

A diferença entre os dois estava no **host da conta**:

| conta | host | funciona? |
|---|---|---|
| `_99435b0941e32814` (site v15) | `localhost` **e** `127.0.0.1` | sim |
| `_9874459769f52231` (site v16) | `%` | não |

O flag `--no-mariadb-socket` faz o Frappe criar a conta apenas em `'%'`. Sem o flag,
ele cria em `localhost` e `127.0.0.1` — que é como o site v15 nasceu.

**Nota sobre a mensagem.** Mesmo conectando por TCP em `127.0.0.1`, o erro diz
`@'localhost'`: com `skip_name_resolve = OFF`, o servidor resolve `127.0.0.1` para o
nome `localhost` antes de casar a conta. Ler o host da mensagem como "veio por socket"
leva para o caminho errado.

## 3. A causa real: contas anônimas herdadas do datadir

Restava a pergunta que o item 2 não responde: **por que `'%'` não casa?** Em
MySQL/MariaDB, `'%'` casa com qualquer host, inclusive `localhost` — deveria funcionar.

**Teste isolado**, sem nada do Frappe no meio:

```sql
CREATE USER 'tst1'@'%'         IDENTIFIED BY 'abc123';  -- negado ao conectar
CREATE USER 'tst2'@'localhost' IDENTIFIED BY 'abc123';  -- conecta
```

Com o comportamento reproduzido em duas linhas, a causa apareceu em
`mysql.global_priv`:

```
[]@[localhost]
[]@[desktop-9rnquit]
```

**Contas anônimas** — usuário de nome vazio —, resquício de um datadir que nunca passou
pelo `mysql_secure_installation`. O MariaDB ordena as contas da **mais específica para a
mais genérica** e usa a primeira que casa: uma conexão vinda de `localhost` casa
`''@'localhost'` **antes** de `usuario@'%'`, e aí a autenticação falha com a senha do
usuário real — reportando o nome do usuário que você pediu, não o da conta que casou.
É por isso que a mensagem engana.

**Correção** (que também é endurecimento de segurança):

```sql
DROP USER ''@'localhost';
DROP USER ''@'desktop-9rnquit';
FLUSH PRIVILEGES;
```

Provado nos dois sentidos: antes, `tst1@'%'` era negado; depois, entra e reporta
`current_user() = tst3@%`.

> **A lição:** um `Access denied` nomeia a conta **solicitada**, nunca a conta que o
> servidor de fato casou. Quando a senha comprovadamente confere, o próximo lugar a
> olhar é a **ordem de casamento de host**, não a senha.

## 4. `apps.txt` sem quebra de linha final

O `sites/apps.txt` do bench-16 terminava sem `\n`. É a mesma armadilha que já tinha
feito uma instalação de app falhar com `App hrms not in apps.txt`: quem lê o arquivo
partindo as linhas não enxerga o último app, ou o cola no próximo texto. Barato de
conferir e invisível a olho nu — `od -c` mostra:

```
0000000   f r a p p e \n e r p n e x t \n e r p n e x t _ b r a s i l \n
```

## Qual versão de MariaDB usar

Verificado na fonte, em `frappe/database/mariadb/setup_db.py::check_compatible_versions`
do frappe v16 — não em documentação de terceiros:

- **abaixo de 10.6**: `"is older than 10.6 which is not supported by Frappe"`;
- **acima de 11.8**: `"is newer than 11.8 which is not yet tested with Frappe Framework"`.

O CI do frappe v16 (`_base-server-tests.yml`, `_base-migration.yml`,
`_base-ui-tests.yml`) e o `patch.yml` do erpnext v16 rodam **`mariadb:11.8`**; um job de
teste individual do erpnext ainda usa `10.6`, o piso da janela.

Este ambiente roda **10.11.9 (LTS)** — dentro da janela suportada, mas não é a versão do
CI. **Não se atualizou**, por dois motivos: nenhum dos quatro problemas acima tem
relação com a versão (o item 3 é configuração do datadir, e existiria igual no 11.8), e
migrar o datadir poria em risco o site v15, hoje o outro ambiente funcional.

## Receita, na ordem que funciona

```sh
# 1. Redis do bench-16, em caminho Linux
mkdir -p ~/redis16
redis-server --port 11001 --daemonize yes --dir ~/redis16 --dbfilename q.rdb --save ""
redis-server --port 13001 --daemonize yes --dir ~/redis16 --dbfilename c.rdb --save ""

# 2. contas anônimas fora (uma vez por datadir)
mariadb -h 127.0.0.1 -u root -p -e "DROP USER ''@'localhost'; FLUSH PRIVILEGES;"

# 3. apps.txt com quebra de linha final
printf "frappe\nerpnext\nerpnext_brasil\n" > sites/apps.txt

# 4. site — SEM --no-mariadb-socket
bench new-site v16.localhost --db-root-password <senha> --admin-password <senha>
bench --site v16.localhost install-app erpnext
bench --site v16.localhost install-app erpnext_brasil
```

## O que a validação no v16 mostrou

Com o site no ar, a conferência dos campos do app contra as colunas reais:

```
campos declarados: 405 em 24 DocTypes
DocTypes ausentes no site: ['Salary Component']   (vem do hrms, não instalado)
campos sem prefixo br_: []
breaks de layout sem coluna (esperado): 62
CAMPOS DE DADO sem coluna (gap): 0
```

E o índice composto de `Transmissao Fiscal` nasceu correto:
`documento_tipo_documento_index` sobre `(documento_tipo, documento)`.

**A separação entre "break de layout" e "campo de dado" é o que dá valor à conferência.**
Uma checagem crua acusaria "62 campos sem coluna" e pareceria um gap grande; breaks de
seção e coluna **não têm coluna por definição**. Sem separar por `fieldtype`, o número
assusta e não informa — e o gap real, que era zero, ficaria escondido no meio.
