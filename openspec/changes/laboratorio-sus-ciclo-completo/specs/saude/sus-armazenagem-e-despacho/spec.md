## Purpose

Operar o almoxarifado e a central de abastecimento farmacêutico como um armazém de verdade, segundo as boas práticas internacionais de armazenagem e
distribuição (OMS, União Europeia) e a norma brasileira de boas práticas de distribuição e armazenagem de medicamentos: zonas, endereçamento, etiquetas,
armazenagem e separação guiadas, painel de situação em tempo real e despacho às micro unidades de saúde com comprovação de entrega.

## ADDED Requirements

### Requirement: Zonas de armazenagem segregadas
O sistema SHALL organizar o armazém em zonas com condição e finalidade definidas: ambiente, refrigerada, congelada, controlados (acesso restrito), recebimento,
**quarentena**, **reprovados, vencidos e recolhidos**, devolução, expedição e área de separação. Um lote SHALL ocupar apenas endereço de zona compatível com seu estado e
sua condição de armazenagem, e o lote em quarentena, vencido ou recolhido SHALL ficar fisicamente na zona segregada.

#### Scenario: Lote recolhido em endereço comum
- **WHEN** um lote passa a recolhido e ainda está em endereço da zona ambiente
- **THEN** o sistema gera a tarefa de mover o lote à zona segregada e o mantém bloqueado até a conclusão

### Requirement: Endereçamento hierárquico com identificação padronizada
O sistema SHALL endereçar o armazém em níveis (armazém, zona, corredor, estante ou rack, nível, posição) com código legível por leitor, e SHALL permitir
identificar o local pelo número global de localização GS1 (GLN) quando o ente o adotar. Um endereço SHALL NOT ser reaproveitado com outro significado, e a
capacidade e a condição de cada endereço SHALL ser cadastradas.

#### Scenario: Endereço de capacidade esgotada
- **WHEN** o estoquista tenta guardar quantidade acima da capacidade do endereço
- **THEN** o sistema recusa e propõe outro endereço compatível

### Requirement: Etiquetas do armazém
O sistema SHALL imprimir etiquetas legíveis por leitor para: endereço (corredor, estante, nível, posição), unidade logística ou palete com identificador GS1 (SSCC), caixa
de separação, volume de expedição (com unidade de destino, rota e condição de transporte), lote em quarentena (cor e texto "NÃO USAR"), lote recolhido, produto fracionado e
área segregada. As etiquetas SHALL usar Code 128 ou GS1-128 para identificação linear e Data Matrix para espaço reduzido, em português, indeléveis, sem dado pessoal de paciente.

#### Scenario: Etiqueta de volume de expedição
- **WHEN** um volume é fechado para despacho
- **THEN** a etiqueta traz o destino, a rota, a condição de transporte e o código do volume

### Requirement: Armazenagem guiada
O sistema SHALL guiar o estoquista na armazenagem (guardar o item recebido): propor o endereço pela zona, pela condição, pelo giro e pela capacidade, exigir a leitura do
item, do lote e do endereço para confirmar, e registrar o movimento. Divergência entre o proposto e o escolhido SHALL exigir justificativa.

#### Scenario: Endereço lido diferente do proposto
- **WHEN** o estoquista guarda em endereço diferente do proposto
- **THEN** o sistema pede a justificativa e confere a compatibilidade de zona

### Requirement: Separação guiada para o estoquista
O sistema SHALL gerar, para cada separação, uma **guia automatizada** ao estoquista: a lista ordenada pelo caminho mais curto no armazém, o endereço, o lote sugerido por FEFO,
a quantidade, a unidade de medida e a embalagem, com confirmação por leitura do endereço e do produto e alerta de erro imediato quando o item ou o lote estiver errado. O sistema SHALL
tratar a falta de saldo (separação curta) com reposição de outro endereço ou lote, ou com registro da falta e aviso à unidade, sem ajustar o saldo em silêncio.

#### Scenario: Produto lido errado
- **WHEN** o estoquista lê um produto diferente do indicado na guia
- **THEN** o terminal bloqueia a confirmação e indica o item e o endereço corretos

### Requirement: Ondas de separação por rota e prioridade
O sistema SHALL agrupar as requisições das micro unidades em ondas de separação por rota, janela de entrega e prioridade (urgência antes de rotina, itens de cadeia de frio no fim da
separação), SHALL liberar a onda conforme a capacidade da equipe e SHALL permitir reabastecer o endereço de separação a partir do estoque de reserva.

#### Scenario: Requisição urgente
- **WHEN** chega uma requisição urgente com a onda em andamento
- **THEN** o sistema a insere à frente na próxima liberação e avisa o líder

### Requirement: Conferência e embalagem antes do despacho
O sistema SHALL exigir a conferência do volume (leitura de cada item e lote contra a requisição), SHALL escolher a embalagem pela condição de transporte (isotérmica com material refrigerante para
itens refrigerados, conforme a validação do tempo de rota), SHALL fechar o volume com etiqueta e SHALL registrar o responsável.

