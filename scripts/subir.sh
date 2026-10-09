#!/bin/bash
# Sobe a pilha inteira — MariaDB, Redis e o servidor do Frappe com ERPNext e
# erpnext_brasil — a partir do zero, sem `sudo` e sem Docker.
#
# Por que existe
# --------------
# `bench start` sozinho não basta neste ambiente: ele lê o `Procfile`, que assume um
# MariaDB já no ar e um Redis que ele mesmo sobe por `honcho`. Aqui o MariaDB é um
# tarball em espaço de usuário e os Redis rodam soltos, então alguém precisa ordená-los.
# Esse alguém é este script.
#
# Ele é **idempotente**: rodar duas vezes não duplica processo nem perde dado. Cada etapa
# verifica antes de agir, e as verificações não usam `pgrep -f` — nesta máquina esse
# padrão casa com a própria linha de comando que o contém e já matou o próprio shell.
#
# Uso
# ---
#   bash scripts/subir.sh                        # bench v16 (o padrão)
#   BENCH=~/frappe-bench bash scripts/subir.sh   # o antigo, v15
#   PORTA=8080 bash scripts/subir.sh
#   SO_SERVICOS=1 bash scripts/subir.sh          # só MariaDB e Redis
#
# `SO_SERVICOS=1` sobe MariaDB e Redis e **para aí**. É o modo certo antes de um
# `bench migrate`, de um `bench execute` ou de qualquer script: nenhum deles precisa do
# servidor web, e deixá-lo em primeiro plano bloquearia o terminal.
set -u

# ⚠️ O padrão é o bench **v16**, e não o v15.
#
# Há dois benches nesta máquina, e a decisão do projeto é a version-16 — `frappe` 16.31,
# `erpnext` 16.33, site `v16.localhost`. Um padrão apontando para o v15 faria o caminho
# mais curto ser o errado, e "validar na versão errada" já aconteceu aqui uma vez.
#
# Para o antigo, explicitamente: `BENCH=~/frappe-bench bash scripts/subir.sh`
BENCH="${BENCH:-$HOME/frappe-bench-16}"
PORTA="${PORTA:-8001}"
DADOS_MARIADB="${DADOS_MARIADB:-$HOME/mariadb-data}"
BASE_MARIADB="${BASE_MARIADB:-$HOME/mariadb-10.11.9-linux-systemd-x86_64}"
PORTA_MARIADB="${PORTA_MARIADB:-3306}"
SO_SERVICOS="${SO_SERVICOS:-}"
VOLUMES="${VOLUMES:-/mnt/g/erpnext-dados}"

# Node e as ferramentas instaladas por `uv tool` vivem fora do PATH padrão.
export PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"

vermelho() { printf '\033[31m%s\033[0m\n' "$1"; }
verde() { printf '\033[32m%s\033[0m\n' "$1"; }
amarelo() { printf '\033[33m%s\033[0m\n' "$1"; }

no_ar() {
	# `timeout` porque nesta máquina a conexão a porta fechada **pendura** em vez de
	# falhar rápido — efeito da rede espelhada do WSL.
	timeout 3 bash -c "echo > /dev/tcp/127.0.0.1/$1" 2>/dev/null
}

exigir() {
	command -v "$1" > /dev/null 2>&1 && return 0

	vermelho "Falta '$1'. $2"
	exit 1
}

# ---------------------------------------------------------------- pré-requisitos

[ -d "$BENCH" ] || {
	vermelho "Bench não encontrado em $BENCH"
	exit 1
}

exigir redis-server "Instale com: sudo apt install redis-server"

