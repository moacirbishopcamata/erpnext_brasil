## Purpose

Permitir subir o ERPNext Brasil (o ERPNext inteiro com a tropicalização brasileira) com Docker, de forma portátil entre Windows e Linux e segura por padrão.

## ADDED Requirements

### Requirement: Uma imagem traz o ERPNext e o erpnext_brasil na versão alvo

A configuração Docker SHALL produzir uma imagem que contém o Frappe, o ERPNext completo e o `erpnext_brasil` na versão 16, construída a partir de uma lista de aplicativos (`apps.json`) e de uma receita de imagem do projeto `frappe_docker` fixada por um commit. A fixação por commit SHALL ser explícita, de modo que a mesma construção produza a mesma base.

#### Scenario: Lista de aplicativos

- **WHEN** o `apps.json` padrão é lido
- **THEN** ele contém o `erpnext` e o `erpnext_brasil`, ambos na versão 16 ou na branch principal indicada, e é um JSON válido

#### Scenario: Receita fixada

- **WHEN** o comando de construção é montado
- **THEN** ele referencia a receita do `frappe_docker` por um identificador de commit completo, e não por uma branch móvel

### Requirement: Segredos nunca entram na imagem nem na linha de comando do host

A configuração Docker SHALL entregar senhas aos serviços por *Docker secrets* (arquivos montados), SHALL tratar o `apps.json` com credencial de repositório privado como *build secret*, e MUST NOT definir valor padrão de senha, nem aceitar senha por argumento de linha de comando do host. O arquivo de exemplo de variáveis MUST NOT conter nenhum segredo.

#### Scenario: Senha por arquivo

- **WHEN** o serviço de banco de dados é definido
- **THEN** ele lê a senha de root de um arquivo de segredo e não de uma variável de ambiente com o valor

#### Scenario: Credencial de repositório privado fora da imagem

- **WHEN** a imagem é construída com um `apps.json` que tem credencial
- **THEN** o arquivo é passado como *build secret* e o conteúdo da credencial não aparece nas camadas da imagem

#### Scenario: Exemplo sem segredo

- **WHEN** o `.env.example` é inspecionado
- **THEN** nenhuma variável contém senha, token ou chave

### Requirement: Os serviços escutam só o computador local por padrão

A porta web publicada SHALL escutar apenas `127.0.0.1` por padrão. Publicar em outro endereço SHALL exigir uma variável explícita. Os serviços de banco de dados e de Redis MUST NOT publicar portas no host.

#### Scenario: Porta local por padrão

- **WHEN** o Compose é resolvido com os valores padrão
- **THEN** a porta web do host está ligada a `127.0.0.1` e nenhum outro serviço publica porta

### Requirement: O Compose sobe a pilha completa e na ordem correta

O Compose SHALL definir: banco de dados, dois Redis, configurador, servidor de aplicação, proxy web, websocket, trabalhadores de fila curta e longa, agendador e um serviço de criação de site. Os serviços de aplicação SHALL esperar o banco e os Redis ficarem saudáveis e o configurador concluir. O serviço de criação de site SHALL ser separado e só executar quando solicitado.

#### Scenario: Ordem de inicialização

- **WHEN** a pilha é iniciada
- **THEN** o configurador só roda depois que o banco e os Redis estão saudáveis, e os serviços de aplicação só iniciam depois que o configurador termina com sucesso

#### Scenario: Criação de site sob demanda

- **WHEN** a pilha sobe sem o perfil de inicialização
- **THEN** nenhum site é criado, e a criação só ocorre quando o perfil de inicialização é pedido

### Requirement: O banco é MariaDB ou PostgreSQL por override, e a escolha é do Cherry

A configuração SHALL oferecer o banco de dados como um override selecionável, MariaDB ou PostgreSQL, sem alterar o arquivo base. A escolha do tipo e do servidor SHALL ser feita pelas configurações do Cherry (perfis de banco) e refletida nas variáveis do Compose, e o Compose MUST NOT decidir o banco sozinho.

#### Scenario: Override de PostgreSQL

- **WHEN** o override de PostgreSQL é combinado com o arquivo base
- **THEN** o Compose resolvido tem o serviço de banco em PostgreSQL, o configurador usa o tipo e a porta de PostgreSQL, e nenhum serviço de MariaDB

#### Scenario: Override de MariaDB

- **WHEN** o override de MariaDB é combinado com o arquivo base
- **THEN** o Compose resolvido tem o serviço de banco em MariaDB com conjunto de caracteres utf8mb4

### Requirement: A configuração é portátil entre Windows e Linux

Os arquivos Docker SHALL funcionar igualmente em Windows (Docker Desktop) e em Linux: sem caminhos do sistema do host, com volumes nomeados, com o separador de arquivos do Compose fixado, e com scripts auxiliares em Python puro que não dependem de um shell específico.

#### Scenario: Mesmo arquivo nos dois sistemas

- **WHEN** o Compose é validado em Windows e em Linux com os mesmos arquivos
- **THEN** o resultado é válido nos dois, sem alteração

### Requirement: A identidade da instância acompanha o projeto

O Compose SHALL aceitar o UUID e o descritivo de uma instância e SHALL aplicá-los como rótulos em todos os serviços de aplicação, e o nome do projeto do Compose SHALL poder ser derivado do UUID, para que várias pilhas convivam no mesmo computador sem colisão de nomes, volumes e portas.

#### Scenario: Rótulos de instância

- **WHEN** o Compose é resolvido com `SODA_INSTANCE_ID` e `SODA_DESCRITIVO`
- **THEN** os serviços de aplicação trazem esses valores como rótulos

#### Scenario: Duas pilhas no mesmo computador

- **WHEN** duas pilhas sobem com nomes de projeto e portas diferentes
- **THEN** seus volumes, redes e contêineres não colidem

### Requirement: Os scripts auxiliares falham fechado e não vazam segredo

Os scripts de apoio SHALL gerar os arquivos de segredo com valores aleatórios criptograficamente seguros, SHALL NOT sobrescrever um segredo existente, SHALL aplicar permissão restrita ao dono onde o sistema permitir, e MUST NOT imprimir os valores gerados. O script de construção SHALL montar o comando como lista de argumentos, sem shell.

#### Scenario: Segredo existente preservado

- **WHEN** o script de preparação roda e o arquivo de segredo já existe
- **THEN** o arquivo não é alterado e o script informa que o manteve

#### Scenario: Comando sem shell

- **WHEN** o script de construção monta o comando de build
- **THEN** o resultado é uma lista de argumentos e o conteúdo do `apps.json` não aparece nela

### Requirement: A configuração é validada pelo CI e por teste

O CI SHALL validar a resolução do Compose com cada combinação de banco. Os testes sem Docker SHALL conferir a estrutura dos arquivos (serviços, portas locais, ausência de segredo, JSON válido, comando de build) e o teste que usa o Docker SHALL ser pulado, com o motivo escrito, quando ele não existir.

#### Scenario: Compose inválido falha o CI

- **WHEN** um arquivo do Compose deixa de ser válido
- **THEN** o job de validação falha e nomeia o arquivo e o erro
