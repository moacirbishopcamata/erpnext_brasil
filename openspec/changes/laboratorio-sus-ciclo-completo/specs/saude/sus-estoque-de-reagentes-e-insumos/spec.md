## Purpose

Controlar reagentes, calibradores, controles e insumos de coleta como um armazém (WMS) próprio do laboratório: endereçamento físico,
lote e validade, cadeia de frio, consumo por exame, ressuprimento e inventário, de modo que nenhum resultado seja produzido com insumo
vencido, bloqueado ou fora de condição, e que cada lote seja rastreável até os resultados em que foi usado.

## ADDED Requirements

### Requirement: Catálogo de insumos com condições de armazenamento
O sistema SHALL manter o catálogo de insumos (reagente, calibrador, controle, material de coleta, etiqueta e consumível) com unidade,
condição de armazenamento (ambiente, refrigerado, congelado, protegido da luz), faixa de temperatura, validade, estabilidade após
abertura e o consumo por exame ou por kit, quando aplicável.

#### Scenario: Reagente refrigerado
- **WHEN** um reagente é cadastrado com armazenamento refrigerado
- **THEN** ele só pode ser endereçado em equipamento de armazenamento compatível com essa faixa de temperatura

### Requirement: Endereçamento físico hierárquico
O sistema SHALL representar o armazenamento por hierarquia de endereços: estabelecimento, sala ou almoxarifado, equipamento de
armazenamento (geladeira, freezer, armário), prateleira ou gaveta e posição. Cada lote em estoque SHALL ter endereço, e o saldo por
endereço SHALL ser derivado dos movimentos.

#### Scenario: Lote sem endereço
- **WHEN** um lote é recebido e ainda não tem endereço
- **THEN** ele fica em área de recebimento, não disponível para uso, até ser endereçado

### Requirement: Recebimento conferido com quarentena
O sistema SHALL registrar o recebimento com documento de origem, item, lote, validade, quantidade, temperatura de chegada quando exigida,
integridade da embalagem e certificado quando houver, e SHALL manter o lote em quarentena de recebimento até a liberação por usuário
autorizado. Recebimento fora das condições SHALL ser recusado ou segregado com ocorrência registrada.

#### Scenario: Reagente refrigerado que chegou quente
- **WHEN** a temperatura de chegada de um reagente refrigerado está fora da faixa
- **THEN** o lote é segregado, uma ocorrência é aberta e ele não é liberado para uso

### Requirement: Primeiro a vencer, primeiro a sair
O sistema SHALL sugerir o lote de menor validade disponível (FEFO) ao separar um insumo para uso e SHALL exigir justificativa para usar
um lote de validade mais distante quando existir lote mais próximo do vencimento disponível.

#### Scenario: Dois lotes do mesmo reagente
- **WHEN** o analista solicita o reagente e há dois lotes disponíveis
- **THEN** o sistema propõe o de validade mais próxima

### Requirement: Insumo vencido ou bloqueado nunca é usado
O sistema SHALL impedir o uso de lote vencido, em quarentena ou bloqueado, e SHALL NOT permitir a revalidação de insumo depois de
expirada a validade. A estabilidade após abertura SHALL ser registrada pela data de abertura e pela nova validade, e o uso depois dela
SHALL ser impedido.

#### Scenario: Frasco aberto além da estabilidade
- **WHEN** o analista tenta usar um frasco aberto cuja estabilidade após abertura terminou
- **THEN** o uso é impedido e o frasco é segregado para descarte

### Requirement: Consumo registrado por exame e lote
O sistema SHALL baixar o consumo de insumo por exame realizado, controle e calibração, registrando o lote usado, e SHALL ligar o lote ao
resultado. O consumo SHALL ser estimado pela cota do exame e conferido contra o consumo real na contagem.

#### Scenario: Exame realizado
- **WHEN** um exame é realizado no equipamento
- **THEN** o consumo do reagente e o lote ficam registrados e ligados ao resultado

