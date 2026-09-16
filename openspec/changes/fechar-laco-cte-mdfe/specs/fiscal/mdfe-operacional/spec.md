## Purpose

Permite que a viagem registrada no `Shipment` do ERPNext gere um MDF-e (modelo 58)
autorizado, agregando as referências fiscais da carga por município de descarga, com
encerramento e os demais eventos acionáveis de uma tela.

## ADDED Requirements

### Requirement: O manifesto agrega as cargas de um Shipment

O sistema DEVE montar um MDF-e (modelo 58) a partir de um `Shipment` do ERPNext, reunindo as
chaves de acesso dos documentos fiscais transportados agrupadas por município de descarga, com
os dados da viagem (veículo, motorista e totalizadores) e os demais grupos obrigatórios do
leiaute.

#### Scenario: Cargas agrupadas por município de descarga

- **WHEN** um `Shipment` transporta documentos fiscais com chave de acesso para mais de um
  município de descarga
- **THEN** o manifesto referencia cada documento no grupo do seu município de descarga

#### Scenario: Referência sem município conhecido recusa a emissão

- **WHEN** um `Shipment` tem documentos fiscais com chave de acesso, mas o endereço de entrega
  não informa o município de descarga
- **THEN** o sistema recusa a emissão do manifesto antes de transmitir, nomeando o dado faltante

#### Scenario: Manifesto sem carga não é manifesto

- **WHEN** um `Shipment` não reúne nenhum documento fiscal com chave de acesso
- **THEN** o sistema recusa a emissão do manifesto com erro e mensagem em pt-BR

### Requirement: A numeração do MDF-e é sequencial por série

O sistema DEVE alocar para cada MDF-e um número sequencial na série do modelo 58 da empresa,
sem lacuna, antes de transmitir, e o número DEVE entrar na chave de acesso do documento.

#### Scenario: Número alocado na emissão

- **WHEN** um MDF-e é emitido
- **THEN** o número do manifesto é alocado na série do modelo 58 e integra a chave de acesso

### Requirement: A transmissão do MDF-e registra o desfecho e não se repete

O sistema DEVE transmitir o MDF-e assinado ao autorizador (lote e recibo), registrar o
resultado em estado persistido em todos os desfechos — autorizado, rejeitado e denegado — e
NÃO DEVE reenviar um MDF-e já autorizado.

#### Scenario: Autorização

- **WHEN** a SEFAZ autoriza o MDF-e
- **THEN** o sistema grava a situação "autorizada", o protocolo, o XML enviado e a resposta
- **AND** a chave de acesso e o protocolo ficam registrados no documento de origem

#### Scenario: Rejeição pela SEFAZ

- **WHEN** a SEFAZ rejeita o MDF-e
- **THEN** o sistema apresenta o código de rejeição e o motivo em pt-BR
- **AND** a rejeição fica registrada em estado persistido com o XML da resposta

#### Scenario: Emitente bloqueado por consumo indevido

- **WHEN** o CNPJ emitente está em janela de bloqueio por consumo indevido (cStat 656)
- **THEN** o sistema recusa a transmissão localmente, informando quanto tempo falta para a
  liberação
- **AND** não envia requisição à SEFAZ

### Requirement: Eventos operacionais do MDF-e são acionáveis a partir do documento

O sistema DEVE permitir acionar os eventos do MDF-e — encerramento da viagem e cancelamento, no
mínimo — a partir do documento autorizado, e DEVE registrar o desfecho de cada evento em estado
persistido.

#### Scenario: Encerramento da viagem

- **WHEN** o operador encerra um MDF-e autorizado
- **THEN** o sistema monta o evento de encerramento, transmite e registra o resultado

#### Scenario: Cancelamento do MDF-e

- **WHEN** o operador cancela um MDF-e autorizado
- **THEN** o sistema monta o evento de cancelamento, transmite e registra o resultado
- **AND** um MDF-e já encerrado não é cancelado