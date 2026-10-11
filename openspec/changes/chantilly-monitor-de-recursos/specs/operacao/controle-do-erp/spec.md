## Purpose

Permitir que o usuário inicie e pare o ERP do bench de forma explícita, graciosa e registrada, sem nunca agir sozinho e sem interromper emissões fiscais em trânsito sem aviso.

## ADDED Requirements

### Requirement: Iniciar o ERP reaproveita o procedimento de subida do projeto

O Chantilly SHALL iniciar a pilha do bench selecionado pelo mesmo procedimento idempotente que o projeto já usa para subi-la, mostrando ao usuário o comando exato antes de executá-lo e reportando cada etapa. Se a pilha já estiver no ar, o Chantilly MUST informar isso e MUST NOT iniciar processos duplicados.

#### Scenario: Início com a pilha parada

- **WHEN** o usuário confirma o início e nenhum processo do ERP está em execução
- **THEN** o Chantilly executa o procedimento de subida, mostra o progresso das etapas e informa quando o servidor passa a responder

#### Scenario: Início com a pilha já no ar

- **WHEN** o usuário pede o início e o ERP já está em execução
- **THEN** o Chantilly informa que já está no ar e não executa a subida

### Requirement: Parar o ERP é gentil por padrão

O Chantilly SHALL parar o ERP em etapas que não surpreendem quem o usa: (1) avisar os usuários conectados, com uma antecedência configurável (padrão 2 min, dispensada quando não houver ninguém conectado); (2) colocar os sites em modo de manutenção **somente leitura**, de modo que quem consulta continue consultando e ninguém grave; (3) deixar o agendador de enfileirar novos jobs; (4) aguardar a conclusão dos jobs em fila e em execução até um prazo configurável (padrão 120 s); (5) encerrar o servidor web, os trabalhadores, o agendador e o socket.io com um pedido de término educado, sem sinal brusco. O Chantilly SHALL mostrar o progresso e o que ainda está em execução. Esgotado o prazo, o Chantilly SHALL oferecer continuar esperando, cancelar a parada ou, só mediante uma confirmação separada que nomeia o que será interrompido, forçar o encerramento. O encerramento forçado MUST NOT ser a ação padrão de nenhum botão nem comando.

#### Scenario: Parada sem jobs em andamento

- **WHEN** o usuário confirma a parada e nenhum job está em fila nem em execução
- **THEN** os sites entram em manutenção somente leitura, os processos do ERP são encerrados em ordem com pedido de término educado e o Chantilly informa que o ERP parou

#### Scenario: Aviso antes de interromper o trabalho dos usuários

- **WHEN** há usuários conectados e a antecedência configurada é de 2 minutos
- **THEN** o Chantilly envia o aviso a todos os usuários conectados, mostra a contagem regressiva ao operador e só então inicia a manutenção

#### Scenario: Quem consulta continua consultando

- **WHEN** os sites entram em manutenção durante a parada
- **THEN** as leituras continuam respondendo e as gravações são recusadas com a mensagem de manutenção do ERP

#### Scenario: Prazo esgotado não força sozinho

- **WHEN** há um job em execução quando o prazo termina
- **THEN** o Chantilly não encerra o job, nomeia o job e oferece continuar esperando, cancelar a parada ou forçar, e só força depois da confirmação separada

#### Scenario: Cancelar a parada devolve o sistema ao normal

- **WHEN** o usuário cancela a parada depois de iniciada a manutenção
- **THEN** o Chantilly desliga a manutenção que ele mesmo ligou e o ERP volta a aceitar gravações

### Requirement: Antes de parar, o que está em trânsito é mostrado

Antes de qualquer parada, o Chantilly SHALL consultar e apresentar o número de requisições e jobs em andamento e as operações fiscais em trânsito: transmissões fiscais ainda sem desfecho, lotes do eSocial em transmissão e pendências da NFC-e. Com operação fiscal em trânsito, o Chantilly MUST NOT parar por padrão e SHALL oferecer esperar ou interromper mesmo assim, esta segunda opção mediante confirmação que nomeia a quantidade e o tipo.

#### Scenario: Transmissão fiscal em trânsito

- **WHEN** o usuário pede a parada e existe uma transmissão fiscal sem desfecho
- **THEN** a parada não prossegue por padrão, e o Chantilly mostra a transmissão e oferece esperar ou interromper mesmo assim

#### Scenario: Nada em trânsito

- **WHEN** não há operação fiscal em trânsito nem job em andamento
- **THEN** o Chantilly informa que a parada é segura e pede a confirmação simples

### Requirement: Banco de dados e Redis só param por pedido explícito

