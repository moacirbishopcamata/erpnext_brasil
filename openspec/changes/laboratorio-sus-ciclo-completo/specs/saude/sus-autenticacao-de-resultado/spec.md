## Purpose

Permitir que o paciente, o solicitante ou um terceiro autorizado confirme, sem login, que um laudo em mãos é autêntico, íntegro e
vigente, e saiba se foi retificado ou revogado, sem que a página de validação vire uma fonte de vazamento de dado de saúde.

## ADDED Requirements

### Requirement: Código de autenticação e QR em todo laudo emitido
O sistema SHALL gerar, para cada laudo emitido, um código de autenticação aleatório e não adivinhável (não derivado de dado do
paciente nem de sequência) e SHALL imprimi-lo no laudo, junto com um QR que leva à página pública de validação com o código já
preenchido. O código SHALL ser único e nunca reaproveitado.

#### Scenario: Laudo emitido
- **WHEN** um laudo é liberado
- **THEN** ele traz o código de autenticação e o QR de validação, e o código é registrado ligado ao laudo

### Requirement: Validação pública com segundo fator
O sistema SHALL oferecer uma página pública de validação que recebe o código e um segundo fator conhecido do paciente (por exemplo,
data de nascimento ou os quatro últimos dígitos do CPF) e SHALL exibir o conteúdo do laudo apenas quando os dois conferem. Sem o
segundo fator, a página SHALL mostrar somente a situação de autenticidade, sem nome nem resultado.

#### Scenario: Só o código, sem segundo fator
- **WHEN** alguém abre o QR sem informar o segundo fator
- **THEN** vê apenas "laudo autêntico, emitido em <data> por <unidade>", sem nome do paciente nem resultados

#### Scenario: Segundo fator errado
- **WHEN** o segundo fator não confere
- **THEN** o conteúdo não é exibido e a tentativa é contada para o limite de tentativas

### Requirement: Situação do laudo informada
O sistema SHALL informar, na validação, a situação do laudo: vigente, retificado (indicando que existe laudo mais novo), revogado ou
inexistente, e SHALL mostrar a data da última alteração. Um laudo retificado SHALL continuar autêntico como documento histórico, mas
SHALL ser sinalizado como substituído.

#### Scenario: Laudo retificado
- **WHEN** o paciente valida um laudo que foi retificado
- **THEN** a página informa que o laudo foi substituído por outro mais recente, sem apagar a autenticidade do original

### Requirement: Integridade comprovada pelo hash do documento
O sistema SHALL guardar o hash (SHA-256) do PDF assinado de cada laudo e SHALL permitir ao paciente enviar o arquivo recebido para
conferir se é idêntico ao emitido; o arquivo enviado SHALL ser processado em memória e não retido. A página SHALL indicar também o
estado da assinatura digital (válida, certificado expirado ou revogado).

#### Scenario: PDF alterado
- **WHEN** o paciente envia um PDF diferente do emitido
- **THEN** a página informa que o documento não confere com o emitido

### Requirement: Validação independente do sistema
O laudo SHALL ser verificável também sem o sistema do laboratório: a assinatura ICP-Brasil do PDF SHALL poder ser validada por um
validador externo (como o do ITI), e o laudo SHALL trazer o endereço da página de validação em texto, além do QR.

#### Scenario: Sistema do laboratório fora do ar
- **WHEN** a página de validação está indisponível
- **THEN** a assinatura do PDF ainda pode ser conferida em validador externo

### Requirement: Proteção contra enumeração e abuso
O sistema SHALL limitar tentativas por origem e por código, SHALL responder de forma idêntica a um código inexistente e a um segundo
fator errado quando o segundo fator for exigido, e SHALL NOT permitir listar, buscar ou prever códigos.

#### Scenario: Varredura de códigos
- **WHEN** um cliente tenta muitos códigos em sequência
- **THEN** é limitado e nenhuma resposta distingue código inexistente de segundo fator errado

### Requirement: Validação auditada e sem dado em registro técnico
O sistema SHALL registrar cada validação (código, data e hora, resultado, origem aproximada) para auditoria e SHALL NOT gravar o
segundo fator nem o conteúdo exibido em registro técnico ou de acesso.

#### Scenario: Registro da validação
- **WHEN** uma validação é feita
- **THEN** o evento fica registrado sem o segundo fator e sem o resultado
