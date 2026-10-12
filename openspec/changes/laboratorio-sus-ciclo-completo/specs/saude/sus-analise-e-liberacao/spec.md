## Purpose

Receber o resultado, casá-lo ao tubo certo sem inferência, reter o que é duvidoso e liberar o laudo por responsável habilitado,
com retificação sempre em novo documento. O módulo opera com digitação conferida; analisadores entram depois por adaptador.

## ADDED Requirements

### Requirement: Resultado só se anexa por identificador exato do tubo
O sistema SHALL anexar um resultado a um tubo apenas pelo identificador exato do tubo, validado pelo dígito de conferência.
Aproximação, "o mais parecido" e inferência por nome, horário ou posição SHALL NOT ser usadas; resultado sem identificador
exato SHALL ir à quarentena.

#### Scenario: Identificador inexistente
- **WHEN** chega um resultado cujo identificador não corresponde a nenhum tubo
- **THEN** o resultado vai à quarentena com o motivo "identificador desconhecido" e não é anexado a paciente algum

### Requirement: Dupla conferência na digitação do resultado
O sistema SHALL exigir, para resultado digitado à mão, a confirmação por segunda pessoa ou a redigitação do valor, e SHALL
registrar quem digitou e quem conferiu. Resultado não conferido SHALL NOT ser liberado.

#### Scenario: Resultado sem conferência
- **WHEN** um resultado digitado ainda não tem segunda conferência
- **THEN** ele permanece pendente e não pode ser liberado

### Requirement: Unidade e faixa de referência explícitas, sem conversão implícita
O sistema SHALL registrar, em cada resultado numérico, a unidade e a faixa de referência aplicadas. O sistema SHALL NOT
converter unidade implicitamente; unidade diferente da esperada para o exame SHALL reter o resultado.

#### Scenario: Unidade diferente da esperada
- **WHEN** o resultado chega em unidade diferente da cadastrada para o exame
- **THEN** o resultado é retido com o motivo "unidade diferente" e nenhuma conversão é aplicada

### Requirement: Quarentena com motivo enumerado e saída decidida por humano
O sistema SHALL manter uma fila de pendências com motivo enumerado (identificador desconhecido ou ambíguo, digitado sem
conferência, dados do paciente divergentes, unidade diferente, controle reprovado, lacuna na cadeia). Sair da quarentena SHALL
exigir usuário autorizado, decisão registrada e, quando o destino for um paciente, a conferência do tubo físico.

#### Scenario: Liberação da quarentena
- **WHEN** um responsável decide anexar um resultado em quarentena a um tubo
- **THEN** a decisão, o usuário e a conferência do tubo físico ficam registrados

### Requirement: Controle de qualidade antes do resultado de paciente
O sistema SHALL registrar o controle interno da qualidade por exame e por lote de reagente e SHALL reter os resultados de
paciente do período cujo controle esteja reprovado ou ausente, até decisão do responsável técnico. Amostra de controle SHALL
NOT ser anexada a paciente.

#### Scenario: Controle reprovado
- **WHEN** o controle do dia de um exame está reprovado
- **THEN** os resultados de paciente desse exame ficam retidos até a decisão registrada

### Requirement: Liberação manual por padrão e por responsável habilitado
O sistema SHALL exigir que a liberação do laudo seja feita por profissional habilitado, identificado e com assinatura
legalmente válida configurada. A liberação automática SHALL ser desligada por padrão e, se ativada, SHALL valer só para
resultados sem retenção, dentro de critérios cadastrados pelo responsável técnico.

#### Scenario: Resultado retido
- **WHEN** um resultado está retido por qualquer motivo
- **THEN** ele não pode ser liberado, nem automática nem manualmente, até a retenção ser resolvida

### Requirement: Conteúdo mínimo do laudo
O sistema SHALL incluir no laudo o paciente, a unidade solicitante, o profissional solicitante, o material e a data e a hora da
coleta, o método quando aplicável, o resultado com unidade e faixa de referência, as observações da coleta, o responsável pela
liberação e a data e a hora da liberação.

#### Scenario: Laudo com observação de coleta
- **WHEN** o tubo foi coletado com a observação "jejum não cumprido"
- **THEN** a observação aparece no laudo

### Requirement: Retificação sempre em novo laudo
O sistema SHALL NOT alterar um laudo liberado. A correção SHALL gerar novo laudo ligado ao anterior, com motivo e registro da
comunicação ao solicitante, preservando o original.

#### Scenario: Correção de laudo liberado
- **WHEN** um erro é encontrado em laudo liberado
- **THEN** o laudo original permanece e um novo laudo retificador é emitido com o motivo

### Requirement: Comunicação de valor crítico
O sistema SHALL, para resultado em faixa crítica configurada, exigir o registro da comunicação ao solicitante (quem, quando,
canal), mantendo o laudo marcado como pendente de comunicação até o registro.

#### Scenario: Crítico sem comunicação
- **WHEN** um resultado crítico é liberado sem registro de comunicação
- **THEN** o laudo permanece com pendência de comunicação em destaque

### Requirement: Entrada de resultado por porta, com adaptadores opcionais
O sistema SHALL receber resultados por uma interface de entrada com implementação própria de digitação conferida. Importação
por arquivo e integração com analisador SHALL ser adaptadores opcionais que usam a mesma regra de casamento e quarentena,
nunca um caminho paralelo que contorne essas regras.

#### Scenario: Importação por arquivo
- **WHEN** um arquivo de resultados é importado
- **THEN** cada linha passa pelo mesmo casamento por identificador exato e pela mesma quarentena da digitação
