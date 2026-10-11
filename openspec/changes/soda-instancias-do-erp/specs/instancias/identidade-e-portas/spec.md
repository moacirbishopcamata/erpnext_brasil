## Purpose

Dar a cada instância do ERPNext Brasil uma identidade única que nunca se repete, um nome de host próprio e um bloco de portas sem conflito, guardados num registro que sobrevive a falhas.

## ADDED Requirements

### Requirement: Toda instância tem um UUID único e imutável

O Soda SHALL gerar, na criação de cada instância, um UUID versão 4 aleatório, e SHALL tratá-lo como a identidade da instância durante toda a sua vida. O UUID MUST NOT mudar quando a instância é renomeada, reiniciada ou muda de porta, e MUST NOT ser reutilizado por nenhuma outra instância, inclusive depois de a instância ser removida. O UUID SHALL constar do registro e do `site_config` da instância.

#### Scenario: UUID gerado na criação

- **WHEN** o usuário cria uma instância
- **THEN** o Soda gera um UUID versão 4, grava-o no registro e no `site_config` da instância, e o mostra completo e abreviado ao usuário

#### Scenario: UUID de instância removida não volta

- **WHEN** uma instância é removida
- **THEN** o seu UUID passa para a lista de aposentados e nenhuma instância futura pode recebê-lo, mesmo que o gerador o sorteie de novo

#### Scenario: Colisão improvável é tratada

- **WHEN** o UUID sorteado já existe entre as instâncias ou entre as aposentadas
- **THEN** o Soda sorteia outro e registra a ocorrência, sem falhar a criação

### Requirement: Cada instância tem um descritivo único

O Soda SHALL exigir, na criação, um descritivo para a instância: um texto de 3 a 60 caracteres que a descreve para quem lê. O descritivo MUST ser único entre as instâncias existentes, comparado sem diferença de maiúsculas, de minúsculas e de acentos. O descritivo SHALL poder ser alterado depois, mantendo a unicidade, e a alteração MUST NOT mudar o UUID, o nome do host nem a porta da instância.

#### Scenario: Descritivo repetido é recusado

- **WHEN** o usuário informa um descritivo que difere de outro apenas por maiúsculas ou acentos
- **THEN** o Soda recusa, informa a instância que já usa aquele descritivo e não cria nada

#### Scenario: Renomear mantém a identidade

- **WHEN** o usuário altera o descritivo de uma instância
- **THEN** o UUID, o host e a porta permanecem os mesmos, e o histórico guardado por outras ferramentas continua ligado ao mesmo UUID

#### Scenario: Descritivo de instância removida

- **WHEN** uma instância é removida
- **THEN** o seu descritivo fica livre para uso, e o UUID aposentado guarda o último descritivo conhecido

### Requirement: Cada instância tem um nome de host único no domínio `.localhost`

O Soda SHALL derivar de cada instância um nome de host único no domínio `.localhost`, composto do descritivo normalizado e do trecho abreviado do UUID, e SHALL usá-lo como o nome do site. Dois nomes de host MUST NOT coincidir, de modo que os cookies de sessão do navegador de uma instância não alcancem as outras.

#### Scenario: Hosts distintos isolam as sessões

- **WHEN** duas instâncias estão no ar em portas diferentes
- **THEN** cada uma é acessada pelo seu próprio nome de host, e entrar numa delas não encerra a sessão da outra

#### Scenario: Descritivo normalizado no host

- **WHEN** o usuário informa o descritivo "Teste da NF-e!"
- **THEN** o nome do host usa uma forma normalizada (letras minúsculas, dígitos e hífen), seguida do trecho do UUID

### Requirement: As portas são alocadas em bloco, sem conflito

O Soda SHALL alocar para cada instância um bloco de portas dentro de uma faixa configurável (padrão 8100 a 8999). A porta alocada MUST NOT repetir a de outra instância do registro e MUST estar livre no sistema no momento da alocação, verificada por tentativa de abri-la. O Soda MUST NOT alocar portas reservadas do ambiente: servidores de banco de dados, Redis, e as portas padrão do bench.

#### Scenario: Alocação automática livre de conflito

- **WHEN** o usuário cria uma instância sem escolher porta
- **THEN** o Soda aloca a menor porta livre da faixa que não pertence a nenhuma instância do registro

#### Scenario: Porta escolhida e ocupada

- **WHEN** o usuário escolhe uma porta que outro processo já escuta
- **THEN** o Soda recusa a criação, informa quem ocupa a porta quando puder identificá-lo e sugere a próxima livre

#### Scenario: Porta reservada é recusada

- **WHEN** o usuário escolhe a porta do servidor de banco de dados ou a padrão do bench
- **THEN** o Soda recusa e explica que a porta é reservada do ambiente

#### Scenario: Faixa esgotada

- **WHEN** não há porta livre na faixa configurada
- **THEN** o Soda recusa a criação e informa que a faixa está esgotada e como ampliá-la

### Requirement: O registro das instâncias é atômico e protegido contra concorrência

O Soda SHALL guardar as instâncias, as portas, os UUIDs aposentados e o estado de cada instância num único registro por bench, gravado de forma atômica, de modo que uma falha no meio da gravação preserve o registro anterior. O Soda SHALL impedir que dois processos do Soda alterem o registro ao mesmo tempo.

#### Scenario: Falha na gravação preserva o registro

- **WHEN** a gravação do registro falha no meio
- **THEN** o registro anterior permanece intacto e nenhum arquivo temporário sobra

#### Scenario: Dois Sodas ao mesmo tempo

- **WHEN** dois processos do Soda tentam criar uma instância ao mesmo tempo
- **THEN** um deles espera a trava ou é recusado com mensagem, e nenhuma porta nem UUID é alocado em duplicidade

#### Scenario: Registro ilegível não é apagado

- **WHEN** o registro existe mas não pode ser lido
- **THEN** o Soda não o sobrescreve, informa o problema e oferece mover o arquivo para uma cópia de quarentena antes de recomeçar

### Requirement: A persistência do registro é selecionável

O Soda SHALL permitir guardar o registro em JSON ou em SQLite, à escolha do usuário, com o mesmo conteúdo e as mesmas garantias de atomicidade, de UUID único e de portas sem conflito nos dois. A troca de um formato para o outro SHALL migrar todas as instâncias e os UUIDs aposentados sem perder nem alterar nenhum UUID, descritivo ou porta, e SHALL manter uma cópia do formato anterior até o usuário confirmar a troca.

#### Scenario: Migração preserva a identidade

- **WHEN** o usuário troca o registro de JSON para SQLite
- **THEN** todas as instâncias e todos os UUIDs aposentados aparecem iguais no novo formato, e a cópia do formato anterior é mantida

#### Scenario: Mesmo comportamento nos dois formatos

- **WHEN** o mesmo conjunto de operações (criar, renomear, remover) é executado com cada formato
- **THEN** o estado final observável, incluindo portas alocadas e UUIDs aposentados, é idêntico

#### Scenario: Falha na migração preserva o original

- **WHEN** a migração falha no meio
- **THEN** o registro no formato original permanece intacto e utilizável

### Requirement: Por padrão a instância só escuta o próprio computador

O Soda SHALL fazer cada instância escutar apenas o endereço local (`127.0.0.1`). Expor uma instância à rede SHALL exigir uma opção explícita, acompanhada de aviso do que isso permite.

#### Scenario: Escuta local por padrão

- **WHEN** uma instância é iniciada sem opção de exposição
- **THEN** a porta escuta somente o endereço local e não é alcançável de outras máquinas
