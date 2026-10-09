## Purpose

Permite conferir, de forma reprodutível, se a pilha que sustenta o ERPNext está em versão suportada e sem
vulnerabilidade conhecida, em vez de depender de uma consulta manual a cada vez.

## ADDED Requirements

### Requirement: As versões instaladas são confrontadas com as séries suportadas

O sistema SHALL comparar a versão instalada de cada componente da pilha com a última versão estável da série
suportada, informando a defasagem e o fim de suporte, e SHALL marcar como falha um componente cuja série esteja
fora de suporte.

#### Scenario: Componente na última versão

- **WHEN** a versão instalada é a última da série suportada
- **THEN** o componente é relatado como em dia

#### Scenario: Componente atrás da última versão

- **WHEN** a versão instalada é anterior à última da série suportada
- **THEN** o relatório informa a versão instalada, a última e a data de fim de suporte da série

#### Scenario: Série fora de suporte

- **WHEN** a série do componente passou da data de fim de suporte
- **THEN** o componente é marcado como falha

#### Scenario: Fonte indisponível

- **WHEN** uma fonte de versão ou de vulnerabilidade não responde
- **THEN** o relatório diz que o componente não pôde ser verificado, em vez de declará-lo em dia

### Requirement: As vulnerabilidades conhecidas são relatadas contra a versão instalada

O sistema SHALL consultar os avisos de segurança publicados para o Frappe, o ERPNext, o HRMS e o bench e as
vulnerabilidades conhecidas das bibliotecas instaladas, e SHALL relatar apenas as que afetam a versão
instalada, com gravidade e versão corrigida.

#### Scenario: Aviso corrigido em versão anterior à instalada

- **WHEN** um aviso de segurança foi corrigido numa versão menor ou igual à instalada
- **THEN** o aviso não é relatado como afetando a instalação

#### Scenario: Aviso sem versão corrigida declarada

- **WHEN** um aviso publicado não declara a versão corrigida
- **THEN** o aviso é relatado à parte, como indeterminado, e não como afetando nem como resolvido

#### Scenario: Biblioteca com vulnerabilidade conhecida

- **WHEN** uma biblioteca instalada tem vulnerabilidades registradas para a sua versão
- **THEN** o relatório lista a gravidade, a versão que corrige e quem a exige

### Requirement: O resultado é utilizável por automação

O sistema SHALL encerrar com código de saída diferente de zero quando houver falha, vulnerabilidade de gravidade
alta ou crítica que afete a instalação, ou componente impossível de verificar, e zero caso contrário.

#### Scenario: Instalação sem pendências

- **WHEN** todos os componentes estão em dia e nenhuma vulnerabilidade de gravidade alta ou crítica os afeta
- **THEN** o código de saída é zero

#### Scenario: Vulnerabilidade alta

- **WHEN** uma vulnerabilidade de gravidade alta afeta um componente
- **THEN** o código de saída é diferente de zero
