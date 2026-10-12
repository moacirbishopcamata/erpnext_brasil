## Purpose

Entregar, para o paciente que é trabalhador, o dado do exame ocupacional ao fluxo do eSocial (evento S-2220, Monitoramento da Saúde
do Trabalhador), sem que o núcleo do laboratório conheça o eSocial: o núcleo produz um dado neutro, e o módulo de integração monta,
assina e transmite.

## ADDED Requirements

### Requirement: Exame ocupacional marcado e ligado ao trabalhador
O sistema SHALL permitir marcar uma solicitação como ocupacional (admissional, periódico, retorno ao trabalho, mudança de risco ou
demissional), ligada a um paciente com vínculo de trabalhador. Solicitação ocupacional para paciente sem vínculo SHALL ser recusada.

#### Scenario: Ocupacional sem vínculo
- **WHEN** alguém marca ocupacional um exame de paciente sem vínculo de trabalho
- **THEN** a solicitação é recusada e o cadastro de vínculo é indicado

### Requirement: Dado neutro do exame ocupacional
O sistema SHALL disponibilizar, para cada exame ocupacional liberado, um registro neutro com o paciente (CPF), o empregador, a
matrícula, a data de realização do exame, o procedimento, a ordem (inicial ou sequencial), as observações e o responsável pela
liberação, sem formato de eSocial. O registro SHALL referenciar o laudo assinado.

#### Scenario: Exame ocupacional liberado
- **WHEN** um exame ocupacional é liberado
- **THEN** o registro neutro fica disponível para o módulo de integração com os dados acima

### Requirement: Procedimento mapeado para a Tabela 27 do eSocial
O módulo de integração SHALL mapear o procedimento do exame para a Tabela 27 (procedimentos diagnósticos) do eSocial por tabela
versionada e SHALL recusar a montagem do evento quando não houver correspondência, em vez de presumir código. Exames diferentes com o
mesmo código SHALL ser diferenciados pela chave do grupo, e o código sozinho não identifica o exame.

#### Scenario: Exame sem correspondência
- **WHEN** o exame liberado não tem correspondência na Tabela 27
- **THEN** a montagem do evento é recusada e o exame aparece em lista de pendências com o motivo

### Requirement: Regras de data e de observação do exame
O módulo de integração SHALL recusar a data de exame anterior à data de admissão, exceto em exame admissional, e SHALL exigir a
observação do procedimento nos códigos da Tabela 27 que a exigem, conforme o leiaute vigente.

#### Scenario: Exame antes da admissão
- **WHEN** um exame periódico tem data anterior à admissão
- **THEN** o evento não é montado e o motivo é informado

### Requirement: Montagem, assinatura e envio pela infraestrutura de eSocial existente
O módulo de integração SHALL montar o evento S-2220 e SHALL assiná-lo e transmiti-lo com a infraestrutura de eSocial do
`erpnext_brasil/folha/` (assinatura, lote, SOAP e leitura de retorno), sem duplicá-la, e SHALL guardar o recibo ou os erros do retorno
ligados ao exame. O núcleo SHALL NOT importar essa infraestrutura.

#### Scenario: Retorno com erro
- **WHEN** o eSocial rejeita o evento
- **THEN** o erro fica ligado ao exame e o exame aparece em lista de pendências até a correção

### Requirement: Prazo de envio acompanhado
O módulo de integração SHALL calcular o prazo de envio do S-2220 a partir da emissão do ASO (até o dia 15 do mês seguinte, conforme o
leiaute vigente) e SHALL alertar o aproximar e o vencimento do prazo.

#### Scenario: Prazo próximo
- **WHEN** o prazo de envio de um evento se aproxima sem envio
- **THEN** um alerta é aberto para o responsável

### Requirement: Quem transmite é o empregador
O módulo de integração SHALL transmitir o evento apenas quando o ERPNext ao qual está acoplado representa o empregador ou o
responsável pelo envio; caso contrário, SHALL exportar o dado para o empregador sem transmitir. A decisão SHALL ser configuração
explícita, não presunção.

#### Scenario: Laboratório que não é o empregador
- **WHEN** o laboratório não é o empregador do trabalhador
- **THEN** o módulo exporta o dado do exame para o empregador e não transmite ao eSocial
