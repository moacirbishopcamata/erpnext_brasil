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

## 4. `bench get-app` não registra o app, e o `apps.txt` sem `\n` final

São **dois** problemas distintos que produzem a mesma mensagem — `App X not in apps.txt` —
e por isso é fácil corrigir um e achar que corrigiu o outro.

### 4a. `get-app` baixa mas não registra

`bench get-app hrms --branch version-16` clona o app em `apps/hrms`, instala as
dependências e **termina com sucesso**. O app fica no lugar certo, aparece em `ls apps`,
com branch e tag corretos — e o `sites/apps.txt` **continua sem ele**. O `install-app`
seguinte falha.

O `apps.txt` é a lista do que aquele conjunto de sites considera instalável; o `get-app`
mexe no diretório, não nessa lista. Tratar os dois como a mesma coisa é o erro:

```sh
ls apps                 # erpnext  erpnext_brasil  frappe  hrms
cat sites/apps.txt      # frappe   erpnext   erpnext_brasil      <- hrms não está
```

### 4b. O arquivo sem quebra de linha final

O `sites/apps.txt` do bench-16 terminava sem `\n`. Quem lê o arquivo partindo as linhas
não enxerga o último app, ou o cola no texto seguinte. É **invisível** num `cat` — só
aparece quando a saída gruda no próximo comando, ou com `od -c`.

**A correção que resolve os dois de uma vez** é reescrever o arquivo inteiro com `printf`,
em vez de acrescentar linha com `>>` — que herda a falta de quebra do que já estava lá:

```sh
printf "frappe\nerpnext\nerpnext_brasil\nhrms\n" > sites/apps.txt
od -c sites/apps.txt | tail -2      # confere o \n final
```

### 4c. Instalar um app **depois** deixa os nossos campos inertes — gap de costura real

Isto não é erro de bench, é armadilha do nosso app, e o v16 a expôs.

`criar_campos_fiscais()` **pula os DocTypes que não existem no site** — é o filtro que
permite o app rodar sem o hrms. Com o `erpnext_brasil` instalado antes do `hrms`, os
campos de `Salary Component` foram legitimamente pulados. Instalar o `hrms` depois **não
os cria**: o `install-app` do hrms não conhece os nossos campos.

Medido no v16, logo após instalar o hrms:

```
CAMPOS DE DADO sem coluna (gap): 2
   !! Salary Component.br_cod_rubrica (Data)
   !! Salary Component.br_ide_tab_rubr (Data)
```

**Nada quebraria.** `doc.get("br_cod_rubrica")` devolveria `None` e a rubrica do eSocial
sairia vazia — o gap de costura clássico: código escrito, testado e inalcançável.

O `after_migrate` **se cura sozinho**, e isso foi verificado, não suposto: um
`bench migrate` depois, o mesmo script devolve `CAMPOS DE DADO sem coluna (gap): 0`. Mas a
cura só chega no próximo `migrate` — a janela entre instalar o app novo e migrar é tempo
real em que a folha grava sem rubrica.

> **Regra:** depois de todo `install-app` de app de terceiros, rodar `bench migrate`. Não é
> higiene opcional; é o que traz os nossos campos para os DocTypes que acabaram de nascer.

### 4d. O resíduo que o v15 deixou, e o v16 não teve

A primeira tentativa de instalar o hrms (no bench v15) falhou pela metade e deixou um
`Module Def` "HR" órfão; toda tentativa seguinte batia em
`DuplicateEntryError: ('Module Def', 'HR')`. No site v16, recém-criado, o mesmo
`install-app hrms` passou limpo — a diferença era o resíduo, não o comando.

**O `install-app` não é transacional**: uma falha no meio deixa registros criados para
trás, e a tentativa seguinte colide com o que a primeira criou. Em site de produção isso
significa apagar o órfão à mão antes de repetir — não adianta insistir no mesmo comando.

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

# 5. app de terceiros: get-app NÃO registra, e todo install-app pede migrate depois
bench get-app hrms --branch version-16
printf "frappe
erpnext
erpnext_brasil
hrms
" > sites/apps.txt
bench --site v16.localhost install-app hrms
bench --site v16.localhost migrate          # sem isto, nossos campos do hrms não existem
```

## O que a validação no v16 mostrou

Com o site no ar, a conferência dos campos do app contra as colunas reais:

```
campos declarados: 405 em 24 DocTypes
campos sem prefixo br_: []
breaks de layout sem coluna (esperado): 63
CAMPOS DE DADO sem coluna (gap): 0
```

Antes do hrms havia um DocType ausente (`Salary Component`) e 62 breaks; depois de
instalá-lo e migrar, **nenhum DocType do app falta no site** e os 63 breaks continuam
sendo o único item sem coluna.

E o índice composto de `Transmissao Fiscal` nasceu correto:
`documento_tipo_documento_index` sobre `(documento_tipo, documento)`.

**A separação entre "break de layout" e "campo de dado" é o que dá valor à conferência.**
Uma checagem crua acusaria "62 campos sem coluna" e pareceria um gap grande; breaks de
seção e coluna **não têm coluna por definição**. Sem separar por `fieldtype`, o número
assusta e não informa — e o gap real, que era zero, ficaria escondido no meio.
