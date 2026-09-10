## Purpose

Mantém a venda no balcão possível quando a SEFAZ não responde: a NFC-e é emitida em
contingência offline, o cupom é entregue ao consumidor na hora, e a autorização é buscada
depois, sem depender de o operador lembrar de fazê-la.

## ADDED Requirements

### Requirement: A indisponibilidade da SEFAZ não impede a venda

Quando a transmissão da NFC-e não obtém resposta conclusiva da SEFAZ, o sistema DEVE emitir o
documento em contingência offline e concluir a venda, em vez de recusá-la.

#### Scenario: SEFAZ não responde

- **WHEN** a transmissão falha por indisponibilidade ou esgotamento de tempo
- **THEN** o documento é emitido em contingência offline
- **AND** a venda é concluída e o cupom é entregue ao consumidor

#### Scenario: Rejeição não é indisponibilidade

- **WHEN** a SEFAZ responde rejeitando o documento
- **THEN** o sistema NÃO entra em contingência
- **AND** apresenta a rejeição, porque o documento está errado e reenviá-lo em contingência
  apenas adia a mesma recusa

#### Scenario: Bloqueio por consumo indevido não é indisponibilidade

- **WHEN** o emitente está bloqueado por consumo indevido
- **THEN** o sistema NÃO entra em contingência por esse motivo
- **AND** informa o bloqueio e o tempo restante

### Requirement: Todo documento emitido em contingência fica pendente de autorização

O sistema DEVE registrar em estado persistido cada documento emitido em contingência, e esse
registro DEVE sobreviver ao encerramento da sessão, ao fechamento do caixa e à reinicialização
do servidor, até que o documento seja autorizado, rejeitado ou denegado.

#### Scenario: Pendência sobrevive ao reinício

- **WHEN** o servidor é reiniciado com documentos em contingência ainda não autorizados
- **THEN** esses documentos continuam listados como pendentes de autorização

#### Scenario: Pendência é visível a quem opera

- **WHEN** existem documentos em contingência não autorizados
- **THEN** o sistema exibe quantos são e há quanto tempo estão pendentes

### Requirement: A autorização pendente é buscada sem intervenção do operador

O sistema DEVE tentar autorizar automaticamente os documentos pendentes quando a SEFAZ voltar a
responder, e DEVE tratar cada resultado de forma distinta — autorizada, rejeitada ou denegada —
sem descartar o documento em nenhum dos casos.

#### Scenario: SEFAZ volta e autoriza

- **WHEN** a SEFAZ volta a responder e autoriza um documento pendente
- **THEN** o documento passa a "autorizada", com protocolo, e sai da lista de pendentes

#### Scenario: SEFAZ volta e rejeita

- **WHEN** a SEFAZ rejeita um documento pendente
- **THEN** o sistema mantém o registro, apresenta o motivo e sinaliza que exige tratamento
  humano, porque o cupom correspondente já foi entregue ao consumidor

#### Scenario: Prazo de transmissão esgotado

- **WHEN** um documento em contingência ultrapassa o prazo de transmissão previsto no Manual de
  Orientação do Contribuinte
- **THEN** o sistema alerta explicitamente, distinguindo essa situação de uma pendência dentro
  do prazo

### Requirement: A contingência é declarada no próprio documento

O documento emitido em contingência DEVE registrar essa condição, o momento em que ela começou
e o motivo, de modo que a situação seja auditável depois sem depender de log.

#### Scenario: Documento em contingência é auditável

- **WHEN** um documento é emitido em contingência
- **THEN** o documento carrega o tipo de emissão de contingência, a data e hora de entrada em
  contingência e a justificativa
