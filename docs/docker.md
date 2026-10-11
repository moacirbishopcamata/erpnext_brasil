# ERPNext Brasil em Docker

Configuração para subir o **ERPNext Brasil** (o ERPNext inteiro com a tropicalização brasileira: `erpnext` e `erpnext_brasil` na versão 16) com Docker, igual em **Windows** (Docker Desktop, que usa o WSL2 por baixo) e em **Linux**. Mudança OpenSpec `configuracao-docker`.

> **Estado em 2026-10-11:** a **configuração está pronta e validada** (o Compose resolve com MariaDB e com PostgreSQL, 39 testes passam no WSL com Docker de verdade). **A imagem ainda não foi construída e a pilha ainda não foi levantada**: a primeira construção baixa gigabytes e leva dezenas de minutos, e fica para quando houver autorização. Tudo que está abaixo sobre o comportamento da pilha em execução é, portanto, o desenho validado na resolução e não a observação de um ERP rodando.

O Docker é um **acréscimo de portabilidade**, não substitui o caminho de desenvolvimento sem Docker (`scripts/subir.sh`, ver `ambiente-dev-bench.md`).

## O que há em `docker/`

| Arquivo | Para quê |
|---|---|
| `compose.yaml` | a base: Redis, configurador, aplicação, proxy, websocket, trabalhadores, agendador e a criação de site (sob perfil). **Sem banco** |
| `compose.mariadb.yaml` | acrescenta o MariaDB (11.8, utf8mb4) |
| `compose.postgres.yaml` | acrescenta o PostgreSQL (15.17) |
| `.env.example` | variáveis de exemplo, **sem nenhum segredo** |
| `apps.json` | os aplicativos da imagem: `erpnext` (versão 16) e `erpnext_brasil` |
| `preparar.py` | cria os arquivos de segredo, sem imprimir os valores |
| `construir.py` | monta e executa o `docker build` |
| `.gitignore`, `.gitattributes` | segredos e `.env` fora do Git; arquivos de contêiner sempre com `LF` |

**A escolha do banco é do Cherry.** O Compose não decide: o banco entra por um override, e o tipo, o servidor e a porta vêm dos perfis de banco do Cherry (mudança `cherry-perfis-de-banco`).

## Passo a passo

```sh
# 1. Segredos (cria docker/segredos/db_password e admin_password; não imprime os valores)
python docker/preparar.py

# 2. Variáveis
cp docker/.env.example docker/.env        # no Windows: copy docker\.env.example docker\.env
#    edite SITE_NAME, COMPOSE_FILE (compose.mariadb.yaml ou compose.postgres.yaml), PORTA_WEB...

# 3. Imagem (a primeira vez baixa gigabytes)
python docker/construir.py

# 4. Subir a pilha
cd docker
docker compose up -d

# 5. Criar o site, uma vez
docker compose --profile inicializacao run --rm create-site
```

Depois, abra `http://127.0.0.1:8080` (ou a `PORTA_WEB` que escolheu). O login é `Administrator` e a senha está em `docker/segredos/admin_password`.

`python docker/construir.py --mostrar` só mostra o comando, sem executar.

### Repositório privado

O repositório `erpnext_brasil` é **privado**, então a construção precisa de uma credencial de leitura. Copie `docker/apps.json` para `docker/apps.local.json` (ignorado pelo Git), coloque o token na URL do `erpnext_brasil` (`https://<TOKEN>@github.com/moacirbishopcamata/erpnext_brasil`) e construa com `python docker/construir.py --apps docker/apps.local.json`. Use um token de **leitura, restrito a esse repositório**. O arquivo entra como *build secret* e **não fica nas camadas da imagem**; a receita ainda remove os diretórios `.git` dos aplicativos.

## Segurança por padrão

