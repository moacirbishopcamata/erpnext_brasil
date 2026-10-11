## Context

Ver `proposal.md` (Why). O que está estabelecido:

- O `frappe_docker` (upstream) suporta a `version-16`: a receita em camadas (`images/layered/Containerfile`) tem `FRAPPE_BRANCH=version-16` como padrão, parte das imagens `frappe/build` e `frappe/base`, instala os aplicativos por `bench init --apps_path` e recebe a lista como *build secret* `apps_json`. Os overrides oficiais (`compose.mariadb.yaml`, `compose.postgres.yaml`, `compose.redis.yaml`, `compose.noproxy.yaml`, `compose.mariadb-secrets.yaml`) mostram o que o upstream testa: MariaDB 11.8, PostgreSQL 15.17 e Redis 8.6-alpine em 2026-10-11, e `MYSQL_ROOT_PASSWORD_FILE` para a senha por arquivo. Não existe um override oficial de criação de site; ele é escrito aqui.
- O repositório do projeto é **privado**: a construção precisa de uma credencial de leitura.
- O ambiente de desenvolvimento atual (`scripts/subir.sh`) é sem `sudo` e sem Docker, e continua.
- Docker 29.7.2 está disponível no WSL2 desta máquina, o que permite validar a resolução do Compose.
- As ferramentas (Cherry, Soda, Chantilly) são complementos desktop em Python puro; os scripts de apoio seguem o mesmo princípio.

## Goals / Non-Goals

**Goals:**
- Subir o ERPNext Brasil com um comando em qualquer máquina com Docker, em Windows e em Linux.
- Segurança por padrão: segredos por arquivo, porta local, nenhuma senha de fábrica.
- Reprodutibilidade: base fixada por commit, versões parametrizadas.
- Deixar o terreno pronto para o Soda orquestrar instâncias em contêineres.

**Non-Goals:**
- Kubernetes, TLS e proxy reverso de produção, backup agendado, alta disponibilidade.
- Reescrever a receita de imagem do upstream: ela é reutilizada.
- Substituir o caminho sem Docker do desenvolvimento.

## Decisions

