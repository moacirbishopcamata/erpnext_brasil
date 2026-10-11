# Chantilly: monitor de recursos do ERPNext Brasil

> **Estado: proposta (2026-10-11). Nada foi implementado.** Mudança OpenSpec `chantilly-monitor-de-recursos` (PR de proposta aberto no GitHub): proposta, 5 specs, design e 56 tarefas. Este documento descreve o que o Chantilly será e será revisto quando houver código. Visão conjunta: [`ferramentas-de-operacao.md`](ferramentas-de-operacao.md).

Pedido do usuário em 2026-10-11: *"monitoramento de performance e custo de RAM, CPU e armazenamento, rodando em segundo plano, para o ERPNext Brasil"*, com *UX/UI profissional e idêntica ao Cherry*, gráficos (calor, uso diário, falhas), e a possibilidade de *parar e iniciar o ERP de forma gentil*.

> **Escopo:** o ERPNext Brasil é o ERPNext inteiro com a tropicalização brasileira. O Chantilly monitora **todo** o ERPNext (todos os módulos e DocTypes), com os DocTypes da camada brasileira destacados como um recorte, não como o todo.

> **Natureza:** complemento desktop em Python puro (só biblioteca padrão). O que exige o bench (tamanho das tabelas, duração dos jobs) é pedido ao próprio `bench execute`; as sondas de requisição são **opcionais** e só acrescentam a CPU por endpoint.

## Por que existe

O projeto mede **versões e CVE** (`scripts/auditar_pilha.py`) e **o relógio** (`medicao_do_relogio`), mas não mede recurso. O disco enche de XML fiscal, SPED e anexos; um job de emissão em lote disputa CPU e RAM com o balcão; e ninguém sabe quanto custa manter a operação nem o que cresce mais rápido. Ferramentas externas (Prometheus, Grafana) não sabem o que é um DocType nem um job do ERPNext e exigem serviços novos, o oposto do ambiente deste projeto (sem `sudo`, sem Docker).

## Dois processos

1. **Coletor em segundo plano**, no Linux ou no WSL2 do bench, só com a biblioteca padrão (leitura do `/proc`). Amostra a cada 60 s (configurável) CPU, carga, memória, troca, disco e CPU e memória por grupo de processo (web, trabalhadores, agendador, socket.io, Redis, banco). Grava num **SQLite** local, com retenção (7 dias brutos, 13 meses agregados, teto de 200 MB). Uma instância por bench.
2. **Interface desktop** no Windows, idêntica ao Cherry, que lê a série pelo caminho `\\wsl.localhost\...`.

O próprio Chantilly **mede o seu custo** e respeita um orçamento (1% de um núcleo, 64 MB); ao estourar, reduz a frequência e avisa.

## O que mede e como atribui

| Recurso | Como | Precisão |
|---|---|---|
| CPU por site, endpoint e job | tempo de CPU da thread e de relógio, somados por janela nos ganchos de requisição e de job | exata para o Python da thread; **não** inclui a CPU do banco em nome da requisição (aparece como "não atribuído") |
| Memória | variação da memória residente em 1% das execuções | **estimativa**, rotulada como tal |
| Armazenamento | metadados do servidor de banco (MariaDB ou PostgreSQL) por DocType e soma de `tabFile` por DocType de origem, de hora em hora | exata |
| Falhas | contagem por categoria: requisição com erro, job que falhou, queda de processo, intervalo perdido, falha do monitor | exata; **sem mensagem nem pilha** |

**Privacidade por construção:** guarda só nomes (site, método, job, DocType, instância) e números. Não há coluna onde caiba SQL, parâmetro, conteúdo, CPF/CNPJ ou nome de usuário. Falha da medição nunca derruba a requisição.

## Desempenho do banco e resumo publicado

Além do host e dos processos, o Chantilly lê **contadores do servidor de banco** de cada instância (conexões, consultas, consultas lentas, tamanho, taxa de acerto do cache, tempo de resposta de uma consulta de verificação) para MariaDB e PostgreSQL, **sem driver de terceiros** (pede ao bench) e **sem texto de consulta**. E publica um **resumo de desempenho por instância**, somente leitura, com versão de esquema e idade, que o [Soda](soda.md) lê para mostrar o desempenho de cada instância na sua lista.

## Identificação por instância

Quando o bench tem instâncias do [Soda](soda.md), o consumo, o armazenamento, as falhas e o custo são atribuídos pelo **UUID**, e a interface mostra o **descritivo único**. O histórico fica preso ao UUID: renomear não o divide, remover o preserva sob o último descritivo, marcado como removida. Sem o Soda, cada site é uma instância sem UUID.

## Custo

Consumo vezes **preço informado pelo usuário** (hora de CPU, GB-hora de memória, GB-mês de armazenamento), com aritmética decimal exata e sempre rotulado como **estimativa**, com o período. **Nunca presume preço**: sem preço, mostra o consumo e diz que o preço não foi informado. Mostra a parte "não atribuída" em vez de ratear em silêncio.

## Alertas e previsão