- **Senhas por arquivo** (Docker secrets), nunca por variável de ambiente nem pela linha de comando do host; o `docker inspect` não as mostra. Nenhum valor padrão de senha.
- **A porta web só escuta `127.0.0.1`.** Para expor à rede, defina `ENDERECO=0.0.0.0` de propósito. Banco e Redis **não publicam porta**.
- `no-new-privileges` em todos os serviços.
- **Limite honesto:** a senha de administrador do ERP e a do banco aparecem na linha de comando do processo `bench new-site` **dentro do contêiner descartável** de criação de site (o comando não oferece outro meio); quem tem acesso ao Docker (equivalente a administrador) pode vê-las com `docker top` durante esses segundos.
- `cap_drop: [ALL]` **não** foi aplicado, porque não foi exercitado contra a imagem; é endurecimento a testar.

## Portabilidade

Windows e Linux com os **mesmos arquivos**: volumes nomeados (nada de caminho do computador), `COMPOSE_PATH_SEPARATOR=,` para o `COMPOSE_FILE` valer igual nos dois, scripts em Python puro, `LF` garantido por `.gitattributes`. Várias pilhas no mesmo computador: dê a cada uma um `COMPOSE_PROJECT_NAME` e uma `PORTA_WEB` diferentes (volumes, redes e contêineres não colidem; testado na resolução). Para uma instância do Soda, derive o nome do projeto do UUID e preencha `SODA_INSTANCE_ID` e `SODA_DESCRITIVO`, que viram **rótulos** em todos os serviços de aplicação.

## Ordem de subida

Banco e Redis têm *healthcheck*. O **configurador** espera os três ficarem saudáveis, grava a configuração comum do bench (`db_type`, `db_host`, `db_port`, Redis, socket.io) e termina. A aplicação, o websocket, os trabalhadores e o agendador só iniciam depois de ele terminar com sucesso; o proxy espera a aplicação ficar saudável. A criação de site é à parte (perfil `inicializacao`) e **idempotente**: se o site já existe, termina sem recriar.

## Atualizar e fazer backup

- **Atualizar:** reconstrua a imagem (`python docker/construir.py --tag <nova>`), ajuste `TAG` no `.env`, `docker compose up -d` e rode a migração: `docker compose exec backend bench --site <site> migrate`. Faça backup antes.
- **Backup:** `docker compose exec backend bench --site <site> backup --with-files`; os arquivos ficam no volume `sites`. Backup agendado **não** está coberto.
- O commit do `frappe_docker` usado na construção está **fixado** em `docker/construir.py` (`FRAPPE_DOCKER_COMMIT`). Atualizá-lo é decisão consciente, junto com a auditoria da pilha.

## Versões

As de MariaDB (11.8), PostgreSQL (15.17) e Redis (8.6-alpine) são as que o `frappe_docker` testa em 2026-10-11, parametrizadas no `.env`. O ambiente de desenvolvimento sem Docker usa MariaDB 10.11 e Redis 7.2, e o PostgreSQL local é o 18. A auditoria da pilha deve passar a ver estas imagens (tarefa 4.3 da mudança).

## Validação

`erpnext_brasil/tests/test_docker.py` (39 testes): estrutura dos arquivos, ausência de segredo, comando de build como lista de argumentos sem o conteúdo do `apps.json`, geração de segredos (não sobrescreve, não imprime, `0600`), e, **onde há Docker**, a resolução real do Compose em JSON para cada banco (só o proxy publica porta, em `127.0.0.1`; rótulos de instância; segredos montados e nenhuma senha no resultado; ordem por saúde; duas pilhas sem colisão). No CI, o passo "Docker disponível" garante que essa parte não seja pulada em silêncio.

## O que não é coberto

TLS e proxy reverso de produção, Kubernetes, backup agendado, alta disponibilidade, publicação da imagem em registro, e o modo "instância por contêiner" do Soda (só se deixaram os rótulos e o nome do projeto).

## Windows e Linux

| | Windows (Docker Desktop, backend WSL2) | Linux |
|---|---|---|
| Construir a imagem | funciona | funciona |
| Subir a pilha | funciona | funciona |
| Sem Docker | o ERP não roda nativo no Windows; use o caminho do WSL2 (`ambiente-dev-bench.md`) | use o bench local |

Os testes que usam o Docker são pulados, com o motivo escrito, em uma máquina Windows sem Docker; o CI (Ubuntu) e o WSL2 os executam.
