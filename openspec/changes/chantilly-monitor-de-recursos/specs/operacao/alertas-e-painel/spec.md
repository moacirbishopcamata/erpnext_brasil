## Purpose

Avisar a tempo quando um recurso se aproxima do limite e apresentar a situação numa interface desktop profissional, com o mesmo padrão de UX, aparência e comportamento do Cherry.

## ADDED Requirements

### Requirement: Os recursos têm limiares com histerese e sem repetição

O Chantilly SHALL avaliar o espaço livre em disco, a memória disponível, o uso de memória de troca e a CPU sustentada contra limiares configuráveis, classificando cada recurso como saudável, em atenção ou crítico. Um alerta SHALL ser emitido na mudança de estado para pior e SHALL NOT ser repetido enquanto o estado persistir, dentro de uma janela configurável.

#### Scenario: Disco entra em atenção

- **WHEN** o espaço livre de um volume do bench cai abaixo do limiar de atenção
- **THEN** o Chantilly emite um alerta nomeando o volume e o espaço livre, uma única vez

#### Scenario: Histerese evita oscilação

- **WHEN** o espaço livre oscila em torno do limiar
- **THEN** o estado só volta a saudável depois que o espaço ultrapassa o limiar somado à margem de histerese, e nenhum alerta novo é emitido durante a oscilação

### Requirement: O esgotamento do disco é projetado

O Chantilly SHALL projetar, por tendência linear sobre os últimos 14 dias de amostras, em quantos dias o espaço livre de cada volume chegará a zero, e SHALL alertar quando a projeção ficar abaixo de um prazo configurável (padrão 30 dias). A projeção SHALL ser identificada como projeção, e SHALL NOT ser calculada com menos de 3 dias de dados.

#### Scenario: Crescimento projetado

- **WHEN** o armazenamento cresce de forma estável e a tendência indica esgotamento em 20 dias
- **THEN** o Chantilly alerta com o número de dias projetado e a taxa de crescimento diária

#### Scenario: Dados insuficientes

- **WHEN** há menos de 3 dias de amostras do volume
- **THEN** o Chantilly informa que ainda não há dados para projetar, e não exibe prazo

### Requirement: O coletor parado é um estado visível

O Chantilly SHALL considerar o coletor parado quando não houver amostra nova por três intervalos de amostragem, e SHALL exibir esse estado, junto da idade da última amostra, em lugar de exibir os últimos valores como se fossem atuais.

#### Scenario: Dados velhos não passam por atuais

- **WHEN** a última amostra tem mais de três intervalos de idade
- **THEN** a interface mostra "coletor parado" e a idade da última amostra, e não classifica os recursos como saudáveis

### Requirement: Os alertas usam o canal que o aplicativo já tem

O Chantilly SHALL entregar os alertas aos responsáveis pelo mesmo canal de notificação dos demais alertas do ERPNext Brasil, por um job agendado que lê a série, sem exigir que a interface esteja aberta.

#### Scenario: Alerta sem a interface aberta

- **WHEN** um recurso fica crítico com a interface do Chantilly fechada
- **THEN** o job agendado emite o alerta pelo canal de notificação do aplicativo

### Requirement: A interface segue o contrato de UX do Cherry

A interface do Chantilly SHALL ser uma aplicação desktop que usa apenas a biblioteca padrão e segue o mesmo contrato de UX da interface do Cherry: abas com nome específico e uma instrução principal imperativa por aba; sucesso comunicado na barra de estado e por uma marca que some sozinha, com caixa de diálogo apenas para problema; vocabulário que não culpa o usuário; foco inicial no primeiro campo, Enter acionando a ação da aba e teclas de acesso; confirmação apenas para ação com consequência; nitidez em telas de alta densidade; janela redimensionável com tamanho mínimo, geometria lembrada e validada contra a área visível da tela.

#### Scenario: Teclado completo

- **WHEN** o usuário abre cada aba e usa apenas o teclado
- **THEN** o foco inicial está no primeiro controle, Tab percorre os controles na ordem de leitura, Enter aciona a ação principal da aba e as teclas de acesso funcionam

#### Scenario: Geometria fora da tela é descartada

- **WHEN** a geometria salva posiciona a janela fora da área visível (por troca de monitor ou resolução)
- **THEN** a janela abre centralizada com o tamanho mínimo, e a geometria inválida não é aplicada

### Requirement: A interface é clara à primeira vista

