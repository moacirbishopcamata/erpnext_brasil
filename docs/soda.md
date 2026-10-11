# Soda: várias instâncias do ERPNext Brasil, cada uma em portas diferentes

> **Estado: proposta (2026-10-11). Nada foi implementado.** Mudança OpenSpec `soda-instancias-do-erp`: proposta, 4 specs, design e 34 tarefas. Este documento descreve o que o Soda será; ele será revisto quando houver código. Visão conjunta das ferramentas: [`ferramentas-de-operacao.md`](ferramentas-de-operacao.md).

Pedido do usuário em 2026-10-11: *"um aplicativo para iniciar várias instâncias em portas diferentes para o ERPNext Brasil com um ID UUID único, estilo Cherry, com nome Soda"*. Depois: *o Cherry e o Chantilly irão identificar cada instância pelo ID UUID com um descritivo único*.

## Por que existe

Hoje há **uma porta e uma instância**: `scripts/subir.sh` sobe o bench v16 na 8001. Testar duas coisas ao mesmo tempo (duas branches, dois sites, duas sessões paralelas em `.claude/worktrees/`) obriga a derrubar uma para subir a outra ou a disputar porta, banco e Redis. O `docs/ambiente-dev-bench.md` mostra o resultado: sites paralelos montados à mão, cada um com receita própria.

## O que será

| Ação | O que faz |
|---|---|
| **Criar** | Um site novo no bench, com banco próprio (MariaDB ou PostgreSQL), nome de host derivado do descritivo e do UUID, e os aplicativos escolhidos. Tudo ou nada: se falhar no meio, desfaz o que criou. |
| **Iniciar** | Sobe o servidor web da instância na sua porta (`bench --site <site> serve --port <porta> --noreload`) e garante os serviços compartilhados do bench, uma única vez. Só declara "no ar" quando o servidor responde. Idempotente. |
| **Parar** | Pedido de término educado ao processo da instância, identificado por **PID e registro, nunca por nome**. Não toca nas outras instâncias nem nos serviços compartilhados. Forçar exige confirmação separada. |
| **Remover** | Destrutivo: exige digitar o nome, faz backup antes, apaga site e banco, libera a porta, **aposenta o UUID**. Instância no ar não se remove. |
| **Renomear** | Altera o descritivo; UUID, host e porta ficam. |
| **Conciliar** | Ao abrir, compara registro, processos, portas e sites e mostra o estado verdadeiro: criando, parada, subindo, no ar, **caiu**, falhou ao subir, criação interrompida. Processo de instância sem registro vira "órfão" e não é encerrado sozinho. |

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

## Estrutura planejada

`erpnext_brasil/soda/` (regra pura: UUID, descritivo, host, alocador de portas, registro, conciliação, planos de criação e remoção, leitor do contrato) e `scripts/soda/` (tkinter, comandos, execução no WSL), com licença MIT e versão `0.1.0` próprias. Reaproveita `Bench`, `caminho_wsl` e a escrita atômica do Cherry.

## O que não faz

Não é para produção (o servidor de cada instância é o de desenvolvimento do Frappe), não isola código por branch (todas as instâncias usam o código do bench), não clona instância, não expõe à rede como fluxo normal.

## Testes e cobertura (meta)

Núcleo a 100% (piso de 95% no CI), interface com piso próprio sob `xvfb`, `ruff` limpo, suíte de contrato da persistência nos dois formatos, teste cruzado com o Cherry e o Chantilly, e uma prova real (criar duas instâncias, usar as duas ao mesmo tempo, parar uma, remover as duas) **somente com autorização e backup**.

## Decisões em aberto

Isolamento por site ou por bench (se a necessidade é testar **branches** em paralelo, por site não basta); aplicativos por instância; padrão de persistência; faixa de portas e limite de instâncias; backup por padrão na remoção; se o Cherry importa o leitor do Soda ou tem leitor próprio. Estão no `design.md`.
