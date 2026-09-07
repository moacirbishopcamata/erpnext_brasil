# Ambiente de desenvolvimento: bench Frappe local (Windows 11 + WSL2 + Docker)

## Atualização: Redis e MariaDB nativos agora disponíveis no Windows

Desde 2026-08-31, a máquina de desenvolvimento tem **Memurai for Redis v8.2-RC3** e
**MariaDB** instalados nativamente no Windows (fora de WSL2/Docker) — os dois
serviços cuja ausência nativa (binário Redis para Windows, rede WSL↔Windows para o
MariaDB) motivou originalmente a decisão de WSL2 + Docker registrada abaixo.

- **Memurai for Redis** (`docs.memurai.com/en/installation.html`) é compatível com o
  protocolo Redis/RESP (documentação cita compatibilidade com a API do Redis 7),
  instalado via MSI, roda como **serviço Windows** (conta `NT AUTHORITY\
  NetworkService`, início automático), porta padrão **6379**, configurável no
  instalador ou depois via arquivo de configuração. É o substituto direto do
  "Redis não foi para Docker — `bench init` exige o binário local" (seção abaixo):
  com Memurai, esse binário passa a existir nativamente no Windows, não só dentro do
  WSL2 via `apt`.
- **MariaDB** nativo do Windows já estava presente antes (`G:\MariaDB 12.3`, citado
  na seção seguinte como a tentativa original que não emplacou por causa da rede
  WSL2↔Windows) — o que muda agora é que, com o bench também rodando nativo no
  Windows (não mais em WSL2 chamando para fora), essa travessia de rede deixa de
  ser necessária: bench e MariaDB estariam na mesma máquina/host, sem fronteira de
  rede virtual para atravessar.

**Atualização de 2026-09-03 — tentado e descartado, achado definitivo**: a pedido
direto do usuário, a alternativa nativa foi de fato tentada (`pip install
frappe-bench` com Python 3.14 nativo do Windows, Memurai e MariaDB nativos já
rodando como serviço). **Não funciona, e não é um obstáculo de configuração
contornável**: `bench/cli.py` (o próprio pacote `frappe-bench`) faz `import pwd` **no
topo do arquivo**, incondicional — `pwd` é módulo da stdlib exclusivamente POSIX
(base de usuários/grupos do Unix, `getpwnam`/`getpwuid`), sem implementação possível
no Windows (não é uma lacuna de porte, é uma API que não existe no SO). O import
falha antes de qualquer comando rodar — `bench --version` já quebra com
`ModuleNotFoundError: No module named 'pwd'`. Um stub de `pwd.py` resolveria esse
import específico (testado e removido), mas não haveria garantia de não bater no
próximo obstáculo POSIX do restante do código (symlinks, possivelmente `fork`) antes
de conseguir `bench init` de verdade. **Conclusão prática: bench não roda nativo no
Windows — o ambiente WSL2 + Docker abaixo continua sendo o único caminho, ponto
final, não "opção não testada ainda".**

Ambiente WSL2 confirmado funcionando de novo na mesma data, depois de um hiato: o
clone de `erpnext_brasil` dentro do bench estava 113 commits atrasado — `git pull`
trouxe tudo, `bench migrate` aplicou os campos novos sem erro, e `bench run-tests
--app erpnext_brasil` confirmou **1671 testes, mesma contagem da suíte pura, 1 skip
esperado** (subiu de 685 desde a confirmação original, refletindo toda a frente de
CT-e/MDF-e/ECF/certificado A1 construída nesta sessão).

## Por que não bench nativo no Windows (decisão original, antes do Memurai)

O `bench` (CLI do Frappe) assume um ambiente Unix: symlinks, `bash`, e historicamente
Redis sem build oficial para Windows. Rodar nativo no Windows é caminho frágil e pouco
documentado — o risco é travar em obstáculo de ambiente sem saída limpa, não um problema
de configuração pontual. Por isso o bench roda em **WSL2 (Ubuntu 24.04 LTS)**, não no
Windows diretamente.

## Por que Docker para Redis e MariaDB, não serviço nativo do Windows

O MariaDB 12.3 nativo do Windows (`G:\MariaDB 12.3`) já estava disponível e ativo, e a
primeira tentativa foi apontar o bench (rodando em WSL2) para ele via TCP — sem duplicar
banco. Não funcionou, e vale registrar por quê, para não repetir a mesma tentativa:

