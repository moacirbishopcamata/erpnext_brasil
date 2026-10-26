## Purpose

Permite gerar o arquivo da ECF de uma empresa e de um período a partir do que o ERPNext já
guarda, recusando com motivo o que a ECF não alcança e o dado que falta, e registrando o
arquivo para ser validado e transmitido no PVA da Receita Federal.

## ADDED Requirements

### Requirement: A ECF só é gerada para quem a Receita obriga

O sistema SHALL recusar a geração da ECF, antes de montar qualquer registro, para a empresa que
a norma dispensa — optante do Simples Nacional, órgão público, autarquia, fundação pública e
pessoa jurídica inativa — nomeando o motivo da dispensa na mensagem, e SHALL NOT tratar a
imunidade ou a isenção, por si só, como motivo de dispensa.

#### Scenario: Órgão público não gera ECF

- **WHEN** a empresa está cadastrada como órgão público, autarquia ou fundação pública
- **THEN** o sistema recusa a geração e informa que a ECF não alcança essa natureza jurídica

#### Scenario: Optante do Simples Nacional não gera ECF

- **WHEN** a empresa é optante do Simples Nacional no período
- **THEN** o sistema recusa a geração e informa a dispensa

#### Scenario: Entidade imune ou isenta continua obrigada

- **WHEN** a empresa é entidade imune ou isenta e não está em nenhuma hipótese de dispensa
- **THEN** o sistema não a recusa pela condição de imune ou isenta

### Requirement: A forma de tributação decide quais blocos o arquivo tem

O sistema SHALL montar o arquivo com os blocos que a forma de tributação da empresa no período
exige — Lucro Presumido com o Bloco P, Lucro Real com os Blocos L, M e N — e SHALL NOT incluir
o bloco do regime que a empresa não usa, nem presumir o regime quando ele não está informado.

#### Scenario: Lucro Presumido não leva os Blocos L, M e N

- **WHEN** a empresa está no Lucro Presumido
- **THEN** o arquivo contém o Bloco P e não contém conteúdo dos Blocos L, M e N

#### Scenario: Regime não informado recusa

- **WHEN** a forma de tributação do período não está informada
- **THEN** o sistema recusa a geração e pede a informação, sem escolher um regime

### Requirement: Indicador regulatório sem resposta recusa a geração

O sistema SHALL exigir resposta explícita da empresa para cada indicador regulatório do
Bloco 0 que o Manual declare obrigatório para o arquivo, e SHALL NOT gravar valor padrão para
indicador sem resposta.

#### Scenario: Indicador sem resposta

- **WHEN** há um indicador obrigatório do Bloco 0 sem resposta registrada para a empresa
- **THEN** o sistema recusa a geração e lista os indicadores pendentes pelo nome que o usuário vê

#### Scenario: Todas as respostas presentes

- **WHEN** todos os indicadores obrigatórios têm resposta registrada
- **THEN** o Bloco 0 é montado com exatamente as respostas registradas

### Requirement: Plano de contas e saldos vêm da escrituração contábil

O sistema SHALL montar o plano de contas e o mapeamento referencial (Bloco J) e os saldos das
contas (Bloco K) a partir da mesma base que alimenta a ECD, de modo que os valores da ECF e da
ECD do período coincidam.

#### Scenario: Saldo da ECF igual ao da ECD

- **WHEN** a ECD e a ECF são geradas para a mesma empresa e período
- **THEN** o saldo de cada conta no Bloco K é igual ao saldo da mesma conta na ECD

#### Scenario: Conta sem mapeamento referencial

- **WHEN** uma conta com saldo no período não tem código referencial
- **THEN** o sistema recusa a geração e nomeia a conta sem mapeamento

### Requirement: O arquivo é íntegro e fechado

O sistema SHALL emitir os registros na ordem do leiaute, fechar cada bloco com a contagem de
linhas correta e emitir o Bloco 9 com a contagem de cada tipo de registro e o total do
arquivo, de modo que a contagem recalculada a partir do texto gerado coincida com a declarada.

#### Scenario: Contagens conferem

- **WHEN** o arquivo é gerado
- **THEN** a contagem de cada tipo de registro no Bloco 9 e a de cada encerramento de bloco
  coincidem com as linhas presentes no texto

#### Scenario: Versão do leiaute registrada

- **WHEN** o arquivo é gerado
- **THEN** o código da versão do leiaute no registro de abertura é o do leiaute vigente para o
  ano-calendário, e o sistema recusa um ano-calendário sem leiaute conhecido

### Requirement: A geração respeita a permissão do usuário e fica registrada

O sistema SHALL exigir do usuário permissão de leitura da empresa e de criação do registro do
arquivo antes de ler qualquer dado contábil, gravar o arquivo gerado como `Arquivo SPED` do
tipo ECF vinculado à empresa e ao período, e SHALL NOT gravá-lo com permissão contornada.

#### Scenario: Usuário sem permissão

- **WHEN** um usuário sem permissão de criar `Arquivo SPED` pede a geração da ECF
- **THEN** o sistema recusa com erro de permissão e nenhum registro é criado

#### Scenario: Geração autorizada

- **WHEN** um usuário autorizado gera a ECF de uma empresa e período
- **THEN** existe um `Arquivo SPED` do tipo ECF com o conteúdo gerado, relido por uma segunda
  leitura do registro e igual ao devolvido

### Requirement: O sistema declara o que não foi validado

O sistema SHALL informar, junto do arquivo gerado, que a validação do PVA da Receita e a
transmissão assinada são etapas fora do sistema, e SHALL NOT marcar o arquivo como entregue.

#### Scenario: Aviso junto do resultado

- **WHEN** a geração termina com sucesso
- **THEN** o resultado informa que o arquivo ainda precisa ser validado e transmitido pelo PVA
