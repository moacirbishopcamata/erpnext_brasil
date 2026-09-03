# Docker/compose — caminho alternativo ao bench WSL2

Pedido direto do usuário: `Dockerfile` e `docker-compose.yml` na raiz do repositório,
para rodar `erpnext_brasil` em container, no padrão de
[`frappe_docker`](https://github.com/frappe/frappe_docker) (o projeto oficial de
containerização do Frappe/ERPNext).

## Por que não é o ambiente principal deste projeto

O ambiente de desenvolvimento efetivamente usado e confirmado funcionando de ponta a
ponta é o **bench WSL2 nativo** (ver `docs/ambiente-dev-bench.md`, `bench run-tests`
rodado de verdade, 1671 testes). Este `Dockerfile`/`docker-compose.yml` é um caminho
**alternativo**, útil para quem não tem WSL2/bench configurado — **não foi
build-testado nesta sessão**: os arquivos seguem o padrão documentado do
`frappe_docker`, mas `docker compose up` de ponta a ponta (build da imagem, criação do
site, instalação dos dois apps) ainda não foi executado e confirmado aqui. Declarado
explicitamente, não escondido — mesma disciplina de nível de confiança já aplicada a
fontes secundárias no resto do projeto.

## Por que `COPY`, não `bench get-app <url>`

O `Dockerfile` copia o código deste repositório para dentro da imagem
(`COPY . /home/frappe/erpnext_brasil_src` + `bench get-app erpnext_brasil
/home/frappe/erpnext_brasil_src`), não clona de uma URL git — **este repositório ainda
não tem remote público** (regra padrão do projeto: nunca fazer push sem pedido
explícito, ver memória do projeto). Quando for publicado no GitHub, trocar o `COPY` por
`bench get-app erpnext_brasil <url>` é a migração natural, sem mudar mais nada na
imagem.

## Estrutura do `docker-compose.yml`

Mesma decomposição de serviços do `frappe_docker`: `mariadb`/`redis-cache`/
`redis-queue` (infraestrutura), `configurator` (grava `common_site_config.json`),
`create-site` (roda uma vez, cria o site e instala `erpnext`+`erpnext_brasil`),
`backend`/`websocket`/`queue-short`/`queue-long`/`scheduler` (os processos do bench
propriamente dito) e `nginx` (proxy reverso, porta `8080`).

## Uso

```sh
docker compose up -d
docker compose logs -f create-site   # acompanha a criação do site na 1ª subida
docker compose exec backend bench --site erpnext-brasil.localhost run-tests --app erpnext_brasil
```

Acesso: `http://localhost:8080` (usuário `Administrator`, senha `admin` — **só para
desenvolvimento local**, trocar antes de qualquer uso real).

## Fonte

Padrão de serviços e variáveis de ambiente seguindo `frappe_docker`'s
`pwd.yml`/`compose.yaml` (documentação oficial do projeto, `github.com/frappe/
frappe_docker`), adaptado para instalar `erpnext_brasil` a partir do código local em
vez de uma imagem/app publicados.
