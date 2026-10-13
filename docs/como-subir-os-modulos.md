# Como subir cada módulo (`sus_brasil` e as extensões `*_Brasil`)

Cada módulo novo é um **app Frappe em repositório próprio**, ao lado do `erpnext_brasil`, e se instala no bench como
qualquer app. O que muda de um para o outro é só **de quem depende**.

| App | Repositório (privado) | Depende de | Estado |
|---|---|---|---|
| `sus_brasil` | `moacirbishopcamata/sus_brasil` | só o Frappe | DocTypes de Cadastros SUS **instalados e testados** em `fr16pg.localhost` |
| `hrms_brasil` | `moacirbishopcamata/hrms_brasil` | `sus_brasil` + HRMS | esqueleto, **instalação não verificada** |
| `healthcare_brasil` | `moacirbishopcamata/healthcare_brasil` | `sus_brasil` + Healthcare | esqueleto, **instalação não verificada** |
| `wms_sus_brasil` | `moacirbishopcamata/wms_sus_brasil` | `sus_brasil` + ERPNext | esqueleto, **instalação não verificada** |
| `erpnext_brasil` | `moacirbishopcamata/erpnext_brasil` | ERPNext (e `sus_brasil`, no módulo "Integração SUS") | em uso |

Ordem de instalação: **o núcleo primeiro**, depois a extensão, no site que já tem a aplicação-alvo.

| Para ter… | Site com… | Instale, nesta ordem |
|---|---|---|
| só o SUS Brasil | só o Frappe | `sus_brasil` |
| SUS + profissionais do HRMS | ERPNext + HRMS | `sus_brasil`, `hrms_brasil` |
| SUS + pacientes do Healthcare | ERPNext + Healthcare | `sus_brasil`, `healthcare_brasil` |
| SUS + estoque do ERPNext | ERPNext | `sus_brasil`, `wms_sus_brasil` |

## O caminho curto (WSL2 ou Linux)

```sh
bash scripts/instalar_app_brasil.sh sus_brasil                          # site fr16pg.localhost, ramo main
bash scripts/instalar_app_brasil.sh sus_brasil fr16pg.localhost meu-ramo
bash scripts/instalar_app_brasil.sh hrms_brasil v16pg.localhost         # depois do sus_brasil, em site com HRMS
```

O script sobe os dois Redis do bench (se faltarem), baixa o app, registra no `apps.txt`, instala e roda `migrate`.
A fonte padrão é o clone local em `/mnt/g/PROJECTS/<app>`; para instalar do GitHub (repositório privado exige
token), use `FONTE=https://github.com/moacirbishopcamata/<app>`.

## O caminho manual, passo a passo

Cada passo existe por uma armadilha que já aconteceu.

1. **Serviços.** O Frappe 16 precisa dos dois Redis (portas em `sites/common_site_config.json`, hoje 13001 e 11001).
   Os sites de teste usam o **PostgreSQL do Windows** (`docs/postgresql.md`): não suba o MariaDB.
   ⚠️ `SO_SERVICOS=1 bash scripts/subir.sh` **trava** neste cenário — fica esperando o MariaDB, que ninguém usa. Para
   site em PostgreSQL, suba só os Redis (o script acima faz isso).
2. **Baixar o app.**
   ```sh
   cd ~/frappe-bench-16
   git config --global --add safe.directory '*'     # clone de /mnt/g reclama de "dubious ownership"
   bench get-app --branch main /mnt/g/PROJECTS/sus_brasil
   ```
   ⚠️ O `get-app` imprime um `TypeError ... paths[0]` do esbuild ao compilar os assets: o app ainda não tem
   `public/`. **Não impede a instalação**; some quando o app ganhar front-end.
3. **Registrar no `apps.txt`.** O `get-app` baixa mas **não registra**, e o arquivo vem sem `\n` final. Reescreva-o
   inteiro:
   ```sh
   printf '%s\n' "$(cat sites/apps.txt)" sus_brasil > sites/apps.txt.novo && mv sites/apps.txt.novo sites/apps.txt
   ```
4. **Instalar e migrar.**
   ```sh
   bench --site fr16pg.localhost install-app sus_brasil
   bench --site fr16pg.localhost migrate
   bench --site fr16pg.localhost list-apps
   ```
   O `migrate` depois de **todo** `install-app` não é opcional: instalar um app depois de outro deixa os campos do
   primeiro inertes até a migração.
5. **Conferir.** `list-apps` deve mostrar o app e o ramo. Para provar que os DocTypes funcionam (e que o Frappe não
   os apagou como órfãos), rode o teste de bench:
   ```sh
   bench --site fr16pg.localhost run-tests --skip-before-tests --app sus_brasil \
     --module sus_brasil.tests_bench.test_cadastros_sus
   ```
   Verificado em 2026-10-12: **10 testes, OK**, no site só-Frappe `fr16pg.localhost` (Frappe 16.51, PostgreSQL).

## Atualizar depois de mudar o código

```sh
cd ~/frappe-bench-16/apps/sus_brasil && git pull
cd ~/frappe-bench-16 && bench --site fr16pg.localhost migrate
```

Mudou `hooks.py` ou DocType? O `migrate` sincroniza. Mudou só código Python de controller? Reinicie o servidor.

## Subir o servidor e abrir no navegador

```sh
bash scripts/subir.sh          # servidor na porta do bench (padrão 8001)
```

`scripts/subir.sh` serve para sites em **MariaDB**. Para PostgreSQL, ele só confere a porta do banco (ver
`docs/como-rodar.md`). Os DocTypes de Cadastros SUS aparecem na busca (`Ctrl+K`) como *Paciente SUS*,
*Estabelecimento SUS*, *Profissional SUS*, *Prontuario SUS*, *Entrada do Prontuario* e *Fusao de Pacientes*.

## Só a suíte pura (sem bench, em qualquer máquina)

Cada repositório roda a sua direto, sem Frappe:

```sh
cd G:\PROJECTS\sus_brasil
pip install tzdata ruff
python -m unittest discover -s sus_brasil/tests -t .
ruff check sus_brasil/ && ruff format --check sus_brasil/
```

## O que ainda não foi verificado

- Instalação de `hrms_brasil`, `healthcare_brasil` e `wms_sus_brasil` num site com a aplicação-alvo. São esqueletos:
  `hooks.py`, `modules.txt` e um teste de versão, sem DocType.
- Instalação a partir do GitHub (repositório privado), em vez do clone local.
- Os DocTypes de Cadastros SUS **num site que também tem ERPNext/HRMS/Healthcare** (só o site só-Frappe foi testado).
- Servidor web respondendo com os DocTypes na interface (só o ORM foi exercitado, pelo teste de bench).
