## Purpose

Apresentar e operar as instâncias numa interface desktop e em comandos de terminal com o mesmo padrão de UX, aparência e comportamento do Cherry.

## ADDED Requirements

### Requirement: A interface segue o contrato de UX do Cherry

A interface do Soda SHALL ser uma aplicação desktop que usa apenas a biblioteca padrão e SHALL seguir o mesmo contrato de UX da interface do Cherry: abas com nome específico e uma instrução principal imperativa por aba; sucesso na barra de estado e por uma marca que some sozinha, com caixa de diálogo apenas para problema; vocabulário que não culpa o usuário; foco inicial no primeiro controle, Enter acionando a ação da aba e teclas de acesso; confirmação apenas para ação com consequência; nitidez em telas de alta densidade; janela redimensionável com tamanho mínimo, geometria lembrada e validada contra a área visível da tela.

#### Scenario: Teclado completo

- **WHEN** o usuário percorre cada aba usando apenas o teclado
- **THEN** o foco inicial está no primeiro controle, Tab segue a ordem de leitura, Enter aciona a ação principal e as teclas de acesso funcionam

#### Scenario: Geometria fora da tela é descartada

- **WHEN** a geometria salva posiciona a janela fora da área visível
- **THEN** a janela abre centralizada com o tamanho mínimo

### Requirement: A lista mostra a identidade e o estado de cada instância

A aba principal SHALL listar as instâncias com o descritivo (coluna principal), o UUID abreviado, nome de host, porta, banco de dados, aplicativos, estado e, para as no ar, o tempo de atividade. O UUID completo SHALL poder ser visto e copiado. O estado SHALL ser comunicado por texto e ícone além da cor. A lista SHALL poder ser filtrada por descritivo, UUID ou estado, e SHALL oferecer "Renomear" para alterar o descritivo.

#### Scenario: UUID copiável

- **WHEN** o usuário seleciona uma instância e aciona "Copiar UUID"
- **THEN** o UUID completo vai para a área de transferência e a barra de estado confirma

#### Scenario: Estado não depende só de cor

- **WHEN** uma instância caiu
- **THEN** a linha mostra a palavra "caiu" e um ícone, além da cor

#### Scenario: Sem instâncias, uma instrução

- **WHEN** o bench escolhido ainda não tem instância
- **THEN** a lista mostra a instrução de como criar a primeira, em lugar de uma tabela vazia

### Requirement: As ações principais ficam à mão e abrem a instância

Para a instância selecionada, a interface SHALL oferecer iniciar, parar, abrir no navegador, copiar a URL, ver o registro de saída e remover, habilitando cada ação conforme o estado da instância e dizendo por que uma ação não está disponível. Abrir no navegador SHALL usar o nome de host da instância e a sua porta.

#### Scenario: Ação indisponível explica o motivo

- **WHEN** a instância está no ar e o usuário aponta para "Remover"
- **THEN** a interface informa que é preciso parar a instância primeiro

#### Scenario: Abrir no navegador

- **WHEN** o usuário aciona "Abrir" numa instância no ar
- **THEN** o navegador abre a URL com o host da instância e a porta dela

### Requirement: O formulário de criação mostra as restrições antes do envio

O formulário de criação SHALL indicar, antes do envio, o que cada campo aceita (obrigatoriedade, tamanho de 3 a 60 caracteres e unicidade do descritivo, banco de dados, aplicativos e porta opcional), SHALL espelhar no servidor as mesmas regras do núcleo, e SHALL mostrar o nome de host e a porta que serão usados antes de o usuário confirmar.

#### Scenario: Pré-visualização do que será criado

- **WHEN** o usuário preenche o descritivo e escolhe o banco
- **THEN** o formulário mostra o nome de host derivado e a porta que será alocada, antes da confirmação

### Requirement: Operações longas não travam a janela

A interface SHALL executar criação, início, parada, remoção e leitura do registro de saída fora da thread da interface, mostrando o progresso por etapa e a saída em tempo real, e oferecendo "Parar de esperar", que interrompe a espera sem perder o registro do que já foi feito.

#### Scenario: Janela responde durante a criação

- **WHEN** a criação de uma instância demora minutos
- **THEN** a janela continua respondendo, mostra a etapa atual e permite parar de esperar

### Requirement: Os comandos de terminal espelham a interface e exigem confirmação

O Soda SHALL oferecer comandos de terminal para criar, listar, iniciar, parar, remover e consultar o estado de instâncias, com o mesmo conteúdo da interface. Comandos que alteram o sistema (criar, iniciar, parar, remover) SHALL exigir uma confirmação explícita no próprio comando; sem ela, SHALL mostrar o plano do que fariam e terminar sem alterar nada.

#### Scenario: Ensaio sem confirmação

- **WHEN** o usuário executa o comando de remover sem a confirmação
- **THEN** o terminal mostra o que seria removido e o backup que seria feito, e nada é alterado
