## Purpose

Fazer do Cherry o dono da configuração de banco de dados (MariaDB e/ou PostgreSQL) do bench, por meio de perfis nomeados, de modo que o Soda e o Chantilly consumam a escolha sem decidi-la.

## ADDED Requirements

### Requirement: O Cherry mantém perfis de banco nomeados

O Cherry SHALL manter, por bench, perfis de banco de dados com nome único, tipo (`mariadb` ou `postgres`), host, porta e usuário administrador. O nome do perfil MUST ser único sem diferença de maiúsculas. O Cherry MUST NOT persistir senha em nenhum perfil nem em nenhum formato de persistência.

#### Scenario: Dois perfis no mesmo bench

- **WHEN** o usuário cria um perfil MariaDB e um perfil PostgreSQL
- **THEN** o Cherry guarda os dois, cada um com host, porta e usuário, sem nenhuma senha

#### Scenario: Nome repetido

- **WHEN** o usuário cria um perfil com nome que difere de outro só por maiúsculas
- **THEN** o Cherry recusa e informa o perfil existente

### Requirement: Existe exatamente um perfil padrão

O Cherry SHALL manter exatamente um perfil padrão quando houver ao menos um perfil. O perfil padrão SHALL ser gravado no `common_site_config.json` do bench (`db_type`, `db_host`, `db_port` e `root_login`), de modo que um `bench new-site` sem opções de banco continue funcionando.

#### Scenario: Troca do padrão

- **WHEN** o usuário define o perfil PostgreSQL como padrão
- **THEN** o `common_site_config.json` passa a ter `db_type` `postgres` com o host, a porta e o usuário desse perfil, e o perfil anterior deixa de ser o padrão

#### Scenario: Único perfil é o padrão

- **WHEN** existe um só perfil
- **THEN** ele é o padrão e não pode ficar sem padrão

### Requirement: Um bench existente vira o perfil padrão

Na primeira abertura de um bench que já tem configuração de banco no `common_site_config.json` e nenhum perfil, o Cherry SHALL criar um perfil padrão a partir dela, sem alterar o arquivo.

#### Scenario: Migração da configuração atual

- **WHEN** o Cherry abre um bench com `db_type` `mariadb` e `db_host` `127.0.0.1` e sem perfis
- **THEN** ele cria o perfil padrão com esses valores e o `common_site_config.json` permanece idêntico

### Requirement: O teste de conexão vale por perfil

O Cherry SHALL testar a conexão de um perfil com a senha informada no momento, SHALL guardar no perfil apenas o resultado do último teste (data, nível alcançado e sucesso ou não) e MUST NOT guardar a senha usada.

#### Scenario: Resultado guardado sem senha

- **WHEN** o usuário testa a conexão de um perfil informando a senha
- **THEN** o perfil passa a mostrar a data, o nível e o resultado do teste, e nenhum registro do Cherry contém a senha

### Requirement: Os perfis são publicados somente para leitura

O Cherry SHALL publicar os perfis do bench para leitura por outras ferramentas, por um leitor somente leitura que não toma a trava de escrita. O Cherry SHALL ser o único escritor dos perfis. Uma ferramenta consumidora SHALL receber apenas nome, tipo, host, porta, usuário administrador, indicação de padrão e resultado do último teste.

#### Scenario: O Soda lista os perfis

- **WHEN** o Soda lê os perfis de um bench
- **THEN** ele recebe a lista de perfis sem senha, com o padrão indicado

#### Scenario: Consumidor não escreve

- **WHEN** uma ferramenta consumidora tenta gravar um perfil
- **THEN** o leitor não oferece operação de escrita

### Requirement: Perfil em uso por instância não é removido nem muda de tipo

O Cherry MUST NOT remover um perfil que alguma instância do Soda usa, nem trocar o tipo ou o servidor dele. Ao recusar, o Cherry SHALL listar as instâncias que o usam pelo descritivo e pelo UUID abreviado.

#### Scenario: Remoção recusada

- **WHEN** o usuário tenta remover um perfil usado por duas instâncias
- **THEN** o Cherry recusa e lista as duas pelo descritivo e pelo UUID abreviado

### Requirement: O comando new-site usa o perfil escolhido

O comando `bench new-site` gerado pelo Cherry SHALL usar o tipo, o host, a porta e o usuário do perfil escolhido, e MUST NOT conter a senha como argumento visível quando executado por outra ferramenta.

#### Scenario: Comando do perfil PostgreSQL

- **WHEN** o usuário gera o comando com o perfil PostgreSQL selecionado
- **THEN** o comando traz `--db-type postgres` e o host, a porta e o usuário desse perfil