### Requirement: Cadeia de frio monitorada com ação automática
O sistema SHALL receber o registro de temperatura dos equipamentos de armazenamento (sensor ou digitação conferida em intervalos
definidos) e, em caso de excursão fora da faixa, SHALL colocar em quarentena os lotes armazenados naquele equipamento, abrir alerta e exigir
a avaliação do responsável antes de qualquer uso.

#### Scenario: Excursão de temperatura em geladeira
- **WHEN** a geladeira registra temperatura acima da faixa por mais que o tempo tolerado
- **THEN** os lotes ali endereçados vão à quarentena e o responsável é alertado

### Requirement: Ressuprimento por mínimo e por demanda
O sistema SHALL calcular o ressuprimento por estoque mínimo, ponto de pedido e consumo previsto a partir dos exames solicitados e do
histórico, descontando o que vence antes do uso, e SHALL alertar o risco de ruptura que impeça a realização de um exame.

#### Scenario: Risco de ruptura
- **WHEN** o saldo utilizável de um reagente não cobre os exames solicitados nos próximos dias
- **THEN** o sistema alerta o risco de ruptura e sugere a quantidade a repor

### Requirement: Inventário cíclico com divergência tratada
O sistema SHALL permitir a contagem cíclica por endereço, SHALL registrar a divergência entre o contado e o saldo e SHALL exigir motivo e
aprovação para o ajuste, mantendo o movimento de ajuste no livro de estoque.

#### Scenario: Saldo divergente
- **WHEN** a contagem difere do saldo
- **THEN** o ajuste só ocorre com motivo e aprovação, e o movimento fica registrado

### Requirement: Livro de estoque só de acréscimo
O sistema SHALL registrar todo movimento (recebimento, endereçamento, transferência, consumo, ajuste, descarte) em livro só de acréscimo,
com usuário, data, hora e local, e SHALL derivar os saldos desse livro, sem editar saldo diretamente.

#### Scenario: Correção de saldo
- **WHEN** um saldo precisa ser corrigido
- **THEN** a correção é um movimento de ajuste, e o saldo anterior continua reconstituível

### Requirement: Transferência entre endereços e unidades com conferência
O sistema SHALL permitir transferir lotes entre endereços e entre unidades por lista de separação, com leitura do código do lote na saída e
na chegada e estado em trânsito. A interface SHALL permitir mover o lote por arrastar e soltar, em que o destino define a ação: outro endereço
transfere, a área de descarte descarta com confirmação e motivo, e a quarentena bloqueia.

#### Scenario: Soltar o lote na área de descarte
- **WHEN** o usuário solta um lote na área de descarte
- **THEN** o sistema pede o motivo e a confirmação, e só então registra o descarte

### Requirement: Segregação e descarte de vencidos
O sistema SHALL segregar o insumo vencido ou próximo do vencimento fora das áreas de análise, listá-lo para descarte conforme o plano de
gerenciamento de resíduos do serviço, e registrar o descarte com responsável e destino.

#### Scenario: Lote vencido no armazém
- **WHEN** a validade de um lote termina
- **THEN** ele é bloqueado, listado para descarte e movido à área de segregação

### Requirement: Kits e controle de lote com verificação entre lotes
O sistema SHALL tratar kit como conjunto de componentes com lotes próprios, SHALL permitir exigir a verificação de desempenho na troca de
lote de reagente (resultado de controle aprovado) antes de liberar o novo lote para uso e SHALL registrar essa liberação.

#### Scenario: Troca de lote de reagente
- **WHEN** um novo lote de reagente é posto em uso
- **THEN** o sistema exige a aprovação do controle de qualidade do novo lote antes de liberar resultados de paciente com ele

### Requirement: Estoque do laboratório independente do ERPNext
O sistema SHALL operar o estoque de reagentes e insumos sem ERPNext, e a integração com o estoque do ERPNext SHALL ser feita pelo módulo
de integração, sincronizando itens, entradas e consumo sem tornar o ERPNext fonte obrigatória.

#### Scenario: Módulo sem ERPNext
- **WHEN** o módulo opera sem ERPNext
- **THEN** o recebimento, o endereçamento, o consumo e o inventário de reagentes funcionam normalmente
