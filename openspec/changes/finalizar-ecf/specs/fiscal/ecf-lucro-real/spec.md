## Purpose

Define os Blocos L, M e N da ECF para a empresa no Lucro Real: a demonstração do resultado
contábil, a transformação em lucro tributável pelo controle da Parte B do LALUR e da LACS, e o
cálculo do IRPJ e da CSLL.

## ADDED Requirements

### Requirement: Cada conta da Parte B carrega o saldo de um período ao outro

O sistema SHALL manter, para cada conta de controle fiscal da Parte B, o saldo inicial do
período, os movimentos de adição, exclusão e compensação e o saldo final, e o saldo final de um
período SHALL ser o saldo inicial do seguinte.

#### Scenario: Saldo atravessa o período

- **WHEN** um período fecha com saldo final em uma conta da Parte B
- **THEN** o período seguinte abre essa conta com o mesmo valor como saldo inicial

#### Scenario: Movimento que deixaria o saldo negativo

- **WHEN** uma compensação é maior que o saldo disponível da conta
- **THEN** o sistema recusa o movimento e informa o saldo disponível

### Requirement: Todo lançamento do LALUR é rastreável a um lançamento contábil

O sistema SHALL vincular cada movimento da Parte B a um lançamento contábil real do período e a
uma conta, e SHALL NOT aceitar movimento sem esse vínculo.

#### Scenario: Movimento sem lançamento contábil

- **WHEN** um movimento é registrado sem o lançamento contábil de origem
- **THEN** o sistema recusa o movimento e nomeia o vínculo faltante

#### Scenario: Reler pelo caminho independente

- **WHEN** um movimento é gravado
- **THEN** a leitura do movimento pela conta e a leitura pelo lançamento contábil de origem
  devolvem o mesmo movimento

### Requirement: O lucro tributável parte do resultado contábil

O sistema SHALL apurar o lucro real a partir do resultado contábil do período (Bloco L),
somando as adições e subtraindo as exclusões e as compensações registradas na Parte B, e a
compensação de prejuízo fiscal SHALL respeitar o limite percentual vigente do lucro antes dela.

#### Scenario: Cadeia do resultado ao lucro real

- **WHEN** o Bloco M é gerado
- **THEN** o lucro real é igual ao resultado contábil mais as adições menos as exclusões menos
  as compensações, todos presentes no próprio bloco

#### Scenario: Compensação de prejuízo acima do limite

- **WHEN** o prejuízo fiscal acumulado é maior que o limite de compensação do período
- **THEN** só o valor do limite é compensado e o restante permanece no saldo

### Requirement: O cálculo do IRPJ e da CSLL sai do lucro real

O sistema SHALL calcular IRPJ e CSLL no Bloco N a partir do lucro real e da base da CSLL,
com alíquotas, adicional e deduções vigentes, e as linhas de cálculo SHALL usar apenas códigos
do catálogo oficial da versão do leiaute.

#### Scenario: Reprodução do cálculo

- **WHEN** o Bloco N é gerado
- **THEN** recalcular o imposto a partir das linhas de base dá o valor devido declarado

#### Scenario: Código fora do catálogo

- **WHEN** uma linha de cálculo usa código ausente do catálogo da versão do leiaute
- **THEN** o sistema recusa a linha e nomeia o código

### Requirement: Entidade imune ou isenta não passa pelo cálculo do lucro real

Quando a empresa é entidade imune ou isenta, o sistema SHALL seguir o tratamento que o Manual
da ECF prevê para essa condição e SHALL NOT aplicar o cálculo do lucro real como se ela fosse
tributada; enquanto o tratamento não estiver implementado, SHALL recusar a geração do bloco com
a informação do que falta.

#### Scenario: Entidade filantrópica de saúde

- **WHEN** a empresa é entidade imune e presta serviços de saúde
- **THEN** o sistema não calcula IRPJ e CSLL pelo lucro real e informa o tratamento aplicado ou
  o que ainda falta implementar
