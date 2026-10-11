## Purpose

Permitir que cada ferramenta (Cherry, Soda e Chantilly) guarde o seu estado em JSON ou em SQLite, à escolha do usuário, com o mesmo comportamento observável, migração sem perda e esquema versionado.

## ADDED Requirements

### Requirement: A persistência é selecionável por ferramenta

Cada ferramenta SHALL permitir escolher, por configuração, entre JSON e SQLite para guardar o seu estado persistente, exceto a série histórica do Chantilly, que SHALL usar SQLite. A escolha SHALL ser mostrada na interface e no terminal, e o formato em uso SHALL poder ser consultado sem abrir o arquivo.

#### Scenario: Formato escolhido e visível

- **WHEN** o usuário abre a configuração de persistência de uma ferramenta
- **THEN** a ferramenta mostra o formato em uso, o caminho do arquivo e a versão de esquema

#### Scenario: Série do Chantilly não oferece JSON

- **WHEN** o usuário abre a persistência da série histórica do Chantilly
- **THEN** a opção JSON não é oferecida e a tela explica que o volume exige SQLite

### Requirement: Os dois formatos têm o mesmo comportamento observável

Para o mesmo conjunto de operações, a ferramenta SHALL produzir o mesmo estado observável com JSON e com SQLite, incluindo ordem de listagem, unicidade e recusas. Uma gravação SHALL ser atômica nos dois formatos: uma falha no meio MUST deixar o estado anterior intacto.

#### Scenario: Paridade comprovada

- **WHEN** a suíte de contrato de uma ferramenta roda contra o adaptador JSON e contra o adaptador SQLite
- **THEN** todos os casos passam nos dois, com os mesmos resultados

#### Scenario: Falha no meio da gravação

- **WHEN** uma gravação falha no meio, em qualquer dos formatos
- **THEN** o estado anterior permanece íntegro e legível, e nenhum arquivo temporário sobra

### Requirement: A troca de formato migra sem perda

A troca de JSON para SQLite e de SQLite para JSON SHALL migrar todo o estado sem perder nem alterar nenhum registro, SHALL manter uma cópia do formato anterior até o usuário confirmar a troca, e MUST NOT apagar o formato anterior em caso de falha. A migração SHALL ser idempotente.

#### Scenario: Ida e volta preserva o estado

- **WHEN** o estado é migrado de JSON para SQLite e de volta para JSON
- **THEN** o estado final é igual ao inicial

#### Scenario: Migração interrompida

- **WHEN** a migração é interrompida
- **THEN** o formato original continua em uso e íntegro, e a tentativa pode ser repetida

### Requirement: O esquema do SQLite é versionado e migrado na abertura

O arquivo SQLite SHALL declarar a versão do seu esquema. Ao abrir um arquivo de esquema anterior, a ferramenta SHALL aplicar as migrações necessárias dentro de uma transação, e ao abrir um arquivo de esquema posterior ao que conhece SHALL recusar gravar e informar o motivo.

#### Scenario: Migração de esquema na abertura

- **WHEN** a ferramenta abre um arquivo de esquema anterior
- **THEN** as migrações são aplicadas numa transação e o arquivo passa à versão atual, ou permanece intacto se alguma falhar

#### Scenario: Esquema mais novo que a ferramenta

- **WHEN** a ferramenta abre um arquivo de esquema posterior
- **THEN** ela não grava, informa que a versão é mais nova e oferece abrir somente leitura

### Requirement: Nenhum segredo é persistido

Nenhuma ferramenta SHALL gravar senha ou segredo em nenhum dos formatos de persistência, e o esquema do SQLite MUST NOT conter coluna destinada a senha ou segredo.

#### Scenario: Esquema sem coluna de segredo

- **WHEN** o esquema do SQLite de uma ferramenta é inspecionado
- **THEN** nenhuma coluna tem nome ou finalidade de senha ou segredo

### Requirement: O arquivo corrompido não é sobrescrito

Se o arquivo de persistência, em qualquer formato, estiver ilegível, a ferramenta SHALL recusar gravar por cima, informar o problema e oferecer movê-lo para uma cópia de quarentena antes de recomeçar.

#### Scenario: Arquivo SQLite corrompido

- **WHEN** a ferramenta abre um arquivo SQLite que não pode ser lido
- **THEN** ela não o sobrescreve e oferece a quarentena
