## Why

O ERPNext Brasil acumula consumo que ninguém vê até virar incidente: o disco enche de XML fiscal, SPED e anexos (`Transmissao Fiscal`, `Arquivo SPED`, `File`), um job de emissão em lote ocupa CPU e RAM do mesmo servidor que atende o balcão, e a pilha do bench (gunicorn, workers, Redis, MariaDB ou PostgreSQL) divide a mesma máquina sem que se saiba quem pesa quanto. Hoje o projeto mede **versões e CVE** (`scripts/auditar_pilha.py`) e **o relógio** (`medicao_do_relogio`), mas **não mede recurso**. A pergunta "quanto custa manter esta operação, e o que cresce mais rápido?" não tem resposta em nenhum lugar.

O Frappe tem peças soltas (Recorder, `Scheduled Job Log`, `System Console`), nenhuma guarda série histórica por site, por app, por DocType ou por job, e nenhuma fala em custo. Ferramentas externas (Prometheus, Grafana, Netdata) enxergam a máquina, mas **não sabem o que é um DocType nem um job do ERPNext**, e exigem instalar e operar mais serviços, o oposto do que o ambiente de desenvolvimento deste projeto prega (`scripts/subir.sh`: sem sudo, sem Docker).

## What Changes

- Um aplicativo de monitoramento chamado **Chantilly**, com **dois processos que se complementam**: um **coletor em segundo plano** que roda junto do bench (Linux ou WSL2) e uma **interface desktop** para quem desenvolve e opera, **idêntica à do Cherry em padrão, aparência e comportamento**.
- O coletor amostra CPU, RAM e armazenamento do host e dos processos do bench e guarda a série histórica num arquivo local compacto, sem serviço novo.
- **Identificação por instância:** quando o bench tem instâncias do Soda, o Chantilly atribui consumo, armazenamento, falhas e custo a cada instância pelo **UUID**, mostrando o **descritivo único**; o histórico fica preso ao UUID e sobrevive a renomeação e a remoção. Sem o Soda, cada site é uma instância sem UUID.
- **Atribuição de consumo** dentro do ERPNext: CPU (tempo de CPU e de relógio) por site, endpoint e job; RAM por amostragem, declarada como estimativa; armazenamento **exato** por DocType (tabela e índices) e por tipo de arquivo anexo; e **contagem de falhas por categoria** (requisição com erro, job que falhou, processo que caiu e voltou, falha do próprio monitor).
- **Custo estimado**: o usuário informa o preço da sua infraestrutura (CPU-hora, GB-hora de RAM, GB-mês de armazenamento) e o Chantilly converte consumo em valor, sempre rotulado como estimativa. Sem preço informado, mostra consumo e diz que o preço não foi informado; **nunca inventa preço**.
- **Alertas e previsão**: disco, RAM, swap e CPU com limiar e histerese, previsão de esgotamento do disco, e aviso de "coletor parado". Entrega pelo mesmo canal dos outros alertas do app, avaliada por um job agendado que lê a série.
- **Interface desktop profissional e idêntica ao Cherry**: tkinter só com a biblioteca padrão, abas com nome específico, uma instrução principal por aba, feedback de rotina sem modal, vocabulário que não culpa, teclado completo, nitidez em HiDPI, geometria lembrada e **validada contra a tela** (corrige o CH-08 do Cherry), operações longas em thread de trabalho com "Parar de esperar" (padrão do Cherry `0.2.1`). Gráficos desenhados no próprio `Canvas`, sem matplotlib: **mapa de calor** de uso por hora e dia da semana, **uso diário** e horários de pico, **falhas** por categoria ao longo do tempo, **maiores consumidores**, **armazenamento empilhado por DocType com projeção** e **distribuição de duração** (p50, p95 e p99), além das séries temporais da visão geral.
- **Mesma disciplina de engenharia do Cherry**: núcleo puro testado a 100%, interface com teste no CI sob `xvfb` e piso próprio, versão própria, licença MIT própria, documento próprio com as fontes de UX.
- O próprio Chantilly **mede o seu custo** e respeita um orçamento (por padrão, no máximo 1% de um núcleo e 64 MB de RAM); ao estourar, reduz a frequência e avisa.
- **Parar e iniciar o ERP**: a interface e o terminal podem **iniciar** a pilha do bench (reaproveitando `scripts/subir.sh`, que já é idempotente) e **pará-la com gentileza**: avisa quem está usando, coloca o sistema em **somente leitura** (quem estava consultando continua consultando), deixa o agendador de enfileirar, espera o trabalho em andamento terminar dentro de um prazo e só então encerra os processos do ERPNext, sem sinal brusco. Antes de parar, o Chantilly mostra o que está em andamento, em especial **emissões fiscais e lotes do eSocial em trânsito**, e exige confirmação. Parar o banco de dados ou o Redis é um pedido à parte, desligado por padrão, com aviso de que outros sites podem compartilhá-los. **Nunca é automático**: nenhum alerta, falha ou agenda inicia, para ou reinicia o ERP sozinho. Cada ação fica registrada, e a parada planejada aparece nos gráficos como "parada planejada", distinta de falha.
- **A monitoração é somente leitura**: o Chantilly **nunca apaga nem compacta dado do usuário**; só o seu próprio arquivo de séries tem retenção. Iniciar e parar o ERP é a única ação de controle, sempre explícita.

