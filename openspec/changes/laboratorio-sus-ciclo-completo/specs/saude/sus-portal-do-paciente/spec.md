## Purpose

Permitir que o paciente recupere o próprio exame com o número da requisição que recebeu, de qualquer aparelho, sem cadastro prévio e
sem que o número da requisição sirva para descobrir exame de outra pessoa. É a porta de entrada do paciente; a conferência de
autenticidade do laudo é a capacidade `saude/sus-autenticacao-de-resultado`.

## ADDED Requirements

### Requirement: Recuperação pelo número da requisição com segundo fator
O sistema SHALL permitir ao paciente informar o número da requisição e um segundo fator conhecido dele (data de nascimento e, quando
configurado, os quatro últimos dígitos do CPF ou do CNS) e SHALL exibir o exame somente quando todos conferem. Número da requisição
isolado SHALL NOT bastar para ver resultado.

#### Scenario: Requisição e nascimento corretos
- **WHEN** o paciente informa o número da requisição e a data de nascimento corretos
- **THEN** vê o estado do exame e, se liberado, baixa o laudo assinado

#### Scenario: Só o número da requisição
- **WHEN** alguém informa o número sem o segundo fator
- **THEN** nenhum dado do exame é exibido

### Requirement: Número da requisição não adivinhável
O sistema SHALL emitir o número da requisição com componente aleatório e dígito de conferência, de modo que números vizinhos não
existam em sequência previsível, e SHALL NOT revelar se um número existe antes de o segundo fator conferir.

#### Scenario: Número vizinho
- **WHEN** alguém tenta o número seguinte a uma requisição conhecida
- **THEN** a resposta não distingue número inexistente de segundo fator errado

### Requirement: Estado do exame visível ao paciente
O sistema SHALL mostrar ao paciente o estado em linguagem simples (solicitado, coletado, em análise, pronto, entregue, recoleta
necessária) e o prazo estimado, e SHALL mostrar "em andamento", sem valor, enquanto o resultado estiver retido, em quarentena, em
revisão ou com comunicação crítica pendente.

#### Scenario: Resultado em revisão
- **WHEN** o paciente consulta um exame em revisão
- **THEN** vê "em análise", sem valor nem sinal de alteração

### Requirement: Pedido de recoleta comunicado com orientação
O sistema SHALL informar ao paciente, quando houver recoleta, o motivo em linguagem simples e a unidade para a nova coleta, sem expor
detalhe técnico interno.

#### Scenario: Recoleta por amostra inadequada
- **WHEN** a amostra foi rejeitada
- **THEN** o paciente vê que precisa recoletar e onde, sem o código de rejeição técnico

### Requirement: Download do laudo assinado
O sistema SHALL permitir baixar o laudo em PDF assinado, com o código de autenticação e o QR, e SHALL registrar o download. O PDF
SHALL ser servido por conexão cifrada e com cabeçalho que impeça indexação e cache compartilhado.

#### Scenario: Download
- **WHEN** o paciente baixa o laudo
- **THEN** o arquivo traz a assinatura, o código e o QR, e o download fica registrado

### Requirement: Interface responsiva e acessível
O sistema SHALL apresentar o portal e todas as telas do módulo de forma responsiva em celular, tablet e computador, sem rolagem
horizontal, com alvos de toque adequados e contraste e rotulagem acessíveis (leitor de tela, foco visível, texto redimensionável).
Nenhuma ação essencial SHALL depender de passar o mouse.

#### Scenario: Celular estreito
- **WHEN** o portal é aberto em tela de 360 px de largura
- **THEN** o formulário e o resultado cabem na largura, sem rolagem horizontal

### Requirement: Proteção contra abuso e vazamento
O sistema SHALL limitar tentativas por origem e por requisição, SHALL bloquear temporariamente após falhas repetidas, SHALL NOT gravar
o segundo fator nem o resultado em registro técnico e SHALL exibir aviso de privacidade antes do primeiro acesso.

#### Scenario: Tentativas em excesso
- **WHEN** muitas tentativas falham para a mesma requisição
- **THEN** novas tentativas são bloqueadas por um tempo e o responsável é alertado

### Requirement: Canais de entrega do número da requisição
O sistema SHALL fornecer o número da requisição ao paciente na coleta, impresso no comprovante com QR e, quando houver contato
cadastrado e consentimento, por mensagem, sem incluir resultado ou dado de saúde na mensagem.

#### Scenario: Comprovante de coleta
- **WHEN** a coleta é confirmada
- **THEN** o paciente recebe o comprovante com o número da requisição e o endereço do portal