Limiares de disco, memória, troca e CPU com **histerese**, sem repetir o alerta enquanto o estado persistir; **previsão de esgotamento do disco** por tendência linear dos últimos 14 dias (só com 3 dias ou mais de dados), identificada como projeção. "Coletor parado" é um estado visível: dados velhos não passam por atuais. A entrega usa o canal de notificação que o app já tem (`notificar_responsaveis`), por um job agendado, sem exigir a interface aberta.

## Gráficos

Todos no `Canvas`, sem matplotlib, com eixos rotulados e unidade, legenda, período e título que diz a pergunta que responde:

| Gráfico | Pergunta |
|---|---|
| Mapa de calor hora × dia da semana | Quando o sistema pesa? |
| Uso diário, 30 dias, com horário de pico | Qual dia e a que horas foi o pico? |
| Falhas por categoria ao longo do tempo | O que está quebrando? |
| Maiores consumidores (barras) | Quem pesa? |
| Armazenamento empilhado por DocType com projeção | Quando o disco acaba, e por culpa de quem? |
| Distribuição de duração com p50, p95 e p99 | É lento sempre ou às vezes? |

Escala de cor sequencial perceptível por daltônicos, estado por texto e ícone além da cor, valor ao passar o ponteiro e tabela equivalente, e **lacunas de coleta desenhadas como lacunas**, nunca interpoladas. Pizza e rosca foram descartadas.

## Parar e iniciar o ERP

A monitoração é somente leitura; **iniciar e parar o ERP é a única ação de controle**, sempre explícita, e **nunca automática**: nenhum alerta ou falha reinicia nada.

- **Iniciar:** reaproveita `scripts/subir.sh` (idempotente).
- **Parar, com gentileza**, em etapas verificadas no código do Frappe 16: (1) avisa os usuários conectados (antecedência padrão de 2 min; a forma de enviar o aviso ainda precisa ser confirmada); (2) coloca os sites em **manutenção somente leitura** (`maintenance_mode` com `allow_reads_during_maintenance`), então quem consulta continua consultando; (3) o agendador deixa de enfileirar; (4) espera os jobs terminarem (`any_job_pending`, até 120 s); (5) encerra os processos com `SIGTERM`. **Forçar nunca é o padrão** e exige confirmação separada que nomeia o que será interrompido.
- **Operação fiscal em trânsito** (transmissão sem desfecho, lote do eSocial, NFC-e pendente) **bloqueia** a parada por padrão.
- **Banco e Redis** ficam fora da parada padrão (o servidor é compartilhado); parar é pedido à parte, com a contagem de conexões.
- O Chantilly só desfaz a manutenção que **ele mesmo** ligou. Cada ação é registrada. A **parada planejada** aparece nos gráficos distinta de falha. Pilha gerenciada por supervisor ou systemd é **recusada**. Processos são identificados por PID e diretório do bench, nunca por nome (o `subir.sh` registra que `pgrep -f` já matou o próprio shell).
- No terminal, `iniciar` e `parar` exigem `--confirmo`; sem ele mostram o plano e o que está em trânsito.

## Interface

Idêntica ao Cherry (ver [`ferramentas-de-operacao.md`](ferramentas-de-operacao.md)). Abas: **Visão geral** (cartões de CPU, memória e disco com valor, série, estado e projeção; instrução quando não há dado), **Processos**, **Consumo**, **Armazenamento**, **Custo**, **Alertas**, **Controle** e **Coletor**. Filtro e comparação por instância em todas as abas.

## Persistência

Série **só em SQLite**. Configuração (limiares, preços) e registro das ações de controle em JSON ou SQLite, à escolha. Ver `persistencia-sqlite-opcional`.

## Estrutura planejada

`erpnext_brasil/chantilly/` (regra pura: leitura de `/proc` a partir de texto, agregação, retenção, projeção, limiares, custo, escalas dos gráficos), `scripts/chantilly/` (coletor e interface tkinter) e sondas finas em `erpnext_brasil/integracao/`. Licença MIT e versão `0.1.0` próprias.

## Testes e cobertura (meta)

Núcleo a 100% (piso de 95% no CI), interface com piso próprio sob `xvfb`, `ruff` limpo, teste de que nenhuma coluna guarda conteúdo, teste de que falha da sonda não afeta a requisição, e medições reais no WSL2 (comparação com `top` e `df`, custo das sondas em mil chamadas). A prova de parar e iniciar no bench de desenvolvimento exige **autorização e backup**.

## Limites declarados

Nada foi medido ainda no WSL2; o `/proc` do WSL2 é o da máquina virtual do bench. A CPU do banco não é atribuível por requisição. SQLite em compartilhamento de rede é frágil: a interface abre o arquivo só para leitura, com um resumo atômico em JSON como plano B. Memória por requisição é estimativa.

## Decisões em aberto

O que "custo" significa (consumo mais preço informado foi o entendido), foco em desenvolvimento e produção Linux, retenção, reuso do Cherry, Prometheus fora, controle de produção gerenciada fora, prazos da parada. Estão no `design.md`.