Fora desta mudança: página do desk do Frappe, exportação para Prometheus, hospedeiro Windows nativo (o bench só roda em WSL2/Linux; a **interface** roda no Windows e lê o arquivo pelo caminho `\\wsl.localhost\...`, como o Cherry), e qualquer ação corretiva **automática** (ex.: limpar arquivos, reiniciar o ERP sozinho). Controle de ERP em produção gerenciada por supervisor ou systemd também fica de fora: o Chantilly o detecta e recusa, apontando o gerenciador correto.

## Capabilities

### New Capabilities

- `operacao/coleta-de-recursos`: amostragem em segundo plano do host e dos processos do bench, retenção limitada e orçamento do próprio custo.
- `operacao/atribuicao-de-consumo`: quanto de CPU, RAM e armazenamento cada site, endpoint, job e DocType consome, sem guardar conteúdo.
- `operacao/custo-estimado`: conversão de consumo em valor a partir de preços informados pelo usuário.
- `operacao/alertas-e-painel`: limiares, previsão de esgotamento, estado do coletor, gráficos e a interface desktop no padrão do Cherry.
- `operacao/controle-do-erp`: iniciar e parar o ERP de forma explícita, graciosa e registrada, com verificação prévia do que está em andamento.

### Modified Capabilities

Nenhuma.

## Impact

- Código novo em três lugares, na mesma fronteira que o projeto já usa:
  - `erpnext_brasil/chantilly/`: regra pura (amostras, agregação, previsão, limiares, custo), **sem `frappe`**; `tests/test_arquitetura.py` passa a vigiá-lo.
  - `scripts/chantilly/`: coletor em segundo plano e a interface tkinter, com licença MIT e versão próprias, como `scripts/cherry/`; a interface reutiliza `Bench` e `caminho_wsl` de `scripts/cherry/config.py`.
  - `erpnext_brasil/integracao/`: sondas finas de atribuição e o job de alertas; `hooks.py` ganha `before_request`/`after_request`, ganchos de job e uma entrada em `scheduler_events`.
- Dependências: nenhuma além da biblioteca padrão (`/proc` no Linux e no WSL2; `tkinter` na interface); `psutil` opcional só fora de Linux.
- Dados: um arquivo local (SQLite) por bench, com teto de tamanho; nada novo no banco do site além da configuração de limiares e preços.
- CI: o job do Chantilly nasce no padrão do job do Cherry (`xvfb`, dois pisos: 95% no núcleo e piso próprio na interface).
- Privacidade: guarda **nomes e contadores** (site, método, DocType, job), nunca texto de consulta, parâmetros, conteúdo de documento nem nome de usuário por padrão.
- Controle: reaproveita `scripts/subir.sh` para iniciar; o parar é novo e identifica processos pelo PID lido do `/proc`, nunca por padrão de nome (o próprio `subir.sh` registra que `pgrep -f` casa com a linha de comando que o contém). A consulta do que está em trânsito é uma leitura nova em `integracao/`.
- Registro de ações de controle: um arquivo local de acréscimo, sem segredo.
- Documentação nova: `docs/chantilly.md`; índice em `docs/README.md`.
