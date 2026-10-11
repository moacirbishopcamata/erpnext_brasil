## Purpose

Criar, iniciar, parar e remover instâncias do ERPNext Brasil de forma segura e reversível, mostrando sempre o estado verdadeiro de cada uma.

## ADDED Requirements

### Requirement: Criar uma instância é tudo ou nada

O Soda SHALL criar uma instância como um site novo do bench, com banco de dados próprio no servidor de um perfil de banco configurado no Cherry, o nome de host derivado do UUID e os aplicativos escolhidos instalados. O Soda SHALL registrar a instância no estado "criando" antes de começar, e SHALL promovê-la a "parada" somente ao concluir. Se a criação falhar ou for interrompida, o Soda SHALL desfazer o que já foi criado (site e banco parciais) e liberar a porta e o nome, sem aposentar um UUID que nunca chegou a existir de fato.

#### Scenario: Criação concluída

- **WHEN** o usuário cria uma instância e todas as etapas terminam
- **THEN** a instância aparece como parada, com UUID, host, porta e aplicativos instalados, e pode ser iniciada

#### Scenario: Falha no meio da criação

- **WHEN** a instalação de um aplicativo falha durante a criação
- **THEN** o Soda remove o site e o banco parciais, libera a porta e informa a etapa que falhou

#### Scenario: Criação interrompida

- **WHEN** o Soda é fechado ou perde a conexão com o bench durante a criação
- **THEN** na próxima abertura a instância aparece como "criação interrompida" e o Soda oferece desfazer o que sobrou

### Requirement: O servidor de banco vem de um perfil configurado no Cherry

O Soda MUST NOT decidir o tipo nem o servidor de banco de dados. O Soda SHALL oferecer, para a criação, apenas os perfis de banco que o Cherry configurou no bench (MariaDB e/ou PostgreSQL), e SHALL usar o perfil escolhido, ou o padrão do Cherry, para criar o banco da instância. Sem nenhum perfil configurado, o Soda SHALL recusar a criação e indicar o Cherry. O Soda SHALL registrar no registro da instância o nome e o tipo do perfil usado.

#### Scenario: Perfil padrão do Cherry

- **WHEN** o usuário cria uma instância sem escolher perfil e o Cherry tem um perfil padrão
- **THEN** o banco da instância é criado no servidor do perfil padrão, e o registro guarda o nome e o tipo do perfil

#### Scenario: Bench com MariaDB e PostgreSQL

- **WHEN** o Cherry tem um perfil MariaDB e um perfil PostgreSQL e o usuário escolhe o PostgreSQL
- **THEN** a instância é criada com `--db-type postgres` e o host e a porta desse perfil

#### Scenario: Sem perfil configurado

- **WHEN** o Cherry ainda não configurou nenhum perfil de banco
- **THEN** o Soda recusa a criação, explica que o banco é configurado no Cherry e não cria nada

#### Scenario: Senha do servidor de banco

- **WHEN** a criação precisa da senha de administrador do servidor de banco
- **THEN** o Soda a lê da configuração do bench, quando o Cherry a gravou lá, ou a pede ao usuário no momento, e não a persiste em nenhum formato

### Requirement: A senha de administrador não trafega em argumento de processo

O Soda MUST NOT passar a senha do administrador do banco de dados nem a do administrador do ERP como argumento de processo. Quando a senha do administrador do ERP não for informada, o Soda SHALL deixar que o `bench` a pergunte, em vez de usar um valor de fábrica.

#### Scenario: Senha por ambiente

- **WHEN** o Soda executa a criação do site com senhas informadas
- **THEN** nenhum argumento da linha de comando do processo contém as senhas

### Requirement: Iniciar uma instância é idempotente e espera o servidor responder

O Soda SHALL iniciar o servidor web da instância na sua porta e SHALL garantir que os serviços compartilhados do bench (banco de dados, Redis, trabalhador de fila, agendador e socket.io) estejam no ar, iniciando-os uma única vez. O Soda SHALL considerar a instância "no ar" somente quando o servidor responder a uma requisição de verificação, dentro de um prazo configurável. Iniciar uma instância já no ar MUST NOT criar um segundo processo.

#### Scenario: Início com serviços parados

