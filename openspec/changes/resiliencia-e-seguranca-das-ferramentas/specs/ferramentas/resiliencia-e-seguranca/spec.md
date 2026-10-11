## Purpose

Estabelecer, para o Cherry, o Soda e o Chantilly, critérios verificáveis de resiliência, robustez e segurança, porque as três ferramentas alteram o ambiente e uma falha delas custa dado, segredo ou o ERP no ar.

## ADDED Requirements

### Requirement: Toda operação que altera o ambiente é desfazível ou retomável

Uma operação com mais de um passo que altera o ambiente (criar instância, remover instância, trocar de formato de persistência, parar o ERP) SHALL registrar a intenção antes do primeiro passo, SHALL desfazer apenas o que os passos já executados fizeram quando um passo falhar, e SHALL deixar rastro suficiente para que, depois de uma interrupção (queda de energia, janela fechada, perda de conexão), a ferramenta mostre o estado "interrompida" e ofereça desfazer ou retomar.

#### Scenario: Falha no terceiro passo

- **WHEN** o terceiro de cinco passos de uma operação falha
- **THEN** os dois primeiros são desfeitos, o terceiro não deixa resto, e o estado final é igual ao inicial

#### Scenario: Interrupção no meio

- **WHEN** a ferramenta é encerrada à força no meio de uma operação
- **THEN** na abertura seguinte a operação aparece como interrompida, com o último passo concluído, e a ferramenta oferece desfazer ou retomar

### Requirement: As operações repetidas são seguras

Iniciar o que já está no ar, criar o que já existe, migrar o que já foi migrado e gravar o mesmo valor duas vezes SHALL ter o mesmo resultado final que fazer uma vez, sem duplicar processo, registro nem efeito.

#### Scenario: Repetição não duplica

- **WHEN** o usuário aciona duas vezes seguidas a mesma operação idempotente
- **THEN** o estado final é igual ao de uma só execução e nenhuma duplicidade é criada

### Requirement: Todo comando externo tem prazo e é interrompível

Toda chamada a um comando externo (`wsl`, `bench`, `ps`, leitura de arquivo em compartilhamento de rede) SHALL ter um prazo máximo, SHALL ter a saída capturada dentro de um limite de tamanho, e SHALL poder ser abandonada pelo usuário sem deixar a interface travada. Esgotado o prazo, a ferramenta SHALL informar qual comando e quanto esperou.

#### Scenario: Comando que não termina

- **WHEN** um comando externo não termina dentro do prazo
- **THEN** a ferramenta o abandona, informa o comando e o prazo, e a interface continua respondendo

#### Scenario: Saída enorme

- **WHEN** um comando produz mais saída do que o limite
- **THEN** a ferramenta guarda apenas o limite, indica que a saída foi truncada e não consome memória sem fim

### Requirement: Nenhuma exceção chega sem tratamento à janela

A interface SHALL tratar qualquer exceção levantada num callback, convertendo-a numa mensagem em linguagem do usuário e num registro técnico, e SHALL manter a janela utilizável. Uma exceção inesperada MUST NOT fechar a ferramenta nem deixar uma operação em andamento sem desfecho.

#### Scenario: Exceção inesperada num botão

- **WHEN** o tratamento de um clique levanta uma exceção não prevista
- **THEN** a janela mostra uma mensagem de problema, registra o detalhe técnico e continua respondendo

### Requirement: Toda entrada externa é validada na fronteira

Toda entrada de fora (campos da tela, argumentos de terminal, arquivos de configuração, saída de comandos, conteúdo de `/proc`, JSON de terceiros) SHALL ser validada na fronteira, com limites de tamanho, de quantidade e de formato, antes de chegar à regra. Entrada malformada SHALL resultar numa recusa clara, nunca numa exceção sem tratamento, num laço sem fim ou num valor aceito por engano. Os leitores de texto externo SHALL ser exercitados por testes com entradas malformadas e aleatórias de semente fixa.

#### Scenario: Conteúdo de /proc malformado

- **WHEN** um arquivo de `/proc` vem truncado, vazio ou com campos fora do formato
- **THEN** o leitor devolve "indisponível" para a métrica com o motivo, sem levantar exceção

#### Scenario: Entrada aleatória

