## Purpose

Confronta o método de valoração de estoque escolhido no ERPNext com o que a legislação do imposto de
renda admite, avisando antes que o custo apurado deixe de ser o dedutível.

## ADDED Requirements

### Requirement: A valoração LIFO é sinalizada para empresas do Brasil

O sistema SHALL avisar o usuário, ao gravar um item ou as configurações de estoque de uma instalação
brasileira com o método de valoração LIFO (UEPS), de que esse método não é admitido para o imposto de
renda segundo as fontes consultadas, e SHALL permitir a gravação.

#### Scenario: Item com LIFO

- **WHEN** um item é gravado com o método de valoração LIFO numa instalação brasileira
- **THEN** a gravação é concluída
- **AND** o usuário vê um aviso que cita o método, a consequência e os métodos aceitos (PEPS e custo médio)

#### Scenario: Configurações de estoque com LIFO como padrão

- **WHEN** as configurações de estoque são gravadas com LIFO como método padrão
- **THEN** a gravação é concluída com o mesmo aviso

#### Scenario: Métodos aceitos

- **WHEN** o método é FIFO (PEPS) ou média móvel
- **THEN** nenhum aviso é emitido

#### Scenario: Método não definido

- **WHEN** o item não define método de valoração
- **THEN** nenhum aviso é emitido

### Requirement: O aviso declara o que não está comprovado

O sistema SHALL tratar a vedação ao LIFO como aviso, e não como bloqueio, enquanto o dispositivo legal
que a estabelece não estiver citado em fonte oficial, e SHALL declarar isso no próprio texto e na
documentação.

#### Scenario: Texto do aviso

- **WHEN** o aviso de LIFO é exibido
- **THEN** o texto diz que a confirmação do dispositivo legal está pendente
