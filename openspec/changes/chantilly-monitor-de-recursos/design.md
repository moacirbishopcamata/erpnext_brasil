## Context

Ver `proposal.md` (Why). O que o repositório já estabelece e que molda o desenho:

- A fronteira do projeto: regra **pura** (`fiscal/`, `contabil/`, `folha/`, sem `frappe`), camada **fina** (`integracao/`) e `tests/test_arquitetura.py` que vigia isso com `ast`. O Chantilly segue a mesma fronteira.
- O Cherry (`scripts/cherry/`) é o molde pedido: núcleo `config.py` sem tkinter e com 100% de cobertura, `app.py` em tkinter só com a biblioteca padrão, versão e licença MIT próprias, `docs/cherry.md` com as fontes de UX, job de CI com `xvfb` e dois pisos de cobertura (95% no núcleo, 87% na interface), leitura do bench no WSL por `\\wsl.localhost\...` e, desde a `0.2.1`, operações longas numa thread de trabalho com "Parar de esperar".
- O bench roda só em WSL2/Linux (`scripts/subir.sh`, sem sudo e sem Docker); a interface roda no Windows e edita/lê arquivos do bench pelo caminho UNC.
- Alertas fiscais já têm canal: `integracao/notificacao.notificar_responsaveis`, usado por `alerta_certificado`, `alerta_fiscal` e `medicao_do_relogio`, disparados por `scheduler_events` em `hooks.py`.
- O padrão de "medir e guardar" do relógio: sonda e decisão puras, cola fina, degradação sem barulho quando o dado falta.

## Goals / Non-Goals

**Goals:**
- Série histórica de CPU, RAM e armazenamento do host e dos processos do bench, sem serviço novo e sem dependência obrigatória.
- Atribuir consumo ao que o ERPNext entende: site, endpoint, job, DocType.
- Converter consumo em custo estimado só com preços informados pelo usuário.
- Interface desktop **idêntica ao Cherry** em padrão, aparência e comportamento, e **mais clara à primeira vista** que uma tabela de números.
- Custo do próprio monitor mensurável e limitado.

**Non-Goals:**
- Página no desk do Frappe, exportador Prometheus, monitoramento do Windows hospedeiro, qualquer ação corretiva **automática** (inclusive reiniciar o ERP sozinho) e controle de pilha gerenciada por supervisor ou systemd.
- Substituir observabilidade de produção em larga escala (APM, tracing distribuído).
- Atribuir memória com precisão por requisição: é estimativa, e a spec manda dizer isso.
- Guardar conteúdo, consulta ou dado pessoal.

## Decisions

1. **Três camadas, na fronteira de sempre.**
   - `erpnext_brasil/chantilly/` (puro): leitura de `/proc` a partir de **texto** (as funções recebem o conteúdo e devolvem estruturas, então testam sem Linux), agregação, retenção, projeção, limiares com histerese, custo com `Decimal`.
   - `scripts/chantilly/` (tkinter e processo): `coletor` (laço de amostragem e acesso ao SQLite) e `app` (interface). Reutiliza `Bench` e `caminho_wsl` de `scripts/cherry/config.py` em vez de duplicar; a dependência é só do Chantilly para o Cherry.
   - `erpnext_brasil/integracao/` (fino): sondas de requisição e job, consulta de armazenamento por DocType, job de alertas.
   Alternativa descartada: tudo dentro do app Frappe, com DocTypes para as amostras. Pesaria no banco do site que se quer proteger e não enxergaria o host.
