## Purpose

Publicar, de forma estável e somente leitura, a identidade de cada instância (UUID, descritivo único, host, porta e estado), para que o Cherry, o Chantilly e outras ferramentas falem da mesma instância pelo mesmo nome.

## ADDED Requirements

### Requirement: O registro publica a identidade das instâncias com versão de esquema

O Soda SHALL publicar, no registro do bench, para cada instância: o UUID, o descritivo único, o nome de host, a porta, o estado, o banco de dados e as datas de criação e de aposentadoria. O registro SHALL declarar a versão do seu esquema. Acrescentar um campo MUST NOT quebrar leitores existentes; remover ou renomear um campo SHALL exigir uma nova versão de esquema.

#### Scenario: Leitor ignora campo novo

- **WHEN** uma versão posterior do Soda acrescenta um campo ao registro
- **THEN** um leitor da versão anterior continua identificando as instâncias pelo UUID e pelo descritivo, ignorando o campo desconhecido

#### Scenario: Versão de esquema maior do que a conhecida

- **WHEN** o registro declara uma versão de esquema maior do que a que o leitor conhece
- **THEN** o leitor informa que a versão é mais nova, mostra o que conseguir identificar e não grava nada

### Requirement: O leitor lê o registro em qualquer formato de persistência

O leitor do contrato SHALL ler o registro tanto em JSON quanto em SQLite e SHALL devolver o mesmo resultado nos dois, sem que o consumidor precise saber qual formato está em uso.

#### Scenario: Mesmo resultado nos dois formatos

- **WHEN** o mesmo conjunto de instâncias está guardado em JSON e em SQLite
- **THEN** o leitor devolve a mesma lista de instâncias, com os mesmos UUIDs, descritivos, hosts, portas e estados

### Requirement: O site da instância carrega a própria identidade

O Soda SHALL gravar no `site_config` de cada instância o UUID (`soda_instance_id`) e o descritivo (`soda_descritivo`), e SHALL mantê-los atualizados quando o descritivo for alterado. Qualquer processo que conheça o site SHALL poder identificar a instância lendo esse `site_config`, sem depender de o Soda estar em execução.

#### Scenario: Identificação sem o Soda em execução

- **WHEN** uma ferramenta lê o `site_config` de um site de instância com o Soda fechado
- **THEN** ela obtém o UUID e o descritivo da instância

#### Scenario: Descritivo renomeado chega ao site

- **WHEN** o descritivo de uma instância é alterado
- **THEN** o `site_config` da instância passa a trazer o novo descritivo, com o mesmo UUID

### Requirement: Os consumidores só leem

O Cherry, o Chantilly e qualquer outra ferramenta SHALL ler o contrato por um leitor somente leitura. As ferramentas consumidoras MUST NOT escrever no registro do Soda nem nas chaves `soda_instance_id` e `soda_descritivo`, e o leitor MUST NOT tomar a trava de escrita do registro.

#### Scenario: Leitura não bloqueia o Soda

- **WHEN** o Chantilly lê o registro enquanto o Soda está criando uma instância
- **THEN** a leitura retorna o último registro consistente e não impede o Soda de gravar

#### Scenario: Chave protegida

- **WHEN** o Cherry exibe o `site_config` de uma instância
- **THEN** as chaves `soda_instance_id` e `soda_descritivo` aparecem como somente leitura

### Requirement: A identidade sobrevive à remoção e à renomeação

O UUID SHALL ser a chave de identidade estável das instâncias, mesmo removidas. Um consumidor que guarda histórico por instância SHALL poder associá-lo ao UUID; o descritivo SHALL ser tratado como rótulo atual. O registro SHALL manter, para instâncias removidas, o UUID, o último descritivo conhecido e a data de aposentadoria.

#### Scenario: Histórico de instância removida

- **WHEN** o Chantilly mostra o consumo passado de uma instância que foi removida
- **THEN** ele a identifica pelo UUID e pelo último descritivo conhecido, marcada como removida

#### Scenario: Histórico preso ao UUID

- **WHEN** o descritivo de uma instância é alterado
- **THEN** o histórico guardado antes da alteração continua associado à mesma instância

### Requirement: Ferramentas funcionam sem o Soda

O Cherry e o Chantilly SHALL continuar funcionando num bench que não tem registro do Soda, tratando cada site como uma instância sem UUID, identificada pelo nome do site.

#### Scenario: Bench sem Soda

- **WHEN** uma ferramenta abre um bench sem registro do Soda
- **THEN** ela lista os sites pelo nome, indica que não têm UUID e funciona como antes