1. **Modo de rede padrão do WSL2 (NAT)**: o WSL2 fica numa sub-rede virtual própria
   (`172.29.16.0/20` neste ambiente); o Windows Firewall clássico tinha uma regra
   permissiva (`Any`/`Any`/`Any`) para a porta 3306, mas a conexão ainda assim falhava
   na camada TCP (nem chegava a autenticar).
2. **Modo *mirrored* do WSL2** (`[wsl2] networkingMode=mirrored` em `.wslconfig`,
   requer `wsl --update` para uma versão recente do kernel WSL — aqui foi para 2.7.12)
   resolve isso oficialmente segundo a documentação da Microsoft (`localhost` funciona
   nos dois sentidos). Mesmo ativado e confirmado (interface `loopback0` presente dentro
   do WSL, sinal de que o modo pegou), a conexão para a porta 3306 **continuou falhando**.
3. A suspeita é uma camada de firewall separada do Windows Defender Firewall clássico —
   o **Hyper-V Firewall**, que governa o tráfego de/para adaptadores virtuais do
   WSL/Hyper-V e não é gerenciado pelos cmdlets `Get-/New-NetFirewallRule` da forma
   usual. Depurar essa camada especificamente não tinha garantia de resolver em tempo
   razoável, e o objetivo era ter um ambiente de teste funcionando, não vencer o
   Hyper-V Firewall.

**Decisão**: em vez de insistir na rede cruzada Windows↔WSL, o bench usa **MariaDB
dedicado, rodando em container Docker dentro do próprio WSL2** — mesma máquina onde o
bench roda, sem fronteira de rede nenhuma para atravessar. O MariaDB nativo do Windows
continua disponível e rodando, sem conflito (portas diferentes, dados completamente
separados) — ele não foi desligado nem alterado, só não é usado pelo bench.

**Redis não foi para Docker — `bench init` exige o binário local.** A primeira tentativa
também colocou Redis em container, mas `bench init` chama `redis-server --version`
diretamente no host para decidir a versão do arquivo de config que gera — não basta a
porta estar acessível, o binário precisa existir no filesystem do WSL. E o próprio bench
espera **dois processos Redis em portas específicas**, não a porta padrão 6379: cache em
`13000` (`config/redis_cache.conf`) e fila em `11000` (`config/redis_queue.conf`),
arquivos que o próprio `bench init` gera. Redis instalado nativo via `apt`
(`redis-server`), o serviço systemd padrão (porta 6379) fica parado — os dois processos
que importam são iniciados manualmente com os configs do bench:

```bash
cd ~/frappe-bench
redis-server config/redis_cache.conf --daemonize yes
redis-server config/redis_queue.conf --daemonize yes
```

(`bench start`, quando usado para rodar o site de verdade, sobe esses dois processos
sozinho via `Procfile` — o passo manual só é necessário durante `bench init`, antes de
existir um `Procfile` para `bench start` gerenciar.)

## O modo *mirrored* do WSL2 ficou ativo mesmo assim

Mesmo não tendo resolvido o problema original, `.wslconfig` com
`networkingMode=mirrored` **permanece ativo** (não há motivo para reverter — é a
configuração recomendada pela Microsoft para WSL2 em geral, só não foi suficiente para
este caso específico de MariaDB). Local: `C:\Users\<usuário>\.wslconfig`.

## Docker dentro do WSL2, não Docker Desktop

Instalado `docker-ce`/`docker-compose-plugin` via `apt` **dentro** do Ubuntu do WSL2 —
não o Docker Desktop (instalador GUI do Windows, mais pesado, com sua própria integração
WSL2 que adicionaria mais uma camada a depurar se algo desse errado). O daemon Docker
roda como serviço dentro do próprio WSL (`service docker start`).

## `docker-compose.yml` — só o MariaDB do bench

Local: `/root/bench-infra/docker-compose.yml` (dentro do WSL2, fora do repositório —
é infraestrutura de ambiente, não parte do app). Só MariaDB — Redis saiu do Docker pelo
motivo explicado acima.

```yaml
services:
  mariadb:
    image: mariadb:10.6
    container_name: bench-mariadb
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: bench_root_pw
      MARIADB_DATABASE: dummy
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --skip-character-set-client-handshake
      - --skip-innodb-read-only-compressed
    ports:
      - "3307:3306"
    volumes:
      - mariadb_data:/var/lib/mysql

volumes:
  mariadb_data:
```

Pontos que importam:

- **Porta 3307, não 3306**, para o MariaDB do container — a 3306 já está ocupada pelo
  MariaDB nativo do Windows (e, com rede *mirrored*, o WSL2 enxerga as portas do Windows
  também, então usar 3306 aqui colidiria).
- **`bench_root_pw` é uma senha de container descartável, gerada para este ambiente de
  dev** — nunca a senha real do MariaDB nativo do Windows, que não é persistida em
  nenhum arquivo por este projeto (só usada de forma transitória, em sessão, quando
  necessária).
- **MariaDB 10.6**, não a versão mais nova: é a versão mínima recomendada pelo Frappe;
  usar exatamente ela evita qualquer superfície de incompatibilidade não testada pelo
  framework.
- Volume nomeado (`mariadb_data`) para persistir os dados do container entre reinícios
  do Docker — sem isso, cada `docker compose up` recriaria o banco do zero.

## O WSL2 inteiro foi movido de `C:` para `G:`

A distro Ubuntu do WSL2, por padrão, guarda seu disco virtual inteiro
(`ext4.vhdx` — todo o filesystem Linux, incluindo o que o Docker usa como
`data-root` e onde o bench/Python/Node vivem) em `C:\Users\<usuário>\...`. `G:` tem
mais espaço livre e evita disputa com o *swap* do Windows em `C:` — pedido explícito
para este ambiente. Mover a distro inteira resolve isso de uma vez para tudo que roda
dentro do WSL (bench, Docker, MariaDB), não só para o volume do banco isoladamente:

```bash
wsl --shutdown
wsl --export Ubuntu G:\WSL\Ubuntu-backup\ubuntu-export.tar
wsl --unregister Ubuntu
wsl --import Ubuntu G:\WSL\Ubuntu-data G:\WSL\Ubuntu-backup\ubuntu-export.tar --version 2
```

Dois detalhes que `wsl --import` não preserva sozinho:

- **O usuário padrão volta a ser `root`.** Corrigido escrevendo
  `/etc/wsl.conf`:
  ```ini
  [user]
  default=moacirbishopcamata
  ```
  e reiniciando (`wsl --shutdown`).
- **As imagens e o storage do Docker não sobrevivem ao export/import intactos.**
  `overlay2` (o storage driver do Docker) usa atributos estendidos de arquivo que o
  `tar` do `wsl --export` não preserva fielmente — depois de reimportar, os containers
  existentes ficam com erro `RWLayer ... is unexpectedly nil` e as imagens precisam ser
  baixadas de novo (`docker compose up -d` resolve sozinho, só demora). Não houve perda
  de dado real neste caso porque o container do MariaDB ainda não tinha nenhum schema
  de site criado — mas é bom saber que isso acontece **antes** de confiar dado de
  verdade a um container através de um export/import de distro.

O `.tar` de export (`G:\WSL\Ubuntu-backup\ubuntu-export.tar`, ~4 GB) foi apagado depois
de confirmado que o import funcionou — é redundante, não um backup a manter.

## Uma gotcha real: Git Bash → `wsl.exe` corrompe caminhos e heredocs

Comandos deste tipo, rodados a partir do Git Bash (MSYS) para invocar `wsl.exe`:

```bash
wsl -d Ubuntu -u root -- bash -lc "algum comando com \$(substituição) ou /caminho/unix"
```

falham de duas formas específicas, sem aviso claro:

1. **Caminho Unix vira caminho Windows**: o MSYS Bash faz conversão automática de
   argumentos que parecem caminho absoluto Unix (`/root/...`) para caminho Windows
   (`C:/Program Files/Git/root/...`) antes de passar para `wsl.exe` — que é um executável
   nativo do Windows, não um programa MSYS. O resultado é `No such file or directory`
   para um caminho que existe perfeitamente dentro do WSL.
2. **Heredoc/substituição de comando corrompida por múltiplas camadas de shell**: um
   heredoc (`cat > arquivo << 'EOF' ... EOF`) ou `$(comando)` escrito dentro de uma string
   que já está entre aspas duplas passada para `bash -lc "..."` sofre expansão extra
   antes de chegar no bash de dentro do WSL — por exemplo, `\$(seq 1 20)` virou os
   números `1` a `20` cada um em uma linha, quebrando a sintaxe do `for`.