2. **Armazenamento: um SQLite por bench, em `sites/chantilly.sqlite` (fora de qualquer site).** Biblioteca padrão, modo WAL, sem servidor. Os escritores são o coletor e as sondas (que gravam **em lote**, a cada 30 s, nunca por requisição); a interface e o job de alertas só leem. Alternativa descartada: Redis (some no reinício, justamente quando mais se quer o histórico) e DocType (peso no banco do site).
3. **Atribuição de CPU por `time.thread_time()` e `time.perf_counter()` nos ganchos `before_request`/`after_request` e nos de job**, somados em agregados em memória por (site, método) e descarregados no lote. É exata para CPU de Python na thread da requisição; não cobre CPU gasta pelo servidor de banco de dados em nome da requisição, e a documentação diz isso. O resto do consumo do host aparece como "não atribuído".
4. **Memória por amostragem, 1% das execuções**, medindo a variação da memória residente do trabalhador antes e depois. Declarada estimativa. Alternativa descartada: `tracemalloc` em tudo (custo alto demais para produção).
5. **Armazenamento exato e barato.** `information_schema.TABLES` (MariaDB) ou `pg_total_relation_size` (PostgreSQL), uma vez por hora por site, mais `SUM(file_size)` agrupado em `tabFile`. É leitura de metadados, não varredura de dados.
6. **Orçamento do próprio custo.** O coletor mede seu `process_time` e seu RSS por janela; excedido por três janelas, dobra o intervalo, suspende a amostragem de memória e registra. As sondas têm um interruptor global que o coletor liga e desliga pelo arquivo de séries.
7. **Falha do monitor nunca derruba o produto.** Toda sonda captura exceção, conta e segue. Um teste injeta exceção na sonda e prova que a requisição conclui.
8. **Privacidade por construção.** O esquema do SQLite só tem colunas de nome e número; não existe coluna onde caiba SQL, parâmetro ou usuário. Um teste confere o esquema.
9. **Interface idêntica ao Cherry, e mais clara.** Mesmo molde: `Tk` com tema do sistema, `ttk.Notebook` com `enable_traversal`, `underline` nas abas e botões, barra de estado e marca "✓" que some em 2,5 s, `_problema` como único modal, vocabulário "não foi possível", `SetProcessDpiAwareness`, geometria em `~/.chantilly.json` **validada contra a tela** (o CH-08 do Cherry não se repete), operação longa em thread com fila e "Parar de esperar". Abas: **Visão geral** (cartões de CPU, memória e disco com valor, série e estado), **Processos**, **Consumo** (por site, endpoint e job, ordenável), **Armazenamento** (por DocType e arquivo), **Custo** (preços e estimativa), **Alertas**, **Controle** (iniciar e parar o ERP) e **Coletor** (escolher bench, iniciar e parar o coletor, custo do próprio Chantilly). Gráficos no `Canvas`, sem matplotlib, com eixos rotulados, unidades e uma paleta distinguível por daltônicos; estado por texto e ícone, nunca só cor. Estado vazio mostra instrução, não gráfico vazio.
10. **Catálogo de gráficos (cada um responde a uma pergunta).** Todos desenhados no `Canvas`; o núcleo puro calcula pontos, escalas, ticks e agrupamentos, e a interface só desenha.
    - **Mapa de calor hora × dia da semana** ("quando o sistema pesa?"): grade 24×7 com a média do período; escala sequencial de um só matiz (claro para escuro) com legenda numérica e valor ao passar o ponteiro. Lacunas de coleta ficam em cinza hachurado, nunca em "zero".
    - **Uso diário, 30 dias** ("qual dia e a que horas foi o pico?"): barras por dia (CPU-hora, memória média ou requisições) com marcador do horário de pico.
    - **Falhas por categoria** ("o que está quebrando?"): barras empilhadas por dia para requisição com erro, job que falhou, queda de processo, intervalo perdido e falha do monitor, mais a lista dos métodos com mais falhas.
    - **Maiores consumidores** ("quem pesa?"): barras horizontais ordenadas por site, endpoint ou job, com o consumo e, se houver preço, o custo estimado.
    - **Armazenamento empilhado + projeção** ("quando o disco acaba, e por culpa de quem?"): áreas empilhadas dos N maiores DocTypes, demais em "outros", e a reta de projeção tracejada e rotulada.
    - **Distribuição de duração** ("é lento sempre ou às vezes?"): histograma por faixas com p50, p95 e p99 marcados.
    - **Séries da visão geral** (CPU, memória, disco) com a faixa de limiar desenhada.
    Alternativa descartada: pizza ou rosca para custo e armazenamento (comparam mal e escondem pequenas fatias); barras e áreas empilhadas respondem melhor.
