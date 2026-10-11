# Soda: várias instâncias do ERPNext Brasil, cada uma em portas diferentes

> **Estado (2026-10-11): o núcleo puro está implementado e mesclado (PR #22); ciclo de vida, interface e CLI ainda são proposta.** Mudança OpenSpec `soda-instancias-do-erp`: proposta, 4 specs, design e 34 tarefas, das quais 1.2, 1.3, 1.4, 1.6, 5.1 e 5.6 estão feitas. O que não está na seção "Núcleo implementado" abaixo descreve o que o Soda será. Visão conjunta das ferramentas: [`ferramentas-de-operacao.md`](ferramentas-de-operacao.md).

Pedido do usuário em 2026-10-11: *"um aplicativo para iniciar várias instâncias em portas diferentes para o ERPNext Brasil com um ID UUID único, estilo Cherry, com nome Soda"*. Depois: *o Cherry e o Chantilly irão identificar cada instância pelo ID UUID com um descritivo único*.

## Por que existe

Hoje há **uma porta e uma instância**: `scripts/subir.sh` sobe o bench v16 na 8001. Testar duas coisas ao mesmo tempo (duas branches, dois sites, duas sessões paralelas em `.claude/worktrees/`) obriga a derrubar uma para subir a outra ou a disputar porta, banco e Redis. O `docs/ambiente-dev-bench.md` mostra o resultado: sites paralelos montados à mão, cada um com receita própria.

## O que será

| Ação | O que faz |
|---|---|
| **Criar** | Um site novo no bench, com banco próprio **no servidor do perfil de banco que o Cherry configurou** (o Soda não escolhe o banco; sem perfil, recusa e aponta o Cherry), nome de host derivado do descritivo e do UUID, e os aplicativos: sempre o `erpnext` completo e o `erpnext_brasil` (o ERPNext Brasil é o ERPNext inteiro com a tropicalização brasileira), mais `hrms` e `healthcare` se escolhidos. Tudo ou nada: se falhar no meio, desfaz o que criou. |
| **Iniciar** | Sobe o servidor web da instância na sua porta (`bench --site <site> serve --port <porta> --noreload`) e garante os serviços compartilhados do bench, uma única vez. Só declara "no ar" quando o servidor responde. Idempotente. |
| **Parar** | Pedido de término educado ao processo da instância, identificado por **PID e registro, nunca por nome**. Não toca nas outras instâncias nem nos serviços compartilhados. Forçar exige confirmação separada. |
| **Remover** | Destrutivo: exige digitar o nome, faz backup antes, apaga site e banco, libera a porta, **aposenta o UUID**. Instância no ar não se remove. |
| **Renomear** | Altera o descritivo; UUID, host e porta ficam. |
| **Conciliar** | Ao abrir, compara registro, processos, portas e sites e mostra o estado verdadeiro: criando, parada, subindo, no ar, **caiu**, falhou ao subir, criação interrompida. Processo de instância sem registro vira "órfão" e não é encerrado sozinho. |

## Desempenho de cada instância e do seu banco

O Soda **lê e mostra** o desempenho de cada instância e do seu banco na lista: tempos de resposta (mediano e p95), CPU e memória do processo da instância, requisições e falhas por minuto, jobs em fila e em execução, e do banco (conexões, tamanho, consultas lentas, taxa de acerto do cache, tempo de resposta). **Quem coleta é o Chantilly**; o Soda consome o resumo que ele publica, identificado pelo UUID da instância, para não ter dois coletores medindo a mesma coisa. Sem o Chantilly, o desempenho aparece como "indisponível" com o motivo, nunca como zero, e cada valor mostra a idade da leitura. *Esta é a leitura adotada do pedido "o Soda lê toda a performance do sistema ERP e seu banco"; ver a decisão em aberto no `design.md`.*

## Identidade

UUID v4 imutável e nunca reutilizado + descritivo único (3 a 60 caracteres, único sem caixa nem acento) + host `descritivo-xxxxxxxx.localhost` + porta própria. Detalhes e o contrato que as outras ferramentas leem em [`ferramentas-de-operacao.md`](ferramentas-de-operacao.md).

**Por que host próprio:** o navegador compartilha cookies entre portas do mesmo host. Duas instâncias em `localhost:8101` e `localhost:8102` se derrubariam. Com `a-1f3c9e2b.localhost` e `b-7d40aa11.localhost` as sessões são independentes. O projeto já usa sites `.localhost` (`v16.localhost`, `v16pg.localhost`). *Premissa a confirmar na tarefa 1.1.*

## Portas

Faixa configurável (padrão 8100 a 8999), um bloco por instância, **livre no sistema no momento da alocação** (verificado abrindo a porta) e fora das portas conhecidas do ambiente: 3306, 5432, 6379, 8000, 8001, 9001, 6788 e as faixas de Redis do bench (11000 a 13999). Porta escolhida e ocupada: o Soda diz quem a ocupa e sugere a próxima. Por padrão a instância só escuta `127.0.0.1`; expor à rede exige opção explícita e aviso.

## O que é compartilhado entre as instâncias

Cada instância é um **site** do mesmo bench, então compartilha o código dos aplicativos, o servidor de banco (cada uma com o seu banco), o Redis, o **trabalhador de fila**, o agendador e o socket.io. Consequência honesta: um job pesado numa instância atrasa os das outras (há um `background_workers`). Isolamento por bench completo é evolução futura.

## Interface e terminal

Idêntica em padrão ao Cherry (ver [`ferramentas-de-operacao.md`](ferramentas-de-operacao.md)). Abas: **Instâncias** (lista com descritivo, UUID abreviado e copiável, host, porta, banco, aplicativos, estado por texto e ícone, tempo de atividade, filtro; ações iniciar, parar, abrir no navegador, copiar URL, ver saída, renomear, remover; cada ação indisponível diz por quê), **Nova instância** (restrições à vista antes do envio e pré-visualização do host e da porta), **Serviços** e **Bench**. Terminal: `criar`, `listar`, `iniciar`, `parar`, `remover`, `estado`; os que alteram o sistema exigem confirmação no próprio comando e, sem ela, mostram o plano e não alteram nada.

## Segurança e robustez

Senhas **nunca em argumento de processo** (ambiente e `WSLENV`, como no Cherry `0.2.0`); nomes só com caracteres seguros; registro com **escrita atômica** e trava contra dois Sodas, ou transação do SQLite; registro ilegível vai para quarentena; limite de instâncias no ar (padrão 8) para proteger a memória.

## Persistência

Registro em JSON (padrão) ou SQLite, à escolha, com migração sem perda e UUIDs aposentados preservados. Ver `persistencia-sqlite-opcional`.

## Núcleo implementado

Pacote `erpnext_brasil/soda/` (mais `erpnext_brasil/sistema/rede.py`): regra pura, **sem `frappe`, `tkinter` nem `integracao/`** (vigiado por `tests/test_arquitetura.py`). Cobertura de linhas e ramos: **100%**. Testes: `test_soda_identidade_e_portas.py`, `test_soda_modelo_e_registro.py` (a mesma bateria contra memória, JSON e SQLite, com concorrência e leitura por um segundo registro) e `test_soda_operacao_e_leitura.py`.

| Módulo | O que faz | Contratos principais |
|---|---|---|
| `identidade` | UUID v4, descritivo único (3 a 60 caracteres; unicidade sem caixa nem acento), nome de host `descritivo-xxxxxxxx.localhost`, UUID abreviado (8 hex) | pré: descritivo e UUID válidos (recusa com erro claro); pós: o host nunca colide entre dois UUIDs; UUID já usado ou aposentado nunca é sorteado de novo |
| `portas` | faixa 8100–8999, portas reservadas (3306, 5432, 6379, 8001, 9001, 6788, 8080, 11000–13999 e outras), menor livre ou porta escolhida | pré: porta escolhida fora das reservadas, do registro e dos programas do sistema; pós: nenhuma porta repetida; faixa esgotada falha alto |
| `modelo` | `Instancia` e `Aposentada` imutáveis, `Estado` e as tabelas de transição (ações do usuário × constatações da conciliação) | invariante: documento malformado é recusado (`DocumentoInvalido`); campo desconhecido é ignorado; aplicativos sempre incluem `erpnext` e `erpnext_brasil` |
| `registro` | criar, renomear, mudar estado, aposentar, descartar criação, consultas, limite de instâncias no ar | pós: o que um registro grava, outro relê; transição inválida recusada; instância subindo, no ar ou criando não se remove; registro de esquema mais novo é lido, nunca gravado (`RegistroMaisNovo`) |
| `conciliacao` | estado verdadeiro a partir de fatos observados; órfãos na faixa do Soda | fail-closed: fato desconhecido (`None`) mantém o estado e marca `incerto`; nunca encerra processo |
| `diario` | intenção registrada antes do primeiro passo, passos concluídos, desfecho, operações interrompidas | só se declara interrupção com prova de que o dono morreu; só operações terminadas são descartadas |
| `plano` | executor de passos com desfazer em ordem inversa | falha no terceiro de cinco passos deixa o estado final igual ao inicial; o passo que falhou e o passo cancelado também são desfeitos; falha ao desfazer é coletada, não engolida |
| `configuracao` | pasta `sites/soda/`, marcador `formato`, troca JSON↔SQLite | dois arquivos sem marcador são recusados (`ConfiguracaoAmbigua`); o marcador só muda depois de a releitura conferir |
| `leitura` | leitor somente leitura do contrato de identidade e chaves do `site_config` | sem método de escrita, não toma a trava; registro ruim é pulado com aviso; arquivo ilegível devolve leitura vazia marcada; paridade JSON/SQLite |

Achado pelos testes: no Windows a leitura do JSON falhava com `PermissionError` quando coincidia com a troca atômica do escritor; o adaptador (`persistencia/json_arquivo.py`) agora repete a leitura por cerca de 0,6 s.

**Ainda não existe:** execução real (criar site, iniciar e parar no WSL), conciliação com `/proc` e portas reais, interface, CLI, escrita de `soda_instance_id` no `site_config` (tarefa 5.2), teste de compatibilidade com arquivos versionados (5.3) e a prova real no bench (8.1, que exige autorização e backup).

## Estrutura planejada

`erpnext_brasil/soda/` (regra pura, **já implementada**: UUID, descritivo, host, alocador de portas, registro, conciliação, diário, executor de planos, leitor do contrato; faltam os planos concretos de criação e remoção) e `scripts/soda/` (tkinter, comandos, execução no WSL; **não iniciado**), com licença MIT e versão `0.1.0` próprias. Reaproveita `Bench`, `caminho_wsl` e a escrita atômica do Cherry.

## Docker (evolução)

Hoje cada instância do Soda é um **site** do mesmo bench. A configuração Docker ([`docker.md`](docker.md)) deixa pronto o que permitiria um segundo modo, **uma instância por pilha de contêineres** (isolamento por bench: Redis, trabalhador e código próprios, o que resolveria testar branches diferentes em paralelo): cada pilha é um projeto do Compose com nome derivado do UUID, porta própria e os rótulos `br.erpnext-brasil.instancia` e `br.erpnext-brasil.descritivo`. Esse modo **não está implementado**; é uma decisão em aberto no `design.md` do Soda.

## O que não faz

Não é para produção (o servidor de cada instância é o de desenvolvimento do Frappe), não isola código por branch (todas as instâncias usam o código do bench), não clona instância, não expõe à rede como fluxo normal.

## Testes e cobertura

Núcleo a 100% (**atingido** no pacote `soda`; o resto é meta) (piso de 95% no CI), interface com piso próprio sob `xvfb`, `ruff` limpo, suíte de contrato da persistência nos dois formatos, teste cruzado com o Cherry e o Chantilly, e uma prova real (criar duas instâncias, usar as duas ao mesmo tempo, parar uma, remover as duas) **somente com autorização e backup**.

## Decisões em aberto

Isolamento por site ou por bench (se a necessidade é testar **branches** em paralelo, por site não basta); aplicativos por instância; padrão de persistência; faixa de portas e limite de instâncias; backup por padrão na remoção; se o Cherry importa o leitor do Soda ou tem leitor próprio. Estão no `design.md`.