**Soluções aplicadas**: `export MSYS_NO_PATHCONV=1` antes de qualquer `wsl` que receba
caminho Unix como argumento (resolve o problema 1); e, para qualquer script com mais de
uma linha ou com `$(...)`/heredoc, **escrever o arquivo com a ferramenta de escrita de
arquivo diretamente** (não via `cat << EOF` dentro de uma invocação aninhada) num
caminho acessível pelos dois lados — o `G:\` do Windows é `/mnt/g/` dentro do WSL2 — e
depois só executar `wsl -d Ubuntu -u root -- bash /mnt/g/caminho/script.sh`. Zero
camadas de escaping aninhado, o script chega exatamente como foi escrito.

## `sudo` sem senha configurada — usar `-u root` direto

O usuário padrão do WSL (`moacirbishopcamata`) não tem `sudo` sem senha configurado, e
comandos com `sudo` dentro de uma invocação não-interativa (`wsl ... -- bash -lc "sudo ..."`)
ficam pendurados esperando uma senha que nunca chega pelo stdin (sem erro claro — só
trava). Correto para automação: `wsl -d Ubuntu -u root -- ...` roda como root
diretamente, sem `sudo` nenhum.

## `bench` não roda como root — e `bench init` precisa de `--skip-assets`

Duas descobertas na hora de rodar `bench init` de verdade:

1. **`bench` se recusa a rodar como `root`** (`WARN: You should not run this command
   as root`, e aborta). O CLI (`pipx install frappe-bench`) e o `bench init` precisam
   rodar como o usuário normal (`moacirbishopcamata`), que precisou entrar no grupo
   `docker` (`usermod -aG docker moacirbishopcamata`) para conseguir gerenciar os
   containers sem precisar de root.
2. **`bench init` sem `--skip-assets` exige Redis rodando nas portas específicas do
   bench antes mesmo de terminar de se criar.** A etapa final do `init` (`bench build`)
   lê `frappe.cache()`, que por sua vez lê `common_site_config.json` — e esse arquivo já
   aponta para `redis://localhost:13000` (cache) e `:11000` (fila), não a porta 6379
   padrão. Como esses arquivos de config só existem depois que o próprio `init` os gera,
   há uma dependência circular na primeira execução: resolvida rodando
   `bench init --skip-assets` (pula o build de assets), subindo os dois processos Redis
   manualmente com os configs recém-gerados, e só então rodando `bench build` à parte.

```bash
# init sem o build de assets:
bench init --frappe-branch version-15 --python python3.12 --skip-assets frappe-bench

# sobe os dois Redis que o bench espera, com os configs que ele mesmo gerou:
cd frappe-bench
redis-server config/redis_cache.conf --daemonize yes
redis-server config/redis_queue.conf --daemonize yes

# só agora o build funciona:
bench build
```

## Estado final — funcionando de ponta a ponta

Bench `~/frappe-bench` (usuário `moacirbishopcamata`, branch `version-15` do Frappe),
site `erpnext-brasil.localhost`, banco no container `bench-mariadb` (porta `3307`).
`erpnext_brasil` entrou como app local (`bench get-app erpnext_brasil
/mnt/g/PROJECTS/erpnext_brasil` — clona do caminho local, não é symlink; mudanças no
repositório original precisam ser trazidas para dentro do bench, ver abaixo). Confirmado
via `bench --site erpnext-brasil.localhost console`:

```
frappe         15.119.1 version-15
erpnext        15.120.0 version-15
erpnext_brasil 0.18.0   main

erpnext_brasil version: 0.18.0
Installed apps: ['frappe', 'erpnext', 'erpnext_brasil']
hooks.py chaves: 10
```

**`bench run-tests` confirmado contra o site real** (precisa de
`bench --site erpnext-brasil.localhost set-config allow_tests true` antes, exigência
padrão do bench):

```
$ bench --site erpnext-brasil.localhost run-tests --app erpnext_brasil
Ran 685 tests in 10.520s
OK (skipped=1)
```

Mesma contagem da suíte pura (`python -m unittest`, sem bench) — primeira vez que ela
roda pelo executor real do Frappe, com banco e Redis de verdade, não só sintaxe/mocks.
O único skip é esperado (`test_compatibilidade.py`, degrada quando uma tabela de
referência externa não está disponível no ambiente).

## Comandos do dia a dia

