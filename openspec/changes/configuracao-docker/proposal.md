## Why

Por decisão do dono do projeto (2026-10-11), o ERPNext Brasil deve ter **configurações em Docker para melhor portabilidade**. Hoje o ambiente é montado à mão: `scripts/subir.sh` sobe MariaDB, Redis e o servidor "sem `sudo` e sem Docker" num bench do WSL2, e cada máquina nova repete a receita de `docs/ambiente-dev-bench.md`. Isso serve ao desenvolvimento, mas não é portátil: não roda igual em Windows, em Linux e em um servidor, e instalar o ERP para um teste exige horas.

Docker resolve exatamente isso: a mesma imagem e o mesmo `compose` sobem o ERPNext Brasil (o ERPNext inteiro mais a tropicalização) em qualquer máquina com Docker, em Windows (com o Docker Desktop, que usa o WSL2 por baixo) e em Linux. É também o caminho que dá ao ERP uma forma suportada de rodar em Windows sem o usuário montar o bench.

## What Changes

- Configuração Docker em `docker/`: **receita de imagem** (usa o `Containerfile` em camadas do projeto `frappe_docker`, fixado por commit, com um `apps.json` que traz `erpnext` e `erpnext_brasil` na `version-16`), **`compose.yaml`** (aplicação, Redis, trabalhadores, agendador, websocket e proxy), **overrides de banco** (`compose.mariadb.yaml` e `compose.postgres.yaml`), **`.env.example`** e **scripts de apoio em Python puro** (`preparar.py`, `construir.py`).
- **Segurança por padrão:** senhas por *Docker secrets* (arquivos), nunca por variável de ambiente nem pela linha de comando do host; o `apps.json` com credencial de repositório privado é um *build secret* que não entra na imagem; a porta web só escuta `127.0.0.1` por padrão; `no-new-privileges` nos serviços; nenhum valor padrão de senha.
- **Portabilidade:** funciona igual em Windows e Linux (separador de arquivos do Compose fixado em vírgula, volumes nomeados, nenhum caminho do sistema), e o MariaDB ou o PostgreSQL são escolhidos por override, em linha com a regra de que **a escolha do banco é do Cherry**.
- **Identidade de instância:** cada projeto do Compose carrega `SODA_INSTANCE_ID` e `SODA_DESCRITIVO` como rótulos e o nome do projeto derivado do UUID, de modo que o Soda possa orquestrar instâncias em contêineres (evolução) e o Chantilly possa medir por contêiner.
- **Validação automática:** `docker compose config` roda no CI (Ubuntu) e em teste local quando há Docker; testes sem Docker conferem a estrutura (serviços, portas locais, ausência de segredo no `.env.example`, `apps.json` válido, comando de build como lista de argumentos).
- `docs/docker.md` com como construir, subir, criar o site, atualizar, fazer backup e o que **não** é coberto.

Fora desta mudança: orquestração em Kubernetes, TLS e proxy reverso de produção, backup agendado, e o modo "instância por contêiner" do Soda (fica como evolução; aqui só se deixam os rótulos e o nome de projeto).

## Capabilities

### New Capabilities

- `implantacao/docker`: a imagem e o Compose do ERPNext Brasil, seguros por padrão e portáteis entre Windows e Linux.

### Modified Capabilities

Nenhuma.

## Impact

- Novos arquivos: `docker/compose.yaml`, `docker/compose.mariadb.yaml`, `docker/compose.postgres.yaml`, `docker/.env.example`, `docker/apps.json`, `docker/preparar.py`, `docker/construir.py`, `docker/.gitignore`, `docs/docker.md`, `erpnext_brasil/tests/test_docker.py`.
- `.github/workflows/ci.yml`: job que valida o Compose.
- O repositório é **privado**: construir a imagem exige uma credencial de leitura, que fica só num arquivo local ignorado pelo Git.
- Versões de imagens de terceiros (MariaDB, PostgreSQL, Redis) vêm do que o `frappe_docker` testa, parametrizadas por variável; a política "sempre LTS, conferida na web" do projeto passa a ver essas imagens na auditoria da pilha.
- Docker não é pré-requisito para o desenvolvimento: o caminho de `scripts/subir.sh` continua.
