## Purpose

Atestar a autenticidade do laudo pela assinatura digital do biomédico responsável, com certificado ICP-Brasil pessoal, de modo que
o documento seja atribuível a uma pessoa habilitada, íntegro e datado, e verificável por terceiros.

## ADDED Requirements

### Requirement: Assinatura digital ICP-Brasil do laudo
O sistema SHALL assinar o laudo em PDF com o certificado ICP-Brasil pessoal do profissional que o libera, em formato PAdES, com
carimbo de tempo, e SHALL guardar o arquivo em PDF/A para retenção. Assinatura por imagem da assinatura manuscrita SHALL NOT valer
como assinatura do laudo.

#### Scenario: Laudo liberado
- **WHEN** o biomédico libera o laudo
- **THEN** o PDF sai assinado digitalmente com o certificado dele, com carimbo de tempo

### Requirement: Nome e registro no conselho no laudo
O sistema SHALL imprimir no laudo o nome do signatário, o conselho, o número de registro e a UF (por exemplo, CRBM), conforme o
cadastro do profissional, e SHALL recusar a assinatura quando o titular do certificado não corresponder ao profissional logado.

#### Scenario: Certificado de outra pessoa
- **WHEN** o usuário tenta assinar com um certificado cujo titular (CPF) é outro
- **THEN** a assinatura é recusada

### Requirement: Habilitação do signatário
O sistema SHALL permitir a assinatura apenas a profissional habilitado (ativo, com registro de conselho válido) e SHALL registrar
quem é o responsável técnico do laboratório no laudo. Profissional inativo ou sem registro SHALL NOT assinar.

#### Scenario: Profissional inativo
- **WHEN** um profissional inativo tenta assinar
- **THEN** a assinatura é recusada

### Requirement: Certificado válido no momento da assinatura
O sistema SHALL conferir, antes de assinar, que o certificado está dentro da validade e não revogado, e SHALL recusar a assinatura
caso contrário. A validade do certificado no momento da assinatura SHALL ficar registrada, para que um laudo assinado permaneça
verificável depois da expiração do certificado.

#### Scenario: Certificado expirado
- **WHEN** o certificado do signatário está expirado
- **THEN** a assinatura é recusada e o motivo é informado

### Requirement: Assinatura de lote de resultados autoverificados
O sistema SHALL permitir ao biomédico responsável assinar um lote de resultados autoverificados, e cada laudo gerado SHALL referenciar
a assinatura do lote, a versão da regra de autoverificação aplicada e quem a aprovou. O laudo SHALL declarar que o resultado foi
autoverificado.

#### Scenario: Laudo autoverificado
- **WHEN** um laudo é liberado por autoverificação
- **THEN** ele traz "autoverificado pela regra v<N>, aprovada por <nome e registro>" e referencia o lote assinado

### Requirement: Provedores de assinatura por porta
O sistema SHALL assinar por uma interface de provedor com implementação própria para certificado A1 em arquivo e adaptadores para A3 e
para assinatura em nuvem. A chave privada SHALL NOT ser armazenada em claro nem registrada em log.

#### Scenario: Troca de provedor
- **WHEN** o serviço troca de certificado A1 para assinatura em nuvem
- **THEN** a regra de assinatura permanece a mesma e só o adaptador muda

### Requirement: Retificação reassina em novo laudo
O sistema SHALL assinar a retificação como novo documento, ligado ao anterior, sem alterar o PDF assinado original.

#### Scenario: Laudo retificado
- **WHEN** um laudo é retificado
- **THEN** o PDF original permanece com a assinatura original e um novo PDF assinado referencia o anterior
