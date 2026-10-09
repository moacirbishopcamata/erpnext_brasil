## Purpose

Faz o cadastro de endereços brasileiros obedecer às regras do IBGE e ao formato brasileiro, para que o
município que entra num documento fiscal seja um município de verdade e coerente com a UF.

## ADDED Requirements

### Requirement: O código de município é conferido pelo dígito verificador

O sistema SHALL recusar, ao gravar um endereço do Brasil, um código de município do IBGE cujo sétimo
dígito não seja o dígito verificador dos seis primeiros, informando o dígito esperado.

#### Scenario: Código com dígito verificador correto

- **WHEN** um endereço do Brasil é gravado com um código de município de sete dígitos de dígito verificador correto
- **THEN** o endereço é gravado

#### Scenario: Um dígito trocado

- **WHEN** um endereço é gravado com um código de município em que um dígito foi trocado
- **THEN** a gravação é recusada com mensagem em pt-BR que informa o dígito verificador esperado
- **AND** o código de erro é o mesmo da recusa por código malformado

#### Scenario: Município real que não obedece à regra

- **WHEN** o endereço informa o código de um dos municípios que a lista oficial do IBGE registra com dígito verificador fora da regra
- **THEN** o endereço é gravado
- **AND** o aviso de dígito verificador não é emitido

#### Scenario: Exceção adicional configurada pelo administrador

- **WHEN** o administrador acrescenta um código à lista de exceções da instalação
- **THEN** esse código é aceito sem a conferência do dígito verificador
- **AND** um valor da configuração que não seja uma lista de códigos de sete dígitos é recusado com mensagem que nomeia a chave

#### Scenario: Código malformado continua recusado

- **WHEN** o código não tem sete dígitos numéricos
- **THEN** a gravação é recusada como antes

### Requirement: O município pertence à UF do endereço

O sistema SHALL recusar um endereço cujo código de município pertença a uma UF diferente da UF
informada no próprio endereço.

#### Scenario: Município de outra UF

- **WHEN** o endereço informa a UF "SP" e o código de município começa com o código de Rondônia
- **THEN** a gravação é recusada com mensagem que nomeia as duas UFs

#### Scenario: UF não informada ou não reconhecida

- **WHEN** o endereço não informa UF, ou o texto não corresponde a nenhuma UF
- **THEN** a conferência de coerência não se aplica e o dígito verificador continua sendo exigido

#### Scenario: Endereço fora do Brasil

- **WHEN** o país do endereço não é o Brasil
- **THEN** nenhuma conferência de município é feita

### Requirement: O endereço é exibido no formato brasileiro

O sistema SHALL, num site que não tem modelo de endereço para o Brasil, instalar um modelo que exiba
logradouro, número, complemento, bairro, cidade com UF e CEP, sem sobrescrever um modelo já existente.

#### Scenario: Site sem modelo para o Brasil

- **WHEN** a instalação ou a migração roda num site sem modelo de endereço para o Brasil
- **THEN** um modelo brasileiro é criado
- **AND** o número e o bairro do endereço aparecem no texto formatado

#### Scenario: Site com modelo próprio

- **WHEN** o site já tem um modelo de endereço para o Brasil
- **THEN** o modelo existente é preservado sem alteração

#### Scenario: Reexecução

- **WHEN** a migração roda novamente
- **THEN** nenhum modelo duplicado é criado