11. **Acessibilidade e honestidade dos gráficos.** Paleta sequencial perceptível por daltônicos (um matiz, variando a luminosidade) e categorias distinguíveis por forma e rótulo além de cor; toda célula e barra tem valor por ponteiro e uma tabela equivalente; lacunas de coleta aparecem como lacunas e nunca são interpoladas.
12. **Controle do ERP (iniciar e parar), explícito e gracioso.** A monitoração continua somente leitura; esta é a única ação de escrita sobre o sistema, e por isso tem regras próprias.
    - **Iniciar** chama `scripts/subir.sh` (já idempotente, sem `sudo`, sem Docker) pelo mesmo executor injetável que o Cherry usa, em `wsl -d <distro> -- bash`, com o `BENCH` do bench escolhido. Não se reimplementa a subida.
    - **Parar** não existe hoje em script nenhum, e a parada é **gentil**, em etapas verificadas no código do Frappe 16 instalado:
      1. **Aviso** aos usuários conectados com antecedência configurável (padrão 2 min), por mensagem em tempo real do Frappe; dispensado se ninguém estiver conectado. *A verificar:* o meio exato de enviar a mensagem e de contar sessões ativas.
      2. **Manutenção somente leitura:** `maintenance_mode` com `allow_reads_during_maintenance` no `site_config` (`frappe/app.py`): quem consulta continua consultando, ninguém grava. Ligado por `bench --site <site> set-maintenance-mode on`, comando do próprio Frappe, em vez de editar o arquivo à mão.
      3. **Agendador quieto:** em manutenção o agendador deixa de enfileirar (`frappe/utils/scheduler.py`, `is_scheduler_inactive`), sem precisar de nenhum passo extra.
      4. **Escoamento:** esperar `any_job_pending(site)` (`frappe/utils/doctor.py`, que lê as filas e os registros de jobs em execução do RQ) ficar falso, até o prazo (padrão 120 s).
      5. **Encerramento educado:** `SIGTERM` ao servidor web, aos trabalhadores, ao agendador e ao socket.io; os trabalhadores do RQ terminam o job corrente ao receber `SIGTERM`. `SIGKILL` só depois de confirmação separada que nomeia o que será morto, e nunca como ação padrão.
      O Chantilly guarda quais sites **ele** pôs em manutenção para só desfazer esses (um site em manutenção por decisão do administrador continua assim).
    - **Identificação por PID, nunca por nome.** O coletor já lê `/proc/<pid>/cwd` e `/proc/<pid>/cmdline` para agrupar processos; o controle usa o mesmo mapa e só age em processos cujo `cwd` está dentro do bench escolhido. O próprio `subir.sh` registra que `pgrep -f` casa com a linha de comando que o contém e já matou o próprio shell: padrão de nome fica proibido.
    - **Verificação prévia fiscal.** Uma leitura nova em `integracao/` conta requisições e jobs em andamento e as operações fiscais em trânsito (`Transmissao Fiscal` sem desfecho, `Lote eSocial` em transmissão, `Pendencia NFC-e`), sem alterar nada. Operação fiscal em trânsito bloqueia a parada por padrão: o projeto grava o desfecho antes de qualquer erro, mas uma emissão interrompida entre o envio e o retorno deixa o documento indeterminado até a consulta, e é isso que se evita.
    - **Banco e Redis ficam de fora da parada padrão.** O servidor de banco local é compartilhado entre sites e benches (ver o aviso do `docs/ambiente-dev-bench.md` sobre o servidor compartilhado); pará-lo é pedido à parte, com contagem de conexões e confirmação.
    - **Supervisor ou systemd:** a cadeia de processos pai é lida do `/proc`; se um gerenciador aparece, o Chantilly recusa. Em produção gerenciada o certo é o gerenciador.
    - **Parada planejada** é um estado da série, gravado pelo coletor quando o controle registra a intenção; some quando o ERP volta ou quando o prazo máximo de parada (configurável) expira, para que um esquecimento não silencie os alertas para sempre.
    - **Registro** em arquivo de acréscimo (`sites/chantilly-controle.log`), com data, ação, usuário do sistema, bench, resultado e motivo; sem segredo.
    - **Terminal:** `iniciar` e `parar` exigem `--confirmo` para executar; sem ele mostram o plano e o que está em trânsito e saem (equivale a um ensaio).
    - **Interface:** aba **Controle** no molde do Cherry: estado atual do ERP, o que está em trânsito, botão "Parar o ERP" e "Iniciar o ERP", a opção de parar também o banco recolhida sob "Mostrar opções avançadas" (divulgação progressiva), saída em tempo real e "Parar de esperar".
13. **Nome e versão.** Chantilly, `0.1.0`, licença MIT própria em `scripts/chantilly/LICENSE`, `docs/chantilly.md` com as fontes de UX relidas na web antes de desenhar a tela.
14. **Teste e CI como o Cherry.** Núcleo (`erpnext_brasil/chantilly/`) a 100% e com teste na costura (escrever no SQLite e reler por outro caminho); `test_app.py` com janela oculta; job de CI com `xvfb`, piso de 95% no núcleo e piso da interface dois pontos abaixo do medido.

