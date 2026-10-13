#!/bin/bash
# Traz um app *_Brasil (sus_brasil, hrms_brasil, healthcare_brasil, wms_sus_brasil) para o bench e o instala num site.
#
# Uso
# ---
#   bash scripts/instalar_app_brasil.sh sus_brasil                       # site fr16pg.localhost, ramo main
#   bash scripts/instalar_app_brasil.sh sus_brasil fr16pg.localhost cadastros-doctypes
#   FONTE=https://github.com/moacirbishopcamata/sus_brasil bash scripts/instalar_app_brasil.sh sus_brasil
#
# O que ele faz e por quê (cada passo é uma armadilha já vivida; ver docs/como-subir-os-modulos.md):
#   1. Redis: sobe os dois do bench se não estiverem no ar. NÃO sobe banco — os sites de teste usam o PostgreSQL do
#      Windows (docs/postgresql.md). `scripts/subir.sh` esperaria o MariaDB e travaria.
#   2. `bench get-app` baixa, mas NÃO registra no `sites/apps.txt` (e o arquivo costuma vir sem `\n` final).
#   3. `install-app` e, em seguida, `migrate`: instalar um app depois de outro deixa campos inertes até o migrate.
#
# Redirecione a saída para arquivo se chamar de outro script (um pipe herdado pendura; ver como-rodar.md).
set -u

APP="${1:?uso: instalar_app_brasil.sh <app> [site] [ramo]}"
SITE="${2:-fr16pg.localhost}"
RAMO="${3:-main}"
BENCH="${BENCH:-$HOME/frappe-bench-16}"
FONTE="${FONTE:-/mnt/g/PROJECTS/$APP}"
REDIS="${REDIS_SERVER:-$HOME/redis-7.2.16/src/redis-server}"
[ -x "$REDIS" ] || REDIS=redis-server

export PATH="$HOME/.local/bin:$PATH"

cd "$BENCH" || { echo "bench não encontrado: $BENCH"; exit 1; }

portas="$(python3 - "$BENCH/sites/common_site_config.json" <<'PY'
import json, sys, urllib.parse
c = json.load(open(sys.argv[1]))
print(*(urllib.parse.urlparse(c[k]).port for k in ("redis_cache", "redis_queue")))
PY
)"

for porta in $portas; do
	if timeout 3 bash -c "echo > /dev/tcp/127.0.0.1/$porta" 2>/dev/null; then
		echo "Redis $porta já no ar"
	else
		mkdir -p "$HOME/redis-$porta"
		setsid nohup "$REDIS" --port "$porta" --dir "$HOME/redis-$porta" > "$HOME/redis-$porta/log" 2>&1 < /dev/null &
		sleep 1
		echo "Redis $porta iniciado"
	fi
done

git config --global --add safe.directory '*'

if [ ! -d "apps/$APP" ]; then
	bench get-app --branch "$RAMO" "$FONTE" || exit 1
fi

if ! grep -qx "$APP" sites/apps.txt; then
	printf '%s\n' "$(cat sites/apps.txt)" "$APP" > sites/apps.txt.novo && mv sites/apps.txt.novo sites/apps.txt
fi

if ! bench --site "$SITE" list-apps | grep -q "^$APP "; then
	bench --site "$SITE" install-app "$APP" || exit 1
fi

bench --site "$SITE" migrate || exit 1
bench --site "$SITE" list-apps