# ⚠️ As portas do Redis são **lidas do bench**, não fixadas aqui.
#
# Cada bench declara as suas em `common_site_config.json`, e elas diferem: o de v15 usa
# 11000/13000, o de v16 usa 11001/13001. Um padrão fixo funcionaria num e falharia no
# outro — e o modo de falhar é o pior possível: o script diz "Redis no ar" (porque a porta
# do outro bench está mesmo no ar) e o `bench` seguinte morre em `TimeoutError`, sem que a
# mensagem tenha relação com a causa. Aconteceu em 2026-09-07.
LEITURA_DE_PORTAS=$(python3 - "$BENCH" <<'FIM'
import json, pathlib, sys, urllib.parse

config = pathlib.Path(sys.argv[1]) / "sites" / "common_site_config.json"
dados = json.loads(config.read_text()) if config.exists() else {}


def porta(chave, padrao):
	url = dados.get(chave) or ""
	achado = urllib.parse.urlparse(url).port if "://" in url else None

	return achado or padrao


print(porta("redis_queue", 11000), porta("redis_cache", 13000))
FIM
)
REDIS_QUEUE="${REDIS_QUEUE:-${LEITURA_DE_PORTAS%% *}}"
REDIS_CACHE="${REDIS_CACHE:-${LEITURA_DE_PORTAS##* }}"

amarelo "Bench: $BENCH  |  Redis fila $REDIS_QUEUE, cache $REDIS_CACHE"

# O banco padrão do bench vem do `common_site_config.json` (`db_type`; ausente = mariadb).
# Com PostgreSQL o servidor fica **fora** deste script — nesta máquina, no Windows, alcançado
# do WSL pela rede espelhada (docs/postgresql.md) — então só se confere que a porta responde.
DB_TYPE="$(python3 -c "import json,sys; c=json.load(open(sys.argv[1])); print(c.get('db_type') or 'mariadb')" "$BENCH/sites/common_site_config.json" 2>/dev/null || echo mariadb)"
DB_HOST="$(python3 -c "import json,sys; c=json.load(open(sys.argv[1])); print(c.get('db_host') or '127.0.0.1')" "$BENCH/sites/common_site_config.json" 2>/dev/null || echo 127.0.0.1)"
PORTA_POSTGRES="${PORTA_POSTGRES:-$(python3 -c "import json,sys; c=json.load(open(sys.argv[1])); print(c.get('db_port') or 5432)" "$BENCH/sites/common_site_config.json" 2>/dev/null || echo 5432)}"

if [ "$DB_TYPE" = "postgres" ]; then
	if timeout 3 bash -c "echo > /dev/tcp/$DB_HOST/$PORTA_POSTGRES" 2>/dev/null; then
		verde "PostgreSQL responde em $DB_HOST:$PORTA_POSTGRES (servidor externo a este script)"
	else
		vermelho "O bench usa PostgreSQL, mas nada responde em $DB_HOST:$PORTA_POSTGRES"
		amarelo "Suba o serviço do PostgreSQL (no Windows: services.msc → postgresql) e rode de novo."
		exit 1
	fi
elif [ ! -x "$BASE_MARIADB/bin/mariadbd" ]; then
	vermelho "MariaDB não encontrado em $BASE_MARIADB"
	amarelo "Baixe o tarball genérico (não precisa de sudo):"
	amarelo "  curl -LO https://archive.mariadb.org/mariadb-10.11.9/bintar-linux-systemd-x86_64/mariadb-10.11.9-linux-systemd-x86_64.tar.gz"
	amarelo "  tar xzf mariadb-10.11.9-linux-systemd-x86_64.tar.gz -C ~"
	exit 1
fi

# ---------------------------------------------------------------- MariaDB

if [ "$DB_TYPE" = "postgres" ]; then
	: # nada a subir — ver acima
elif no_ar "$PORTA_MARIADB"; then
	verde "MariaDB já no ar na porta $PORTA_MARIADB"
else
	# O datadir fica em ext4 de propósito. Em `/mnt/g` (drvfs) o InnoDB **corrompe o
	# tablespace** sob carga real de DDL — testado, com crash em sinal 6. A persistência
	# no G: se faz por dump, não por datadir.
	if [ ! -d "$DADOS_MARIADB/mysql" ]; then
		amarelo "Inicializando o datadir em $DADOS_MARIADB"
		mkdir -p "$DADOS_MARIADB"
		(cd "$BASE_MARIADB" && ./scripts/mariadb-install-db --user="$USER" \
			--basedir=. --datadir="$DADOS_MARIADB" > /tmp/mariadb-install.log 2>&1) || {
			vermelho "Falha ao inicializar o datadir; veja /tmp/mariadb-install.log"
			exit 1
		}
	fi

	amarelo "Subindo o MariaDB na porta $PORTA_MARIADB"
	(cd "$BASE_MARIADB" && setsid nohup ./bin/mariadbd \
		--datadir="$DADOS_MARIADB" --socket=/tmp/mariadb.sock --port="$PORTA_MARIADB" \
		< /dev/null > "$HOME/mariadb.log" 2>&1 &)

	for _ in $(seq 1 30); do
		sleep 2
		no_ar "$PORTA_MARIADB" && break
	done

	no_ar "$PORTA_MARIADB" && verde "MariaDB no ar" || {
		vermelho "MariaDB não subiu; veja $HOME/mariadb.log"
		exit 1
	}
