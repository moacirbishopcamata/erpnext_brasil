## Purpose

Fazer cada resultado carregar o exame, a unidade e o código certos, ligando o código do equipamento a LOINC e TUSS por uma
tabela explícita e versionada — para que nenhum código, unidade ou conversão seja presumido.

## ADDED Requirements

### Requirement: Correspondência explícita entre código do equipamento, exame, LOINC e TUSS

O sistema MUST manter uma tabela de correspondência entre o código do exame no equipamento, o exame do ERPNext, o código LOINC
e o código TUSS. Resultado cujo código do equipamento não tenha correspondência MUST ir para a quarentena e MUST NOT ser
interpretado por semelhança de nome.

#### Scenario: Código sem correspondência

- **WHEN** chega resultado com um código que a tabela não conhece
- **THEN** o resultado vai para a quarentena, com o código original preservado

### Requirement: Unidade em UCUM sem conversão implícita

A unidade de cada resultado MUST ser registrada em UCUM. Quando a unidade do equipamento diferir da do exame no ERPNext, o
sistema MUST reter o resultado, salvo se existir regra de conversão explícita, aprovada e versionada.

#### Scenario: Unidade diferente

- **WHEN** o equipamento envia glicose em mmol/L e o exame no ERPNext usa mg/dL, sem regra de conversão
- **THEN** o resultado é retido e nada é convertido por conta própria

#### Scenario: Conversão aprovada

- **WHEN** existe regra de conversão aprovada e vigente para aquele par de unidades
- **THEN** o sistema converte e guarda o valor original, o convertido e a regra aplicada

### Requirement: Origem e versão de cada código registradas

Todo código de terminologia usado MUST registrar a tabela de origem e a versão (por exemplo, a competência da TUSS). Código
que deixou de constar na versão vigente MUST ser sinalizado.

#### Scenario: Código TUSS descontinuado

- **WHEN** um exame mapeado usa um código que saiu da versão vigente da TUSS
- **THEN** o sistema sinaliza a correspondência para revisão

### Requirement: Alteração de correspondência só vale para o futuro

A mudança de uma correspondência MUST ser feita por usuário autorizado, MUST ser auditada e MUST valer apenas para resultados
recebidos depois dela; resultados já registrados MUST NOT ser reescritos.

#### Scenario: Correção de uma correspondência

- **WHEN** um administrador corrige o LOINC de um exame
- **THEN** os resultados anteriores mantêm o código com que foram registrados
- **AND** a alteração fica no histórico com usuário, data e motivo
