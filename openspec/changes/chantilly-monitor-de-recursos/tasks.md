## 1. Fundação: pesquisa, núcleo puro e fronteira

- [ ] 1.1 Verificar na máquina o que o `/proc` do WSL2 entrega (CPU, memória, processos, discos) e ler as fontes de UX de `docs/cherry.md` de novo na web, registrando o que valeu em `docs/chantilly.md` — verificar com a tabela "o que é medido e de onde" no documento, com o comando que a gerou.
- [ ] 1.2 Criar `erpnext_brasil/chantilly/` (sem `frappe`) com as estruturas de amostra e o leitor de `/proc` a partir de **texto** — verificar com testes que alimentam trechos reais de `/proc/stat`, `/proc/meminfo`, `/proc/<pid>/stat` e `/proc/<pid>/status` e conferem os números.
- [ ] 1.3 Estender `tests/test_arquitetura.py` para vigiar o pacote novo (não importa `frappe` nem `integracao/`) — verificar acrescentando um import proibido e vendo o teste falhar.
- [ ] 1.4 Núcleo de agregação, retenção (bruto para horário), projeção linear e limiares com histerese — verificar com testes de borda (oscilação em torno do limiar, menos de 3 dias de dados, série com buraco) e 100% de cobertura do pacote.
- [ ] 1.5 Núcleo de custo com `Decimal`: preço ausente, preço parcial, arredondamento para centavos e linha "não atribuído" — verificar com os cenários da spec `custo-estimado` como testes.

## 2. Armazenamento da série (SQLite)

- [ ] 2.1 Esquema do SQLite só com colunas de nome e número, em `sites/chantilly.sqlite`, modo WAL — verificar com um teste que lê o esquema e falha se existir coluna de tipo texto livre fora da lista de nomes permitidos.
- [ ] 2.2 Gravação em lote e leitura somente leitura, com teto de tamanho e descarte dos agregados mais antigos — verificar com teste de costura: grava por um caminho e relê por outro, e simula o teto atingido.
- [ ] 2.3 Concorrência: coletor e duas sondas simuladas escrevendo ao mesmo tempo — verificar medindo lotes perdidos (deve ser contado, nunca bloqueante) e documentar o número.

## 3. Coletor em segundo plano

- [ ] 3.1 `scripts/chantilly/coletor`: laço de amostragem do host e dos grupos de processo do bench, com ausência registrada como ausência e métrica ilegível como nula com motivo — verificar com executor/lerdor injetável e testes dos três cenários da spec.
- [ ] 3.2 Instância única por bench (trava em arquivo) e comandos `iniciar`, `parar`, `estado` e `relatorio` — verificar iniciando duas vezes e vendo a segunda recusada com o identificador da primeira.
- [ ] 3.3 Orçamento do próprio custo: mede CPU e RSS próprios, dobra o intervalo ao exceder por três janelas e registra o motivo — verificar com um relógio e um medidor injetados que simulam o estouro.
- [ ] 3.4 Rodar no WSL2 real por pelo menos 30 minutos e comparar com `top` e `df` — verificar com a tabela de comparação no `docs/chantilly.md`, dizendo a diferença encontrada.

## 4. Sondas dentro do ERPNext

- [ ] 4.1 Sondas de requisição (`before_request`/`after_request`) e de job, com agregados em memória descarregados em lote a cada 30 s — verificar com teste de bench que faz chamadas reais e relê os agregados do SQLite.
- [ ] 4.2 Amostragem de memória em fração configurável (padrão 1%), rotulada estimativa — verificar com teste que conta quantas de mil execuções foram medidas.
- [ ] 4.3 Falha da sonda nunca afeta a requisição — verificar com teste que injeta exceção na sonda e confere a resposta normal e o contador de falhas.
- [ ] 4.4 Nenhum dado pessoal: requisição com CPF/CNPJ no parâmetro não deixa rastro — verificar procurando o valor em todas as tabelas do SQLite após a chamada.
- [ ] 4.4a Contagem de falhas por categoria (requisição com erro, job que falhou, queda de processo, intervalo perdido, falha do monitor) sem mensagem nem pilha — verificar provocando cada categoria e procurando o texto do erro no SQLite, que não pode estar lá.
- [ ] 4.4b Identificação da instância: UUID de `frappe.conf` na sonda, UUID como chave dos agregados e tabela de rótulos com histórico de descritivo — verificar com teste de bench com dois sites com UUID, renomeando o descritivo e conferindo que a série continua única; e com um bench sem Soda, onde o site vira instância sem UUID.
- [ ] 4.4c Contadores de desempenho do banco por instância (conexões, consultas, consultas lentas, tamanho, taxa de acerto, tempo de resposta) para MariaDB e PostgreSQL, pedidos ao bench sem driver e sem texto de consulta — verificar em bench nos dois bancos e procurando texto de consulta no SQLite, que não pode estar lá.
- [ ] 4.4d Resumo de desempenho por instância publicado somente para leitura, com versão de esquema e idade, e leitor puro para o Soda — verificar com leitor lendo durante a gravação, com resumo velho marcado como desatualizado, e sem nenhum dado pessoal.
- [ ] 4.5 Armazenamento exato por DocType (MariaDB e PostgreSQL) e por arquivo anexo, uma vez por hora — verificar em bench nos dois bancos, conferindo `Transmissao Fiscal` e `Arquivo SPED` contra `information_schema` e `pg_total_relation_size`.
- [ ] 4.6 Medir o custo das sondas: a requisição com e sem Chantilly, 1.000 chamadas — verificar com a diferença média registrada e comparada ao orçamento.