1. **Reutilizar a receita do upstream, não copiá-la.** `docker/construir.py` chama `docker build` usando o repositório `frappe_docker` como contexto remoto, **fixado por commit** (`2b26e9ab8d751e5ea33bb7b930aea3550bb81ded`, de 2026-10-09), com `-f images/layered/Containerfile`. A receita traz os scripts de entrada (`resources/core/`), que seriam centenas de linhas para manter. O preço é depender do upstream; a fixação por commit torna a base reprodutível, e a atualização do commit é uma decisão consciente.
2. **`apps.json` como build secret.** O repositório do projeto é privado, então o `apps.json` pode levar uma credencial. Ele é passado por `--secret id=apps_json,src=<arquivo>`, que **não** entra nas camadas. O `apps.json` versionado não tem credencial; quem constrói com repositório privado usa `apps.local.json` (ignorado pelo Git) e a opção `--apps`. A receita remove os diretórios `.git` dos aplicativos, o que tira a URL com credencial da imagem; uma tarefa confere isso depois de construir.
3. **Compose em arquivo base mais override de banco.** `compose.yaml` não tem banco; `compose.mariadb.yaml` e `compose.postgres.yaml` o acrescentam. Assim a escolha de banco (que é do Cherry) é uma combinação de arquivos, sem `!reset` nem `!override`. As variáveis `DB_HOST`, `DB_PORT` e `DB_TIPO` vêm do override para o configurador e para a criação de site.
4. **Segredos por arquivo.** `secrets: db_password` e `admin_password`, a partir de `docker/segredos/` (ignorado pelo Git, criado por `preparar.py`). O MariaDB usa `MYSQL_ROOT_PASSWORD_FILE`; o PostgreSQL, `POSTGRES_PASSWORD_FILE`. O serviço de criação de site lê os arquivos para variáveis de shell dentro do contêiner descartável. *Limite honesto:* a senha aparece na linha de comando do processo `bench new-site` **dentro do contêiner efêmero** (visível a quem já tem acesso ao Docker, que é equivalente a administrador); o `bench new-site` não oferece outro meio. Em contrapartida, a senha não aparece em `docker inspect`, no `.env`, nem na imagem.
5. **Porta local por padrão.** O proxy publica `${ENDERECO:-127.0.0.1}:${PORTA_WEB:-8080}:8080`. Banco e Redis não publicam porta. Expor à rede é uma variável explícita.
6. **Ordem por saúde.** Banco e Redis têm `healthcheck`; o configurador espera ficar saudáveis (`service_healthy`) e termina (`service_completed_successfully`); os demais esperam o configurador. A aplicação tem `healthcheck` próprio (Python da própria imagem, com o cabeçalho `Host` do site), porque a imagem não tem `curl` garantido.
7. **Criação de site sob demanda.** `create-site` fica num perfil (`inicializacao`) e não roda no `up` normal. É idempotente: se o site já existe, termina com sucesso sem recriar.
8. **Portabilidade entre Windows e Linux.** Volumes nomeados (nada de caminho do host), `COMPOSE_PATH_SEPARATOR=,` para o `COMPOSE_FILE` valer igual nos dois sistemas, scripts em Python puro sem shell específico, e `.gitattributes`/`.gitignore` que mantêm `LF` nos arquivos de contêiner (um `CRLF` num script de entrada quebra o contêiner Linux).
9. **Identidade de instância.** `SODA_INSTANCE_ID` e `SODA_DESCRITIVO` viram rótulos de todos os serviços de aplicação; `COMPOSE_PROJECT_NAME` pode ser derivado do UUID. Isso não implementa o modo "instância por contêiner" do Soda; só deixa a identidade onde o Soda e o Chantilly (`docker stats` por rótulo) possam ler.
10. **Versões parametrizadas.** `MARIADB_VERSION=11.8`, `POSTGRES_VERSION=15.17`, `REDIS_VERSION=8.6-alpine` como no upstream de 2026-10-11, sobrescrevíveis. O desenvolvimento local usa MariaDB 10.11 e Redis 7.2; o contêiner usa o que o upstream testa. A auditoria da pilha ganha uma tarefa para ver essas imagens.
11. **Resiliência.** `restart: unless-stopped` nos serviços de longa duração, `on-failure` no configurador, `no` na criação de site; volumes nomeados para `sites`, `logs`, dados do banco e fila.
12. **Segurança do contêiner.** `no-new-privileges` em todos os serviços de aplicação. `cap_drop: [ALL]` **não** é aplicado por padrão porque não foi exercitado contra a imagem; fica como endurecimento a testar.
13. **Padrões do projeto, resiliência e segurança** valem para os scripts Python (contrato, listas de argumentos sem shell, escrita de segredo restrita ao dono, sem impressão de segredo) e são conferidos por teste.

## Risks / Trade-offs

- **Dependência do upstream:** receita e imagens base vêm do `frappe_docker`. Fixar por commit mitiga; a atualização é manual.
- **Construção pesada:** a primeira construção baixa gigabytes e leva dezenas de minutos. Não foi executada nesta mudança sem autorização; a validação é a resolução do Compose e os testes de estrutura, e a construção real é uma tarefa que depende de autorização.
- **Credencial no `apps.json`:** o arquivo local com token é sensível; fica ignorado pelo Git, e o token deve ser de leitura restrita a esse repositório.
- **Senha na linha de comando do contêiner efêmero:** documentada na decisão 4.
- **Versões de terceiros diferentes do desenvolvimento local:** documentado na decisão 10.
- **PostgreSQL no Frappe:** o upstream o testa na 15.17; o override é validado na resolução, mas o fluxo completo com PostgreSQL só se prova construindo e criando um site.

## Open Questions

1. **Credencial para o repositório privado:** token de leitura do GitHub (recomendado, com escopo mínimo) ou chave de implantação? A construção só roda com uma delas.
2. **Publicar a imagem?** Um registro (GHCR) permitiria baixar em vez de construir, ao custo de gerir credenciais e retenção. Fica fora até haver decisão.
3. **Modo "instância por contêiner" no Soda:** isola por bench (Redis e trabalhador próprios, código por imagem), resolvendo o teste de branches em paralelo. Quer que isso entre como evolução do Soda?
4. **Quando atualizar o commit fixado do `frappe_docker`?** Proposta: a cada atualização da pilha (auditoria de versões).
