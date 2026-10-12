## Purpose

Receber resultados dos equipamentos de análise e enviar-lhes as ordens de trabalho de forma automática, sem perder nem duplicar
mensagem e sem nunca atribuir um resultado a uma amostra por inferência.

## ADDED Requirements

### Requirement: Protocolos suportados por leitores puros
O sistema SHALL interpretar mensagens de HL7 v2 (perfil IHE LAW: ordem `OML^O33`, resultado `OUL^R22`, e `ORU^R01`) e de CLSI
LIS01/LIS02 (ex-ASTM E1381/E1394), por leitores sem E/S que recebem bytes ou texto e devolvem estruturas. Mensagem malformada SHALL
ser retida com o motivo e a mensagem bruta, nunca descartada.

#### Scenario: Mensagem malformada
- **WHEN** chega uma mensagem que não pode ser interpretada
- **THEN** ela é guardada bruta, marcada como malformada, e um alerta é aberto sem afetar as demais

### Requirement: Transporte separado do protocolo
O sistema SHALL receber e enviar por serial, TCP e MLLP, em camada de transporte trocável, sem que o protocolo dependa do transporte.

#### Scenario: Troca de serial por TCP
- **WHEN** um analisador passa de conexão serial para TCP
- **THEN** o protocolo e as regras de casamento permanecem as mesmas

### Requirement: Armazenar e reenviar sem perda nem duplicidade
O sistema SHALL gravar a mensagem recebida em fila durável antes de confirmá-la ao equipamento, entregá-la ao núcleo em ordem por
equipamento e aplicá-la uma só vez por chave de idempotência. A chave SHALL combinar equipamento, identificador do tubo, exame,
horário de análise, valor e sinalizadores, mais o identificador de controle da mensagem quando existir.

#### Scenario: Queda do núcleo no meio da entrega
- **WHEN** o núcleo cai com mensagens na fila
- **THEN** nenhuma é perdida e, ao voltar, cada uma é aplicada uma só vez

### Requirement: Mensagem bruta preservada
O sistema SHALL guardar a mensagem bruta inalterada, com hash, e derivar o resultado dela, de modo que a interpretação possa ser
refeita e auditada.

#### Scenario: Reinterpretação
- **WHEN** a regra de interpretação é corrigida
- **THEN** o resultado pode ser rederivado da mensagem bruta guardada, sem novo envio do equipamento

### Requirement: Casamento por identificador exato do tubo
O sistema SHALL casar o resultado ao tubo apenas pelo identificador exato, validado pelo dígito de conferência. Marcação de
identificador digitado à mão no equipamento SHALL reter o resultado para conferência, e identificador desconhecido ou ambíguo SHALL
ir à quarentena.

#### Scenario: Identificador digitado no equipamento
- **WHEN** o equipamento marca o identificador como digitado à mão
- **THEN** o resultado é retido para conferência do tubo físico

### Requirement: Consulta de ordem e envio de trabalho ao equipamento
O sistema SHALL responder à consulta de ordem do equipamento com os exames pedidos para o tubo lido, usando a correspondência
cadastrada entre o exame e o código do equipamento, e SHALL responder "sem trabalho" quando não houver pedido. Exame sem
correspondência SHALL ser sinalizado, nunca presumido.

#### Scenario: Tubo sem pedido
- **WHEN** o equipamento consulta um tubo sem pedido ativo
- **THEN** o sistema responde "sem trabalho" e registra a consulta

### Requirement: Repetição e correção viram versões
O sistema SHALL tratar a repetição do exame e a correção como novas versões do resultado, sem sobrescrever a anterior, e SHALL
manter a ordem pelo horário de análise do equipamento, não pelo de chegada.

#### Scenario: Mensagens fora de ordem
- **WHEN** a repetição chega antes do resultado original
- **THEN** a ordem das versões segue o horário de análise, e nenhuma é perdida

### Requirement: Amostra de controle separada da de paciente
O sistema SHALL reconhecer identificadores de controle cadastrados e SHALL NOT anexá-los a paciente em hipótese alguma.

#### Scenario: Controle lido como amostra
- **WHEN** chega um resultado de material de controle
- **THEN** ele vai ao controle de qualidade, nunca a um paciente

### Requirement: Falha de um equipamento não afeta os outros
O sistema SHALL isolar cada equipamento em conexão e fila próprias, de modo que a queda de um não pare os demais.

#### Scenario: Um analisador cai
- **WHEN** a conexão de um analisador é perdida
- **THEN** os outros seguem recebendo, e a falha gera alerta

### Requirement: Modo sombra antes de publicar
O sistema SHALL operar cada equipamento em modo sombra (receber, interpretar e comparar sem publicar ao paciente) antes de ligar a
publicação, e SHALL registrar as divergências em relatório.

#### Scenario: Equipamento em sombra
- **WHEN** o equipamento está em modo sombra
- **THEN** os resultados são gravados e comparados, mas nenhum é liberado ou entregue

### Requirement: Canal autenticado e acesso mínimo
O sistema SHALL autenticar o serviço de interface junto ao núcleo com credencial de permissão mínima e canal cifrado.

#### Scenario: Credencial inválida
- **WHEN** o serviço de interface apresenta credencial inválida
- **THEN** o núcleo recusa a entrega e registra a tentativa
