## Purpose

Garantir que o Cherry, o Soda e o Chantilly funcionem em Windows e em Linux com o mesmo código, dizendo com clareza o que cada combinação de sistema e de bench permite.

## ADDED Requirements

### Requirement: As ferramentas rodam em Windows e em Linux

O Cherry, o Soda e o Chantilly SHALL funcionar em Windows 10 ou 11 e em Linux, usando apenas a biblioteca padrão do Python, com o mesmo código nos dois sistemas. As diferenças entre os sistemas SHALL ficar confinadas a adaptadores de plataforma; a regra de cada ferramenta MUST NOT conter teste de sistema operacional.

#### Scenario: Mesma regra, dois sistemas

- **WHEN** a suíte da regra das ferramentas roda em Windows e em Linux
- **THEN** os mesmos testes passam nos dois, sem nenhum teste pulado por causa do sistema, exceto os de recursos que só existem em um deles e que declaram o motivo

### Requirement: O bench pode estar no WSL2 (Windows) ou no mesmo Linux

As ferramentas SHALL operar um bench que vive no WSL2, quando a janela roda no Windows, e um bench local, quando a janela roda em Linux. A escolha SHALL ser uma configuração do bench e SHALL ser mostrada ao usuário. As ferramentas MUST NOT exigir `wsl.exe` em Linux nem presumir caminho `/home/...` no Windows.

#### Scenario: Windows com bench no WSL2

- **WHEN** a ferramenta roda no Windows e o bench está numa distribuição do WSL2
- **THEN** os comandos executam por `wsl.exe` e os arquivos do bench são lidos pelo caminho `\\wsl.localhost\<distro>\...`

#### Scenario: Linux com bench local

- **WHEN** a ferramenta roda em Linux e o bench está no mesmo sistema
- **THEN** os comandos executam diretamente, sem `wsl.exe`, e os arquivos são lidos pelo caminho nativo

#### Scenario: Windows sem WSL

- **WHEN** a ferramenta roda no Windows e não encontra o `wsl.exe` nem um bench acessível
- **THEN** ela informa que o ERP precisa do WSL2 no Windows, explica como obtê-lo e não tenta executar o bench

### Requirement: Caminho do computador e caminho do bench nunca se misturam

As ferramentas SHALL representar o caminho do computador onde a janela roda e o caminho do bench com tipos distintos, e SHALL tratar o caminho do bench como caminho Linux em qualquer sistema. Uma conversão entre os dois SHALL passar por uma função única que a documenta e a testa.

#### Scenario: Caminho Linux em máquina Windows

- **WHEN** o bench está em `/home/usuario/frappe-bench` numa distribuição chamada `Ubuntu`
- **THEN** o computador Windows o enxerga como `\\wsl.localhost\Ubuntu\home\usuario\frappe-bench`, e o comando executado dentro do WSL2 usa o caminho Linux original

### Requirement: O que só existe em um sistema declara a alternativa ou a indisponibilidade

Quando um recurso existir em um sistema e não no outro (sinais de processo, leitura de `/proc`, permissão de arquivo `0600`), a ferramenta SHALL usar o equivalente documentado ou SHALL declarar o recurso como indisponível naquele sistema, com o motivo. A ferramenta MUST NOT falhar em silêncio nem registrar um valor falso.

#### Scenario: Permissão de arquivo no Windows

- **WHEN** a ferramenta cria um arquivo de estado no Windows
- **THEN** ela não tenta aplicar permissão POSIX, e a documentação diz que vale o controle de acesso da pasta do usuário

#### Scenario: Métrica indisponível

- **WHEN** uma métrica só pode ser lida por `/proc` e a ferramenta roda no Windows fora do WSL2
- **THEN** a métrica aparece como indisponível com o motivo, e não como zero

### Requirement: O Chantilly mede o computador Windows e o ambiente do bench separadamente

Quando a interface roda no Windows com o bench no WSL2, o Chantilly SHALL medir o computador Windows (CPU, memória e disco) por meios da biblioteca padrão e SHALL medir o ambiente do bench (processos, carga, disco da distribuição) dentro do WSL2, apresentando as duas fontes identificadas, sem somá-las nem confundi-las.

#### Scenario: Duas fontes identificadas

- **WHEN** a visão geral do Chantilly é aberta num Windows com o bench no WSL2
- **THEN** CPU, memória e disco aparecem separados em "computador Windows" e "ambiente do bench (WSL2)"

### Requirement: Em Linux sem ambiente gráfico, o terminal é completo

Em um sistema sem ambiente gráfico, as ferramentas SHALL oferecer todos os comandos de terminal previstos para a ferramenta e, ao serem iniciadas em modo gráfico, SHALL informar que não há display e como instalar o suporte (`python3-tk`) ou usar o terminal.

#### Scenario: Servidor sem display

- **WHEN** o usuário inicia a interface num Linux sem display
- **THEN** a ferramenta informa a ausência do ambiente gráfico e lista os comandos de terminal equivalentes

### Requirement: A compatibilidade é conferida em ambos os sistemas pelo CI

O CI SHALL executar a suíte pura e os testes do Cherry, do Soda e do Chantilly em Windows e em Linux. Um defeito que apareça em apenas um dos sistemas SHALL fazer o CI falhar nesse sistema.

#### Scenario: Defeito só no Windows

- **WHEN** uma mudança passa em Linux e falha em Windows
- **THEN** o job do Windows falha e o PR não é considerado verde

### Requirement: O ERP no Windows é o ERP no WSL2, e isso é dito

A documentação SHALL afirmar que o ERPNext e o Frappe não são suportados nativamente no Windows e que, no Windows, o ERP roda no WSL2. A documentação MUST NOT prometer execução nativa do ERP no Windows.

#### Scenario: Tabela de compatibilidade

- **WHEN** o usuário consulta a documentação de compatibilidade
- **THEN** ela mostra, para cada ferramenta e para o ERP, o que funciona em Windows com WSL2, em Windows sem WSL e em Linux