A interface SHALL apresentar, na primeira aba, uma visão geral com um cartão por recurso (CPU, memória, disco), cada um com o valor atual, uma série temporal recente, o estado (saudável, atenção, crítico) e, para o disco, a projeção de esgotamento. O estado SHALL ser comunicado por texto e ícone além da cor. Gráficos SHALL ser desenhados sem dependência fora da biblioteca padrão, com eixos rotulados e unidades, e SHALL usar uma paleta distinguível por quem tem daltonismo.

#### Scenario: Estado não depende só de cor

- **WHEN** um recurso está em estado crítico
- **THEN** o cartão mostra a palavra "crítico" e um ícone, além da cor

#### Scenario: Sem dados, uma instrução

- **WHEN** o bench escolhido ainda não tem nenhuma amostra
- **THEN** a visão geral mostra uma instrução de como iniciar o coletor, em lugar de gráficos vazios

### Requirement: A interface oferece gráficos para responder perguntas de operação

A interface SHALL oferecer, desenhados sem dependência fora da biblioteca padrão, os gráficos: mapa de calor de uso por hora do dia e dia da semana; uso diário dos últimos 30 dias com os horários de pico; falhas por categoria ao longo do tempo; maiores consumidores por site, endpoint e job; armazenamento empilhado por DocType com a projeção de esgotamento; e distribuição de duração das requisições e dos jobs por faixas, com os percentis 50, 95 e 99. Cada gráfico SHALL ter título que diz a pergunta que responde, eixos rotulados com unidade, legenda e o período a que se refere.

#### Scenario: Mapa de calor revela o horário de pico

- **WHEN** o usuário abre o mapa de calor de CPU de um período de quatro semanas
- **THEN** a grade mostra a média de cada combinação de hora do dia e dia da semana, a escala de cores tem legenda numérica, e a célula mais intensa é identificável pelo valor

#### Scenario: Uso diário com os picos

- **WHEN** o usuário abre o uso diário dos últimos 30 dias
- **THEN** cada dia aparece como uma barra do consumo escolhido (CPU, memória ou requisições), com o horário de pico do dia indicado

#### Scenario: Falhas ao longo do tempo

- **WHEN** o usuário abre o gráfico de falhas
- **THEN** cada dia mostra as falhas empilhadas por categoria, e a lista abaixo nomeia os métodos com mais falhas no período

#### Scenario: Armazenamento por DocType com projeção

- **WHEN** o usuário abre o gráfico de armazenamento
- **THEN** as áreas empilhadas mostram o tamanho dos maiores DocTypes ao longo do tempo, os demais agrupados em "outros", e a linha de projeção do esgotamento do volume aparece identificada como projeção

#### Scenario: Distribuição de duração

- **WHEN** o usuário abre a distribuição de duração de um endpoint
- **THEN** o gráfico mostra as faixas de duração e marca os percentis 50, 95 e 99 com os valores

### Requirement: Os gráficos são acessíveis e honestos

Os gráficos SHALL usar uma escala de cor sequencial perceptível por quem tem daltonismo, SHALL oferecer o valor numérico de cada elemento por aproximação do ponteiro e por uma tabela equivalente, e SHALL NOT usar cor como único canal de informação. Um gráfico SHALL mostrar lacunas de coleta como lacunas, e SHALL NOT interpolar nem preencher o intervalo em que o coletor esteve parado.

#### Scenario: Lacuna não é preenchida

- **WHEN** o coletor ficou parado por duas horas dentro do período exibido
- **THEN** o gráfico mostra a lacuna vazia e a identifica como "sem coleta", sem interpolar valores

#### Scenario: Valor acessível sem depender de cor

- **WHEN** o usuário passa o ponteiro sobre uma célula do mapa de calor
- **THEN** a interface mostra o valor numérico, a hora e o dia da semana, e a mesma informação está disponível na tabela equivalente

### Requirement: Operações longas não travam a janela

A interface SHALL executar fora da thread da interface qualquer operação que possa demorar (leitura de séries longas, cálculo de agregados, consulta de armazenamento), SHALL mostrar que a operação está em andamento e SHALL oferecer "Parar de esperar", descartando o resultado ao parar.

#### Scenario: Janela responde durante a leitura

- **WHEN** o usuário seleciona um período de 13 meses e a leitura demora
- **THEN** a janela continua respondendo, o botão vira "Parar de esperar" e o resultado aparece quando a leitura termina

### Requirement: Comandos de terminal espelham a interface

O Chantilly SHALL oferecer comandos de terminal para iniciar, parar, consultar o estado e gerar um relatório do coletor, com o mesmo conteúdo que a interface mostra.

#### Scenario: Estado pelo terminal

- **WHEN** o usuário executa o comando de estado
- **THEN** o terminal mostra se o coletor está em execução, a idade da última amostra e o custo do próprio Chantilly frente ao orçamento
