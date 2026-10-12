## Purpose

Dar ao módulo um cadastro de pacientes próprio, confiável e deduplicado, porque o ERPNext não tem paciente e o resultado só pode
ser entregue, enviado à RNDS e, quando for trabalhador, reportado ao eSocial se a identidade do paciente for única e rastreável.

## ADDED Requirements

### Requirement: Dados mínimos do paciente
O sistema SHALL manter, para cada paciente, nome civil, nome social quando houver, data de nascimento, sexo, nome da mãe, CNS e/ou
CPF, município de residência, endereço e contato. Nome da mãe e nascimento SHALL ser exigidos para a identificação positiva quando o
paciente não tem CNS nem CPF.

#### Scenario: Cadastro sem CNS nem CPF
- **WHEN** o paciente é cadastrado sem CNS nem CPF
- **THEN** o sistema exige nome, nascimento e nome da mãe e marca o cadastro como pendente de regularização

### Requirement: Documento único por paciente
O sistema SHALL recusar um segundo cadastro ativo com o mesmo CNS ou o mesmo CPF e SHALL apontar o cadastro existente. Um paciente
MAY ter mais de um CNS ao longo do tempo (definitivo e provisório), todos ligados ao mesmo cadastro.

#### Scenario: CPF repetido
- **WHEN** alguém cadastra um paciente com CPF já existente
- **THEN** o cadastro é recusado e o existente é indicado

### Requirement: Deduplicação por similaridade com decisão humana
O sistema SHALL sugerir possíveis duplicados (nome, nascimento e nome da mãe semelhantes) e SHALL NOT fundir cadastros sem decisão
registrada de usuário autorizado.

#### Scenario: Possível duplicado
- **WHEN** o cadastro novo é semelhante a um existente
- **THEN** o sistema avisa e exige a decisão de manter separados ou fundir

### Requirement: Fusão rastreável e reversível
O sistema SHALL, ao fundir dois cadastros, preservar o histórico dos dois, redirecionar exames e solicitações para o cadastro
mantido, registrar quem fundiu, quando e por quê, e SHALL permitir desfazer a fusão. Resultados já liberados SHALL manter a
identificação que tinham ao serem liberados.

#### Scenario: Fusão desfeita
- **WHEN** uma fusão feita por engano é desfeita
- **THEN** os dois cadastros voltam ao estado anterior com seus exames originais

### Requirement: Vínculo opcional de trabalhador
O sistema SHALL permitir registrar que o paciente é trabalhador, com o CPF, o empregador (CNPJ ou CAEPF), a matrícula e a data de
admissão, sem torná-los obrigatórios para os demais pacientes.

#### Scenario: Paciente que não é trabalhador
- **WHEN** um paciente é cadastrado sem vínculo de trabalho
- **THEN** o cadastro é aceito e nenhum dado de eSocial é exigido

### Requirement: Acesso e alteração auditados
O sistema SHALL registrar toda alteração de dado do paciente com valor anterior e novo, usuário, local e horário, e toda
alteração de identificação (nome, nascimento, documento) em paciente com exame liberado SHALL exigir motivo.

#### Scenario: Correção de nascimento com exame liberado
- **WHEN** a data de nascimento de um paciente com exame liberado é corrigida
- **THEN** o motivo é exigido e o valor anterior fica registrado

### Requirement: Cadastro próprio sem dependência de outro módulo
O sistema SHALL operar o cadastro de pacientes sem ERPNext nem Healthcare instalados. A leitura de pacientes de outro cadastro SHALL
ser feita pelo módulo de integração, que cria ou atualiza o cadastro próprio, nunca o substitui.

#### Scenario: Módulo instalado sozinho
- **WHEN** o módulo opera sem ERPNext
- **THEN** o cadastro, a busca e a fusão de pacientes funcionam
