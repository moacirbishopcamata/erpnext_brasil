## Purpose

Converter o consumo medido de CPU, memória e armazenamento em valor estimado, a partir de preços informados pelo usuário, sem nunca presumir um preço.

## ADDED Requirements

### Requirement: Os preços são informados pelo usuário e nunca presumidos

O Chantilly SHALL calcular custo somente a partir de uma tabela de preços preenchida pelo usuário, com o preço da hora de CPU, do GB-hora de memória e do GB-mês de armazenamento, numa moeda declarada. O Chantilly MUST NOT usar preço de fábrica, preço de mercado nem valor derivado de outra fonte quando a tabela estiver vazia.

#### Scenario: Sem preço informado, só consumo

- **WHEN** o usuário consulta o custo e nenhum preço foi informado
- **THEN** o Chantilly mostra o consumo medido e a mensagem de que o preço não foi informado, sem exibir valor monetário

#### Scenario: Preço parcial calcula só o que tem preço

- **WHEN** apenas o preço do armazenamento foi informado
- **THEN** o custo de armazenamento é calculado e os de CPU e memória aparecem como "preço não informado"

### Requirement: O custo é consumo vezes preço, por período, e sempre rotulado como estimativa

O Chantilly SHALL calcular o custo de um período como o consumo do período vezes o preço da unidade correspondente, usando aritmética decimal exata e arredondando o resultado final para centavos. Todo valor monetário apresentado SHALL ser rotulado como estimativa.

#### Scenario: Cálculo exato

- **WHEN** um site consumiu 10 horas de CPU num período e o preço da hora de CPU é 0,40
- **THEN** o custo de CPU do site no período é 4,00

#### Scenario: Rótulo de estimativa

- **WHEN** qualquer tela ou relatório exibe um valor monetário
- **THEN** o valor aparece acompanhado do rótulo de estimativa e do período a que se refere

### Requirement: O custo pode ser aberto por site, app, DocType, endpoint e job

O Chantilly SHALL apresentar o custo de CPU e memória por site, endpoint e job, e o de armazenamento por site e DocType, para um período escolhido pelo usuário.

#### Scenario: Maiores custos primeiro

- **WHEN** o usuário abre o custo por job de um período
- **THEN** os jobs aparecem ordenados do maior para o menor custo, com o consumo que o originou

### Requirement: A parte não atribuída é mostrada, não escondida

O Chantilly SHALL mostrar a diferença entre o consumo total do host e a soma do consumo atribuído como "não atribuído", e SHALL NOT ratear essa diferença em silêncio entre os sites.

#### Scenario: Consumo não atribuído visível

- **WHEN** o consumo de CPU do host no período excede a soma dos tempos atribuídos
- **THEN** o resultado inclui uma linha "não atribuído" com a diferença e o seu custo estimado
