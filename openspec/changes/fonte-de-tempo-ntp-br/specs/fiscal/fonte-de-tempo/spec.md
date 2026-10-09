## Purpose

Dá ao app uma medida confiável do desvio do relógio do servidor contra a Hora Legal Brasileira
(disseminada pelo NTP.br), avisa quando esse desvio passa do tolerável e impede que um documento
fiscal seja emitido com o instante de um relógio comprovadamente errado.

## ADDED Requirements

### Requirement: O desvio do relógio é medido contra a Hora Legal Brasileira

O sistema SHALL medir o desvio do relógio local em relação a servidores do NTP.br, consultando mais
de um servidor e devolvendo o deslocamento em milissegundos junto com a indicação de quão confiável
é a medição (quantas fontes responderam e se concordam entre si).

#### Scenario: Fontes concordam

- **WHEN** ao menos duas fontes respondem com deslocamentos próximos entre si
- **THEN** a medição é marcada como confiável
- **AND** o deslocamento informado é o consenso das fontes, não o de uma só

#### Scenario: Fontes divergem

- **WHEN** as fontes respondem com deslocamentos que discordam além da dispersão tolerada
- **THEN** a medição é marcada como não confiável
- **AND** nenhum alerta de deriva nem bloqueio de emissão decorre dela

#### Scenario: Servidor com resposta inválida é ignorado

- **WHEN** um servidor responde sem estar sincronizado, ou pede para reduzir a frequência das consultas
- **THEN** essa resposta não entra no consenso
- **AND** o sistema reduz a frequência de consulta a esse servidor

#### Scenario: Sem acesso à rede

- **WHEN** nenhuma fonte responde (por exemplo, UDP de saída bloqueado)
- **THEN** o resultado é "não medido", nunca um desvio de zero
- **AND** a causa fica registrada para o administrador

### Requirement: A deriva do relógio gera alerta antes de virar problema

O sistema SHALL avisar o administrador, de forma recorrente, quando o desvio medido e confiável passa
de um limite de aviso configurável, informando o desvio medido e o que fazer.

#### Scenario: Desvio acima do limite de aviso

- **WHEN** a medição periódica confiável encontra desvio acima do limite de aviso
- **THEN** o sistema emite o alerta com o desvio medido, a data da medição e a indicação de sincronizar o servidor com o NTP.br

#### Scenario: Desvio dentro do limite

- **WHEN** o desvio medido está dentro do limite de aviso
- **THEN** nenhum alerta é emitido

### Requirement: A emissão fiscal é protegida de um relógio comprovadamente errado

O sistema SHALL, antes de alocar número e transmitir uma NF-e, CT-e ou MDF-e (e a NFC-e, quando ela existir), consultar a última medição
confiável: acima do limite crítico recusa a emissão antes de qualquer chamada à SEFAZ, acima do
limite de aviso emite o documento e avisa o usuário, e sem medição confiável e recente não bloqueia.

#### Scenario: Desvio acima do limite crítico

- **WHEN** a última medição confiável e recente está acima do limite crítico
- **THEN** a emissão é recusada antes de transmitir, com mensagem em pt-BR que informa o desvio medido e como corrigi-lo
- **AND** nenhum número da série é consumido

#### Scenario: Desvio entre o limite de aviso e o crítico

- **WHEN** a última medição confiável e recente está entre os dois limites
- **THEN** o documento é emitido normalmente
- **AND** o usuário é avisado do desvio

#### Scenario: Medição ausente, vencida ou não confiável

- **WHEN** não há medição, ela está vencida ou não é confiável
- **THEN** a emissão não é bloqueada
- **AND** o sistema registra que a guarda não pôde verificar o relógio

#### Scenario: Guarda desligada

- **WHEN** o administrador desliga a guarda de emissão
- **THEN** a emissão não consulta a medição, e o alerta periódico continua valendo

### Requirement: A correção do instante de emissão é opcional e explícita

O sistema SHALL, por padrão, usar o relógio do servidor como instante de emissão; somente se o
administrador ligar a correção, aplicará o deslocamento medido, e apenas com medição confiável e
recente.

#### Scenario: Correção desligada (padrão)

- **WHEN** um documento é emitido sem a correção ligada
- **THEN** o instante de emissão é o do relógio do servidor, com o fuso do sistema

#### Scenario: Correção ligada com medição confiável

- **WHEN** a correção está ligada e há medição confiável e recente
- **THEN** o instante de emissão é o do relógio do servidor somado ao deslocamento medido
- **AND** o deslocamento aplicado fica registrado junto ao documento

#### Scenario: Correção ligada sem medição utilizável

- **WHEN** a correção está ligada mas não há medição confiável e recente
- **THEN** o instante de emissão é o do relógio do servidor, sem deslocamento
- **AND** o sistema registra que a correção não pôde ser aplicada

### Requirement: O app não altera o relógio do servidor nem exige mudança no ERPNext

O sistema SHALL NOT alterar o relógio do sistema operacional nem o comportamento de outros módulos
do ERPNext; a melhoria de acuidade do instante dos demais módulos fica a cargo da sincronização do
servidor, documentada para o administrador.

#### Scenario: Orientação de sincronização do servidor

- **WHEN** o administrador consulta a documentação da fonte de tempo
- **THEN** encontra como sincronizar o servidor com o NTP.br usando autenticação NTS, e o que liberar de rede para isso
