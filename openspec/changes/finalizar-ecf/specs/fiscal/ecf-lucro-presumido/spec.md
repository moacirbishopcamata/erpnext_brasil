## Purpose

Define o Bloco P da ECF para a empresa no Lucro Presumido: a base presumida por atividade e as
memórias de cálculo do IRPJ e da CSLL, sempre contra o catálogo oficial de códigos da Receita.

## ADDED Requirements

### Requirement: A receita bruta é classificada por atividade, sem padrão

O sistema SHALL apurar a base presumida a partir da receita bruta classificada por atividade,
conforme o mapeamento configurado pela empresa, e SHALL NOT aplicar percentual de presunção a
receita que não está mapeada para uma atividade.

#### Scenario: Receita sem atividade mapeada

- **WHEN** há receita no período cuja origem não está mapeada para nenhuma atividade
- **THEN** o sistema recusa a geração do Bloco P e lista as origens sem mapeamento

#### Scenario: Atividades com percentuais diferentes

- **WHEN** a empresa tem receita em duas atividades de percentuais de presunção distintos
- **THEN** a base presumida é a soma de cada receita pelo percentual da sua atividade

### Requirement: Serviços de saúde têm presunção própria por tipo de serviço

Quando a empresa presta serviços de saúde, o sistema SHALL distinguir os serviços hospitalares
dos demais serviços de saúde na apuração da base presumida, com os percentuais conferidos
contra a norma citada na documentação, e SHALL NOT usar um percentual único para os dois.

#### Scenario: Hospital e consultório na mesma empresa

- **WHEN** a empresa tem receita de serviço hospitalar e de outro serviço de saúde
- **THEN** cada receita entra na base com o percentual do seu tipo de serviço

#### Scenario: Atendimento sem faturamento fiscal é listado, não presumido

- **WHEN** há atendimento ou dispensação registrado no período sem documento fiscal de
  faturamento (por exemplo, dispensação gratuita pelo balcão não fiscal)
- **THEN** o sistema não o inclui na receita bruta apurada e o lista como "não faturado" para
  conferência do contador, sem presumir que seja ou não receita

### Requirement: Os códigos das memórias de cálculo vêm do catálogo oficial

O sistema SHALL preencher o código de cada linha das memórias de cálculo do Bloco P apenas com
códigos presentes no catálogo oficial da versão do leiaute em uso, e SHALL NOT aceitar código
fora do catálogo nem inventar descrição.

#### Scenario: Código fora do catálogo

- **WHEN** uma linha de memória de cálculo recebe um código que não existe no catálogo da
  versão do leiaute
- **THEN** o sistema recusa a linha e nomeia o código inválido

#### Scenario: Catálogo de outra versão

- **WHEN** o ano-calendário usa uma versão do leiaute sem catálogo carregado
- **THEN** o sistema recusa a geração do Bloco P e informa a versão faltante

### Requirement: O cálculo do IRPJ e da CSLL fecha com a base e as alíquotas

O sistema SHALL calcular IRPJ e CSLL a partir da base presumida, das alíquotas e do adicional
vigentes para o período, de modo que o valor devido registrado nas memórias de cálculo seja
reproduzível a partir dos valores das linhas anteriores do próprio bloco.

#### Scenario: Reprodução do cálculo

- **WHEN** o Bloco P é gerado
- **THEN** recalcular o IRPJ e a CSLL a partir das linhas de base do bloco dá o valor devido
  declarado nas linhas de cálculo

#### Scenario: Adicional sobre o excedente

- **WHEN** a base presumida do período excede o limite do adicional
- **THEN** o adicional incide somente sobre o excedente