fi

# ---------------------------------------------------------------- Redis

# Redis em `/mnt/g` funciona: o RDB é gravação sequencial, não InnoDB.
subir_redis() {
	local porta="$1" pasta="$2" arquivo="$3"

	if no_ar "$porta"; then
		verde "Redis já no ar na porta $porta"
		return
	fi

	mkdir -p "$VOLUMES/$pasta"
	redis-server --port "$porta" --dir "$VOLUMES/$pasta" \
		--dbfilename "$arquivo" --save '60 1' --daemonize yes 2>&1 | tail -1

	sleep 2
	no_ar "$porta" && verde "Redis no ar na porta $porta" || vermelho "Redis $porta não subiu"
}

# Pasta por porta, e não por papel: dois benches no ar gravariam o mesmo `cache.rdb` em
# cima um do outro, e o segundo a subir carregaria o dump do primeiro.
subir_redis "$REDIS_CACHE" "redis-cache-$REDIS_CACHE" cache.rdb
subir_redis "$REDIS_QUEUE" "redis-queue-$REDIS_QUEUE" queue.rdb

if [ -n "$SO_SERVICOS" ]; then
	echo
	verde "Banco ($DB_TYPE) e Redis no ar. Servidor web não foi iniciado (SO_SERVICOS)."
	exit 0
fi

# ---------------------------------------------------------------- Frappe

cd "$BENCH" || exit 1

# `bench serve` sem site escolhido devolve **404 em toda rota**, inclusive `/login` — o
# que parece servidor quebrado quando é só site não definido.
#
# O padrão vai em `default_site` do `common_site_config.json`, e **não** em
# `currentsite.txt`: o Frappe avisa em tempo de execução que o segundo deixou de ser
# suportado. `bench use` é quem escreve a chave certa.
#
# Havendo um único site, escolhe-se ele; havendo vários, exige-se a escolha, porque
# adivinhar qual atender é o tipo de decisão que produz dado no lugar errado.
SITE=$(python3 -c "
import json, pathlib
config = pathlib.Path('sites/common_site_config.json')
print(json.loads(config.read_text()).get('default_site', '') if config.exists() else '')
" 2>/dev/null)

if [ -z "$SITE" ]; then
	SITES=$(find sites -maxdepth 2 -name site_config.json -exec dirname {} \; | xargs -r -n1 basename)
	QUANTOS=$(echo "$SITES" | grep -c .)

	if [ "$QUANTOS" -eq 1 ]; then
		"$HOME/.local/bin/bench" use "$SITES" > /dev/null 2>&1
		SITE="$SITES"
		amarelo "Site padrão definido: $SITE"
	elif [ "$QUANTOS" -eq 0 ]; then
		vermelho "Nenhum site em $BENCH/sites."
		amarelo "Crie um com:"
		amarelo "  bench new-site meu-site.localhost --install-app erpnext --install-app erpnext_brasil"
		exit 1
	else
		vermelho "Há mais de um site e nenhum padrão definido:"
		echo "$SITES" | sed 's/^/  - /'
		amarelo "Escolha com: bench use <site>"
		exit 1
	fi
fi

echo
verde "Pilha pronta. Subindo o servidor em http://localhost:$PORTA"
verde "Site: $SITE"
amarelo "Ctrl+C encerra o servidor; banco e Redis continuam no ar."
echo

# `bench serve` e não `bench start`: o `start` usa o Procfile, que sobe outro Redis nas
# mesmas portas e falha. Aqui a infraestrutura já está de pé.
exec "$HOME/.local/bin/bench" serve --port "$PORTA"
