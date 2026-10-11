## 1. Arquivos de configuração

- [x] 1.1 `docker/apps.json` (erpnext e erpnext_brasil na versão 16) e `docker/.gitignore` (segredos, `.env`, `apps.local.json`) — verificar com teste que lê o JSON e confere os dois aplicativos e a ausência de credencial.
- [x] 1.2 `docker/compose.yaml`: Redis, configurador, aplicação, proxy, websocket, trabalhadores, agendador e criação de site (perfil), com saúde, ordem, rótulos de instância, porta local e `no-new-privileges` — verificar com `docker compose config` e com testes de estrutura (serviços, portas, ausência de senha).
- [x] 1.3 `docker/compose.mariadb.yaml` e `docker/compose.postgres.yaml` — verificar com `docker compose config` de cada combinação e confirmar que cada uma tem um só banco e o tipo certo no configurador.
- [x] 1.4 `docker/.env.example` sem nenhum segredo, com `COMPOSE_PATH_SEPARATOR=,` e `COMPOSE_FILE` — verificar com teste que procura valor de senha, token ou chave.

## 2. Scripts de apoio em Python puro

- [x] 2.1 `docker/preparar.py`: gera `docker/segredos/db_password` e `admin_password` com `secrets`, sem sobrescrever, com permissão restrita onde o sistema permitir, sem imprimir o valor — verificar com testes de geração, de preservação, de modo `0600` (em Linux/WSL) e de que a saída não contém o valor.
- [x] 2.2 `docker/construir.py`: monta o comando de build como lista de argumentos, com a receita do `frappe_docker` fixada por commit, o `apps.json` como `--secret` e a etiqueta da imagem; recusa etiqueta inválida e commit não fixado — verificar com testes do comando (sem shell, sem o conteúdo do `apps.json`, commit de 40 caracteres).
- [x] 2.3 Os dois scripts recusam executar fora do que prometem (sem `docker` instalado, `apps.json` ausente) com mensagem orientadora — verificar com testes de cada recusa.

## 3. Verificação

- [x] 3.1 `tests/test_docker.py`: estrutura dos arquivos sem Docker e `docker compose config` quando o Docker existir (com o motivo escrito no teste pulado) — verificar rodando no Windows (pulado, dizendo o motivo) e no WSL (executado).
- [ ] 3.2 (feito: passo "Docker disponível" no job da suíte, que roda a resolução real do Compose; **só se prova no primeiro run do CI do PR**) Job de CI que valida o Compose com MariaDB e com PostgreSQL — verificar com o job verde no PR.
- [ ] 3.3 Construção real da imagem e criação de um site, **somente com autorização** (baixa gigabytes) e depois conferir que a credencial do `apps.json` não está nas camadas (`docker history` e busca na imagem) — verificar com a saída; se não houver autorização, esta tarefa fica aberta e o motivo é dito.
- [ ] 3.4 Subir a pilha e abrir o ERP em `http://127.0.0.1:8080`, parar e subir de novo preservando os dados — verificar com o registro de execução; mesma condição da 3.3.

## 4. Documentação e integração

- [x] 4.1 `docs/docker.md` (como construir, subir, criar o site, atualizar, backup e o que não é coberto), indexado em `docs/README.md`, com a tabela Windows e Linux — verificar relendo contra os arquivos.
- [x] 4.2 Ligar `docs/ferramentas-de-operacao.md`, `docs/soda.md` e `docs/cherry.md` ao Docker (portabilidade; a escolha de banco é do Cherry; rótulos de instância; `docker stats` para o Chantilly como evolução) — verificar relendo.
- [ ] 4.3 (registrado em `docs/auditoria-da-pilha.md`; **falta** estender o `auditar_pilha.py`) Tarefa na auditoria da pilha para ver as imagens do Compose (MariaDB, PostgreSQL, Redis) e o commit fixado do `frappe_docker` — verificar com a lista no documento da auditoria.
- [x] 4.4 Gate de padrões e de resiliência e segurança — verificar com a saída de `ruff`, dos testes e do `docker compose config`.
