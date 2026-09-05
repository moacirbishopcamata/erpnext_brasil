# Como rodar Frappe + ERPNext + erpnext_brasil

`scripts/subir.sh` sobe a pilha inteira — MariaDB, Redis e o servidor web — **sem `sudo` e
sem Docker**. Testado nesta máquina: `HTTP 200` em `/login` e em
`/api/method/frappe.ping`.

```bash
bash scripts/subir.sh
```

Depois: <http://localhost:8000>, usuário `Administrator`.

## Variáveis

| Variável | Padrão | Para quê |
|---|---|---|
| `BENCH` | `~/frappe-bench` | outro bench (ex.: `~/frappe-bench-16`) |
| `PORTA` | `8000` | rodar dois benches ao mesmo tempo |
| `PORTA_MARIADB` | `3306` | quando a 3306 já está tomada |
| `REDIS_CACHE` / `REDIS_QUEUE` | `13000` / `11000` | idem |
| `VOLUMES` | `/mnt/g/erpnext-dados` | onde o Redis persiste |

```bash
BENCH=~/frappe-bench-16 PORTA=8001 REDIS_CACHE=13001 REDIS_QUEUE=11001 bash scripts/subir.sh
```

⚠️ **Dois benches nunca devem compartilhar o mesmo Redis.** Eles dividem o espaço de
chaves, e cache de um site respondendo consulta de outro aparece como **dado errado**, não
como falha.

## Por que o script existe

`bench start` sozinho não basta aqui. Ele lê o `Procfile`, que pressupõe um MariaDB já no
ar e sobe o Redis por `honcho`. Neste ambiente o MariaDB é um tarball em espaço de usuário
e os Redis rodam soltos — alguém precisa ordenar isso, e o script é esse alguém.

Ele é **idempotente**: rodar duas vezes não duplica processo nem perde dado.

## As decisões que o script toma, e por quê

### O datadir do MariaDB fica em ext4, não no `G:`

Testado e confirmado: em `/mnt/g` (drvfs) o `mariadb-install-db` passa, o servidor sobe, um
teste de escrita e leitura passa — e então o `bench migrate`, com sua carga real de DDL,
produz `corruption in the InnoDB tablespace` e crash em sinal 6.

A lição vale além do banco: **teste pequeno não prova durabilidade**. A escrita de uma
linha passou; o que quebrou foi o volume. A persistência no `G:` se faz por **dump**, não
por datadir.

O Redis, ao contrário, funciona no `G:` — RDB é gravação sequencial, não InnoDB.

### O site padrão vai em `default_site`, não em `currentsite.txt`

Sem site escolhido, `bench serve` devolve **404 em toda rota, inclusive `/login`** — o que
parece servidor quebrado quando é só configuração faltando. Custou uma rodada de
diagnóstico.

O `currentsite.txt` **deixou de ser suportado**; o próprio Frappe avisa em tempo de
execução. O certo é `default_site` no `common_site_config.json`, escrito por `bench use`.

Havendo um único site, o script escolhe. Havendo vários, ele **para e pede** — adivinhar
qual atender é o tipo de decisão que grava dado no lugar errado.

### Verificação de porta com `timeout`

Nesta máquina, conectar a porta fechada **pendura** em vez de falhar rápido (rede espelhada
do WSL). Um `redis-cli ping || redis-server` trava o script inteiro. Por isso toda checagem
usa `timeout 3` sobre `/dev/tcp`.

Pelo mesmo motivo o script **não usa `pgrep -f`**: esse padrão casa com a própria linha de
comando que o contém, e já matou o próprio shell nesta sessão.

### `bench serve` e não `bench start`

O `start` usa o `Procfile`, que tentaria subir outro Redis nas mesmas portas e falharia.
Quando o script chega ao fim, a infraestrutura já está de pé.

## Parar

`Ctrl+C` encerra **só o servidor web**. MariaDB e Redis continuam — de propósito: eles
demoram a subir e não guardam estado de sessão.

Para derrubar tudo:

```bash
kill $(ss -lptn 'sport = :3306' | grep -oP 'pid=\K[0-9]+' | sort -u)
kill $(ss -lptn 'sport = :13000' | grep -oP 'pid=\K[0-9]+' | sort -u)
kill $(ss -lptn 'sport = :11000' | grep -oP 'pid=\K[0-9]+' | sort -u)
```

Pelo **dono da porta**, não por nome de processo — ver acima sobre `pgrep -f`.

## Quando falta alguma coisa

O script recusa e diz o que fazer. Todas as dependências se instalam **sem `sudo`**:

```bash
uv python install 3.14          # exigido pelo Frappe v16
uv tool install pkgconf         # já instala com o nome `pkg-config`
uv tool install cmake
curl -LO https://nodejs.org/dist/v24.20.0/node-v24.20.0-linux-x64.tar.xz  # v16 exige Node >= 24
```

E o MariaDB pelo tarball genérico de `archive.mariadb.org`, que roda como usuário comum.

⚠️ Se `mysqlclient` falhar ao compilar dizendo que não acha o MariaDB, é o `pkgconf` do
PyPI recusando procurar `.pc` do sistema. A saída:

```bash
export MYSQLCLIENT_CFLAGS="$(mariadb_config --cflags)"
export MYSQLCLIENT_LDFLAGS="$(mariadb_config --libs)"
```

Ver também [ambiente-dev-bench.md](ambiente-dev-bench.md).
