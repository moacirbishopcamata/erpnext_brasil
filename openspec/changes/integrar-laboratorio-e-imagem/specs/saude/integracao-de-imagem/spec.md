## Purpose

Ligar o pedido de exame de imagem ao equipamento e ao estudo no PACS sem guardar imagens no ERPNext, com a mesma regra de
segurança do laboratório: o estudo só se liga ao pedido quando os identificadores casam, e o que não casa fica em quarentena.

## ADDED Requirements

### Requirement: Pedido de imagem publicado na lista de trabalho da modalidade

O sistema MUST publicar cada pedido de exame de imagem na lista de trabalho da modalidade com o identificador do paciente e o
número de acesso do pedido, e MUST retirar da lista o pedido cancelado.

#### Scenario: Pedido novo

- **WHEN** um exame de imagem é solicitado e agendado
- **THEN** a modalidade encontra o pedido na lista de trabalho com o identificador do paciente e o número de acesso

#### Scenario: Pedido cancelado

- **WHEN** o pedido é cancelado antes da execução
- **THEN** ele deixa de constar na lista de trabalho

### Requirement: Estudo ligado ao pedido por identificadores, imagens no PACS

O sistema MUST guardar o vínculo entre o pedido e o estudo (identificador do estudo) e MUST NOT armazenar os pixels das
imagens; o acesso às imagens MUST ocorrer pelo PACS ou visualizador, respeitando as permissões do usuário.

#### Scenario: Estudo executado

- **WHEN** a modalidade conclui o estudo e o PACS o recebe
- **THEN** o pedido passa a "realizado" e guarda o identificador do estudo

### Requirement: Estudo que não casa vai para quarentena

O sistema MUST NOT ligar a um pedido o estudo cujo identificador de paciente ou número de acesso não coincida; o estudo MUST
ir para uma fila de pendências para decisão humana, com registro.

#### Scenario: Número de acesso desconhecido

- **WHEN** chega a notificação de um estudo com número de acesso sem pedido correspondente
- **THEN** o estudo fica em quarentena e nenhum pedido é alterado

### Requirement: Estado do exame sincronizado de forma idempotente

As notificações de estado vindas da modalidade ou do PACS MUST ser aplicadas de forma idempotente e ordenada, e uma
notificação repetida MUST NOT alterar o estado nem criar registro novo.

#### Scenario: Notificação repetida

- **WHEN** a mesma notificação de conclusão chega duas vezes
- **THEN** o estado do pedido permanece o mesmo, e a repetição fica registrada

### Requirement: Laudo de imagem referencia o estudo e é rastreável

O laudo de imagem MUST referenciar o estudo, MUST seguir as mesmas regras de liberação, assinatura e retificação do laudo
laboratorial, e o acesso ao estudo MUST ficar registrado.

#### Scenario: Retificação de laudo de imagem

- **WHEN** um laudo de imagem já emitido é corrigido
- **THEN** a correção é um novo laudo que identifica a retificação e mantém o original
