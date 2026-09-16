# CT-e Operacional Specification

## Purpose

Permite que a prestação de serviço de transporte registrada no ERPNext gere um CT-e
(modelo 57) autorizado pela SEFAZ, com os eventos do documento acionáveis de uma tela e o
desfecho auditável em estado persistido.

## Requirements

### Requirement: A prestação de transporte gera um CT-e autorizável

O sistema DEVE montar um CT-e (modelo 57) a partir de um documento de transporte do ERPNext,
com numeração sequencial por série, chave de acesso de 44 posições derivada do próprio
conteúdo, assinatura digital e todos os grupos obrigatórios do leiaute preenchidos a partir
do cadastro.

#### Scenario: Emissão com numeração alocada

- **WHEN** uma prestação de transporte é emitida como CT-e
- **THEN** o sistema aloca um número sequencial na série do modelo 57 da empresa
- **AND** o número alocado entra na chave de acesso do documento

#### Scenario: Dado obrigatório ausente recusa antes da SEFAZ

- **WHEN** o documento de transporte não tem algum dado obrigatório do leiaute (ex.: RNTRC,
  identificação de remetente ou destinatário)
- **THEN** o sistema recusa a emissão antes de transmitir, com código de erro e mensagem em
  pt-BR nomeando o dado faltante

### Requirement: A transmissão do CT-e registra o desfecho e não se repete

O sistema DEVE transmitir o CT-e assinado ao autorizador da UF do emitente (autorização
síncrona, resposta na própria chamada — o CT-e 4.00 não usa lote + recibo),
registrar o resultado em estado persistido em todos os desfechos — autorizado, rejeitado e
denegado — e NÃO DEVE reenviar um CT-e já autorizado.

#### Scenario: Autorização

- **WHEN** a SEFAZ autoriza o CT-e
- **THEN** o sistema grava a situação "autorizada", o protocolo, o XML enviado e a resposta
- **AND** a chave de acesso e o protocolo ficam registrados no documento de origem

#### Scenario: Rejeição pela SEFAZ

- **WHEN** a SEFAZ rejeita o CT-e
- **THEN** o sistema apresenta o código de rejeição e o motivo em pt-BR
- **AND** a rejeição fica registrada em estado persistido com o XML da resposta

#### Scenario: Emitente bloqueado por consumo indevido

- **WHEN** o CNPJ emitente está em janela de bloqueio por consumo indevido (cStat 656)
- **THEN** o sistema recusa a transmissão localmente, informando quanto tempo falta para a
  liberação
- **AND** não envia requisição à SEFAZ

### Requirement: Eventos do CT-e são acionáveis a partir do documento

O sistema DEVE permitir acionar os eventos do CT-e — cancelamento e carta de correção, no
mínimo — a partir do documento já autorizado, e DEVE registrar o desfecho de cada evento em
estado persistido, sem nunca reenviar um evento já aceito.

#### Scenario: Cancelamento do CT-e

- **WHEN** o operador cancela um CT-e autorizado
- **THEN** o sistema monta o evento de cancelamento com a justificativa e o protocolo do
  documento, transmite e registra o resultado
- **AND** um CT-e já cancelado não é reenviado para cancelamento

#### Scenario: Carta de correção do CT-e

- **WHEN** o operador corrige um CT-e autorizado
- **THEN** o sistema monta a carta de correção do CT-e, transmite e registra o resultado
- **AND** um documento sem correção pendente não gera carta de correção
