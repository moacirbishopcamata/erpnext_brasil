## Purpose

Permite que uma fatura de serviços do ERPNext gere uma NFS-e autorizada pelo caminho que o
município e o regime do prestador exigem, com o desfecho em estado persistido, o cancelamento
como evento e tratamento próprio dos serviços de saúde.

## ADDED Requirements

### Requirement: O caminho de emissão é decidido pelo prestador e nunca presumido

O sistema SHALL escolher o caminho de emissão da NFS-e — emissor nacional ou emissor municipal
— a partir do município e do regime do prestador, e SHALL NOT transmitir pelo caminho
errado: o caminho ainda não implementado SHALL ser recusado antes de qualquer transmissão, com
o motivo e o caminho que o prestador deveria usar.

#### Scenario: Optante do Simples ME ou EPP usa o caminho nacional

- **WHEN** o prestador é microempresa ou empresa de pequeno porte optante do Simples Nacional
  e o prazo de obrigatoriedade do padrão nacional já começou
- **THEN** a emissão segue pelo caminho nacional

#### Scenario: Caminho municipal sem implementação recusa

- **WHEN** o prestador deve emitir pelo emissor municipal e esse caminho não está implementado
  para o município
- **THEN** o sistema recusa a emissão antes de transmitir, nomeando o município e o caminho

#### Scenario: Caminho não configurado

- **WHEN** a empresa não tem o caminho de emissão da NFS-e definido
- **THEN** o sistema recusa a emissão e pede a definição, sem escolher um caminho

### Requirement: A fatura de serviços gera uma DPS completa

O sistema SHALL montar a DPS a partir da fatura de serviços, com prestador, tomador, serviço,
valores, tributação municipal e os campos de IBS e CBS que o leiaute do período exige, numeração
sequencial por série, identificador conferido e assinatura digital, e SHALL recusar a emissão
antes de transmitir quando faltar dado obrigatório do leiaute.

#### Scenario: Numeração alocada na emissão

- **WHEN** uma fatura de serviços é emitida como NFS-e
- **THEN** o sistema aloca o número da DPS na série da empresa sem lacuna e esse número integra
  o identificador da DPS

#### Scenario: Dado obrigatório ausente

- **WHEN** a fatura não tem um dado obrigatório do leiaute, por exemplo o código do serviço
- **THEN** o sistema recusa a emissão antes de transmitir, nomeando o dado faltante em pt-BR

#### Scenario: Serviço sem enquadramento na tabela oficial

- **WHEN** o item de serviço não tem código nas tabelas oficiais de serviços
- **THEN** o sistema recusa a emissão e não infere o código por palavra-chave

### Requirement: O desfecho da transmissão é persistido e não se repete

O sistema SHALL transmitir a DPS assinada, registrar a NFS-e autorizada ou a rejeição em estado
persistido em todos os desfechos, e SHALL NOT reenviar uma DPS cuja NFS-e já foi autorizada.

#### Scenario: Autorizada

- **WHEN** o emissor devolve a NFS-e
- **THEN** o estado persistido guarda a chave de acesso, o XML da NFS-e e a data de autorização

#### Scenario: Rejeitada

- **WHEN** o emissor rejeita a DPS
- **THEN** o estado persistido guarda o código e a mensagem da rejeição e a fatura continua
  disponível para correção

#### Scenario: Reenvio de nota já autorizada

- **WHEN** o usuário pede a emissão de uma fatura cuja NFS-e já está autorizada
- **THEN** o sistema não transmite de novo e devolve a NFS-e existente

### Requirement: O cancelamento é um evento da NFS-e autorizada

O sistema SHALL permitir cancelar somente NFS-e autorizada, por evento transmitido ao emissor,
registrando o desfecho, e SHALL NOT cancelar nota inexistente, rejeitada ou já cancelada.

#### Scenario: Cancelamento autorizado

- **WHEN** o usuário cancela uma NFS-e autorizada informando o motivo
- **THEN** o evento é transmitido e a nota passa a constar como cancelada com o protocolo

#### Scenario: Cancelar nota rejeitada

- **WHEN** o usuário tenta cancelar uma fatura cuja DPS foi rejeitada
- **THEN** o sistema recusa e informa que não há NFS-e a cancelar

### Requirement: A discriminação de serviço de saúde não carrega dado clínico

Quando o serviço é de saúde, o sistema SHALL montar a discriminação do serviço a partir do
cadastro do item e da competência, e SHALL NOT incluir na NFS-e diagnóstico, CID, resultado de
exame ou qualquer dado clínico do atendimento.

#### Scenario: Atendimento com dado clínico

- **WHEN** a fatura de saúde se origina de um atendimento que tem diagnóstico e resultado
- **THEN** a discriminação da NFS-e contém só a descrição do serviço e a competência

### Requirement: O tomador é o paciente ou a operadora, conforme a cobrança

O sistema SHALL identificar como tomador a pessoa que paga o serviço — o paciente pessoa
física ou a operadora de saúde pessoa jurídica —, e SHALL recusar a emissão quando o tomador
exigido pelo leiaute para a operação não puder ser identificado.

#### Scenario: Cobrança a operadora

- **WHEN** o serviço é faturado a uma operadora de saúde
- **THEN** o tomador da NFS-e é a operadora, pelo CNPJ, e não o paciente

#### Scenario: Cobrança ao paciente

- **WHEN** o serviço é faturado ao paciente
- **THEN** o tomador da NFS-e é o paciente, pelo CPF

### Requirement: Atendimento sem cobrança não gera NFS-e

O sistema SHALL NOT gerar NFS-e para atendimento ou dispensação sem cobrança, como o realizado
pelo SUS sem faturamento fiscal, e SHALL recusar o pedido de emissão para eles com mensagem que
explica que não há operação tributável a documentar.

#### Scenario: Pedido de emissão para atendimento gratuito

- **WHEN** o usuário pede a NFS-e de um atendimento sem cobrança
- **THEN** o sistema recusa a emissão e nenhum registro de NFS-e é criado

### Requirement: A emissão e o cancelamento respeitam a permissão do usuário

O sistema SHALL exigir permissão de leitura da empresa e de escrita da fatura antes de qualquer
leitura ou transmissão, e SHALL NOT gravar o estado da NFS-e com permissão contornada.

#### Scenario: Usuário sem permissão

- **WHEN** um usuário sem permissão sobre a fatura pede a emissão
- **THEN** o sistema recusa com erro de permissão e nada é transmitido nem gravado
