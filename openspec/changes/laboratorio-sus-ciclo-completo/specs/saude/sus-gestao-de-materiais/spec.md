## Purpose

Estender o armazém, as compras, a contabilidade pública e o despacho a todos os materiais da rede, não só aos de saúde: expediente, limpeza, copa e cozinha, informática, manutenção,
combustíveis e lubrificantes, equipamentos de proteção individual, uniformes, material de coleta e bens permanentes. Cada classe de material liga os controles que lhe cabem
(lote e validade, série, registro sanitário), de modo que o mesmo WMS sirva ao almoxarifado geral e à central de abastecimento farmacêutico.

## ADDED Requirements

### Requirement: Classes de material com perfil de controle
O sistema SHALL organizar os materiais em classes (medicamento, produto para saúde, reagente, material de coleta, material de consumo geral, equipamento de proteção individual,
combustível e lubrificante, material permanente), e SHALL associar a cada classe um **perfil de controle** que liga ou desliga: lote e validade, número de série, registro sanitário,
condição de armazenagem, fracionamento, controle especial, tombamento patrimonial e quarentena de recebimento. O perfil SHALL ser cadastrável por classe e ajustável por item.

#### Scenario: Material de expediente
- **WHEN** um item de papelaria é cadastrado na classe de material de consumo geral
- **THEN** ele não exige lote nem validade, mas segue o endereçamento, o recebimento, a requisição e o inventário

### Requirement: Catálogo do governo federal para todos os materiais
O sistema SHALL usar o catálogo de materiais do governo federal (CATMAT) para identificar **todos** os materiais, e não só os de saúde, com o código de item numérico oficial como chave e a classe, o padrão
descritivo e a situação do item vindos do catálogo. A forma `BR` + 7 dígitos SHALL ser tratada como a apresentação do código para os itens de saúde (e-SUS), e a representação dos demais SHALL ser
confirmada na fonte. O item inativo ou inexistente SHALL ser recusado como nos materiais de saúde.

#### Scenario: Item de limpeza
- **WHEN** um material de limpeza é cadastrado com o código do catálogo
- **THEN** o sistema valida o código, a classe e a situação no catálogo oficial

### Requirement: Mesma disciplina de movimento para todos os materiais
O sistema SHALL aplicar a todas as classes o livro de movimentos só de acréscimo, o recebimento em etapas com ateste, a requisição interna, o inventário cíclico, a perda com motivo, o fechamento mensal
e a avaliação do estoque do setor público, ligando apenas os controles do perfil da classe. Um controle desligado pelo perfil SHALL NOT bloquear a movimentação, e um controle ligado SHALL bloquear a falta dele.

#### Scenario: Material perecível sem validade
- **WHEN** um item de classe com validade obrigatória é recebido sem validade
- **THEN** o recebimento é recusado pelo perfil da classe

### Requirement: Bens permanentes com tombamento
O sistema SHALL tratar o material permanente com número de patrimônio (tombamento), responsável, localização e estado, mantendo-o fora do estoque de consumo e registrando a carga e a movimentação entre
responsáveis e locais. A depreciação e a reavaliação SHALL permanecer no sistema contábil do município, e o módulo SHALL entregar a ele o inventário e as movimentações.

#### Scenario: Transferência de equipamento
- **WHEN** um equipamento é transferido de uma unidade a outra
- **THEN** a movimentação exige o responsável de origem e o de destino e atualiza a localização

### Requirement: Combustíveis e itens de consumo contínuo
O sistema SHALL permitir controlar combustível e lubrificante por veículo ou embarcação, rota e período, com o consumo ligado à rota de despacho e à coleta, para conciliar o consumo com a atividade realizada, e SHALL
tratar o fornecimento por ordem de abastecimento como entrada e saída conferidas.

#### Scenario: Consumo de combustível da rota fluvial
- **WHEN** uma rota fluvial é concluída
- **THEN** o consumo de combustível lançado é comparado com o esperado para a distância e a carga

### Requirement: Equipamentos de proteção individual por pessoa
O sistema SHALL registrar a entrega de equipamento de proteção individual e de uniforme por pessoa, com o certificado de aprovação quando houver, a data, a validade e o termo de recebimento, e SHALL alertar o
vencimento e a reposição.

#### Scenario: EPI vencido
- **WHEN** a validade do EPI entregue a um profissional termina
- **THEN** o sistema alerta a reposição

### Requirement: Uma central de estoque, vários armazéns lógicos
O sistema SHALL permitir vários armazéns lógicos (central de abastecimento farmacêutico, almoxarifado geral, depósitos de unidades, laboratório) sobre a mesma base de itens, endereços e movimentos, com permissões por armazém,
fonte de recurso e responsável, e SHALL impedir que o perfil de um armazém movimente o de outro sem transferência.

#### Scenario: Atendente do almoxarifado geral
- **WHEN** um usuário do almoxarifado geral tenta dispensar medicamento
- **THEN** o acesso é negado, porque o perfil não alcança a farmácia

### Requirement: Painel e alertas por classe e armazém
O sistema SHALL apresentar o painel de situação e os alertas por classe e por armazém, filtráveis, de modo que cada gestor veja somente o que gere, e SHALL oferecer a visão consolidada ao gestor da rede.

#### Scenario: Gestor do almoxarifado geral
- **WHEN** o gestor abre o painel
- **THEN** vê as classes e armazéns sob sua gestão, sem os dados clínicos da farmácia