## Risks / Trade-offs

- **Contar com `/proc` no WSL2:** o WSL2 expõe o `/proc` da sua máquina virtual, não o do Windows. Documentar que o Chantilly mede a VM em que o bench roda, que é o que importa para o bench. Verificar na máquina antes de prometer.
- **CPU do banco não atribuível por requisição:** aparece como "não atribuído"; quem quiser mais detalhe usa o Recorder do Frappe. A spec manda mostrar a diferença.
- **SQLite com vários escritores:** WAL e lotes curtos mitigam; um teste de concorrência com o coletor e duas sondas simuladas mede perda de escrita. Se houver `database is locked`, a sonda descarta o lote e conta, em vez de bloquear a requisição.
- **Acesso ao arquivo pelo UNC:** SQLite em compartilhamento de rede é frágil. A interface abre o arquivo em **somente leitura** e, se a leitura falhar, mostra a mensagem e tenta de novo; o gargalo é do compartilhamento do WSL, a verificar na prática. Alternativa se falhar: o coletor publica também um resumo em JSON atômico (o mesmo padrão de escrita atômica do Cherry) que a interface lê.
- **Gráficos em tkinter:** exigem trabalho de desenho e de teste; o ganho é zero dependência. O núcleo calcula os pontos, escalas e agrupamentos (puro e testável), e a interface só desenha. O mapa de calor (168 células) e o uso diário (30 barras) são pequenos; o risco real é o histograma e o empilhado de séries longas, que precisam de agregação prévia no núcleo para não desenhar milhares de elementos.
- **Preços como fonte de erro:** valor monetário errado pode enganar. Mitigação: estimativa sempre rotulada, preço nunca presumido, período sempre visível.
- **Parar um ERP fiscal é arriscado:** a mitigação é a verificação prévia, o bloqueio por padrão com operação fiscal em trânsito, a parada gradual e o registro. Ainda assim a prova real exige um ciclo de parar e iniciar no bench de desenvolvimento, que só será feito com autorização explícita do dono do projeto, com backup antes.
- **Aviso e contagem de usuários dependem do Frappe:** o meio de transmitir a mensagem e de contar as sessões precisa ser confirmado antes de prometer a antecedência de 2 minutos; se não houver como, a etapa 1 vira apenas a contagem regressiva ao operador, e a spec e a tarefa dizem isso.
- **Sinal no processo errado:** o `cwd` de um processo pode não estar legível sem permissão; nesse caso o Chantilly não age naquele processo e informa, em vez de supor.
- **Produção:** a spec garante o comportamento; **a implantação em produção** (supervisor ou systemd) fica documentada e não automatizada nesta mudança.

## Open Questions

Decisões que mudam o que se constrói e que o dono do projeto precisa confirmar antes da aplicação:

1. **"Custo"** foi entendido como **consumo mais preço opcional informado pelo usuário** (nunca preço presumido). Se a intenção é outra (por exemplo, custo de nuvem importado de uma fatura), muda a spec `custo-estimado`.
2. **Foco:** desenvolvimento (WSL2) e produção Linux têm o mesmo coletor; a interface roda no Windows. Se a interface também precisar rodar **no servidor de produção sem display**, os comandos de terminal passam a ser a superfície principal.
3. **Retenção:** 7 dias brutos, 13 meses agregados e teto de 200 MB são padrões propostos. Confirmar contra o que o negócio precisa guardar.
4. **Reuso do Cherry:** o Chantilly importa de `scripts/cherry/config.py`. Se preferirem independência total entre as ferramentas, extrai-se um módulo comum pequeno, ao custo de tocar no Cherry.
5. **Exportar para Prometheus** ficou de fora; vale reabrir se já existir um Prometheus na operação.
6. **Parar e iniciar** foi desenhado para o bench de desenvolvimento (WSL2) e recusa pilha gerenciada. Se a intenção é controlar também produção gerenciada, o Chantilly teria de chamar o gerenciador (`supervisorctl`, `systemctl`), o que muda a segurança e o escopo.
7. **Prazo de parada gradual** de 120 s e **prazo máximo de parada planejada** (padrão a decidir) são palpites; confirmar.
