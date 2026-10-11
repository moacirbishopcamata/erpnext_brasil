## Purpose

Amostrar CPU, RAM e armazenamento do host e dos processos do bench em segundo plano, guardar a série histórica com retenção limitada e manter o custo do próprio monitor dentro de um orçamento declarado.

## ADDED Requirements

### Requirement: O host e os grupos de processo do bench são amostrados periodicamente

O Chantilly SHALL registrar, em intervalo configurável (padrão 60 s, mínimo 10 s), o uso de CPU, a carga, a memória usada, disponível e de troca, e o espaço usado e livre de cada volume que contém o bench. O Chantilly SHALL registrar também CPU e memória residente por grupo de processo do bench: servidor web, trabalhadores de fila, agendador, socket.io, Redis e o servidor de banco de dados.

#### Scenario: Amostra completa registrada

- **WHEN** o intervalo de amostragem termina com o bench em execução
- **THEN** o Chantilly grava uma amostra com data e hora, métricas do host e uma linha por grupo de processo encontrado

#### Scenario: Grupo ausente é ausência, não zero

- **WHEN** um grupo de processo esperado (por exemplo, o agendador) não está em execução
- **THEN** a amostra marca o grupo como ausente e não o registra com consumo zero

#### Scenario: Métrica ilegível é nula com o motivo

- **WHEN** uma métrica não pode ser lida (permissão negada ou arquivo do sistema ausente)
- **THEN** a amostra grava a métrica como nula com o motivo, e as demais métricas são gravadas normalmente

### Requirement: O desempenho do banco de dados é lido por contadores, sem texto de consulta

O Chantilly SHALL registrar, para o servidor de banco de dados de cada instância, contadores de desempenho: conexões abertas, total de consultas, número de consultas lentas, tamanho dos dados e dos índices, taxa de acerto do cache do banco e tempo de resposta de uma consulta de verificação. O Chantilly MUST NOT guardar o texto de nenhuma consulta nem seus parâmetros. A leitura SHALL funcionar para MariaDB e para PostgreSQL, sem driver de terceiros, pedindo ao bench que consulte os contadores do servidor.

#### Scenario: Contadores do MariaDB

- **WHEN** o Chantilly coleta o desempenho de uma instância em MariaDB
- **THEN** a amostra traz conexões, consultas, consultas lentas, tamanho e tempo de resposta, sem nenhum texto de consulta

#### Scenario: Contadores do PostgreSQL

- **WHEN** o Chantilly coleta o desempenho de uma instância em PostgreSQL
- **THEN** a amostra traz conexões, transações, taxa de acerto do cache, tamanho e tempo de resposta, sem nenhum texto de consulta

#### Scenario: Servidor de banco inacessível

- **WHEN** o servidor de banco não responde à leitura dos contadores
- **THEN** a amostra marca o desempenho do banco como indisponível com o motivo, e não grava zeros

### Requirement: O Chantilly publica um resumo de desempenho por instância, somente para leitura

O Chantilly SHALL publicar, para cada instância identificada pelo UUID, um resumo recente de desempenho: tempo de resposta (mediano e p95) de uma verificação, CPU e memória do processo web da instância, requisições e falhas por minuto, jobs em fila e em execução, e os contadores do banco da instância. O resumo SHALL declarar a versão do seu esquema e a idade da última atualização, SHALL ser lido por outras ferramentas por um leitor somente leitura, e MUST NOT conter conteúdo, consulta, parâmetro nem dado pessoal.

#### Scenario: O Soda lê o resumo

- **WHEN** o Soda lê o resumo de desempenho das instâncias
- **THEN** recebe, por UUID, os tempos, o consumo de recursos e os contadores do banco, com a idade da atualização

#### Scenario: Resumo desatualizado

- **WHEN** a última atualização do resumo tem mais de três intervalos de idade
- **THEN** o leitor informa a idade e marca o resumo como desatualizado, em vez de apresentá-lo como atual

### Requirement: O Chantilly funciona sem dependência obrigatória fora da biblioteca padrão

O Chantilly SHALL coletar as métricas em Linux e em WSL2 apenas com a biblioteca padrão do Python. Uma biblioteca de terceiros SHALL ser opcional e SHALL nunca ser pré-requisito para instalar ou iniciar o monitor.

#### Scenario: Instalação sem dependência nova

- **WHEN** o aplicativo é instalado num bench que não tem nenhuma biblioteca de monitoramento
- **THEN** o Chantilly inicia e coleta as métricas do host e dos processos

### Requirement: Cada bench tem uma única instância em segundo plano

O Chantilly SHALL rodar como um processo em segundo plano por bench, com comandos para iniciar, parar e consultar o estado. Uma segunda tentativa de iniciar no mesmo bench MUST ser recusada com a indicação do processo em execução.

#### Scenario: Segunda instância recusada

- **WHEN** o usuário inicia o Chantilly num bench onde ele já está em execução
- **THEN** o comando termina sem iniciar outro processo e informa o identificador do processo existente

#### Scenario: Reinício do Frappe não interrompe a coleta

- **WHEN** o servidor web ou os trabalhadores do Frappe são reiniciados
- **THEN** o Chantilly continua amostrando, e a série registra a queda e o retorno dos grupos de processo

### Requirement: A série histórica tem retenção e tamanho limitados

O Chantilly SHALL manter as amostras brutas por um prazo configurável (padrão 7 dias) e depois agregá-las por hora, mantendo os agregados por um prazo maior (padrão 13 meses). O arquivo de séries SHALL respeitar um teto de tamanho configurável (padrão 200 MB).

#### Scenario: Amostras antigas viram agregado horário

- **WHEN** uma amostra bruta passa do prazo de retenção
- **THEN** ela é substituída pelo agregado da sua hora (média, máximo e contagem) e a amostra bruta é removida

#### Scenario: Teto de tamanho atingido

- **WHEN** o arquivo de séries atinge o teto de tamanho
- **THEN** o Chantilly descarta primeiro os agregados mais antigos, registra o descarte e continua coletando

### Requirement: O Chantilly mede o próprio custo e respeita um orçamento

O Chantilly SHALL medir o seu próprio consumo de CPU, memória e disco e SHALL respeitar um orçamento configurável (padrão: média de 1% de um núcleo e 64 MB de memória residente). Ao exceder o orçamento, o Chantilly MUST reduzir a frequência de amostragem, suspender a atribuição por amostragem de memória e registrar o motivo.

#### Scenario: Custo do monitor visível

- **WHEN** o usuário consulta o estado do Chantilly
- **THEN** o estado mostra o consumo recente do próprio Chantilly ao lado do orçamento

#### Scenario: Orçamento excedido reduz a frequência

- **WHEN** o consumo médio do Chantilly excede o orçamento por três janelas consecutivas
- **THEN** o intervalo de amostragem aumenta, a amostragem de memória por requisição é suspensa e o estado informa o motivo
