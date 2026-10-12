## Purpose

Ligar o estoque de medicamentos, insumos médicos e reagentes aos pedidos de compra e às notas fiscais eletrônicas, no recebimento em etapas
(provisório, conferência e definitivo com ateste), de modo que o que entra no estoque seja o que foi pedido, faturado e conferido, com o lote lido da
embalagem e comparado ao lote da nota.

## ADDED Requirements

### Requirement: Pedido como origem do recebimento
O sistema SHALL registrar o pedido de fornecimento (ordem de compra, autorização de fornecimento ou empenho, com contrato ou ata de registro de preços quando
houver) com fornecedor (CNPJ), itens por código CATMAT, quantidade, valor unitário e prazo, e SHALL manter o saldo do pedido por item. O recebimento SHALL ser
vinculado a um pedido, salvo entrada excepcional autorizada e justificada.

#### Scenario: Recebimento sem pedido
- **WHEN** chega mercadoria sem pedido correspondente
- **THEN** a entrada é recusada, ou segue como entrada excepcional com autorização e justificativa registradas

### Requirement: Recebimento em três etapas
O sistema SHALL conduzir o recebimento pelas etapas **provisório** (conferência da nota, do pedido e do documento de transporte e contagem dos volumes),
**conferência quantitativa e qualitativa** (quantidade, lote, validade, temperatura, integridade, rótulo, registro na ANVISA) e **definitivo** (ateste),
com recusa possível em qualquer etapa. A conferência SHALL ser feita por pelo menos duas pessoas para medicamentos e SHALL ter prioridade para itens de
cadeia de frio.

#### Scenario: Recusa na conferência
- **WHEN** a conferência encontra embalagem violada
- **THEN** o item é recusado, a ocorrência é registrada e a quantidade não entra no saldo disponível

### Requirement: NF-e de entrada conferida
O sistema SHALL importar a NF-e de entrada pelo XML e SHALL conferir: chave de acesso, protocolo de autorização, emitente igual ao fornecedor do pedido,
destinatário igual à unidade, itens e quantidades contra o pedido, valor unitário contra o pedido, e, por item, o grupo de rastreabilidade de lote (`rastro`:
número do lote, quantidade, fabricação e validade) e o código do produto na ANVISA contra o cadastro. O sistema SHALL NOT corrigir a nota: divergência
vira pendência.

#### Scenario: XML sem protocolo de autorização
- **WHEN** o XML importado não traz o protocolo de autorização
- **THEN** a entrada fica pendente, porque pode ser arquivo pré-envio

### Requirement: Lote lido da embalagem comparado ao lote da nota
O sistema SHALL comparar o lote, a validade e a quantidade lidos no código GS1 de cada embalagem com o `rastro` da NF-e, e SHALL mandar à quarentena o lote cuja
leitura difere da nota, sem redigitar o lote. Lote da nota que não aparece na leitura SHALL ficar pendente.

#### Scenario: Lote da etiqueta diferente do da nota
- **WHEN** a leitura da etiqueta traz um lote diferente do que a nota declara
- **THEN** o lote vai à quarentena e a divergência é registrada para o fornecedor

### Requirement: Ateste condicionado à conferência
O sistema SHALL permitir o ateste (recebimento definitivo) somente após a conferência completa e sem divergência aberta, SHALL registrar o responsável e a
data, e SHALL bloquear o ateste de nota com valor, quantidade ou fornecedor divergentes do pedido. A data do ateste SHALL ficar disponível ao pagamento.

#### Scenario: Ateste com divergência aberta
- **WHEN** alguém tenta atestar uma nota com divergência não resolvida
- **THEN** o ateste é recusado, com a divergência indicada

### Requirement: Entrega parcial e excesso
O sistema SHALL atualizar o saldo do pedido a cada recebimento definitivo, SHALL aceitar entrega parcial e SHALL recusar a quantidade que exceder o saldo do
pedido, salvo autorização registrada.

#### Scenario: Entrega acima do saldo
- **WHEN** a nota traz quantidade maior que o saldo do pedido
- **THEN** o excedente é recusado e registrado

### Requirement: Transporte e cadeia de frio no recebimento
O sistema SHALL conferir o documento de transporte quando houver e SHALL registrar a temperatura de chegada dos itens refrigerados ou congelados, mandando à
quarentena o item fora da faixa, conforme `saude/sus-estoque-de-reagentes-e-insumos`.

#### Scenario: Insulina que chegou quente
- **WHEN** a temperatura de chegada de uma insulina está fora da faixa
- **THEN** o lote é segregado em quarentena e a ocorrência é aberta

### Requirement: Requisição interna entre almoxarifado e unidades
O sistema SHALL permitir às unidades solicitar itens ao almoxarifado central por requisição interna, com quantidade calculada pelo consumo e pelo estoque, aprovação,
separação por lote (FEFO), transferência com conferência na saída e na chegada e estado em trânsito. A necessidade de documento fiscal na movimentação entre
unidades da mesma entidade SHALL ser parâmetro, a confirmar com a contabilidade e a fazenda.

#### Scenario: Requisição de uma UBS
- **WHEN** uma UBS requisita itens ao almoxarifado
- **THEN** a separação sugere lotes por FEFO e a entrega só fecha com a conferência da UBS

### Requirement: Necessidade de compra gerada pelo ressuprimento
O sistema SHALL transformar o alerta de ressuprimento em solicitação de compra para aprovação, com a quantidade sugerida e o saldo de ata ou contrato
disponível, sem emitir pedido sem aprovação.

#### Scenario: Risco de ruptura
- **WHEN** o ressuprimento aponta risco de ruptura de um item
- **THEN** a solicitação de compra é gerada para aprovação com a quantidade sugerida

### Requirement: Integração com pedidos e notas do ERPNext
O módulo de integração SHALL ligar o pedido ao Purchase Order, o recebimento ao Purchase Receipt e a NF-e de entrada ao Purchase Invoice do ERPNext, usando a
importação de NF-e do `erpnext_brasil` para ler o XML e SHALL estender essa leitura ao `rastro` e ao grupo de medicamento. O núcleo SHALL operar sem o ERPNext,
com pedido e nota cadastrados diretamente.

#### Scenario: Núcleo sem ERPNext
- **WHEN** o núcleo opera sem ERPNext
- **THEN** o pedido é cadastrado diretamente e o XML da NF-e é conferido pelo núcleo
