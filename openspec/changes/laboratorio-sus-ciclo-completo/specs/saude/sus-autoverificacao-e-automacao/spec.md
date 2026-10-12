## Purpose

Automatizar o que é seguro automatizar, do roteamento da amostra à liberação do resultado que passa em todas as regras, mantendo a
revisão humana para o que foge delas e a responsabilidade técnica do biomédico sobre as regras. Segue o modelo de CLSI AUTO10/AUTO15,
em que cada laboratório constrói, valida e aprova as próprias regras e limites.

## ADDED Requirements

### Requirement: Regras de autoverificação cadastradas, versionadas e aprovadas
O sistema SHALL manter regras de autoverificação por exame, versionadas, cada uma aprovada nominalmente pelo responsável técnico com
data e evidência de validação. Uma regra não aprovada SHALL NOT liberar resultado. A alteração de regra SHALL gerar nova versão e
valer apenas para resultados posteriores.

#### Scenario: Regra sem aprovação
- **WHEN** existe uma regra cadastrada e ainda não aprovada
- **THEN** ela não libera nenhum resultado

### Requirement: Critérios avaliáveis pela regra
O sistema SHALL permitir compor, por exame, os critérios: controle de qualidade do período aprovado, alarmes e sinalizadores do
instrumento ausentes, comparação com o resultado anterior do mesmo paciente (*delta check*), faixa de referência, faixa de medição
analítica, valor crítico, índices de soro (hemólise, icterícia, lipemia) e média móvel. O resultado SHALL ser autoverificado apenas
quando **todos** os critérios da regra forem atendidos.

#### Scenario: Um critério falha
- **WHEN** o resultado está na faixa, mas a variação contra o anterior excede o limite do *delta check*
- **THEN** o resultado não é autoverificado e vai à revisão humana com o motivo

### Requirement: Liberação automática desligada até a validação
O sistema SHALL manter a liberação automática desligada por exame até que o responsável técnico a ative após validar a regra. Ativada,
SHALL valer só para resultados sem retenção de nenhuma natureza. Resultado crítico, de controle reprovado, com lacuna na cadeia ou
em quarentena SHALL NOT ser autoverificado.

#### Scenario: Resultado crítico
- **WHEN** um resultado atende a faixa mas é crítico
- **THEN** não é autoverificado e exige revisão e comunicação humanas

### Requirement: Exceção vai à revisão humana com o motivo
O sistema SHALL encaminhar o resultado que não atende à regra à fila de revisão humana, com o motivo de cada critério que falhou,
ordenada por prioridade, e SHALL registrar quem revisou e a decisão.

#### Scenario: Resultado em revisão
- **WHEN** o analista abre um resultado retido pela regra
- **THEN** vê os critérios que falharam e decide liberar, repetir ou rejeitar

### Requirement: Repetição e teste reflexo por regra
O sistema SHALL executar, quando a regra pedir, a repetição automática do exame (nova ordem ao equipamento) e o teste reflexo
(exame adicional condicionado ao resultado), com limite de repetições e registro de cada uma como versão. Repetição ou reflexo SHALL
NOT ocorrer sem regra aprovada que o prescreva.

#### Scenario: Repetição por flag
- **WHEN** o equipamento sinaliza interferência e a regra prevê repetição
- **THEN** uma nova ordem é enviada ao equipamento, e o resultado novo vira versão sem apagar o primeiro

### Requirement: Roteamento automático da lista de trabalho
O sistema SHALL distribuir as ordens aos equipamentos e às listas de trabalho conforme o exame, a prioridade e a disponibilidade,
sem intervenção, e SHALL registrar a decisão de roteamento.

#### Scenario: Urgência
- **WHEN** chega uma urgência
- **THEN** ela entra à frente das rotinas na lista do equipamento adequado

### Requirement: Alertas automáticos
O sistema SHALL abrir alertas automáticos para: prazo de etapa excedido, valor crítico sem comunicação, notificação compulsória
pendente, remessa sem chegada, controle de qualidade reprovado, fila de quarentena envelhecida, certificado de assinatura próximo do
vencimento e envio à RNDS pendente, cada um com destinatário e prazo de escalonamento.

#### Scenario: Remessa sem chegada
- **WHEN** uma remessa passa do limite em trânsito
- **THEN** o alerta é aberto e escalado se ninguém o tratar no prazo

### Requirement: Cada decisão automática é rastreável
O sistema SHALL registrar, em cada decisão automática (autoverificar, reter, repetir, rotear, alertar), a regra e a versão aplicadas,
os valores avaliados e o instante, e SHALL permitir reconstituir por que um resultado foi liberado sem humano.

#### Scenario: Auditoria de liberação automática
- **WHEN** o auditor consulta um laudo autoverificado
- **THEN** vê a regra, a versão, os valores avaliados e o aprovador da regra

### Requirement: Monitoramento do desempenho da automação
O sistema SHALL medir a taxa de autoverificação e as discordâncias identificadas pela revisão humana por regra, e SHALL alertar o
responsável técnico quando a discordância ultrapassar o limite configurado, sugerindo desligar a liberação automática da regra.

#### Scenario: Discordância acima do limite
- **WHEN** a revisão humana discorda de muitos resultados autoverificados de uma regra
- **THEN** o responsável técnico é alertado e pode desligar a liberação automática dessa regra
