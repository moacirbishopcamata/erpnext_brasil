## Purpose

Controlar a logística das coletas: o que precisa ser coletado, onde, por quem e com quais insumos, incluindo coleta em campo, domiciliar e
fluvial, de modo que nenhum exame solicitado se perca entre o pedido e o laboratório, e que o kit certo esteja no lugar certo.

## ADDED Requirements

### Requirement: Fila de coleta por unidade e prioridade
O sistema SHALL manter, por unidade coletora, a fila de coletas pendentes ordenada por prioridade e por prazo, com o preparo exigido de cada
exame, e SHALL destacar a coleta atrasada em relação ao prazo da prioridade.

#### Scenario: Urgência na fila
- **WHEN** chega uma solicitação de urgência
- **THEN** ela aparece no topo da fila da unidade coletora

### Requirement: Agenda e rotas de coleta
O sistema SHALL permitir planejar rotas e janelas de coleta (unidade fixa, coleta domiciliar, coleta em comunidade ribeirinha e coleta
fluvial), com data, responsável, locais e a estimativa de tempo entre a coleta e a chegada ao laboratório, e SHALL alertar quando a rota
não cumpre a estabilidade dos exames da carga.

#### Scenario: Rota longa com exame de estabilidade curta
- **WHEN** a rota tem tempo estimado maior que a estabilidade de um exame previsto
- **THEN** o sistema alerta e sugere coletar esse exame na unidade ou transportar sob condição validada

### Requirement: Kit de coleta por rota e por coletor
O sistema SHALL montar o kit de coleta de cada rota ou coletor a partir dos exames previstos (tubos, agulhas, etiquetas, swabs, coletores,
material refrigerante e formulários), SHALL separá-lo do estoque de insumos com lote e validade e SHALL conferir a saída e o retorno, tratando a
sobra e a falta.

#### Scenario: Kit com tubo vencido
- **WHEN** o kit inclui tubo cuja validade terminou
- **THEN** o sistema impede a separação do item vencido e indica a substituição

### Requirement: Reconciliação das coletas
O sistema SHALL reconciliar, por período e por unidade, os exames solicitados, coletados, remetidos e recebidos, listando cada diferença como
pendência: solicitado e não coletado, coletado e não remetido, remetido e não recebido, recebido sem requisição.

#### Scenario: Coletado e não remetido
- **WHEN** um tubo coletado não consta de nenhuma remessa depois do prazo
- **THEN** a pendência é aberta para a unidade, com o tempo decorrido

### Requirement: Coleta em campo com consumo de insumo baixado
O sistema SHALL baixar do kit os insumos consumidos em cada coleta (tubos, etiquetas, agulhas) e SHALL conferir o consumo contra os tubos
coletados, tratando como divergência a etiqueta impressa e não usada ou o tubo sem etiqueta.

#### Scenario: Etiqueta impressa e não usada
- **WHEN** o kit retorna com etiqueta de identificador impresso e sem tubo coletado
- **THEN** o identificador é anulado e registrado, nunca reaproveitado

### Requirement: Indicadores de coleta
O sistema SHALL calcular, sem identificar o paciente, os indicadores de coleta: tempo da solicitação à coleta, taxa de recoleta por motivo, coletas
por coletor e por rota, coletas pendentes e atrasadas, consumo de insumo por coleta, e SHALL oferecê-los por unidade e período.

#### Scenario: Taxa de recoleta
- **WHEN** o gestor consulta a recoleta por unidade
- **THEN** vê a taxa por motivo (hemólise, volume, identificação), sem dado de paciente

### Requirement: Coleta registrada no ponto, mesmo sem conectividade
O sistema SHALL permitir registrar a coleta em estação offline, conforme `saude/sus-coleta-e-recepcao`, e SHALL sincronizar o consumo de kit e a
reconciliação quando houver conexão, sem duplicar nem perder movimento.

#### Scenario: Retorno de rota fluvial
- **WHEN** a equipe volta de uma rota sem conectividade
- **THEN** as coletas e o consumo do kit sincronizam uma só vez e a reconciliação é feita
