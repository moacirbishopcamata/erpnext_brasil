## ADDED Requirements

### Requirement: O MDF-e é emitido nos modais aquaviário, aéreo e ferroviário

O sistema SHALL montar o MDF-e com o grupo do modal da viagem — aquaviário, aéreo ou
ferroviário, além do rodoviário —, com os dados do modal vindos do `Shipment` e validados
contra o leiaute oficial, e SHALL recusar com mensagem em pt-BR o modal que o MDF-e não prevê,
em vez de reaproveitar a codificação do CT-e.

#### Scenario: Viagem fluvial

- **WHEN** o `Shipment` é uma viagem aquaviária e traz os dados obrigatórios da embarcação e da
  viagem
- **THEN** o MDF-e contém o grupo do modal aquaviário e as referências fiscais da carga

#### Scenario: Dado do modal ausente

- **WHEN** o `Shipment` é de um modal implementado, mas falta um dado obrigatório do modal
- **THEN** o sistema recusa a emissão antes de transmitir e nomeia o dado e o modal

#### Scenario: Código de modal do CT-e não vale no MDF-e

- **WHEN** a viagem usa um modal que o MDF-e não prevê (por exemplo, dutoviário)
- **THEN** o sistema recusa a emissão e informa que o MDF-e não tem esse modal

### Requirement: A emissão do MDF-e é uma ação do usuário, nunca automática

O sistema SHALL emitir o MDF-e somente por ação explícita do usuário sobre o `Shipment`, e
SHALL NOT emiti-lo por efeito colateral de outra operação, inclusive de despacho de armazém,
porque a obrigatoriedade do manifesto em cada transporte depende da legislação da unidade
federada e do contribuinte.

#### Scenario: Despacho de armazém não emite manifesto

- **WHEN** uma carga é despachada por rota fluvial
- **THEN** nenhum MDF-e é emitido até o usuário pedir a emissão
