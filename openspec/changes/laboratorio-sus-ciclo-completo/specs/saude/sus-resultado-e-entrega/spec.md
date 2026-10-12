## Purpose

Fechar o ciclo devolvendo o laudo liberado à unidade solicitante e ao paciente com prazo acompanhado, e reportando-o aos sistemas
públicos (RNDS e, quando o laboratório de referência o usa, GAL), sem perder o rastro do que foi entregue.

## ADDED Requirements

### Requirement: Entrega ao solicitante com confirmação de ciência
O sistema SHALL disponibilizar o laudo liberado à unidade e ao profissional solicitantes e registrar a data e o responsável pela
ciência. Laudo sem ciência após o prazo configurado SHALL aparecer em lista de pendências de entrega.

#### Scenario: Laudo sem ciência
- **WHEN** o prazo de ciência passa sem registro
- **THEN** o exame aparece na lista de pendências de entrega da unidade solicitante

### Requirement: Tempo de resposta por etapa
O sistema SHALL calcular o tempo de cada etapa (solicitação à coleta, coleta à chegada ao laboratório, chegada à liberação,
liberação à ciência) com carimbos de relógio sincronizado, e SHALL destacar o exame cuja etapa excedeu o prazo da prioridade.

#### Scenario: Urgência atrasada
- **WHEN** uma urgência passa do prazo entre a chegada e a liberação
- **THEN** o exame é destacado como atrasado e a etapa responsável é indicada

### Requirement: Relógio sincronizado e tolerância de desvio
O sistema SHALL medir o desvio do relógio dos servidores e das estações de coleta contra uma fonte de tempo configurada e SHALL
recusar carimbar eventos de coleta e de liberação quando o desvio exceder a tolerância, em vez de gravar horário comprovadamente
errado.

#### Scenario: Estação com relógio atrasado
- **WHEN** o relógio de uma estação de coleta está além da tolerância
- **THEN** a coleta nessa estação é bloqueada com a explicação do desvio

### Requirement: Envio do resultado à RNDS no modelo REL
O sistema SHALL montar o resultado no modelo de informação REL (Portaria GM/MS 8.276/2025), com o paciente por CPF ou CNS, o CNES
do estabelecimento receptor da amostra e do executor e o responsável técnico do laboratório, e SHALL enviá-lo de forma
idempotente. Resultado sem esses dados, ou de paciente pendente de regularização, SHALL NOT ser enviado e SHALL constar de lista
de pendências com o motivo.

#### Scenario: Reenvio após falha
- **WHEN** o envio à RNDS falha por indisponibilidade e é repetido
- **THEN** o resultado é aplicado uma só vez e as tentativas ficam registradas

#### Scenario: Retificação
- **WHEN** um laudo é retificado em novo laudo
- **THEN** o sistema envia a versão nova referenciando a anterior, sem apagar a original

### Requirement: Transição com o GAL sem duplicar a verdade
O sistema SHALL, durante a transição, registrar o número da requisição do GAL ligado à solicitação e ao tubo para exame processado em
laboratório de referência que ainda use o GAL, conforme `saude/sus-equivalencia-ao-gal`. Resultado liberado no GAL SHALL NOT ser
reescrito aqui, e divergência entre os dois SHALL ir à quarentena. O módulo é o sistema principal; o GAL é o sistema legado a
substituir.

#### Scenario: Resultado divergente entre os sistemas
- **WHEN** o resultado importado do GAL difere do já registrado para o mesmo tubo
- **THEN** nenhum dos dois é sobrescrito e a divergência vai à quarentena para decisão humana

### Requirement: Consulta pelo paciente limitada e auditada
O sistema SHALL permitir ao paciente consultar apenas os próprios resultados liberados, após autenticação adequada, e SHALL
registrar cada consulta. Resultado retido, em quarentena ou com comunicação crítica pendente SHALL NOT ser exibido.

#### Scenario: Resultado retido
- **WHEN** o paciente consulta um exame cujo resultado está retido
- **THEN** o exame aparece como "em andamento", sem valor
