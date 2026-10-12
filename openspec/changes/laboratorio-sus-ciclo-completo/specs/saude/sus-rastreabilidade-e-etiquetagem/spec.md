## Purpose

Dar a cada tubo uma identidade única e a cada passagem de mão um registro que não se apaga, e etiquetar no ponto de coleta
somente depois de confirmar quem é o paciente. É o controle central contra a troca de amostra.

## ADDED Requirements

### Requirement: Identificador único e nunca reutilizado para tubo e alíquota
O sistema SHALL atribuir a cada tubo e a cada alíquota um identificador numérico opaco, sem dado de paciente nem de data
embutido, com dígito de conferência, gerado por contador transacional e nunca reaproveitado, mesmo após rejeição, descarte ou
cancelamento.

#### Scenario: Identificador de tubo rejeitado
- **WHEN** um tubo é rejeitado e outro é coletado em seu lugar
- **THEN** o novo tubo recebe identificador inédito e o antigo nunca é atribuído de novo

#### Scenario: Leitura com um dígito errado
- **WHEN** um identificador é lido ou digitado com um dígito diferente
- **THEN** o dígito de conferência não confere e o sistema recusa, sem aproximar para outro tubo

### Requirement: Identificação positiva do paciente antes de imprimir
O sistema SHALL exigir, antes de imprimir a etiqueta, que o coletador confirme a identidade do paciente com dois identificadores
distintos (por exemplo, nome completo e data de nascimento, ou leitura da pulseira), perguntados ao paciente ou lidos, e não
apenas mostrados para "conferir".

#### Scenario: Identificação não confirmada
- **WHEN** o coletador tenta imprimir sem registrar a confirmação de identidade
- **THEN** nenhuma etiqueta é impressa

### Requirement: Rótulo impresso por coleta iniciada, não em lote antecipado
O sistema SHALL imprimir o rótulo do tubo somente a partir de uma coleta iniciada para aquele paciente. A impressão de
etiquetas de pacientes distintos em lote antes das coletas SHALL ser impedida.

#### Scenario: Pedido de impressão em lote
- **WHEN** o usuário pede etiquetas de vários pacientes sem coleta iniciada
- **THEN** o sistema recusa e orienta a imprimir na coleta de cada paciente

### Requirement: Conteúdo mínimo do rótulo
O sistema SHALL imprimir, no rótulo do tubo, o nome do paciente, a data de nascimento ou idade, o tipo de material, a data e a
hora da coleta e o identificador do tubo em texto e em código de barras. O código de barras SHALL carregar somente o
identificador do tubo.

#### Scenario: Conteúdo do código de barras
- **WHEN** o código de barras do rótulo é decodificado
- **THEN** só o identificador do tubo é obtido

### Requirement: Impressão e reimpressão auditadas
O sistema SHALL registrar cada impressão com usuário, data, hora, estação e impressora. A reimpressão SHALL exigir motivo, SHALL
sair marcada como segunda via e SHALL manter o mesmo identificador do tubo.

#### Scenario: Reimpressão
- **WHEN** a etiqueta de um tubo é reimpressa
- **THEN** o motivo é registrado e o rótulo sai com a marca de segunda via e o identificador original

### Requirement: Falha de impressão não produz tubo sem rótulo
O sistema SHALL manter a coleta como não confirmada enquanto a impressão da etiqueta não for confirmada, e SHALL oferecer a
contingência documentada (rótulo manual com reconciliação posterior) quando a impressora estiver indisponível.

#### Scenario: Impressora fora do ar
- **WHEN** a impressora não responde durante a coleta
- **THEN** a coleta não é confirmada e o sistema oferece o procedimento de contingência com reconciliação

### Requirement: Rótulo de alíquota só a partir do tubo de origem lido
O sistema SHALL emitir o rótulo de alíquota apenas depois da leitura do tubo de origem e SHALL ligar o novo identificador ao do
tubo pai.

#### Scenario: Alíquota sem leitura do tubo pai
- **WHEN** alguém pede o rótulo de uma alíquota sem ler o tubo de origem
- **THEN** o sistema recusa

### Requirement: Cadeia de custódia imutável e encadeada
O sistema SHALL registrar cada evento do tubo (coleta, impressão, remessa, recebimento, análise, descarte) em registro só de
acréscimo, com usuário, local, data e hora, e com o hash do evento anterior do mesmo tubo. Uma verificação periódica SHALL
recalcular a cadeia e alertar quando houver quebra.

#### Scenario: Evento alterado diretamente no banco
- **WHEN** um evento da cadeia é modificado fora do sistema
- **THEN** a verificação detecta a quebra do encadeamento e abre um alerta

### Requirement: Lacuna na cadeia impede a liberação
O sistema SHALL bloquear a liberação de resultado de um tubo cuja cadeia tenha lacuna (etapa obrigatória ausente) ou quebra de
encadeamento, até a decisão registrada do responsável técnico.

#### Scenario: Tubo sem evento de recebimento
- **WHEN** há resultado para um tubo sem evento de recebimento
- **THEN** a liberação é bloqueada e a lacuna é indicada

### Requirement: Retenção e recuperação mínima de cinco anos
O sistema SHALL reter a cadeia, os rótulos impressos e os registros de custódia por, no mínimo, cinco anos, e SHALL permitir
recuperar o caminho de um laudo de volta ao tubo, à coleta e ao paciente, e o caminho de um tubo adiante até o descarte.

#### Scenario: Rastreio nos dois sentidos
- **WHEN** o responsável consulta um laudo antigo
- **THEN** o sistema mostra o tubo, os eventos de custódia, a coleta e o equipamento ou método usado
