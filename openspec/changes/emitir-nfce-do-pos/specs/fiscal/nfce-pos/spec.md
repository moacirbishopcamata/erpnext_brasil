## Purpose

Permite que a venda registrada no ponto de venda do ERPNext gere uma NFC-e (modelo 65)
autorizada pela SEFAZ, com o cupom entregue ao consumidor contendo a chave de acesso e o QR
Code que ele usa para conferir a nota.

## ADDED Requirements

### Requirement: Venda do caixa é classificada como cupom, não como nota

O sistema DEVE classificar todo documento de ponto de venda com o indicador de aplicabilidade
`indNFCe` ao conferir a combinação CST/cClassTrib dos itens, e NÃO DEVE recorrer ao indicador
padrão de nota (`indNFe`) para esse documento.

#### Scenario: Item conferido pela tabela do cupom

- **WHEN** um documento de ponto de venda com itens é validado
- **THEN** a aplicabilidade de cada combinação CST/cClassTrib é conferida contra as entradas
  válidas para `indNFCe`

#### Scenario: Combinação válida só para nota é recusada no caixa

- **WHEN** um item do ponto de venda carrega uma combinação CST/cClassTrib admitida apenas em
  `indNFe`
- **THEN** o sistema recusa o documento com código de erro e mensagem em pt-BR nomeando o item
- **AND** a recusa acontece antes da transmissão, não como rejeição da SEFAZ

### Requirement: A tela do caixa expõe os campos fiscais que a NFC-e exige

O sistema DEVE declarar no documento de ponto de venda os mesmos campos fiscais de cabeçalho e
de item que os demais documentos fiscais já declaram, e todo campo lido ou escrito pela emissão
DEVE existir declarado.

#### Scenario: Campo lido pela emissão existe no documento

- **WHEN** a emissão lê ou grava qualquer campo fiscal do documento de ponto de venda
- **THEN** esse campo consta da declaração de campos do app
- **AND** um campo não declarado é reprovado por conferência automática antes da entrega, não
  descoberto por gravação silenciosamente perdida

### Requirement: Emissão da NFC-e a partir do ponto de venda

O sistema DEVE emitir NFC-e modelo 65 a partir do documento de ponto de venda, com chave de
acesso e autorizador determinados pela UF do emitente, e DEVE registrar no documento o
resultado da SEFAZ — protocolo quando autorizada, código e motivo quando rejeitada.

#### Scenario: Autorização normal

- **WHEN** o caixa conclui a venda e a SEFAZ autoriza o documento
- **THEN** o documento passa a exibir a chave de acesso, o protocolo e a situação "autorizada"
- **AND** o XML autorizado fica recuperável a partir do documento

#### Scenario: Rejeição pela SEFAZ

- **WHEN** a SEFAZ rejeita o documento
- **THEN** o sistema apresenta o código de rejeição e o motivo em pt-BR
- **AND** a venda não é dada como fiscalmente concluída

#### Scenario: Emitente bloqueado por consumo indevido

- **WHEN** o CNPJ emitente está em janela de bloqueio por consumo indevido (cStat 656)
- **THEN** o sistema recusa a transmissão localmente, informando quanto tempo falta para a
  liberação
- **AND** não envia requisição à SEFAZ, porque tentar de novo reinicia a janela

### Requirement: A fatura consolidada do caixa não gera documento fiscal próprio

O ERPNext consolida as vendas do ponto de venda numa fatura de venda agregada. Essa fatura
consolidada NÃO DEVE gerar documento fiscal próprio, porque cada venda que ela agrega já tem
seu cupom — emitir sobre ela documentaria as mesmas operações duas vezes.

#### Scenario: Tentativa de emitir sobre a fatura consolidada

- **WHEN** alguém solicita emissão de documento fiscal para uma fatura de venda marcada como
  consolidada do ponto de venda
- **THEN** o sistema recusa com código de erro e mensagem em pt-BR explicando que as vendas
  agregadas já têm cupom próprio

#### Scenario: Fatura de venda comum não é afetada

- **WHEN** a fatura de venda não é consolidada do ponto de venda
- **THEN** a emissão segue normalmente, sem restrição nova

### Requirement: O cupom entregue permite ao consumidor conferir a nota

O sistema DEVE produzir um cupom com a chave de acesso em texto legível e o QR Code no formato
que a NFC-e exige, de modo que o consumidor consiga localizar a nota no portal da SEFAZ da UF
do emitente.

#### Scenario: Cupom de venda autorizada

- **WHEN** uma NFC-e é autorizada
- **THEN** o cupom apresenta a chave de acesso, o QR Code e o endereço de consulta da SEFAZ

#### Scenario: Cupom de venda em contingência

- **WHEN** uma NFC-e é emitida em contingência offline
- **THEN** o cupom identifica essa condição ao consumidor
- **AND** o QR Code é o admitido para o documento em contingência
