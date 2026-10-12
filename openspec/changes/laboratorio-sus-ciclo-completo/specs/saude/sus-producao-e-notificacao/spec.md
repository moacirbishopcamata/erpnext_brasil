## Purpose

Registrar a produção laboratorial do SUS por procedimento e unidade, sem tratá-la como fatura, e alertar o profissional quando um
resultado corresponde a agravo de notificação compulsória, sem decidir por ele.

## ADDED Requirements

### Requirement: Produção por procedimento SIGTAP e unidade
O sistema SHALL contabilizar, por competência, unidade e procedimento SIGTAP, os exames realizados e liberados, e SHALL NOT
contabilizar exame cancelado, rejeitado sem resultado ou não liberado. A produção SHALL permanecer rastreável até os exames de
origem.

#### Scenario: Exame rejeitado e recoletado
- **WHEN** um exame foi rejeitado e recoletado
- **THEN** somente o exame que gerou resultado liberado entra na produção

### Requirement: Instrumento de registro conforme o procedimento
O sistema SHALL registrar a produção no instrumento exigido para o procedimento na competência (individualizado ou
consolidado), conforme a tabela vigente. A regra de qual procedimento exige qual instrumento SHALL vir da tabela da competência e
não de código fixo, e instrumentos SHALL NOT ser misturados na mesma competência quando a regra proibir.

#### Scenario: Procedimento que exige registro individualizado
- **WHEN** o procedimento exige registro individualizado na competência
- **THEN** a produção inclui o paciente (CNS) daquele exame e é recusada quando falta

### Requirement: Fechamento de competência imutável
O sistema SHALL fechar a competência registrando totais e quem fechou. Correção posterior SHALL ocorrer por retificação
registrada, nunca por edição silenciosa.

#### Scenario: Correção depois do fechamento
- **WHEN** um erro é descoberto numa competência fechada
- **THEN** a correção é feita por retificação que preserva o fechamento original

### Requirement: Alerta de notificação compulsória
O sistema SHALL manter a correspondência entre resultados e agravos da Lista Nacional de Notificação Compulsória vigente e, ao
liberar um resultado que corresponde a um agravo, SHALL abrir um alerta para o profissional com o prazo da lista (imediata ou
semanal), sem notificar por conta própria. O alerta SHALL permanecer aberto até o registro da notificação feita ou da dispensa
justificada.

#### Scenario: Resultado de agravo de notificação imediata
- **WHEN** é liberado um resultado correspondente a agravo de notificação imediata
- **THEN** um alerta com o prazo imediato é aberto e permanece até o registro da notificação ou da dispensa

### Requirement: Lista de agravos versionada
O sistema SHALL guardar a lista de agravos com a norma de origem e a data de vigência, e uma alteração SHALL valer apenas para
resultados liberados após a vigência.

#### Scenario: Agravo incluído por nova portaria
- **WHEN** a lista passa a incluir um agravo
- **THEN** resultados liberados antes da vigência não geram alerta retroativo
