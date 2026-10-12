## Purpose

Enviar e receber, pelos modelos nacionais, os dados da assistência farmacêutica: estoque para a BNAFAR, dispensação e prescrição para a RNDS, com os
códigos padronizados, de modo que o município que adota este módulo cumpra a obrigação de interoperar sem depender de um sistema único.

## ADDED Requirements

### Requirement: Dispensação enviada à RNDS no modelo de dispensação
O sistema SHALL montar e enviar a dispensação ou o fornecimento de medicamento à RNDS no Registro Eletrônico de Dispensação ou Fornecimento de
Medicamentos (REDFM, Portaria GM/MS 6.100/2024), de forma idempotente, com repetição após falha, e SHALL registrar cada tentativa e o recibo. O
sistema SHALL NOT informar a entrega ao paciente como saída de estoque.

#### Scenario: Reenvio após falha
- **WHEN** o envio da dispensação falha e é repetido
- **THEN** o registro é aplicado uma só vez e as tentativas ficam registradas

### Requirement: Prescrição eletrônica recebida
O sistema SHALL receber a prescrição eletrônica pelo modelo de prescrição de medicamentos da RNDS (REPM) e vinculá-la à dispensação, e SHALL manter a
dispensação por prescrição em papel quando não houver a eletrônica.

#### Scenario: Prescrição eletrônica no balcão
- **WHEN** o usuário tem prescrição eletrônica ativa
- **THEN** o terminal a traz e vincula a dispensação a ela

### Requirement: Estoque enviado à BNAFAR
O sistema SHALL enviar à BNAFAR a posição de estoque e as saídas por movimentação entre estabelecimentos ou por perda (validade vencida e outras), nos modelos
da Portaria GM/MS 5.713/2024 (posição de estoque e saídas por movimentação ou perda), distinguindo a dispensação ao usuário, que vai pelo modelo próprio.

#### Scenario: Perda por validade
- **WHEN** um lote vence e é descartado
- **THEN** a saída por perda é enviada à BNAFAR com o lote e o motivo

### Requirement: Códigos padronizados CATMAT e OBM
O sistema SHALL identificar o medicamento pelo código CATMAT e pela Ontologia Brasileira de Medicamentos (Portaria GM/MS 6.093/2024) nos envios, e SHALL
manter pendente, sem enviar, o item sem correspondência, listando-o para curadoria.

#### Scenario: Item sem código
- **WHEN** um item dispensado não tem código CATMAT válido
- **THEN** o envio fica pendente com o motivo, e o item vai à curadoria

### Requirement: Transição do Hórus e do e-SUS Assistência Farmacêutica
O sistema SHALL operar como sistema próprio interoperável com a BNAFAR e a RNDS, e SHALL oferecer a importação de cadastros e do estoque de origem do Hórus
ou do e-SUS Assistência Farmacêutica, no formato que o Ministério publicar, sem tornar nenhum deles pré-requisito. A situação do cronograma de
transição (Hórus para e-SUS AF, prazo de interoperabilidade de 120 dias a partir de 17/02/2025 para sistemas próprios) SHALL ser verificada antes de cada
implantação.

#### Scenario: Município com sistema próprio
- **WHEN** o município adota este módulo em vez do e-SUS AF
- **THEN** o módulo envia à BNAFAR e à RNDS pelos modelos nacionais, sem depender do e-SUS AF

### Requirement: Pendências de envio visíveis e prazos acompanhados
O sistema SHALL listar os registros de dispensação, prescrição e estoque pendentes de envio, com o motivo (dado faltante, código sem correspondência, falha de
comunicação), SHALL alertar o vencimento do prazo configurado e SHALL registrar quem tratou a pendência.

#### Scenario: Registro pendente há dias
- **WHEN** uma dispensação permanece pendente além do prazo configurado
- **THEN** o alerta é aberto para o responsável da unidade

### Requirement: Dado mínimo e base legal nos envios
O sistema SHALL enviar apenas o dado exigido pelo modelo nacional e SHALL registrar no inventário de tratamento a base legal de cada envio, conforme
`saude/sus-protecao-de-dados`.

#### Scenario: Novo destinatário
- **WHEN** um novo envio é habilitado
- **THEN** exige o registro da base legal e da finalidade antes de ser ativado
