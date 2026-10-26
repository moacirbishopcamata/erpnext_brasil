## ADDED Requirements

### Requirement: O CT-e é emitido nos modais aquaviário, aéreo e ferroviário

O sistema SHALL montar o CT-e com o grupo do modal escolhido na prestação de transporte —
aquaviário, aéreo ou ferroviário, além do rodoviário —, com os dados do modal vindos do
documento de transporte e validados contra o leiaute oficial, e SHALL recusar com mensagem em
pt-BR o modal ainda não implementado (dutoviário e multimodal), nomeando-o, em vez de emitir
com o grupo errado ou vazio.

#### Scenario: Modal aquaviário com dados completos

- **WHEN** a prestação de transporte é do modal aquaviário e traz os dados obrigatórios do modal
- **THEN** o CT-e contém o grupo do modal aquaviário e nenhum grupo de outro modal

#### Scenario: Dado do modal ausente

- **WHEN** a prestação é de um modal implementado, mas falta um dado obrigatório do modal
- **THEN** o sistema recusa a emissão antes de transmitir e nomeia o dado e o modal

#### Scenario: Modal não implementado

- **WHEN** a prestação é do modal dutoviário ou multimodal
- **THEN** o sistema recusa a emissão antes de transmitir e informa que esse modal não está
  implementado

#### Scenario: Modal rodoviário permanece como estava

- **WHEN** a prestação é do modal rodoviário
- **THEN** o CT-e é montado exatamente como antes desta mudança
