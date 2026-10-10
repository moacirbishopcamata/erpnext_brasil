## Purpose

Receber resultados dos analisadores e enviar-lhes as ordens sem nunca atribuir um resultado à amostra errada, aplicar a mesma
mensagem duas vezes ou perder resultado quando o ERPNext está fora do ar — com tudo carimbado por um relógio confiável.

## ADDED Requirements

### Requirement: Recepção idempotente de resultado

O sistema MUST produzir o mesmo estado ao receber a mesma mensagem de resultado uma ou várias vezes. Uma repetição MUST ser
reconhecida como repetição, MUST NOT criar resultado novo e MUST ficar registrada.

#### Scenario: Mensagem repetida

- **WHEN** o equipamento reenvia uma mensagem já recebida
- **THEN** nenhum resultado novo é criado
- **AND** o sistema registra que houve repetição

### Requirement: Resultado só se anexa por identificador exato de amostra

O sistema MUST anexar um resultado apenas ao tubo ou alíquota cujo identificador coincida exatamente com o informado pelo
equipamento. Identificador desconhecido, ambíguo ou digitado à mão no equipamento MUST levar o resultado à quarentena, e
nenhuma correspondência aproximada MUST ser aceita.

#### Scenario: Identificador desconhecido

- **WHEN** chega resultado para um identificador que não existe
- **THEN** o resultado vai para a fila de quarentena, sem paciente
- **AND** um usuário autorizado decide o destino, com registro

#### Scenario: Identificador ambíguo

- **WHEN** o identificador informado corresponde a mais de uma amostra
- **THEN** o resultado vai para a quarentena e nada é anexado

#### Scenario: Identificador digitado manualmente no equipamento

- **WHEN** o equipamento sinaliza que o identificador foi digitado e não lido por código de barras
- **THEN** o resultado fica retido para conferência antes de ser anexado

### Requirement: Dados do paciente divergentes retêm o resultado

Quando o equipamento enviar dados demográficos, o sistema MUST compará-los com o pedido e MUST reter o resultado se sexo ou
idade conflitarem.

#### Scenario: Sexo diferente do pedido

- **WHEN** a mensagem traz sexo diferente do cadastrado para o paciente do tubo
- **THEN** o resultado é retido e sinalizado, e não é liberado

### Requirement: Armazenar e reenviar sem perda nem duplicidade

O serviço de interface MUST gravar a mensagem em armazenamento durável antes de confirmá-la ao equipamento, MUST entregá-la
ao ERPNext quando este estiver disponível, e MUST reprocessar a fila em ordem, sem perder e sem duplicar, quando o ERPNext
voltar.

#### Scenario: ERPNext fora do ar

- **WHEN** o ERPNext fica indisponível por duas horas e o equipamento envia 50 resultados
- **THEN** o serviço guarda os 50 e confirma cada um ao equipamento
- **AND** quando o ERPNext volta, os 50 são entregues uma única vez, na ordem em que chegaram

#### Scenario: Queda do serviço no meio da entrega

- **WHEN** o serviço é interrompido após entregar parte da fila
- **THEN** ao reiniciar, entrega só o que falta, sem repetir o que já foi aplicado

### Requirement: Repetição de exame e correção viram versões

Uma repetição de análise ou um resultado corrigido pelo equipamento MUST ser guardado como nova versão do resultado, ligada
às anteriores. Versões anteriores MUST NOT ser apagadas, e a escolha do resultado válido MUST ser de profissional autorizado.

#### Scenario: Exame repetido

- **WHEN** o mesmo exame do mesmo tubo é repetido e dá valor diferente
- **THEN** o sistema guarda as duas versões e exige que um profissional escolha qual vale

### Requirement: Amostra de controle nunca é anexada a paciente

O sistema MUST reconhecer o material de controle pelos identificadores cadastrados para ele, MUST guardar o resultado como
controle de qualidade e MUST NOT anexá-lo a paciente. Controle fora do aceitável MUST sinalizar os resultados de paciente da
mesma corrida, conforme a política configurada do laboratório.

#### Scenario: Resultado de controle

- **WHEN** chega resultado com identificador de material de controle
- **THEN** é registrado no controle interno da qualidade, e nenhum paciente é afetado

#### Scenario: Controle reprovado

- **WHEN** o controle de uma corrida está fora dos limites
- **THEN** os resultados de paciente daquela corrida ficam sinalizados e retidos segundo a política do laboratório

### Requirement: Resposta às consultas e envio de ordens ao equipamento

Quando o equipamento consultar um tubo, o sistema MUST responder com os exames pedidos traduzidos para os códigos do
equipamento, ou com "sem trabalho" se não houver pedido. Exame sem correspondência MUST ser sinalizado, e MUST NOT ser
enviado com código presumido.

#### Scenario: Tubo com pedido

- **WHEN** o equipamento consulta um tubo com dois exames pedidos e mapeados
- **THEN** o sistema responde com os dois exames nos códigos do equipamento

#### Scenario: Tubo sem pedido

- **WHEN** o equipamento consulta um tubo sem exame para ele
- **THEN** o sistema responde "sem trabalho"

### Requirement: Carimbo por relógio sincronizado e tolerância de desvio

Toda mensagem MUST receber carimbo de recebimento por relógio sincronizado com fonte confiável, e o carimbo do equipamento
MUST ser guardado à parte. Se a diferença entre os dois passar da tolerância configurada, o sistema MUST alertar e MUST
reter os resultados afetados. Relógio do servidor sem sincronização confiável MUST impedir a liberação de resultados.

#### Scenario: Equipamento com relógio atrasado

- **WHEN** o horário do equipamento difere do de recebimento além da tolerância
- **THEN** o sistema alerta, guarda os dois horários e retém os resultados daquele equipamento

### Requirement: Falha de um equipamento não afeta os outros

A falha de conexão com um equipamento MUST ficar isolada e visível, sem interromper a comunicação com os demais.

#### Scenario: Um analisador desconecta

- **WHEN** a conexão com um analisador cai
- **THEN** o painel mostra o equipamento como desconectado e os outros continuam operando

### Requirement: Modo sombra antes de publicar

Antes de entrar em uso, cada equipamento MUST poder operar em modo sombra: os resultados são recebidos e comparados com o
processo vigente, mas não são publicados no prontuário.

#### Scenario: Comparação em paralelo

- **WHEN** um equipamento está em modo sombra
- **THEN** os resultados aparecem em relatório de divergência e nenhum é liberado ao paciente

### Requirement: Canal autenticado e acesso mínimo

O serviço de interface MUST autenticar-se no ERPNext com credencial própria de permissão mínima, MUST usar transporte
cifrado e MUST NOT gravar dado pessoal de paciente além do necessário em registros técnicos.

#### Scenario: Credencial do serviço

- **WHEN** o serviço envia um resultado
- **THEN** usa credencial dedicada que só pode lançar resultados, e não consultar ou alterar outros dados
