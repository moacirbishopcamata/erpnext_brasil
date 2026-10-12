## Purpose

Fazer o estoque de medicamentos, insumos médicos e reagentes respeitar a contabilidade e o fiscal da administração pública municipal: empenho, recebimento,
ateste e liquidação em sequência, avaliação do estoque pelos critérios do setor público, fontes de recurso, fechamento mensal e inventário, entregando as
evidências ao sistema contábil do município (SIAFIC) sem tentar substituí-lo. As escolhas que variam por município são parâmetros a confirmar com a
contabilidade e o controle interno.

## ADDED Requirements

### Requirement: Recebimento alimenta a liquidação, sem a substituir
O sistema SHALL tratar o recebimento definitivo atestado como evidência do estágio de **liquidação** da despesa (conferência do direito do credor pelo contrato ou
ata, nota de empenho e comprovante de entrega), SHALL registrar empenho, nota fiscal, ateste e data para o sistema contábil, e SHALL NOT executar a execução
orçamentária (empenho, liquidação e pagamento), que permanece no SIAFIC do município. Nota sem recebimento atestado SHALL constar como não liquidável.

#### Scenario: Nota sem ateste
- **WHEN** existe nota fiscal sem recebimento definitivo atestado
- **THEN** o relatório aponta a nota como não liquidável, com o motivo

### Requirement: Ateste por servidor designado
O sistema SHALL permitir o ateste somente a servidor formalmente designado como fiscal do contrato, da ata de registro de preços ou do recebimento, SHALL registrar o ato
de designação (número e data) e SHALL impedir que o mesmo usuário solicite, receba, ateste e pague, aplicando segregação de funções entre as etapas.

#### Scenario: Usuário não designado
- **WHEN** um usuário sem designação tenta atestar uma nota
- **THEN** o ateste é recusado

### Requirement: Fonte de recurso e componente de financiamento por lote
O sistema SHALL registrar, em cada entrada e em cada lote, a fonte de recurso e o componente de financiamento (por exemplo, recurso próprio do município, repasse
federal fundo a fundo, Componente Básico, Componente Estratégico, Hospitalar Municipal), SHALL manter o saldo por fonte e componente, e SHALL registrar o consumo contra a
fonte de origem do lote.

#### Scenario: Consumo de lote do componente estratégico
- **WHEN** um lote do Componente Estratégico é dispensado
- **THEN** o consumo é registrado contra esse componente e essa fonte

### Requirement: Natureza da despesa por item como parâmetro
O sistema SHALL ligar cada item a uma natureza de despesa (elemento de despesa) configurável, distinguindo ao menos o material de consumo e o material de distribuição
gratuita, conforme o plano de contas e o decreto de classificação do município, SHALL emitir essa classificação nos dados enviados à contabilidade e SHALL NOT
presumir o elemento: a atribuição inicial exige confirmação da contabilidade.

#### Scenario: Item sem natureza de despesa
- **WHEN** um item entra no estoque sem natureza de despesa definida
- **THEN** a entrada fica pendente de classificação pela contabilidade

### Requirement: Avaliação do estoque pelo critério do setor público
O sistema SHALL avaliar o estoque pelo **custo médio ponderado** ou pelo **primeiro que entra, primeiro que sai (PEPS)**, com **um critério único por classe de itens
de uso e natureza semelhantes**, SHALL NOT oferecer o critério último que entra, primeiro que sai, e SHALL compor o custo com o preço de compra, os tributos
irrecuperáveis, o transporte, o seguro e o manuseio atribuíveis. A mensuração SHALL observar o menor valor entre o custo e o valor realizável líquido, e, para item distribuído
gratuitamente, o menor entre o custo histórico e o custo corrente de reposição.

#### Scenario: Mudança de critério
- **WHEN** a contabilidade troca o critério de uma classe
- **THEN** a mudança vale a partir do período indicado, com registro e sem reescrever os períodos fechados