## 5. Alertas e previsão

- [ ] 5.1 Job agendado que lê a série, aplica limiares e histerese e entrega por `notificar_responsaveis` sem repetir — verificar com teste de bench que cruza o limiar duas vezes e conta uma notificação.
- [ ] 5.2 Previsão de esgotamento do disco, só com 3 dias ou mais de dados — verificar com série sintética de crescimento conhecido, conferindo os dias projetados.
- [ ] 5.3 Estado "coletor parado" por três intervalos sem amostra — verificar com relógio injetado.
- [ ] 5.4 Configuração de limiares e preços (DocType único de configuração) e declaração dos campos em `setup/` — verificar com o teste de costura de campos e hooks (`test_costura_campos_e_hooks`).

## 6. Interface desktop idêntica ao Cherry

- [ ] 6.1 Esqueleto da interface no molde do Cherry: janela, `ttk.Notebook` com `enable_traversal`, barra de estado, marca "✓", `_problema`, nitidez em HiDPI, escolha do bench reaproveitando `Bench` e `caminho_wsl` — verificar com `test_app.py` (janela oculta) e a lista de diretrizes do Cherry conferida uma a uma.
- [ ] 6.2 Geometria lembrada **e validada contra a área visível** — verificar com teste que grava uma geometria fora da tela e vê a janela abrir centralizada.
- [ ] 6.3 Aba **Visão geral**: cartões de CPU, memória e disco com valor, série temporal, estado por texto e ícone, projeção do disco e estado vazio com instrução — verificar vendo a tela de verdade (captura) nos três estados e com o coletor parado.
- [ ] 6.4 Base de gráficos no `Canvas`: eixos rotulados, unidades, legenda, tabela equivalente, valor ao passar o ponteiro, paleta sequencial para daltônicos e lacuna desenhada como lacuna; pontos, escalas e ticks calculados no núcleo — verificar com testes do núcleo (escala, ticks, formatação de unidade, lacuna sem interpolação) e inspeção visual.
- [ ] 6.4a Mapa de calor hora × dia da semana (CPU, memória e requisições) — verificar com série sintética de pico conhecido (segunda-feira às 14h) e a célula mais intensa batendo, e com uma lacuna de duas horas desenhada vazia.
- [ ] 6.4b Uso diário dos últimos 30 dias com horário de pico — verificar com série sintética e o pico do dia conferido no núcleo.
- [ ] 6.4c Falhas por categoria ao longo do tempo, com a lista dos métodos com mais falhas — verificar com falhas injetadas nas cinco categorias e a soma por dia conferida contra o SQLite.
- [ ] 6.4d Maiores consumidores (barras horizontais) com custo estimado quando houver preço — verificar com e sem preço informado.
- [ ] 6.4e Armazenamento empilhado por DocType com a reta de projeção rotulada — verificar com crescimento sintético e os dias projetados conferidos contra o núcleo.
- [ ] 6.4f Distribuição de duração com p50, p95 e p99 — verificar com amostra de percentis conhecidos e a agregação por faixas feita no núcleo.
- [ ] 6.5 Abas **Processos**, **Consumo**, **Armazenamento**, **Custo**, **Alertas**, **Controle** (ver o grupo 7) e **Coletor** (iniciar e parar o coletor, custo do próprio Chantilly) — verificar com um teste de interface por aba e a conferência de teclado (foco, Tab, Enter, Alt) de cada uma.
- [ ] 6.5a Filtro e comparação por instância (descritivo, UUID abreviado e completo copiável) em todas as abas — verificar com um teste de interface que filtra por instância e confere que só os dados dela aparecem, e que instância removida aparece marcada.
- [ ] 6.6 Leitura de séries longas fora da thread da interface, com "Parar de esperar" — verificar com leitura lenta simulada: a janela responde em menos de 0,5 s, como no Cherry `0.2.1`.
- [ ] 6.7 Revisão de UX por alguém que não escreveu a tela, ou checklist da Microsoft aplicada ponto a ponto — verificar com o checklist preenchido em `docs/chantilly.md`.

## 7. Parar e iniciar o ERP

