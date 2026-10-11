## Purpose

Fazer o Cherry identificar cada instância do ERPNext Brasil pelo UUID com o descritivo único, proteger essa identidade e deixar claro o alcance das configurações comuns do bench.

## ADDED Requirements

### Requirement: As instâncias são identificadas pelo UUID e pelo descritivo

Quando o bench tem registro do Soda, o Cherry SHALL identificar cada site de instância pelo descritivo único e pelo UUID abreviado, e SHALL mostrar a porta e o estado da instância lidos do registro, sem poder alterá-los. O Cherry SHALL oferecer o UUID completo para cópia.

#### Scenario: Aba Sites com identidade

- **WHEN** o usuário abre a aba Sites de um bench com instâncias do Soda
- **THEN** cada instância aparece com o descritivo, o UUID abreviado, a porta e o estado, e o nome do site como informação secundária

#### Scenario: Sem Soda, comportamento de antes

- **WHEN** o bench não tem registro do Soda
- **THEN** o Cherry lista os sites pelo nome, indica que não têm UUID e funciona como antes

### Requirement: A identidade da instância é protegida

O Cherry MUST NOT alterar o registro do Soda nem as chaves `soda_instance_id` e `soda_descritivo` do `site_config` de uma instância. Ao exibir o `site_config`, o Cherry SHALL mostrar essas chaves como somente leitura.

#### Scenario: Edição de site preserva a identidade

- **WHEN** o usuário liga `allow_tests` numa instância
- **THEN** o `site_config` da instância mantém inalteradas as chaves `soda_instance_id` e `soda_descritivo`

### Requirement: Configuração comum avisa que vale para todas as instâncias

Antes de gravar a configuração comum do bench (banco de dados, portas, Redis, `default_site` e `apps.txt`), o Cherry SHALL avisar que a alteração vale para todas as instâncias, listar pelo descritivo e pelo UUID abreviado as que estão no ar, e pedir confirmação quando houver instância no ar.

#### Scenario: Gravar com instância no ar

- **WHEN** o usuário grava a configuração de banco com duas instâncias no ar
- **THEN** o Cherry lista as duas pelo descritivo e pelo UUID abreviado, explica que a mudança vale para todas e pede confirmação

### Requirement: Portas das instâncias não podem ser tomadas pela configuração comum

O Cherry SHALL recusar, no formulário de portas, um valor que caia na faixa de portas alocada às instâncias do Soda ou em uma porta já alocada a uma instância, dizendo qual instância a usa.

#### Scenario: Porta de uma instância

- **WHEN** o usuário informa para o servidor web uma porta alocada a uma instância
- **THEN** o Cherry recusa e nomeia a instância pelo descritivo e pelo UUID abreviado

### Requirement: O default_site só aceita instância existente

O Cherry SHALL permitir definir o `default_site` apenas entre os sites existentes do bench, mostrando o descritivo das instâncias, e SHALL avisar quando a instância escolhida estiver parada.

#### Scenario: Escolha pelo descritivo

- **WHEN** o usuário abre a lista de `default_site` num bench com instâncias do Soda
- **THEN** a lista mostra o descritivo e o UUID abreviado de cada instância e grava o nome do site escolhido

### Requirement: Sites criados fora do Soda são sinalizados

Ao gerar o comando `bench new-site`, o Cherry SHALL avisar que um site criado fora do Soda não terá UUID nem descritivo e SHALL indicar o Soda como forma de criar instâncias.

#### Scenario: Aviso no comando gerado

- **WHEN** o usuário gera o comando `bench new-site` num bench que tem registro do Soda
- **THEN** a tela mostra o aviso de que o site não será uma instância identificada
