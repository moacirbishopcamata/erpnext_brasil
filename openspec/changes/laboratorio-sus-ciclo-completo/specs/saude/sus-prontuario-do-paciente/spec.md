## Purpose

Fazer de todos os dados do ciclo laboratorial parte do prontuário do paciente: cada solicitação, coleta, resultado, laudo, ocorrência,
consentimento e acesso é uma entrada do prontuário, que concentra a guarda, o acesso, a auditoria e os direitos do titular conforme a
Lei 13.787/2018 e a LGPD.

## ADDED Requirements

### Requirement: Todo dado do ciclo pertence a um prontuário
O sistema SHALL associar toda solicitação, amostra, resultado, laudo, ocorrência de transporte, rejeição, recoleta, consentimento,
revisão e acesso a um único prontuário do paciente, e SHALL NOT permitir registro clínico do ciclo sem prontuário.

#### Scenario: Solicitação cria a entrada
- **WHEN** uma solicitação de exame é registrada
- **THEN** ela aparece como entrada cronológica do prontuário do paciente

### Requirement: Prontuário como linha do tempo só de acréscimo
O sistema SHALL manter o prontuário como linha do tempo de entradas só de acréscimo, cada uma com tipo, referência ao documento de origem,
hash do conteúdo, autor, local e horário. Corrigir uma entrada SHALL gerar nova entrada que a referencia, preservando a original.

#### Scenario: Correção de entrada
- **WHEN** uma entrada precisa ser corrigida
- **THEN** uma nova entrada a substitui por referência e a original permanece visível no histórico

### Requirement: Identidade única do prontuário
O sistema SHALL manter um prontuário por paciente e SHALL, na fusão de cadastros, fundir os prontuários preservando todas as entradas,
com a fusão reversível, conforme `saude/sus-cadastro-de-pacientes`.

#### Scenario: Fusão de cadastros
- **WHEN** dois cadastros do mesmo paciente são fundidos
- **THEN** o prontuário mantido reúne as entradas dos dois, e a fusão pode ser desfeita

### Requirement: Integridade e autenticidade do prontuário digital
O sistema SHALL garantir a integridade e a autenticidade das entradas por hash encadeado e assinatura digital dos laudos, e SHALL
verificar periodicamente a integridade do prontuário, alertando qualquer quebra.

#### Scenario: Entrada adulterada
- **WHEN** o conteúdo de uma entrada é alterado fora do sistema
- **THEN** a verificação detecta a quebra e abre alerta

### Requirement: Guarda mínima de vinte anos do último registro
O sistema SHALL reter o prontuário por, no mínimo, 20 anos a partir da última entrada (Lei 13.787/2018), prazo parametrizável para cima
quando outra norma exigir mais, e SHALL NOT eliminar nenhuma entrada antes desse prazo. O prazo de guarda do laboratório da RDC 786 SHALL
ser tratado como piso do que está nele, nunca como razão para eliminar antes dos 20 anos do prontuário.

#### Scenario: Tentativa de eliminar antes do prazo
- **WHEN** alguém tenta eliminar um prontuário com a última entrada há menos de 20 anos
- **THEN** a eliminação é recusada

### Requirement: Eliminação formal após o prazo
O sistema SHALL tratar a eliminação depois do prazo como procedimento com aprovação do responsável, registro da destinação final
(eliminação ou devolução ao paciente) e eliminação que impeça a recuperação indevida, mantendo o registro da eliminação, não o conteúdo.

#### Scenario: Eliminação aprovada
- **WHEN** um prontuário com mais de 20 anos sem registro é eliminado
- **THEN** o conteúdo é removido, e o registro da eliminação, quem aprovou e quando permanecem

### Requirement: Cópia do prontuário ao paciente
O sistema SHALL gerar a cópia do prontuário laboratorial do paciente em formato legível e estruturado, assinada, a pedido do titular,
após conferência de identidade, e SHALL registrar o pedido e a entrega.

#### Scenario: Pedido de cópia
- **WHEN** o paciente pede a cópia do prontuário
- **THEN** o sistema gera o pacote assinado e registra a entrega

### Requirement: Acesso ao prontuário por função, unidade e finalidade
O sistema SHALL permitir ver o prontuário apenas a quem tem função e unidade compatíveis com o atendimento, SHALL pedir finalidade para
acesso fora do fluxo e SHALL registrar toda consulta, conforme `saude/sus-seguranca-e-privacidade`.

#### Scenario: Consulta fora do fluxo
- **WHEN** um usuário abre o prontuário sem solicitação ativa
- **THEN** informa a finalidade e a consulta é registrada para revisão
