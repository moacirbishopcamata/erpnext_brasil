## Purpose

Garantir que o módulo inteiro seja tropicalizado: idioma, formatos, tabelas oficiais, calendário, fuso horário, documentos e integrações
brasileiras, de modo que nenhuma tela, etiqueta, laudo, prazo ou código dependa de padrão estrangeiro quando existe equivalente
brasileiro, no mesmo sentido de tropicalização do restante do projeto.

## ADDED Requirements

### Requirement: Interface e documentos em português do Brasil
O sistema SHALL apresentar toda tela, mensagem, e-mail, etiqueta, comprovante e laudo em português do Brasil com acentuação correta,
usando o vocabulário do SUS e da ANVISA (requisição, amostra, material biológico, competência, CNES). Texto sem tradução ou sem acento
SHALL ser tratado como defeito.

#### Scenario: Cadeia sem tradução
- **WHEN** uma cadeia de interface aparece em outro idioma ou sem acento
- **THEN** o teste de tradução falha e aponta a cadeia

### Requirement: Formatos brasileiros
O sistema SHALL exibir e aceitar data no formato dd/mm/aaaa, hora de 24 horas, vírgula como separador decimal, e CPF, CNS, CNPJ, CEP e
telefone no formato brasileiro, em tela, etiqueta, laudo e exportação, e SHALL armazenar valores em formato canônico independente da
apresentação.

#### Scenario: Valor decimal no laudo
- **WHEN** um resultado de 5,2 é impresso
- **THEN** o laudo mostra a vírgula decimal e o dado armazenado permanece canônico

### Requirement: Fuso horário de Brasília e horário de verão histórico
O sistema SHALL registrar os instantes com fuso explícito, apresentá-los no horário de Brasília (ou no fuso da unidade, quando
diferente), e SHALL aplicar as regras históricas de horário de verão ao interpretar instantes antigos, de modo que a hora de coleta de um
laudo antigo seja a que valia na data.

#### Scenario: Coleta em data com horário de verão
- **WHEN** um laudo de uma coleta feita durante o horário de verão é exibido
- **THEN** a hora apresentada é a que valia naquela data

### Requirement: Calendário de dias úteis com feriados nacionais
O sistema SHALL contar prazos em dias úteis (comunicação de incidente, ciência do laudo, envio do S-2220) com o calendário de fins de
semana e feriados nacionais, versionado e atualizável, e SHALL permitir feriados estaduais e municipais por unidade.

#### Scenario: Prazo que atravessa feriado
- **WHEN** um prazo de três dias úteis começa antes de um feriado nacional
- **THEN** o feriado não é contado

### Requirement: Tabelas oficiais brasileiras versionadas
O sistema SHALL usar como dados versionados, com origem, versão e vigência registradas, as tabelas: municípios e raça/cor do IBGE, CBO,
CID, CNES, SIGTAP, Tabela 27 do eSocial, TUSS e a correspondência com o LOINC. Código inexistente na versão vigente SHALL ser
recusado, e a atualização de uma tabela SHALL valer apenas para registros posteriores.

#### Scenario: Município incompatível com a UF
- **WHEN** o endereço informa um município que não pertence à UF
- **THEN** o cadastro é recusado com o motivo

### Requirement: Endereço brasileiro
O sistema SHALL representar o endereço com CEP, logradouro, número, complemento, bairro, município pelo código IBGE e UF, e SHALL
validar o município contra a tabela do IBGE.

#### Scenario: Município inexistente
- **WHEN** o código IBGE do município não existe na tabela vigente
- **THEN** o endereço é recusado

### Requirement: Integrações e documentos pelo padrão brasileiro
O sistema SHALL usar o padrão brasileiro onde existe: assinatura pela ICP-Brasil, tempo pela fonte NTP.br, envio de resultado pela
RNDS, saúde ocupacional pelo eSocial e produção pelo SIASUS. Um padrão estrangeiro SHALL ser usado somente quando não houver
equivalente brasileiro, com a justificativa registrada.

#### Scenario: Fonte de tempo
- **WHEN** o relógio é sincronizado
- **THEN** a fonte padrão é o NTP.br, e outra fonte exige justificativa registrada

### Requirement: Normas sanitárias e de saúde brasileiras como referência
O sistema SHALL referenciar, na documentação e nas validações, as normas brasileiras aplicáveis (RDC 786/2023, RDC 504/2021, Lei
13.787/2018, LGPD, Lei 14.063/2020 e portarias do Ministério da Saúde), com a versão e a data de leitura, e SHALL registrar quando uma
exigência vem de fonte secundária.

#### Scenario: Regra de fonte secundária
- **WHEN** uma regra se apoia em fonte secundária
- **THEN** a documentação a marca como não confirmada em fonte primária