```bash
# Windows (Git Bash) — sempre com a variável antes de qualquer comando com caminho Unix:
export MSYS_NO_PATHCONV=1

# Subir/derrubar o MariaDB do bench:
wsl -d Ubuntu -u root -- bash -lc "cd /root/bench-infra && docker compose up -d"
wsl -d Ubuntu -u root -- bash -lc "cd /root/bench-infra && docker compose down"

# Redis do bench (portas 13000/11000) — precisa estar de pé antes de bench build/start:
wsl -d Ubuntu -u moacirbishopcamata -- bash -lc "cd ~/frappe-bench && redis-server config/redis_cache.conf --daemonize yes && redis-server config/redis_queue.conf --daemonize yes"

# Entrar no WSL como o usuário normal (para rodar bench):
wsl -d Ubuntu

# Dentro do WSL, a partir de ~/frappe-bench:
bench --site erpnext-brasil.localhost console          # REPL com o site carregado
bench --site erpnext-brasil.localhost migrate          # aplica mudança de schema/hooks
bench --site erpnext-brasil.localhost run-tests --app erpnext_brasil --module <dotted.path>
bench start                                             # sobe web + workers + redis via Procfile
```

## Trazer mudanças do repositório original para dentro do bench

`apps/erpnext_brasil` dentro do bench é um clone, não um link para
`G:\PROJECTS\erpnext_brasil` — commitar no repositório original não atualiza o bench
sozinho. Para refletir uma mudança:

```bash
# dentro do WSL, em ~/frappe-bench/apps/erpnext_brasil:
git pull /mnt/g/PROJECTS/erpnext_brasil <branch>
# ou, para testar antes de commitar no original, git remote add/fetch apontando pro
# caminho local e mergear a branch de trabalho.
```

## ⚠️ Site sem assistente de configuração: sete faltas, e nenhuma se explica

Um site criado por `bench new-site` + `install-app erpnext` **não passou pelo assistente de
configuração**, e por isso lhe faltam cadastros que o ERPNext considera óbvios. Escrever
testes de bench esbarra em todos eles, um de cada vez, e o custo não é o conserto — é que
**nenhuma das mensagens diz que a causa é configuração faltando**:

| O que falta | Erro que aparece | Onde morde |
|---|---|---|
| `Warehouse Type: Transit` | `LinkValidationError: Could not find Warehouse Type: Transit` | criar `Company` |
| `Fiscal Year` ativo | `FiscalYearError: Date … is not in any active Fiscal Year` | submeter lançamento de estoque |
| `Stock Entry Type` | `LinkValidationError: Could not find Stock Entry Type` | criar `Stock Entry` |
| `Address Template` padrão | `No default Address Template found` | criar `Address` |
| `Price List` de venda | `MandatoryError: selling_price_list, price_list_currency, plc_conversion_rate` | criar `Sales Invoice` |
| `valuation_rate` no `Item` | `Valuation Rate for the Item … is required` | baixar estoque |
| segundo armazém no `Material Transfer` | `Target warehouse is mandatory for row 1` | transferir estoque |

Duas armadilhas a mais, que não são "falta de cadastro" e custam o mesmo tempo:

- **Cliente interno precisa autorizar a empresa.** `is_internal_customer` +
  `represents_company` não bastam: sem a empresa em `companies` ("Allowed To Transact
  With"), a nota é recusada com *"Customer not allowed to transact with"*. É proteção do
  ERPNext contra faturamento cruzado — legítima, e invisível para quem leu só a
  documentação de `is_internal_customer`.
- **Setup idempotente por existência não incorpora mudança no cadastro.** Um
  `if not frappe.db.exists("Item", X): criar(...)` faz o item de uma execução anterior
  sobreviver a qualquer correção no `setUpClass` — e o teste segue falhando por um motivo
  que já foi consertado. Campos que o teste depende (`valuation_rate`,
  `br_producao_propria`) vão **fora** do `if`, com `frappe.db.set_value`.

Também é preciso habilitar os testes uma vez por site:

```sh
bench --site v16.localhost set-config allow_tests true
```

Os arquivos em `erpnext_brasil/tests_bench/` já trazem tudo isso no `setUpClass`, e servem
de receita para o próximo.

## Fonte

Testado e documentado em 2026-08-29, na máquina de desenvolvimento deste projeto
(Windows 11 Pro, build 26100; WSL 2.7.12; Docker CE 29.7.2; MariaDB 12.3 nativo do
Windows e MariaDB 10.6 em container; Ubuntu 24.04.4 LTS no WSL2).

Atualização de 2026-08-31: Memurai for Redis v8.2-RC3 instalado nativamente
(`docs.memurai.com/en/installation.html`) — registrado como opção disponível para
rodar o bench sem WSL2/Docker, ainda não exercitado (ver seção no topo deste
documento).
