## Purpose

Atribuir o consumo de CPU, memória e armazenamento a sites, endpoints, jobs e DocTypes do ERPNext, sem guardar conteúdo de documento, texto de consulta ou dado pessoal.

## ADDED Requirements

### Requirement: O tempo de CPU e de relógio é atribuído por site, endpoint e job

O Chantilly SHALL medir, para cada requisição web e cada job em segundo plano, o tempo de CPU e o tempo de relógio, e SHALL atribuí-los ao site e ao método (endpoint ou job). O Chantilly SHALL guardar apenas agregados por janela (contagem, soma, máximo e distribuição por faixas de duração), nunca uma linha por requisição.

#### Scenario: Requisição pesada aparece no agregado do endpoint

- **WHEN** um endpoint consome mais CPU do que os demais numa janela
- **THEN** o agregado da janela mostra esse endpoint com a maior soma de tempo de CPU e o número de chamadas

#### Scenario: Job em segundo plano é atribuído ao seu método

- **WHEN** um job de emissão em lote termina
- **THEN** o seu tempo de CPU e de relógio entram no agregado do método do job, no site em que rodou

### Requirement: A memória é atribuída por amostragem e declarada como estimativa

O Chantilly SHALL estimar o crescimento de memória atribuível a requisições e jobs medindo apenas uma fração configurável das execuções (padrão 1%). Todo valor de memória atribuída SHALL ser identificado como estimativa na saída.

#### Scenario: Amostragem por fração

- **WHEN** a fração de amostragem é de 1% e ocorrem mil requisições
- **THEN** aproximadamente dez delas têm a memória medida, e o agregado informa quantas execuções foram medidas

#### Scenario: Memória apresentada como estimativa

- **WHEN** o painel ou o relatório mostra memória por endpoint ou job
- **THEN** o valor aparece rotulado como estimativa, com o número de execuções medidas

### Requirement: O armazenamento é atribuído de forma exata por DocType e por arquivo

O Chantilly SHALL calcular, para cada site, o tamanho em disco de cada DocType (dados mais índices) lendo os metadados do servidor de banco de dados, e o tamanho dos arquivos anexados agrupado por DocType de origem e por privacidade (público ou privado). O Chantilly SHALL registrar a variação desses tamanhos ao longo do tempo.

#### Scenario: Tabelas fiscais acompanhadas

- **WHEN** o cálculo de armazenamento roda num site com documentos fiscais emitidos
- **THEN** o resultado inclui o tamanho de `Transmissao Fiscal` e de `Arquivo SPED` e a variação desde o cálculo anterior

#### Scenario: Anexos agrupados por DocType de origem

- **WHEN** existem arquivos anexados a `Sales Invoice` e a `Purchase Invoice`
- **THEN** o resultado informa o total de bytes de cada grupo, separando públicos de privados

### Requirement: As falhas são contadas por categoria, sem conteúdo

O Chantilly SHALL contar, por janela, site e método, as falhas nas categorias: requisição que terminou em erro do servidor, job em segundo plano que falhou, processo do bench que caiu e voltou, intervalo de amostragem perdido e falha da própria medição. O Chantilly SHALL guardar de cada falha apenas a categoria, o nome do método e a contagem, e MUST NOT guardar a mensagem de erro, a pilha de chamadas nem qualquer parâmetro.

#### Scenario: Job que falhou é contado na sua categoria

- **WHEN** um job em segundo plano termina em falha
- **THEN** o agregado da janela incrementa a categoria "job falhou" para o método do job, sem registrar a mensagem do erro

#### Scenario: Queda e retorno de processo

- **WHEN** um trabalhador do bench deixa de existir numa amostra e reaparece com outro identificador na seguinte
- **THEN** o Chantilly conta uma queda de processo para o grupo e o horário em que ocorreu

### Requirement: Nenhum conteúdo nem dado pessoal é guardado

O Chantilly MUST guardar somente nomes (site, método, job, DocType) e valores numéricos. O Chantilly MUST NOT guardar texto de consulta, parâmetros, corpo de requisição, conteúdo de documento nem nome de usuário.

#### Scenario: Consulta com dado pessoal não deixa rastro

- **WHEN** uma requisição envia um CPF ou CNPJ como parâmetro
- **THEN** nenhum registro do Chantilly contém esse valor

### Requirement: Falha da medição nunca afeta a requisição

O Chantilly SHALL tratar qualquer exceção da própria medição como falha do monitor: a requisição ou o job MUST concluir normalmente, e a falha SHALL ser contada e registrada.

#### Scenario: Erro na sonda não derruba a requisição

- **WHEN** a sonda de medição levanta uma exceção durante uma requisição
- **THEN** a requisição responde normalmente ao usuário e o contador de falhas do Chantilly aumenta em um