- [ ] 7.1 Núcleo puro do controle: o plano de parada como máquina de estados (parar de aceitar, aguardar jobs, encerrar, forçar), com prazos e decisões testáveis sem processo algum — verificar com testes dos cenários da spec `controle-do-erp`, inclusive prazo esgotado e confirmação separada para forçar.
- [ ] 7.2 Identificação dos processos do bench por PID, `cwd` e cadeia de pais lidos do `/proc` (texto injetável), com detecção de supervisor e systemd — verificar com trechos reais de `/proc` de dois benches, provando que só os do escolhido entram, e com um pai `supervisord` provando a recusa.
- [ ] 7.3 Verificação prévia do que está em trânsito (requisições, jobs, `Transmissao Fiscal` sem desfecho, `Lote eSocial` em transmissão, `Pendencia NFC-e`) em `integracao/`, somente leitura — verificar em bench criando cada situação e conferindo a contagem, e com leitura que não altera nenhum registro.
- [ ] 7.4 Iniciar pelo `scripts/subir.sh` com executor injetável, idempotente, mostrando o comando e o progresso — verificar com executor simulado (já no ar e parado) e confirmar que o `BENCH` e a distro certos chegam ao comando.
- [ ] 7.5 Parada gentil: manutenção somente leitura por `bench set-maintenance-mode`, escoamento por `any_job_pending`, encerramento com `SIGTERM` e `SIGKILL` só após a confirmação separada que nomeia o que será morto; guarda quais sites o Chantilly pôs em manutenção — verificar com executor simulado (ordem das chamadas) e com processos de teste (um que obedece e um que ignora o sinal) numa pasta temporária, nunca no bench real.
- [ ] 7.5a Aviso aos usuários conectados com antecedência configurável: confirmar no Frappe como enviar a mensagem em tempo real e como contar as sessões ativas — verificar lendo o código do Frappe e anotando em `docs/chantilly.md`; se não houver meio confiável, rebaixar a etapa para contagem regressiva ao operador e dizer isso.
- [ ] 7.5b Cancelar a parada e iniciar o ERP desligam só a manutenção que o Chantilly ligou — verificar com um site em manutenção por decisão do administrador, que deve continuar em manutenção.
- [ ] 7.5c Prova de que o modo somente leitura é gentil de verdade: com o site em manutenção, uma leitura responde e uma gravação é recusada com a mensagem de manutenção — verificar em bench de teste, num site descartável.
- [ ] 7.6 Banco e Redis fora da parada padrão; parada opcional com contagem de conexões e aviso de compartilhamento — verificar que a parada padrão não toca neles e que a opcional mostra a contagem.
- [ ] 7.7 Registro de ações em `sites/chantilly-controle.log` (acréscimo, sem segredo) — verificar relendo o arquivo por outro caminho e procurando senha, que não pode estar lá.
- [ ] 7.8 Parada planejada na série: marca no coletor, supressão de queda de processo e de alerta, fim da marca no retorno ou no prazo máximo — verificar com relógio injetado que a marca expira e que o gráfico mostra "parada planejada" distinta de lacuna e de falha.
- [ ] 7.9 Aba **Controle** e comandos `iniciar` e `parar` (com `--confirmo`; sem ele, ensaio) — verificar com teste de interface (janela oculta, executor simulado) e com o ensaio do terminal listando o plano e o que está em trânsito.
- [ ] 7.10 Ciclo real de parar e iniciar no bench de desenvolvimento, **somente com autorização explícita** e backup antes — verificar com o registro de ações, a série marcando "parada planejada" e o bench voltando a responder; se não houver autorização, esta tarefa fica aberta e o motivo é dito.

## 8. CI, versão e documentação

- [ ] 8.1 Job de CI do Chantilly no padrão do job do Cherry (`xvfb`, `python3-tk`, piso de 95% no núcleo e piso da interface dois pontos abaixo do medido) — verificar com o job verde no PR e o log mostrando que a interface rodou e não foi pulada.
- [ ] 8.2 Versão `0.1.0`, licença MIT em `scripts/chantilly/LICENSE`, `README.md` da pasta e `docs/chantilly.md` (como rodar, o que mede, o que não mede, privacidade, orçamento, produção) — verificar relendo contra o código.
- [ ] 8.3 Indexar em `docs/README.md` e apontar do `docs/cherry.md` — verificar abrindo os dois índices.
- [ ] 8.4 Rodar suíte pura, testes do Cherry e do Chantilly, `coverage` e `ruff` em `erpnext_brasil/` e `scripts/` — verificar com a saída verde e `openspec validate chantilly-monitor-de-recursos`.
- [ ] 8.5 Gate de padrões antes de fechar: contratos (pré, pós e invariante) listados por módulo no documento da ferramenta, dependências injetadas por porta, teste na costura em cada gravação, cobertura do núcleo a 100% e pisos de CI cumpridos, `ruff check`, `ruff format --check` e `tests/test_arquitetura.py` verdes — verificar com a saída dos comandos e a lista de contratos no documento.
- [ ] 8.6 Gate de resiliência e segurança (mudança `resiliencia-e-seguranca-das-ferramentas`): desfazer e retomar, idempotência, prazos em todo comando externo, tratamento de exceção na interface, validação de entrada, nenhum vazamento de segredo, varredura de padrões proibidos, confinamento de caminhos, permissões e limites — verificar com a saída dos comandos e a tabela de requisitos.
