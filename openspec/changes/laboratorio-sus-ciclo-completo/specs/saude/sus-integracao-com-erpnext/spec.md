## Purpose

Acoplar o módulo laboratorial ao ERPNext sem torná-lo dependente dele: profissionais vêm do cadastro do ERPNext, reagentes e lotes
do estoque dele, e o ERPNext enxerga o laboratório. A integração é um módulo à parte, que conhece os dois lados.

## ADDED Requirements

### Requirement: Núcleo sem dependência do ERPNext
O núcleo SHALL funcionar sem ERPNext instalado, e nenhum arquivo do núcleo SHALL importar ERPNext, Healthcare ou `erpnext_brasil`.
O módulo de integração SHALL ficar em pasta própria e ser o único a importá-los.

#### Scenario: Núcleo instalado sozinho
- **WHEN** o núcleo é instalado em um site sem ERPNext
- **THEN** a instalação conclui e o ciclo laboratorial funciona com cadastros próprios

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

### Requirement: Reagentes e lotes do estoque do ERPNext
O módulo de integração SHALL oferecer ao núcleo os itens de reagente, calibrador e controle e seus lotes e validades, a partir do
estoque do ERPNext, e SHALL baixar o consumo registrado pelo laboratório. O núcleo SHALL registrar o lote usado em cada resultado e
SHALL NOT usar lote vencido ou bloqueado.

#### Scenario: Lote vencido
- **WHEN** o analista tenta registrar um resultado com reagente de lote vencido
- **THEN** o núcleo recusa e indica o lote

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