- **WHEN** o usuário inicia a primeira instância e os serviços compartilhados estão parados
- **THEN** o Soda sobe os serviços compartilhados uma vez, sobe o servidor da instância e informa a URL quando ele responde

#### Scenario: Início de uma segunda instância

- **WHEN** uma instância já está no ar e o usuário inicia outra
- **THEN** os serviços compartilhados não são reiniciados e a segunda instância sobe na sua porta

#### Scenario: Início de instância já no ar

- **WHEN** o usuário inicia uma instância que já está no ar
- **THEN** o Soda informa que já está no ar e não cria outro processo

#### Scenario: Servidor que não responde

- **WHEN** o servidor da instância não responde dentro do prazo
- **THEN** a instância é marcada como "falhou ao subir", com o trecho final do registro de saída, e o Soda não a declara no ar

### Requirement: Parar uma instância afeta somente ela

O Soda SHALL parar o servidor web de uma instância enviando-lhe um pedido de término educado e aguardando que ele conclua as requisições em andamento, e SHALL identificar o processo pelo identificador de processo e pelo registro da instância, nunca por padrão de nome na linha de comando. Parar uma instância MUST NOT afetar as outras nem os serviços compartilhados. Os serviços compartilhados SHALL ser parados apenas por pedido explícito do usuário e SHALL ser recusados enquanto houver instância no ar.

#### Scenario: Parar uma entre várias

- **WHEN** três instâncias estão no ar e o usuário para uma
- **THEN** somente o processo daquela instância termina, e as outras duas continuam respondendo

#### Scenario: Processo que ignora o pedido

- **WHEN** o servidor da instância não termina dentro do prazo
- **THEN** o Soda não o mata sozinho, informa o impasse e oferece esperar mais ou forçar o encerramento, este mediante confirmação separada

#### Scenario: Serviços compartilhados com instância no ar

- **WHEN** o usuário pede para parar os serviços compartilhados e há instância no ar
- **THEN** o Soda recusa e lista as instâncias que dependem deles

### Requirement: Remover uma instância é destrutivo e exige confirmação forte

O Soda SHALL remover uma instância somente depois de o usuário digitar o nome da instância, SHALL fazer um backup do site antes por padrão, e SHALL então apagar o site e o banco de dados, liberar a porta e aposentar o UUID. A remoção MUST NOT ser possível com a instância no ar. A opção de remover sem backup SHALL ser explícita e acompanhada de aviso.

#### Scenario: Remoção com backup

- **WHEN** o usuário digita o nome correto e confirma a remoção de uma instância parada
- **THEN** o Soda faz o backup, informa onde ele ficou, apaga o site e o banco, libera a porta e aposenta o UUID

#### Scenario: Nome errado

- **WHEN** o usuário digita um nome diferente do da instância
- **THEN** o Soda não remove nada

#### Scenario: Instância no ar

- **WHEN** o usuário pede a remoção de uma instância que está no ar
- **THEN** o Soda recusa e pede que ela seja parada primeiro

### Requirement: O estado mostrado é conciliado com a realidade

Ao abrir e a cada atualização, o Soda SHALL conferir o registro contra o sistema (processo existente, porta em escuta, site presente no bench) e SHALL mostrar o estado verdadeiro de cada instância: criando, parada, subindo, no ar, caiu, falhou ao subir ou criação interrompida. Uma instância registrada como no ar cujo processo não existe MUST ser mostrada como "caiu", e um processo de instância sem registro MUST ser mostrado como órfão, sem ser encerrado.

#### Scenario: Instância que caiu

- **WHEN** o processo de uma instância registrada como no ar deixou de existir
- **THEN** o Soda mostra a instância como "caiu", com o horário em que foi percebido

#### Scenario: Processo órfão

- **WHEN** existe um processo servindo uma porta do bloco do Soda sem instância correspondente no registro
- **THEN** o Soda o lista como órfão e não o encerra sem pedido do usuário

### Requirement: O número de instâncias tem um limite

O Soda SHALL impor um limite configurável de instâncias simultâneas no ar (padrão 8), recusando iniciar além dele com a explicação de que cada instância consome memória, e SHALL permitir ao usuário alterar o limite.

#### Scenario: Limite atingido

- **WHEN** o limite de instâncias no ar já foi atingido e o usuário inicia mais uma
- **THEN** o Soda recusa e informa o limite e como alterá-lo