O Chantilly MUST NOT parar o servidor de banco de dados nem o Redis na parada padrão. O usuário SHALL poder pedir essa parada separadamente; nesse caso o Chantilly MUST avisar que outros sites ou benches podem compartilhar o servidor e SHALL mostrar o número de conexões abertas antes de pedir a confirmação.

#### Scenario: Parada padrão preserva o banco

- **WHEN** o usuário confirma a parada padrão
- **THEN** o servidor de banco de dados e o Redis continuam em execução

#### Scenario: Parar o banco mostra as conexões

- **WHEN** o usuário pede também a parada do servidor de banco de dados
- **THEN** o Chantilly mostra o número de conexões abertas e o aviso de compartilhamento, e só prossegue após a confirmação

### Requirement: O controle nunca é automático

O Chantilly MUST NOT iniciar, parar ou reiniciar o ERP em resposta a alerta, falha, limiar, agenda ou ausência de processo. Cada ação de controle SHALL exigir um pedido explícito do usuário, pela interface ou por comando de terminal com a confirmação indicada no próprio comando.

#### Scenario: Alerta crítico não reinicia nada

- **WHEN** a memória chega ao estado crítico ou um processo cai
- **THEN** o Chantilly alerta e não executa nenhuma ação de controle

### Requirement: O Chantilly só desfaz a manutenção que ele mesmo ligou

O Chantilly SHALL registrar quais sites ele colocou em manutenção, e ao iniciar o ERP ou cancelar a parada SHALL desligar a manutenção somente desses sites. Um site que já estava em manutenção por decisão do administrador MUST permanecer em manutenção.

#### Scenario: Manutenção do administrador é preservada

- **WHEN** um site já estava em manutenção antes da parada e o ERP é iniciado pelo Chantilly
- **THEN** o site continua em manutenção e o Chantilly informa isso

### Requirement: Cada ação de controle é registrada

O Chantilly SHALL registrar em arquivo local de acréscimo cada início, parada, parada forçada e recusa: data e hora, ação, usuário do sistema operacional, bench, resultado e o motivo informado pelo usuário, quando houver. O registro MUST NOT conter senha, segredo nem conteúdo de documento.

#### Scenario: Parada registrada

- **WHEN** o ERP é parado pelo Chantilly
- **THEN** o registro ganha uma linha com a data, o usuário do sistema, a ação, o bench e o resultado

### Requirement: Parada planejada é distinta de falha

Enquanto uma parada pedida pelo usuário estiver em vigor, o Chantilly SHALL manter a coleta, marcar o intervalo como "parada planejada" nas séries e nos gráficos, SHALL NOT contar a ausência dos processos como falha nem emitir alerta de processo ausente, e SHALL encerrar essa marca quando o ERP for iniciado.

#### Scenario: Ausência durante a parada planejada

- **WHEN** o ERP foi parado pelo usuário e o coletor amostra sem os processos do ERP
- **THEN** o intervalo aparece como "parada planejada", nenhuma queda de processo é contada e nenhum alerta é emitido

#### Scenario: Retorno encerra a marca

- **WHEN** o ERP é iniciado pelo Chantilly e os processos voltam
- **THEN** a marca de parada planejada termina e a coleta volta ao tratamento normal

### Requirement: O controle age só no bench escolhido e só nos seus processos

O Chantilly SHALL identificar os processos a parar pelo identificador de processo e pelo diretório do bench selecionado, lidos do sistema, e MUST NOT selecionar processos por padrão de nome na linha de comando. Processos de outros benches MUST NOT ser afetados.

#### Scenario: Dois benches na mesma máquina

- **WHEN** existem dois benches em execução e o usuário para o selecionado
- **THEN** apenas os processos cujo diretório de trabalho pertence ao bench selecionado são encerrados

### Requirement: Pilha gerenciada por supervisor ou systemd é recusada

Quando os processos do ERP estiverem sob um gerenciador de serviços (supervisor ou systemd), o Chantilly SHALL recusar iniciar e parar, explicar o motivo e indicar que o controle deve ser feito pelo gerenciador.

#### Scenario: Recusa em produção gerenciada

- **WHEN** o processo do servidor web tem o supervisor como processo pai
- **THEN** o Chantilly recusa a ação, informa o gerenciador detectado e não envia nenhum sinal

### Requirement: Operações de controle não travam a janela e não expõem segredo

A interface SHALL executar iniciar e parar fora da thread da interface, mostrar a saída em tempo real e permitir interromper a espera sem perder o registro do que já foi feito. O Chantilly MUST NOT passar senha ou segredo como argumento de processo ao executar o controle, e o executor de comandos SHALL ser substituível para teste.

#### Scenario: Janela responde durante a parada

- **WHEN** a parada gradual está aguardando um job terminar
- **THEN** a janela continua respondendo e mostra o job aguardado e o tempo restante do prazo
