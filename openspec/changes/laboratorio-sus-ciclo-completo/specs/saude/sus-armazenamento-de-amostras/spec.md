## Purpose

Controlar, como um armazém (WMS), onde está cada amostra e alíquota coletada depois da análise: mapa de armazenamento com endereço de
posição, retenção por política, busca e separação para reanálise ou envio, e resposta à falha de temperatura, sem nunca perder a
amostra nem eliminá-la sem aprovação.

## ADDED Requirements

### Requirement: Mapa de armazenamento de amostras
O sistema SHALL representar o armazenamento de amostras por hierarquia: equipamento (geladeira, freezer), prateleira, rack, caixa e posição
em grade. Cada tubo ou alíquota armazenado SHALL ter exatamente um endereço de posição vigente, e o sistema SHALL recusar uma posição já
ocupada.

#### Scenario: Posição ocupada
- **WHEN** o usuário tenta guardar um tubo em posição que já contém outro
- **THEN** o sistema recusa e indica a posição livre mais próxima

### Requirement: Entrada no armazenamento por leitura do tubo e da posição
O sistema SHALL registrar a entrada de uma amostra no armazenamento somente com a leitura do identificador do tubo e do código da posição, e
SHALL gravar o movimento na cadeia de custódia do tubo.

#### Scenario: Guardar sem ler a posição
- **WHEN** o usuário tenta registrar a entrada sem ler o código da posição
- **THEN** a entrada não é registrada

### Requirement: Retenção por política, sem eliminação automática
O sistema SHALL aplicar a cada amostra o prazo de retenção definido pela política do serviço por exame e material (o prazo é parâmetro do
serviço, porque não há norma federal que fixe o tempo de guarda de material biológico em análises clínicas), SHALL listar as amostras com
retenção vencida para descarte e SHALL exigir aprovação e registro do descarte, nunca eliminando sozinho.

#### Scenario: Retenção vencida
- **WHEN** o prazo de retenção de uma amostra termina
- **THEN** ela entra na lista de descarte e permanece até a aprovação e o registro do descarte

### Requirement: Amostra em investigação não é descartada
O sistema SHALL impedir o descarte de amostra ligada a quarentena, ocorrência aberta, pedido de revisão, notificação compulsória pendente
ou solicitação de reanálise, até que a pendência seja resolvida.

#### Scenario: Descarte de amostra com ocorrência
- **WHEN** alguém tenta descartar uma amostra com ocorrência aberta
- **THEN** o descarte é impedido e a ocorrência é indicada

### Requirement: Localização e separação para reanálise ou envio
O sistema SHALL localizar uma amostra por identificador do tubo, requisição ou prontuário, mostrando o endereço, e SHALL gerar lista de
separação (por exemplo, para reanálise, acréscimo de exame ou envio a laboratório de referência), com leitura na retirada e estado "fora do
armazenamento" até o retorno ou a remessa.

#### Scenario: Acréscimo de exame
- **WHEN** o solicitante pede um exame adicional sobre amostra já armazenada e dentro da estabilidade
- **THEN** o sistema lista a posição, gera a separação e registra a retirada e o retorno

### Requirement: Estabilidade da amostra armazenada
O sistema SHALL comparar o tempo e a temperatura de armazenamento com a estabilidade do exame e SHALL impedir o acréscimo de exame sobre
amostra fora da estabilidade, indicando o motivo.

#### Scenario: Amostra além da estabilidade
- **WHEN** o solicitante pede acréscimo de exame sobre amostra cuja estabilidade terminou
- **THEN** o pedido é recusado com o motivo e a recoleta é sugerida

### Requirement: Excursão de temperatura do armazenamento
O sistema SHALL, em excursão de temperatura de um equipamento de armazenamento, listar as amostras ali endereçadas, retê-las para avaliação do
responsável e registrar a decisão (manter, reavaliar o prazo ou descartar) para cada uma.

#### Scenario: Freezer desligado
- **WHEN** o freezer registra temperatura acima da faixa
- **THEN** as amostras daquele equipamento são retidas e a decisão do responsável é registrada

### Requirement: Inventário e amostra não encontrada
O sistema SHALL permitir a contagem por caixa e por equipamento e SHALL tratar a amostra não encontrada na posição esperada como ocorrência de
custódia, com investigação registrada, nunca ajustando o saldo em silêncio.

#### Scenario: Tubo ausente da posição
- **WHEN** a contagem não encontra o tubo na posição registrada
- **THEN** uma ocorrência é aberta e a cadeia de custódia indica a lacuna

### Requirement: Rótulo de endereço legível por leitor
O sistema SHALL imprimir etiquetas de equipamento, rack, caixa e posição com código legível por leitor (Code 128 ou Data Matrix) e identificador
próprio, sem dado de paciente.

#### Scenario: Etiqueta de caixa
- **WHEN** a etiqueta de uma caixa é impressa
- **THEN** traz o código da caixa e do equipamento, sem nome nem documento de paciente
