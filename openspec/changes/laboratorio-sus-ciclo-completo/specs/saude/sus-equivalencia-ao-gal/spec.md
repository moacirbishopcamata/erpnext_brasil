## Purpose

Fazer, dentro do módulo, o que o GAL faz hoje para o laboratório público de biologia médica humana: cadastros, requisição de exame
entre unidades, recepção e triagem, gerência de exames, resultado e laudo, rastreio, estatísticas e vigilância, com um caminho de
transição enquanto os LACENs ainda usam o GAL. O escopo inicial exclui os módulos animal e ambiental.

## ADDED Requirements

### Requirement: Cadastro de estabelecimentos e usuários
O sistema SHALL manter o cadastro de estabelecimentos (CNES, município, tipo, laboratório de referência) e de usuários com perfil por
função e unidade. Um usuário SHALL ser criado por pedido registrado e SHALL aceitar termo de confidencialidade antes do primeiro
acesso.

#### Scenario: Usuário novo
- **WHEN** um usuário é criado
- **THEN** ele só acessa após aceitar o termo de confidencialidade

### Requirement: Requisição de exame entre unidades
O sistema SHALL permitir à unidade solicitante cadastrar a requisição **antes** de enviar a amostra, indicando o laboratório destino,
e SHALL exigir todos os campos obrigatórios da requisição. O laboratório destino SHALL ver a requisição antes da chegada da amostra
e conferir a amostra contra ela.

#### Scenario: Amostra sem requisição
- **WHEN** chega uma amostra para a qual não existe requisição
- **THEN** ela fica retida até haver requisição, e a unidade de origem é consultada

### Requirement: Recepção e triagem de amostras
O sistema SHALL registrar a recepção da amostra no laboratório destino com a conferência da requisição e a triagem de aceite ou
rejeição por motivo enumerado, conforme `saude/sus-coleta-e-recepcao`.

#### Scenario: Amostra aceita
- **WHEN** a amostra confere com a requisição
- **THEN** a recepção é registrada e o exame entra na fila de análise

### Requirement: Gerência de exames, painéis e kits
O sistema SHALL manter o catálogo de exames com procedimento SIGTAP, material, método, estabilidade, valores de referência e
unidade, e SHALL permitir agrupá-los em painéis e kits, de modo que a requisição de um painel gere os exames componentes.

#### Scenario: Requisição de painel
- **WHEN** a unidade requisita um painel
- **THEN** são criados os exames componentes, cada um com seu estado

### Requirement: Rastreio do paciente e do exame do cadastro à liberação
O sistema SHALL permitir consultar, por paciente, requisição, tubo ou código de autenticação, em que etapa o exame está e todo o
caminho percorrido, com tempos por etapa.

#### Scenario: Consulta pelo tubo
- **WHEN** o usuário informa o identificador de um tubo
- **THEN** vê o estado, o histórico de custódia e os tempos

### Requirement: Laudo consultável e imprimível na unidade de origem
O sistema SHALL disponibilizar o laudo liberado, assinado, para consulta e impressão pela unidade solicitante e pelo município de
origem, respeitados os perfis, sem depender de envio do laboratório destino.

#### Scenario: Município imprime o laudo
- **WHEN** o laudo é liberado no laboratório de referência
- **THEN** a unidade solicitante consulta e imprime o laudo assinado

### Requirement: Relatórios e estatísticas
O sistema SHALL gerar relatórios por período, unidade, exame e resultado (produção, tempo de resposta, rejeição, positividade de
agravo), sem identificação do paciente, exportáveis.

#### Scenario: Relatório de positividade
- **WHEN** a vigilância pede a positividade de um agravo no mês
- **THEN** o relatório traz contagens por município, sem dado pessoal

### Requirement: Vigilância por agravo
O sistema SHALL oferecer à vigilância visão por agravo e município dos resultados que correspondem a agravo de notificação, conforme
`saude/sus-producao-e-notificacao`, com perfil e acesso próprios.

#### Scenario: Perfil de vigilância
- **WHEN** um usuário de vigilância consulta os resultados de um agravo
- **THEN** vê os casos do seu território, conforme a permissão

### Requirement: Transição com o GAL por importação e exportação
O sistema SHALL importar do GAL (requisições, cadastros e resultados) e exportar para ele, no formato que o GAL aceitar, enquanto o
laboratório de referência ainda o usar, e SHALL tratar divergência entre os dois como quarentena. O formato de troca SHALL ser
confirmado em fonte primária antes da implementação; sem interface oficial, a transição SHALL ser por arquivo ou digitação conferida.

#### Scenario: Requisição vinda do GAL
- **WHEN** uma requisição é importada do GAL
- **THEN** ela vira requisição no módulo com a origem registrada e o número do GAL guardado

### Requirement: Escopo humano inicial
O sistema SHALL tratar apenas amostras de origem humana no início; amostra animal ou ambiental SHALL ser recusada com o motivo, e não
silenciosamente tratada como humana.

#### Scenario: Amostra animal
- **WHEN** uma requisição indica origem animal
- **THEN** o sistema recusa e informa que o escopo inicial é humano
