## Purpose

Garantir que todo exame laboratorial do SUS nasça de uma solicitação completa e identificável: paciente, unidade e profissional
solicitantes, procedimento da tabela SIGTAP, prioridade e preparo. Solicitação incompleta é recusada na origem, antes de gerar
tubo, etiqueta ou custo.

## ADDED Requirements

### Requirement: Identificação do paciente por CNS ou CPF válido
O sistema SHALL exigir, em toda solicitação, ao menos um entre CNS e CPF do paciente, validado pelo dígito verificador. Quando
o paciente não tem nenhum dos dois, o sistema SHALL aceitar a solicitação apenas por uma via explícita de "paciente sem
documento", com nome e data de nascimento ou idade, marcada como pendente de regularização.

#### Scenario: CNS com dígito inválido
- **WHEN** a solicitação traz um CNS cujo dígito verificador não confere
- **THEN** a solicitação é recusada com o motivo, sem criar exame

#### Scenario: Paciente sem documento
- **WHEN** o profissional escolhe "paciente sem documento" e informa nome e data de nascimento
- **THEN** a solicitação é aceita, marcada como pendente de regularização, e o resultado não é enviado à RNDS até a regularização

### Requirement: Unidade e profissional solicitantes identificados
O sistema SHALL registrar, em cada solicitação, o estabelecimento solicitante pelo CNES e o profissional solicitante com registro
no conselho e CBO. Solicitação sem esses dados SHALL ser recusada.

#### Scenario: Solicitação sem CNES
- **WHEN** a unidade solicitante não tem CNES cadastrado
- **THEN** a solicitação é recusada e o motivo indica o cadastro da unidade como a pendência

### Requirement: Exame identificado por procedimento SIGTAP
O sistema SHALL ligar cada exame solicitado a um procedimento SIGTAP vigente na competência da solicitação, e SHALL registrar a
competência usada. Procedimento inexistente na competência SHALL ser recusado.

#### Scenario: Procedimento fora da competência
- **WHEN** o código informado não consta na tabela SIGTAP da competência
- **THEN** a solicitação é recusada e a competência consultada é informada

### Requirement: Prioridade, preparo e hipótese diagnóstica registrados
O sistema SHALL registrar a prioridade (rotina ou urgência), o preparo exigido do paciente (por exemplo, jejum) e a hipótese
diagnóstica quando o exame depender dela. A prioridade SHALL ordenar as filas de coleta e de análise e permanecer visível em
toda etapa posterior.

#### Scenario: Urgência na fila de coleta
- **WHEN** há uma urgência e várias solicitações de rotina aguardando coleta
- **THEN** a urgência aparece primeiro e carrega a marca de urgência até o resultado

### Requirement: Origem da solicitação preservada
O sistema SHALL guardar a origem da solicitação (consulta, pronto atendimento, internação, campanha, busca ativa) e uma
referência ao atendimento de origem, sem copiar dados do atendimento além do necessário.

#### Scenario: Solicitação vinda de pronto atendimento
- **WHEN** o exame é pedido a partir de um registro de pronto atendimento
- **THEN** a solicitação referencia o registro e herda a prioridade, sem duplicar o prontuário

### Requirement: Cancelamento só antes da coleta
O sistema SHALL permitir cancelar uma solicitação apenas antes da coleta; depois dela, o encerramento SHALL ocorrer por descarte
registrado na cadeia de custódia. Solicitação cancelada SHALL NOT entrar na produção.

#### Scenario: Cancelamento depois da coleta
- **WHEN** o usuário tenta cancelar uma solicitação cujo tubo já foi coletado
- **THEN** o sistema exige o descarte do material com motivo e só então encerra a solicitação

### Requirement: Cadastros de referência por porta, sem dependência de outro módulo
O sistema SHALL obter paciente, unidade e profissional por uma interface de cadastro com implementação própria, de modo que
possa operar sem qualquer outro módulo de saúde instalado; uma ponte para outro cadastro SHALL ser um adaptador opcional.

#### Scenario: Módulo instalado sozinho
- **WHEN** o módulo é instalado sem Healthcare nem app fiscal
- **THEN** é possível cadastrar paciente, unidade e profissional e registrar uma solicitação completa
