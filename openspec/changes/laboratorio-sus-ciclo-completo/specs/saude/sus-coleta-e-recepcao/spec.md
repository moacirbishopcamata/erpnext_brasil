## Purpose

Conduzir o exame do SUS da coleta à análise por um ciclo de estados explícito, com rejeição de amostra inadequada, recoleta
segura e coleta em campo sem conectividade, preservando a identidade do tubo.

## ADDED Requirements

### Requirement: Ciclo de estados explícito e sem salto
O sistema SHALL manter para cada exame os estados solicitado, coletado, em remessa, recebido, em análise, resultado
disponível, liberado e entregue, e os estados terminais cancelado, rejeitado e descartado. Transição fora da ordem permitida
SHALL ser recusada, e cada transição SHALL gerar evento na cadeia de custódia.

#### Scenario: Salto de estado
- **WHEN** alguém tenta marcar "em análise" um exame ainda "solicitado"
- **THEN** a transição é recusada e nenhum evento é gravado

### Requirement: Coleta confirmada só após identificação positiva e etiqueta
O sistema SHALL permitir confirmar a coleta apenas depois da identificação positiva do paciente e da confirmação da impressão da
etiqueta daquele tubo, conforme `saude/sus-rastreabilidade-e-etiquetagem`.

#### Scenario: Coleta sem identificação positiva
- **WHEN** o coletador tenta confirmar a coleta sem ter confirmado a identidade do paciente
- **THEN** a coleta não é confirmada e nenhuma etiqueta é impressa

### Requirement: Preparo conferido na coleta
O sistema SHALL mostrar o preparo exigido e exigir a confirmação do coletador de que foi cumprido. Quando não foi, o coletador
SHALL escolher entre adiar a coleta ou coletar com observação registrada, que acompanha o resultado até o laudo.

#### Scenario: Jejum não cumprido
- **WHEN** o paciente não está em jejum para um exame que o exige e o coletador coleta mesmo assim
- **THEN** a observação "jejum não cumprido" é gravada na amostra e aparece no laudo

### Requirement: Critérios de rejeição enumerados
O sistema SHALL rejeitar amostra apenas por motivo de lista enumerada (rótulo ilegível ou ausente, divergência de
identificação, volume insuficiente, hemólise, tubo inadequado, amostra coagulada, estabilidade vencida, temperatura fora da
faixa, material derramado). A rejeição SHALL registrar quem, quando, onde e o motivo, e SHALL comunicar a unidade solicitante.

#### Scenario: Rejeição por hemólise
- **WHEN** a recepção rejeita um tubo por hemólise
- **THEN** o exame vai ao estado rejeitado, o motivo é gravado e a unidade solicitante recebe o pedido de recoleta

### Requirement: Recoleta gera novo tubo
O sistema SHALL tratar a recoleta como nova coleta, com novo identificador e nova etiqueta, ligando o tubo novo ao rejeitado na
cadeia. O resultado SHALL poder vir apenas do tubo novo.

#### Scenario: Recoleta depois de rejeição
- **WHEN** o paciente é recoletado após rejeição
- **THEN** o novo tubo tem identificador diferente, aponta para o rejeitado, e só ele recebe resultado

### Requirement: Coleta em campo com faixa de identificadores reservada
O sistema SHALL permitir, em estação sem conectividade, imprimir etiquetas a partir de uma faixa de identificadores reservada
àquela estação, usada em sequência. Identificador reservado e não usado SHALL ser anulado e registrado, nunca reaproveitado. Na
sincronização, o sistema SHALL recusar identificador fora da faixa da estação ou já usado.

#### Scenario: Sincronização com identificador repetido
- **WHEN** a estação sincroniza um tubo cujo identificador já existe em outra estação
- **THEN** o segundo registro vai à quarentena e nenhum dos dois recebe resultado até a decisão humana

### Requirement: Recepção confere etiqueta e solicitação
O sistema SHALL exigir, na recepção do laboratório, a leitura do código do tubo e a conferência com a solicitação (paciente,
exame, material). Tubo sem solicitação ou divergente SHALL ficar retido e não ser liberado para análise.

#### Scenario: Tubo sem solicitação
- **WHEN** a leitura na recepção não encontra solicitação
- **THEN** o tubo fica retido com ocorrência e não entra na fila de análise
