## Purpose

Etiquetar cada tubo no ponto de coleta, depois de confirmar a identidade do paciente, com os elementos que a norma exige e um
código de barras que os analisadores leiam, de forma que o rótulo seja a primeira barreira contra amostra trocada — e que
toda impressão, inclusive a repetida, deixe rastro.

## ADDED Requirements

### Requirement: Identificação positiva do paciente antes de imprimir

O sistema MUST exigir, antes de imprimir o rótulo, que o responsável pela coleta confirme a identidade do paciente por pelo
menos dois identificadores (por exemplo, nome completo e data de nascimento, ou a leitura da pulseira) e MUST NOT imprimir
sem essa confirmação.

#### Scenario: Confirmação correta

- **WHEN** o coletador confirma os dois identificadores do paciente diante do paciente
- **THEN** o sistema imprime o rótulo e registra a confirmação, o usuário e o horário

#### Scenario: Identificador não confere

- **WHEN** a leitura da pulseira não corresponde ao paciente da coleta aberta
- **THEN** o sistema não imprime nenhum rótulo
- **AND** informa o motivo ao coletador

### Requirement: Rótulo impresso por coleta iniciada, não em lote antecipado

O sistema MUST emitir o rótulo de coleta somente a partir de uma coleta iniciada para aquele paciente. A impressão antecipada
de rótulos em lote MUST vir desligada por padrão e, quando um administrador a habilitar, MUST ser registrada e MUST exigir a
conferência do rótulo contra o paciente no momento da coleta.

#### Scenario: Pedido de impressão sem coleta aberta

- **WHEN** alguém tenta imprimir um rótulo de coleta sem uma coleta iniciada
- **THEN** o sistema recusa

### Requirement: Conteúdo mínimo do rótulo

O rótulo MUST conter, legíveis a olho nu, o nome do paciente, a data de nascimento ou a idade, o tipo de material biológico
e a data e o horário da coleta (RDC 786/2023, art. 104, parágrafo único), além do identificador do tubo em código de barras.

#### Scenario: Dado obrigatório ausente

- **WHEN** falta o horário da coleta ou o tipo de material
- **THEN** o sistema não permite imprimir o rótulo

#### Scenario: Nome longo

- **WHEN** o nome do paciente excede o espaço do rótulo
- **THEN** o sistema trunca por regra definida, preservando o início do primeiro nome e o último sobrenome
- **AND** marca visivelmente que houve truncamento, sem produzir um nome que possa ser confundido com outro paciente

### Requirement: Código de barras só com o identificador do tubo

O código de barras MUST conter apenas o identificador do tubo, sem dado pessoal do paciente, e a simbologia MUST ser definida
por perfil de equipamento. A leitura do código MUST levar o sistema ao paciente e aos exames, e não o contrário.

#### Scenario: Conteúdo do código

- **WHEN** o rótulo é impresso
- **THEN** o código de barras carrega apenas o identificador do tubo

#### Scenario: Perfil de analisador exige outra simbologia

- **WHEN** o perfil de um analisador define outra simbologia
- **THEN** o rótulo desse tubo usa a simbologia do perfil

### Requirement: Impressão e reimpressão auditadas

Toda impressão MUST registrar usuário, horário, impressora e tubo. A reimpressão de rótulo de tubo já coletado MUST exigir
motivo, MUST identificar visivelmente a via (por exemplo, "2ª via") e MUST ser comunicada ao responsável pela bancada.

#### Scenario: Reimpressão

- **WHEN** um rótulo de tubo já coletado é impresso de novo
- **THEN** o sistema exige o motivo, imprime a marca de segunda via e registra a ocorrência na cadeia de custódia

### Requirement: Falha de impressão não produz tubo sem rótulo

Se a impressão falhar, o sistema MUST NOT considerar o tubo etiquetado nem confirmar a coleta.

#### Scenario: Impressora desligada

- **WHEN** a impressora não responde
- **THEN** o sistema informa o coletador e mantém a coleta pendente
- **AND** nenhum tubo é registrado como etiquetado

### Requirement: Rótulo de alíquota só a partir do tubo de origem lido

O rótulo de uma alíquota MUST ser gerado somente depois da leitura do tubo de origem, MUST receber identificador novo e
MUST repetir os elementos de identificação do paciente.

#### Scenario: Alíquota sem ler o tubo

- **WHEN** se pede o rótulo de uma alíquota sem ter lido o tubo de origem
- **THEN** o sistema recusa

### Requirement: Conferência do rótulo no recebimento

No recebimento, a leitura do código MUST mostrar o paciente e os exames para conferência, e MUST bloquear o tubo cujo
identificador não exista, não tenha coleta registrada ou não corresponda ao tipo de material esperado.

#### Scenario: Código desconhecido

- **WHEN** se lê um código que não existe no sistema
- **THEN** o tubo fica bloqueado e a ocorrência vai para tratamento humano
