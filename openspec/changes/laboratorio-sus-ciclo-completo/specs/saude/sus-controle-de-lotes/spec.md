## Purpose

Controlar com rigor o lote de medicamentos, insumos médicos (produtos para saúde) e reagentes, pela identificação internacional GS1 e pela
identificação única de dispositivos (UDI) que a ANVISA adotou, de modo que cada unidade, cada paciente e cada resultado seja rastreável ao
lote, e que um lote suspeito ou recolhido seja bloqueado em todo o município no mesmo instante. A regra é do núcleo; as obrigações da
norma ainda em implantação são parâmetros ativáveis.

## ADDED Requirements

### Requirement: Lote como registro de primeira classe
O sistema SHALL representar cada lote com: item (código CATMAT e GTIN), número do lote do fabricante, validade, fabricante, número de registro
ou notificação na ANVISA, data de fabricação quando houver, número de série quando houver e, para produto para saúde, o identificador único
(UDI-DI e UDI-PI). O sistema SHALL NOT permitir movimentar, dispensar ou usar item sem lote identificado.

#### Scenario: Entrada sem lote
- **WHEN** alguém tenta receber um item sem informar o lote e a validade
- **THEN** o recebimento é recusado

### Requirement: Leitura do código GS1 no recebimento, movimento e dispensação
O sistema SHALL interpretar o código GS1 DataMatrix ou GS1-128 lido, extraindo os identificadores de aplicação de GTIN (01), lote (10), validade
(17) e número de série (21), SHALL validar o dígito de conferência do GTIN e SHALL preencher o lote por essa leitura, recusando a digitação
manual do lote quando o código estiver legível. Leitura incompleta ou inconsistente SHALL ir à pendência, nunca ser completada por suposição.

#### Scenario: GTIN com dígito errado
- **WHEN** o GTIN lido não passa na validação do dígito de conferência
- **THEN** a leitura é recusada e o lote não é criado nem movimentado

### Requirement: Estados do lote sem salto
O sistema SHALL manter o lote nos estados **quarentena**, **liberado**, **bloqueado**, **recolhido**, **vencido** e **esgotado**, com tabela de
transições permitidas. Somente o lote **liberado** e dentro da validade SHALL ser dispensado ou usado, e uma transição fora da tabela SHALL ser
recusada.

#### Scenario: Lote em quarentena
- **WHEN** alguém tenta dispensar item de lote em quarentena
- **THEN** a dispensação é recusada e o estado do lote é informado

### Requirement: Recebimento conferido contra a nota e a etiqueta
O sistema SHALL conferir no recebimento o lote, a validade e a quantidade lidos no código contra o documento de origem (nota ou guia), e SHALL
mandar o lote à quarentena quando houver divergência, embalagem violada, validade restante abaixo do mínimo configurado, ou item sem o registro da
ANVISA. A liberação SHALL exigir usuário autorizado e registrar a decisão.

#### Scenario: Validade abaixo do mínimo
- **WHEN** o lote chega com validade restante menor que o mínimo configurado
- **THEN** o lote vai à quarentena, e a liberação exige decisão registrada

### Requirement: Rastreabilidade nos dois sentidos
O sistema SHALL responder, em tempo hábil, por lote: de onde veio e para onde foi (unidades, endereços, pacientes dispensados, resultados e
consumo); e, por paciente: quais lotes recebeu. A consulta SHALL cobrir medicamentos, produtos para saúde e reagentes.

#### Scenario: Lote apontado como defeituoso
- **WHEN** o responsável consulta um lote
- **THEN** vê todas as unidades com saldo, os pacientes que o receberam e os resultados em que foi usado

### Requirement: Recolhimento bloqueia o lote em todo o município de uma vez
O sistema SHALL registrar uma ação de recolhimento (determinada pela ANVISA, pelo detentor do registro ou por decisão local) e SHALL, no mesmo
instante, colocar o lote em estado **recolhido** em todas as unidades, impedir dispensação e uso, listar os saldos a segregar e as pessoas que o
receberam, e acompanhar a retirada e a devolução em quarentena até o encerramento. A comunicação ao paciente SHALL respeitar a proteção de dados e
seguir a orientação do responsável. Os prazos e relatórios exigidos pela norma de recolhimento vigente (RDC 625/2022, a confirmar) SHALL ser
parâmetros.