#### Scenario: Volume refrigerado
- **WHEN** a requisição inclui item refrigerado
- **THEN** o sistema exige a embalagem isotérmica validada e o registro do material refrigerante

### Requirement: Despacho às micro unidades de saúde por rota
O sistema SHALL organizar o despacho às micro unidades (UBS, postos e unidades de distritos e comunidades, inclusive rotas fluviais) por rota, veículo ou embarcação, motorista e janela, com a lista de
volumes por parada, a guia de remessa e a estimativa de tempo, e SHALL comparar o tempo de rota com a estabilidade dos itens de cadeia de frio, alertando quando não couber.

#### Scenario: Rota fluvial longa com item refrigerado
- **WHEN** o tempo estimado da rota excede o tempo validado da embalagem do item refrigerado
- **THEN** o sistema alerta, e sugere outra embalagem, outra rota ou a entrega prioritária desse item

### Requirement: Comprovação de entrega na unidade
O sistema SHALL registrar a entrega em cada micro unidade por leitura dos volumes, conferência de quantidade, lote e condição (incluindo temperatura de chegada quando exigida), assinatura ou
código do recebedor identificado e horário, e SHALL tratar falta, avaria ou volume a mais como ocorrência, mantendo a custódia em trânsito até a conferência na unidade.

#### Scenario: Volume faltante
- **WHEN** a unidade confere a entrega e falta um volume
- **THEN** a ocorrência é aberta, a custódia do volume continua com o transportador e o almoxarifado é avisado

### Requirement: Painel de situação em tempo real
O sistema SHALL oferecer um painel de situação, atualizado sem recarregar a tela e responsivo, com: nível de estoque por item e unidade, itens com risco de ruptura, lotes a vencer em prazos
configuráveis, quarentena e recolhimentos abertos, estado da cadeia de frio (temperatura, alarmes, excursões), requisições pendentes e atrasadas, progresso das ondas de separação,
rotas em andamento com a previsão de chegada, entregas pendentes de conferência e ocorrências abertas. Cada indicador SHALL levar à lista de origem.

#### Scenario: Alarme de temperatura
- **WHEN** uma geladeira excede a faixa
- **THEN** o painel mostra o alarme em destaque e leva aos lotes afetados

### Requirement: Alertas e escalonamento operacional
O sistema SHALL alertar o responsável por ruptura iminente, lote próximo do vencimento, quarentena parada, recolhimento aberto, entrega atrasada, excursão de temperatura e divergência de
inventário, com escalonamento por prazo, e SHALL registrar o tratamento.

#### Scenario: Entrega atrasada
- **WHEN** uma rota passa do horário previsto de chegada
- **THEN** o alerta é aberto para o responsável e a unidade é avisada

### Requirement: Mapeamento térmico e qualificação das áreas
O sistema SHALL registrar o mapeamento de temperatura (e, quando exigida, umidade) das áreas e equipamentos de armazenagem, com data, resultado, pontos críticos e validade, SHALL exigir
nova qualificação após mudança de local, manutenção do compressor ou alteração relevante, e SHALL impedir o endereçamento de item termossensível em área sem qualificação vigente. O
protocolo de mapeamento (duração mínima, pontos de sensor) SHALL seguir a referência adotada pelo serviço (OMS), a confirmar.

#### Scenario: Qualificação vencida
- **WHEN** a qualificação térmica de uma câmara vence
- **THEN** o sistema impede novos endereçamentos termossensíveis nela e alerta o responsável

### Requirement: Inventário cíclico guiado
O sistema SHALL guiar a contagem cíclica por endereço, priorizando itens de maior valor, controlados, de maior giro e de maior divergência anterior, com a contagem às cegas (sem mostrar o
saldo esperado) e a recontagem de divergência acima da tolerância.

#### Scenario: Contagem às cegas
- **WHEN** o estoquista inicia a contagem de um endereço
- **THEN** o terminal não mostra o saldo esperado

### Requirement: Normas de referência declaradas e verificáveis
O sistema SHALL registrar, na configuração do armazém, as normas de referência adotadas (boas práticas de armazenagem e distribuição da OMS, as diretrizes de distribuição da
União Europeia e a norma brasileira de boas práticas de distribuição, armazenagem e transporte de medicamentos), com a versão e a data de leitura, e SHALL listar os controles do
módulo que atendem a cada exigência, para auditoria. A aplicabilidade das normas à distribuição interna da rede pública SHALL ser parâmetro a confirmar com a vigilância sanitária.

#### Scenario: Auditoria sanitária
- **WHEN** a vigilância sanitária pede a evidência de um requisito de armazenagem
- **THEN** o módulo lista os controles e registros que o atendem