### Requirement: Reconhecimento por tipo de movimento
O sistema SHALL classificar cada movimento para a contabilidade patrimonial: a compra para estoque aumenta o estoque sem efeito no patrimônio líquido, o consumo ou a
dispensação reconhece a variação patrimonial diminutiva, a perda (vencimento, avaria, furto) reconhece a perda com o motivo, a doação ou remessa recebida (como a do
Componente Estratégico) entra como aumento patrimonial pelo valor de referência, e a devolução ao fornecedor estorna a entrada. A tabela de contas SHALL ser parâmetro do município.

#### Scenario: Dispensação
- **WHEN** um item é dispensado
- **THEN** o movimento gera o reconhecimento do consumo no período, pelo custo apurado

### Requirement: Doação e remessa de outro ente
O sistema SHALL receber medicamento e insumo doado ou remetido por outro ente (Ministério da Saúde, Estado) sem empenho, mediante nota ou termo, com valor de referência, fonte
e componente, aplicando a conferência de recebimento, a quarentena e o controle de lote como na compra.

#### Scenario: Remessa do Ministério
- **WHEN** chega uma remessa do Componente Estratégico com nota
- **THEN** a entrada é conferida e registrada sem empenho, com a fonte e o componente

### Requirement: Fechamento mensal imutável com conciliação
O sistema SHALL fechar o estoque por mês, gerando o relatório de movimentação com saldo anterior, entradas, saídas e saldo final por classe e conta, SHALL conciliar o saldo
do estoque com o saldo contábil, SHALL impedir lançamento em período fechado e SHALL tratar a correção posterior como ajuste no período aberto, com referência.

#### Scenario: Movimento retroativo
- **WHEN** alguém tenta lançar movimento em mês já fechado
- **THEN** o lançamento é recusado, e a correção segue como ajuste no período aberto

### Requirement: Inventário com comissão e termos
O sistema SHALL realizar o inventário anual e o de mudança de responsável por comissão designada, com contagem por lote e endereço, termo de responsabilidade do
guardião do estoque, tratamento da divergência (sobra, falta, avaria) com apuração e sem ajuste silencioso, e relatório assinado.

#### Scenario: Falta apurada
- **WHEN** o inventário encontra falta de um item
- **THEN** a apuração é aberta, e a baixa só ocorre com motivo e aprovação

### Requirement: Entrega de lançamentos ao SIAFIC
O sistema SHALL exportar ao sistema contábil do município os lançamentos do estoque (entradas com empenho e nota, atestes, consumo, perdas, doações, ajustes e fechamento) em
layout parametrizável, de forma idempotente e com recibo, e SHALL conferir se o empenho citado existe e tem saldo no sistema contábil quando houver interface. O módulo
SHALL NOT criar um segundo sistema contábil do município.

#### Scenario: Reenvio de lançamentos
- **WHEN** o envio dos lançamentos falha e é repetido
- **THEN** cada lançamento é aplicado uma só vez

### Requirement: Dados para prestação de contas e transparência
O sistema SHALL gerar os dados de estoque, compras e consumo para o tribunal de contas competente e para o portal da transparência do município, sem dado pessoal de paciente e no
formato que o órgão exigir (a confirmar), com a rastreabilidade do documento de origem.

#### Scenario: Relatório de consumo por medicamento
- **WHEN** a transparência publica o consumo por medicamento
- **THEN** o relatório traz itens e quantidades, sem identificar paciente

### Requirement: Documento fiscal da administração pública conferido
O sistema SHALL conferir que o destinatário da NF-e de entrada é a entidade correta (fundo ou secretaria), que o emitente é o fornecedor do empenho, e que os valores batem com o empenho,
e SHALL deixar as retenções de tributos na liquidação e no pagamento fora do escopo do estoque.

#### Scenario: Destinatário diferente do empenho
- **WHEN** a NF-e tem destinatário que não corresponde à entidade do empenho
- **THEN** a entrada é recusada com o motivo