#### Scenario: Recolhimento registrado
- **WHEN** o recolhimento de um lote é registrado
- **THEN** a dispensação do lote é impedida em todas as unidades imediatamente, e a lista de saldos e destinatários é gerada

### Requirement: Primeiro a vencer, primeiro a sair com validade mínima de uso
O sistema SHALL aplicar FEFO a medicamentos e insumos e SHALL impedir a dispensação de lote cuja validade restante não cubra o período de uso previsto
(parâmetro por item), exigindo justificativa do farmacêutico para exceção.

#### Scenario: Validade curta para tratamento longo
- **WHEN** o tratamento prescrito dura mais que a validade restante do lote
- **THEN** o sistema sugere outro lote e exige justificativa para manter o atual

### Requirement: Serialização quando disponível
O sistema SHALL registrar o número de série (e, para medicamentos, o identificador único do medicamento do SNCM, que reúne GTIN, registro, série, validade
e lote) quando presente no código, SHALL detectar série repetida ou já dispensada, e SHALL ativar a verificação obrigatória de serialização apenas
por parâmetro, porque a obrigação de serialização de medicamentos teve a implantação alterada e a situação vigente é **a confirmar** (a base é a Lei 11.903/2009,
alterada pela Lei 13.410/2016; as fontes divergem entre a RDC 157/2017 e a RDC 319/2019 como norma do SNCM). A NF-e `rastro` (obrigação fiscal) e o SNCM (obrigação sanitária) SHALL ser registros
independentes, nenhum alimentando o outro.

#### Scenario: Série já dispensada
- **WHEN** o número de série lido já consta como dispensado
- **THEN** a leitura é recusada e uma ocorrência de possível duplicidade ou falsificação é aberta

### Requirement: Identificação única de produtos para saúde
O sistema SHALL registrar, para produto para saúde, o UDI-DI (identificador do dispositivo) e o UDI-PI (série, lote, fabricação e validade) conforme a
RDC 591/2021 e suas alterações, e SHALL aceitar produto cujo rótulo ainda não tenha UDI conforme o escalonamento por classe de risco vigente,
registrando a ausência. A transmissão à base de dados UDI da ANVISA SHALL ficar parametrizada até a norma que a ativa estar vigente.

#### Scenario: Produto classe IV sem UDI após o prazo
- **WHEN** um produto de classe de risco IV fabricado após o prazo de rotulagem chega sem UDI
- **THEN** o lote vai à quarentena com o motivo, para decisão do responsável

### Requirement: Queixa técnica e evento adverso ligados ao lote
O sistema SHALL permitir abrir uma ocorrência de queixa técnica ou evento adverso ligada ao lote, item e, quando houver, paciente, reunindo os dados
necessários para o profissional notificar a vigilância sanitária (NOTIVISA), sem notificar por conta própria, e SHALL oferecer o bloqueio preventivo do
lote enquanto a ocorrência é investigada.

#### Scenario: Queixa técnica
- **WHEN** a farmácia registra defeito de um medicamento
- **THEN** a ocorrência liga ao lote e oferece o bloqueio preventivo, e o profissional decide e notifica

### Requirement: Lote imutável e corrigido por ajuste
O sistema SHALL tornar os dados de identificação do lote (item, número, validade, fabricante) imutáveis após o primeiro movimento, e SHALL tratar
correção como novo registro com referência, nunca como edição. Os movimentos do lote SHALL formar cadeia verificável por hash.

#### Scenario: Correção de validade
- **WHEN** a validade de um lote movimentado foi digitada errada
- **THEN** a correção é um registro novo que referencia o original e exige aprovação

### Requirement: Inventário e divergência por lote
O sistema SHALL contar o estoque por lote e endereço, SHALL tratar divergência de lote (lote diferente do esperado na posição) como ocorrência, e SHALL
bloquear o lote divergente até a conferência.

#### Scenario: Lote trocado na prateleira
- **WHEN** a contagem encontra lote diferente do registrado na posição
- **THEN** o lote é bloqueado, uma ocorrência é aberta e a posição é conferida