- **WHEN** um leitor de texto externo recebe mil entradas aleatórias de semente fixa
- **THEN** nenhuma produz exceção não tratada e nenhuma é aceita como válida sem passar na validação

### Requirement: Segredos nunca vazam

Senha, token e chave MUST NOT aparecer em argumento de processo, em arquivo de persistência, em registro de log, em mensagem de erro, em texto exibido na tela nem na área de transferência além do tempo configurado. Todo texto de erro e de registro SHALL passar por um redator que mascara valores de segredo conhecidos antes de ser exibido ou gravado.

#### Scenario: Erro de comando com segredo

- **WHEN** um comando falha e sua mensagem contém a senha usada
- **THEN** o texto exibido e o registro gravado mostram o valor mascarado

### Requirement: Comandos são listas de argumentos, nunca texto de shell

As ferramentas SHALL montar todo comando externo como uma lista de argumentos, MUST NOT usar `shell=True`, `os.system`, `eval`, `exec` nem desserialização insegura, e MUST NOT concatenar texto de usuário num comando. O texto de comando que a ferramenta mostra ou copia para o usuário colar num terminal SHALL usar apenas valores que passaram pelo critério de caracteres seguros ou estão entre aspas de shell.

#### Scenario: Varredura de código

- **WHEN** o teste de varredura percorre o código das ferramentas
- **THEN** ele não encontra `shell=True`, `os.system`, `eval`, `exec`, `pickle` nem `except` sem tipo

### Requirement: Caminhos são confinados

Todo caminho derivado de entrada do usuário ou de arquivo de configuração SHALL ser resolvido e conferido contra a pasta permitida, e SHALL ser recusado se sair dela por `..` ou por link simbólico. As ferramentas MUST NOT seguir link simbólico para fora do bench ao ler ou gravar.

#### Scenario: Tentativa de sair da pasta

- **WHEN** um nome de site ou de arquivo contém `..` ou aponta, por link simbólico, para fora do bench
- **THEN** a ferramenta recusa e não lê nem grava nada fora do bench

### Requirement: Arquivos de estado têm permissão restrita

Os arquivos de persistência, de registro e de trava que as ferramentas criam SHALL ter permissão de leitura e escrita apenas para o dono, nos sistemas que permitem isso, e a ferramenta SHALL avisar quando encontrar um arquivo de estado legível por outros usuários.

#### Scenario: Arquivo novo restrito

- **WHEN** a ferramenta cria um arquivo de estado em Linux ou no WSL
- **THEN** o arquivo tem permissão de leitura e escrita somente para o dono

### Requirement: Ação destrutiva falha fechada

Toda ação destrutiva (remover instância, forçar encerramento, parar o servidor de banco, descartar o formato anterior) SHALL exigir confirmação forte, SHALL recusar na dúvida (estado desconhecido, processo não identificado, permissão insuficiente) em vez de presumir, e SHALL ser registrada. Em caso de incerteza sobre o alvo, a ferramenta MUST NOT agir.

#### Scenario: Alvo não identificado

- **WHEN** a ferramenta não consegue provar que um processo pertence ao bench escolhido
- **THEN** ela não envia nenhum sinal ao processo e informa o motivo

### Requirement: Recursos locais são limitados

Registros de log, saída capturada de comandos, histórico de ações e arquivos de série SHALL ter tamanho máximo e rotação ou descarte controlado, de modo que as ferramentas nunca encham o disco nem a memória do computador onde rodam.

#### Scenario: Log com teto

- **WHEN** o registro de ações atinge o tamanho máximo
- **THEN** a ferramenta rotaciona ou descarta o mais antigo, mantém o mais recente e continua gravando

### Requirement: A qualidade é conferida por um gate

Cada mudança do Cherry, do Soda e do Chantilly SHALL terminar com um gate que confere, com a saída dos comandos, os critérios desta capability aplicáveis à mudança: desfazer e retomar, idempotência, prazos, tratamento de exceção, validação de entrada, ausência de vazamento de segredo, varredura de padrões proibidos, confinamento de caminhos, permissões e limites de recurso.

#### Scenario: Gate falha com padrão proibido

- **WHEN** alguém introduz `shell=True` em código de uma das ferramentas
- **THEN** o teste de varredura falha e nomeia o arquivo e a linha
