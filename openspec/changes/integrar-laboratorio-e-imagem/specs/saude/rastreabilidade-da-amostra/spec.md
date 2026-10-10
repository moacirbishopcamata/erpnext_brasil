## Purpose

Garantir que cada tubo, cada alíquota e cada resultado do laboratório possam ser seguidos da solicitação ao descarte, sem
brecha e sem reescrita do passado, de modo que um resultado nunca seja atribuído ao paciente errado e que qualquer laudo
possa ser reconstituído até o equipamento, o lote de reagente e o controle de qualidade que o produziram.

## ADDED Requirements

### Requirement: Identificador único e nunca reutilizado para tubo e alíquota

O sistema MUST atribuir a cada tubo e a cada alíquota um identificador único, e MUST NOT reutilizar um identificador, em
nenhuma hipótese, durante o período de retenção dos registros. A alíquota MUST registrar o tubo de origem.

#### Scenario: Dois tubos do mesmo paciente no mesmo dia

- **WHEN** duas coletas do mesmo paciente geram dois tubos no mesmo dia
- **THEN** os dois tubos recebem identificadores diferentes
- **AND** nenhum dos dois repete o identificador de qualquer tubo já registrado

#### Scenario: Identificador de tubo descartado

- **WHEN** um tubo é descartado e outro é criado depois
- **THEN** o novo tubo não recebe o identificador do descartado

#### Scenario: Alíquota aponta para o tubo de origem

- **WHEN** uma alíquota é criada a partir de um tubo
- **THEN** a alíquota recebe identificador próprio e fica ligada ao tubo de origem
- **AND** a partir da alíquota é possível chegar ao paciente

### Requirement: Cadeia de custódia imutável

O sistema MUST registrar um evento de custódia para cada passagem do material — solicitação, coleta, rotulagem, transporte,
recebimento, triagem, alíquota, análise, validação, liberação e descarte — contendo quem, onde, quando (hora sincronizada) e,
quando houver, qual equipamento. Eventos MUST NOT ser editados nem apagados; uma correção MUST ser um novo evento que
referencia o evento corrigido.

#### Scenario: Tentativa de alterar um evento

- **WHEN** um usuário, mesmo administrador, tenta editar ou apagar um evento de custódia já registrado
- **THEN** o sistema recusa a operação
- **AND** a tentativa fica registrada

#### Scenario: Correção de um registro errado

- **WHEN** o recebimento de um tubo foi registrado com o local errado
- **THEN** o usuário autorizado registra um novo evento de correção que cita o evento original e o motivo
- **AND** o evento original continua visível no histórico

### Requirement: Histórico de alteração com data, horário, usuário e local

O sistema MUST manter, para todo cadastro ou alteração de dado e de resultado de exame de paciente, o histórico com data,
horário, usuário e local em que ocorreu (RDC 786/2023, art. 71, II), e MUST controlar quem pode lançar e alterar resultados.

#### Scenario: Alteração de um resultado

- **WHEN** um usuário autorizado altera o resultado de um exame
- **THEN** o histórico guarda o valor anterior, o novo valor, o usuário, a data, o horário e o local da alteração

#### Scenario: Usuário sem permissão

- **WHEN** um usuário sem permissão tenta lançar ou alterar um resultado
- **THEN** o sistema recusa e registra a tentativa

### Requirement: Ligação entre resultado, amostra, equipamento, reagente e controle

Cada resultado MUST guardar o identificador do tubo ou da alíquota, o equipamento e o método que o produziram e, quando o
equipamento informar, o lote de reagente e a situação do controle de qualidade vigente no momento da análise.

#### Scenario: Reconstituir a origem de um laudo

- **WHEN** um laudo emitido é consultado
- **THEN** é possível chegar, a partir dele, ao tubo, à cadeia de custódia, ao equipamento, ao método e à situação do controle
  de qualidade na hora da análise

#### Scenario: Recolhimento de lote de reagente

- **WHEN** um lote de reagente é apontado como defeituoso
- **THEN** o sistema lista todos os resultados produzidos com aquele lote, por equipamento e por período

### Requirement: Lacuna na cadeia impede a liberação

O sistema MUST NOT liberar resultado cujo tubo não tenha registrados, no mínimo, a coleta e o recebimento.

#### Scenario: Tubo sem recebimento

- **WHEN** um resultado chega para um tubo que não tem evento de recebimento
- **THEN** o resultado fica retido e nenhum laudo é liberado
- **AND** a pendência aparece para tratamento humano

### Requirement: Recuperação e retenção mínima de cinco anos

O sistema MUST manter toda a documentação e os registros de rastreabilidade por no mínimo 5 (cinco) anos (RDC 786/2023,
art. 81) e MUST permitir recuperar, a qualquer momento nesse período, as informações que rastreiam um laudo (art. 97).

#### Scenario: Laudo antigo

- **WHEN** se consulta um laudo emitido há quatro anos
- **THEN** o sistema devolve o laudo com a cadeia de custódia e a ligação ao equipamento, completos

### Requirement: Rastreabilidade nos dois sentidos, da coleta ao descarte

O sistema MUST permitir seguir o material nos dois sentidos — do paciente a todos os seus tubos, alíquotas e resultados, e
de qualquer tubo, alíquota ou resultado ao paciente — e MUST registrar o descarte como o último evento da cadeia (art. 94).

#### Scenario: Do tubo ao paciente e de volta

- **WHEN** se lê o identificador de um tubo
- **THEN** o sistema mostra o paciente, os exames pedidos e os resultados já produzidos para aquele tubo

#### Scenario: Tubo descartado

- **WHEN** o material é descartado
- **THEN** o evento de descarte fecha a cadeia, com quem descartou e quando
