## Purpose

Acoplar o módulo laboratorial ao ERPNext sem torná-lo dependente dele: profissionais vêm do cadastro do ERPNext, reagentes e lotes
do estoque dele, e o ERPNext enxerga o laboratório. A integração é um módulo à parte, que conhece os dois lados.

## ADDED Requirements

### Requirement: Núcleo sem dependência do ERPNext
O núcleo SHALL funcionar sem ERPNext instalado, e nenhum arquivo do núcleo SHALL importar ERPNext, Healthcare ou `erpnext_brasil`.
As pontes SHALL ficar em extensões nomeadas `<Aplicação>_Brasil` (por exemplo `hrms_brasil`, `healthcare_brasil` e o módulo "Integração SUS" do `erpnext_brasil`), e somente elas SHALL importá-los.

#### Scenario: Núcleo instalado sozinho
- **WHEN** o núcleo é instalado em um site sem ERPNext
- **THEN** a instalação conclui e o ciclo laboratorial funciona com cadastros próprios

### Requirement: Uma extensão por aplicação, no padrão `<Aplicação>_Brasil`
O sistema SHALL oferecer cada ponte como extensão própria, com app e título no padrão `<aplicação>_brasil` e `<Aplicação> Brasil`, instalável à parte e ativa somente quando a aplicação alvo está instalada. A ausência de uma
extensão SHALL NOT impedir o núcleo nem as demais extensões, e a instalação de uma aplicação depois da extensão SHALL ser curada por `bench migrate`, sem deixar campos inertes.

#### Scenario: Healthcare não instalado
- **WHEN** o site tem o núcleo e o HRMS, mas não o Healthcare
- **THEN** `healthcare_brasil` não é exigido, e as demais extensões funcionam

#### Scenario: Aplicação instalada depois
- **WHEN** o Healthcare é instalado depois de `healthcare_brasil`
- **THEN** o `bench migrate` cria os campos e os vínculos que ficaram de fora, sem perda

### Requirement: Profissionais vêm do cadastro de profissionais do ERPNext
O módulo de integração SHALL ler os profissionais do cadastro de funcionários do ERPNext (Employee) e SHALL criar ou atualizar, no
núcleo, a projeção mínima do profissional: nome, CPF, conselho e número de registro (por exemplo, CRBM), UF, CBO e situação. O
cadastro do ERPNext SHALL ser a fonte, e o núcleo SHALL NOT permitir editar esses dados diretamente.

#### Scenario: Profissional novo no ERPNext
- **WHEN** um funcionário com registro de conselho é cadastrado no ERPNext
- **THEN** o núcleo passa a ter o profissional, com registro e CBO, disponível para solicitar, coletar ou liberar

#### Scenario: Profissional sem registro de conselho
- **WHEN** o funcionário não tem registro de conselho
- **THEN** ele é sincronizado como não habilitado e não pode liberar nem assinar laudo

### Requirement: Desligamento no ERPNext retira a habilitação
O módulo de integração SHALL, ao desligar ou inativar o funcionário no ERPNext, marcar o profissional como inativo no núcleo. O
histórico de laudos assinados por ele SHALL permanecer intacto e verificável.

#### Scenario: Biomédico desligado
- **WHEN** um biomédico é desligado no ERPNext
- **THEN** ele não consegue liberar novos laudos, e os laudos já assinados continuam válidos

### Requirement: Estoque do ERPNext sincronizado com o WMS do laboratório
O núcleo SHALL manter o próprio estoque de reagentes e insumos (`saude/sus-estoque-de-reagentes-e-insumos`). O módulo de integração SHALL
sincronizar com o estoque do ERPNext: trazer itens, entradas de compra e lotes e validades para o recebimento do núcleo (que continua
exigindo a conferência e a quarentena), e levar ao ERPNext o consumo e os ajustes registrados pelo laboratório. O núcleo SHALL NOT usar
lote vencido ou bloqueado, qualquer que seja o saldo no ERPNext.

#### Scenario: Lote vencido
- **WHEN** o analista tenta registrar um resultado com reagente de lote vencido
- **THEN** o núcleo recusa e indica o lote

#### Scenario: Entrada de compra no ERPNext
- **WHEN** uma entrada de compra de reagente é lançada no ERPNext
- **THEN** o núcleo recebe o lote em quarentena de recebimento, aguardando a conferência do laboratório

#### Scenario: Divergência entre os dois estoques
- **WHEN** o saldo do WMS do laboratório difere do saldo do ERPNext
- **THEN** a divergência é listada para conciliação, sem sobrescrever nenhum dos dois

### Requirement: Sincronização idempotente e sem perda
O módulo de integração SHALL sincronizar de forma idempotente, repetir a tentativa após falha sem duplicar registros e registrar o
resultado de cada sincronização. A indisponibilidade do ERPNext SHALL NOT parar o ciclo laboratorial.

#### Scenario: ERPNext fora do ar
- **WHEN** o ERPNext fica indisponível durante a coleta
- **THEN** a coleta segue com a última projeção de profissionais e a sincronização é retomada depois

### Requirement: Visão do laboratório dentro do ERPNext
O módulo de integração SHALL expor ao ERPNext a produção, o consumo de reagentes e os indicadores do laboratório, sem expor dado
identificável de paciente a perfis do ERPNext sem permissão específica.

#### Scenario: Relatório de consumo
- **WHEN** o gestor consulta o consumo de reagentes no ERPNext
- **THEN** vê quantidades por exame e lote, sem nome de paciente
