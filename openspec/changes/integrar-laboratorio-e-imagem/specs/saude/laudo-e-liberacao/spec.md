## Purpose

Liberar laudos com política definida, assinatura legalmente válida e o conteúdo que a norma exige, e tratar qualquer correção
como novo laudo — nunca como edição silenciosa do que o paciente já recebeu.

## ADDED Requirements

### Requirement: Liberação sistematizada, manual por padrão

O sistema MUST ter processo definido de liberação de resultados e laudos, automático ou manual (RDC 786/2023, art. 71, III, e
art. 136). A liberação MUST ser manual por padrão; a automática só MUST operar quando habilitada, com regras documentadas e
sem se aplicar a resultado retido, em quarentena ou com valor crítico.

#### Scenario: Liberação manual

- **WHEN** um profissional habilitado valida e libera o resultado
- **THEN** o sistema registra quem liberou e quando, e disponibiliza o laudo

#### Scenario: Resultado retido

- **WHEN** o resultado está retido por divergência, controle reprovado ou lacuna na cadeia
- **THEN** nenhuma liberação, manual ou automática, ocorre

### Requirement: Assinatura legalmente válida por profissional habilitado

O laudo MUST ser datado e assinado por profissional de nível superior legalmente habilitado, com assinatura legalmente válida
(art. 137; Lei 14.063/2020), e MUST registrar o nome e o número no conselho de classe de quem assina e do responsável técnico.

#### Scenario: Laudo sem assinatura válida

- **WHEN** se tenta emitir um laudo sem assinatura legalmente válida
- **THEN** o sistema recusa a emissão

### Requirement: Conteúdo mínimo do laudo

O laudo MUST conter, no mínimo, os elementos do art. 138 da RDC 786/2023: nome e CNES do serviço responsável pela análise;
endereço e telefone; nome e registro do responsável técnico e do signatário; nome e registro de identificação do paciente;
idade ou data de nascimento; data da coleta; nome do exame, tipo de material e método; resultado e unidade; valores de
referência, limitações da metodologia e dados para interpretação; metodologia própria, quando aplicável; condição de material
aceito com restrição; data de emissão; e assinatura legalmente válida.

#### Scenario: Elemento obrigatório ausente

- **WHEN** falta qualquer elemento obrigatório, como o CNES ou o método
- **THEN** o sistema não emite o laudo e informa qual elemento falta

#### Scenario: Material com restrição

- **WHEN** o material foi aceito com restrição
- **THEN** a restrição consta no laudo

### Requirement: Retificação sempre em novo laudo

Qualquer retificação de dado de laudo já emitido MUST ser feita em novo laudo que deixe clara a retificação, e o laudo original
MUST ser preservado (art. 140). Em alteração relevante após a entrega, o sistema MUST exigir o registro do contato com o
paciente ou responsável, com o nome da pessoa contatada e a data.

#### Scenario: Correção de laudo já entregue

- **WHEN** um resultado de laudo entregue é corrigido
- **THEN** o sistema emite um novo laudo que identifica a retificação e mantém o original
- **AND** exige o registro do contato com o paciente, o nome contatado e a data

### Requirement: Comunicação de valor crítico

O sistema MUST permitir definir a lista de resultados que exigem decisão imediata e o fluxo de comunicação ao paciente, ao
médico ou ao profissional responsável (art. 136, parágrafo único), e MUST registrar quem foi comunicado, quando e por quem.

#### Scenario: Valor crítico

- **WHEN** um resultado enquadrado como crítico é validado
- **THEN** o sistema exige o registro da comunicação antes de concluir a liberação

### Requirement: Laudo de laboratório de apoio preserva fidedignidade

Quando o serviço transcrever laudo de laboratório de apoio, o sistema MUST preservar o conteúdo original, MUST identificar o
laboratório de apoio no laudo e MUST registrar à parte qualquer comentário de interpretação acrescentado (art. 139).

#### Scenario: Transcrição

- **WHEN** um laudo de laboratório de apoio é incorporado
- **THEN** o laudo informa o nome do laboratório de apoio e distingue o comentário do serviço do texto original
