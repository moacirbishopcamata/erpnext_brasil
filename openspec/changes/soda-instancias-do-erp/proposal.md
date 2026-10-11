## Why

Hoje o ERPNext Brasil de desenvolvimento tem **uma porta e uma instância**: `scripts/subir.sh` sobe o bench v16 na 8001, e testar duas coisas ao mesmo tempo (duas branches, dois sites, duas sessões paralelas de trabalho em `.claude/worktrees/`) significa derrubar uma para subir a outra, ou disputar a mesma porta, o mesmo banco e os mesmos Redis. O projeto já sofre as consequências: o `docs/ambiente-dev-bench.md` registra benches e sites paralelos montados à mão (`v16.localhost`, `v16pg.localhost`, `hc16pg.localhost`, `fr16pg.localhost` e até um site órfão), cada um com receita própria, e o aviso recorrente sobre o servidor de banco compartilhado.

Falta uma forma única, segura e reproduzível de **ter várias instâncias do ERPNext Brasil de pé ao mesmo tempo, cada uma na sua porta, cada uma com uma identidade que não se repete e que dê para rastrear**, sem editar `common_site_config.json` nem `apps.txt` à mão a cada vez.

## What Changes

- Um aplicativo chamado **Soda**, no estilo do Cherry, para **criar, listar, iniciar, parar e remover instâncias do ERPNext Brasil**, cada uma em **portas diferentes**.
- Toda instância recebe um **UUID** (versão 4) **único e imutável**, gerado na criação e nunca reutilizado, nem depois de removida. O UUID aparece na interface (completo e abreviado, copiável), no registro e no `site_config` da instância.
- Ao lado do UUID, toda instância tem um **descritivo único**: um texto curto e legível (por exemplo, "NF-e em homologação") que não se repete entre instâncias. O UUID identifica para sempre; o descritivo identifica para quem lê, pode ser renomeado, e o histórico continua preso ao UUID.
- **O Cherry e o Chantilly passam a identificar cada instância pelo UUID, com o descritivo único**, lidos de um **contrato de identidade** publicado pelo Soda (registro com versão de esquema e as chaves `soda_instance_id` e `soda_descritivo` no `site_config`), de modo que as três ferramentas falem da mesma instância pelo mesmo nome.
- Cada instância tem um **nome de host único** derivado do descritivo e do UUID, no domínio `.localhost`. Isso importa além do enfeite: o navegador compartilha cookies entre portas do mesmo host, então duas instâncias em `localhost:8101` e `localhost:8102` derrubariam a sessão uma da outra. Com hosts diferentes (`a-1f3c9e2b.localhost`, `b-7d40aa11.localhost`) as sessões são independentes.
- **Alocação automática de portas**: um bloco por instância, dentro de uma faixa configurável, sem repetir entre instâncias, livre no sistema (verificado ao alocar) e fora das portas conhecidas do ambiente (3306, 5432, 6379, 8001, 9001, 11000 a 13999...). O usuário pode escolher a porta; se estiver ocupada, o Soda diz por quem.
- **Isolamento por site no mesmo bench** na primeira versão: cada instância é um site novo com banco próprio, **no servidor do perfil de banco que o Cherry configurou** (MariaDB e/ou PostgreSQL; a escolha do banco é do Cherry, não do Soda), servido por um processo web próprio na sua porta; o trabalhador de fila, o agendador, o Redis e o socket.io do bench são **compartilhados** e sobem uma só vez. Isolamento por bench completo (Redis e trabalhador próprios) fica como evolução, se for necessário.
- **Ciclo de vida seguro**: criar (com desfazer se falhar no meio), iniciar (idempotente, espera o servidor responder), parar (gentil, só os processos daquela instância, identificados por PID e não por nome) e remover (destrutivo: exige digitar o nome, faz backup antes e aposenta o UUID).
- **Estado reconciliado**: ao abrir, o Soda confere o registro contra a realidade (processo vivo? porta escutando?) e mostra o estado verdadeiro, inclusive "caiu".
- **Interface desktop e linha de comando idênticas em padrão ao Cherry**: tkinter só com a biblioteca padrão, núcleo puro testado a 100%, interface com teste no CI sob `xvfb` e piso próprio, escrita atômica, senha nunca em argumento de processo, operações longas em thread de trabalho com "Parar de esperar", vocabulário que não culpa, teclado completo, HiDPI, geometria validada contra a tela.

Fora desta mudança: produção (o servidor web de cada instância é o de desenvolvimento do Frappe, não o gunicorn), isolamento por bench, uma instância por branch de código (todas as instâncias compartilham o código do app do bench), exposição à rede, e clonagem de instância a partir de outra.

## Capabilities

### New Capabilities

- `instancias/identidade-e-portas`: UUID único e imutável, nome de host único, alocação de portas sem conflito e registro atômico das instâncias.
- `instancias/ciclo-de-vida`: criar, iniciar, parar e remover instâncias com segurança, e conciliar o registro com a realidade.
- `instancias/interface-soda`: a interface desktop e os comandos de terminal, no padrão do Cherry.
- `instancias/contrato-de-identidade`: o que o Cherry, o Chantilly e qualquer outra ferramenta podem ler e esperar estável sobre a identidade de uma instância (UUID, descritivo único, host, porta, estado).

### Modified Capabilities

Nenhuma.

## Impact

- Código novo: um pacote de regra pura (`erpnext_brasil/soda/`, sem `frappe`: UUID, nomes, alocador de portas, modelo do registro, conciliação de estado) e `scripts/soda/` (interface tkinter, comandos e execução no WSL), com licença MIT e versão próprias, como `scripts/cherry/`. `tests/test_arquitetura.py` passa a vigiar o pacote novo. A interface reutiliza `Bench`, `caminho_wsl` e a escrita atômica de `scripts/cherry/config.py`. Um leitor puro e somente leitura do contrato (`erpnext_brasil/soda/leitura.py`) é o que o Cherry e o Chantilly importam para identificar instâncias.
- Dependências: nenhuma além da biblioteca padrão (`uuid`, `socket`, `tkinter`).
- Dados: um registro por bench, em `sites/soda/registro.json`, com escrita atômica e trava; um arquivo de processos por instância; nada novo no banco do site além do que o `new-site` já cria.
- Ambiente: reaproveita `scripts/subir.sh` para os serviços compartilhados e o `bench` do WSL para criar e servir sites.
- CI: job do Soda no padrão do job do Cherry (`xvfb`, dois pisos de cobertura).
- Integração: o Cherry (mudança `cherry-instancias-por-uuid`) e o Chantilly (mudança `chantilly-monitor-de-recursos`) passam a identificar instâncias pelo UUID e pelo descritivo único. O Soda publica o contrato; as outras duas mudanças o consomem.
- Documentação nova: `docs/soda.md`; índice em `docs/README.md`.
