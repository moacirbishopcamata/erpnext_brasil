## Purpose

Dispensar medicamentos e insumos ao público por um terminal de balcão (POS) próprio, rápido e seguro: identifica o usuário, confere a receita e a
padronização da REMUME para aquela unidade, separa o lote por leitura de código, baixa o estoque e registra a dispensação no prontuário e nos
sistemas públicos. É um POS de dispensação gratuita, não de venda.

## ADDED Requirements

### Requirement: Terminal de balcão de dispensação
O sistema SHALL oferecer um terminal de balcão (POS) para dispensação ao público, operável por teclado e leitor de código de barras (linear e 2D),
responsivo (computador de balcão e tablet), acessível, com fluxo guiado de poucos passos e sem rolagem horizontal. O terminal SHALL NOT tratar
preço, pagamento nem documento fiscal, porque a dispensação do SUS é gratuita.

#### Scenario: Atendimento ao balcão
- **WHEN** o atendente abre o terminal
- **THEN** vê o fluxo identificar usuário, receita, itens, conferência e comprovante, sem campos de preço ou pagamento

### Requirement: Identificação do usuário por CNS ou CPF
O sistema SHALL identificar o usuário pelo CNS (por leitura do cartão ou digitação com validação do dígito) ou pelo CPF, buscando o cadastro de pacientes
do módulo, e SHALL exigir confirmação por segundo identificador (nome e nascimento) antes de dispensar. Sem documento, a dispensação SHALL exigir o
farmacêutico e ficar marcada como pendente de regularização.

#### Scenario: CNS inválido
- **WHEN** o CNS lido tem dígito verificador inválido
- **THEN** o terminal recusa e pede a identificação por outro meio

### Requirement: Registro da prescrição
O sistema SHALL registrar, em cada dispensação, a prescrição: prescritor (conselho e número), unidade de origem, data de emissão, validade, itens, posologia
e duração, e a forma (papel conferido ou prescrição eletrônica recebida pela RNDS). Receita vencida ou ilegível SHALL ser recusada, e a validade SHALL ser
parâmetro por tipo de receita.

#### Scenario: Receita vencida
- **WHEN** a data de emissão excede a validade configurada para o tipo da receita
- **THEN** o terminal recusa a dispensação e informa a validade

### Requirement: Padronização da REMUME aplicada ao balcão
O sistema SHALL permitir dispensar somente item da REMUME vigente, padronizado para a unidade de dispensação (`saude/sus-remume-e-padronizacao`),
respeitando o subgrupo e a restrição de uso (inscrição em programa, uso na unidade). Item fora da lista ou da unidade SHALL ser recusado, e a exceção
SHALL exigir o farmacêutico com justificativa registrada.

#### Scenario: Item não padronizado na unidade
- **WHEN** o item não consta como padronizado para aquela unidade
- **THEN** o terminal recusa e indica a unidade padronizada, ou oferece a exceção ao farmacêutico

### Requirement: Medicamentos sob controle especial
O sistema SHALL tratar medicamentos sujeitos a controle especial (Portaria SVS/MS 344/1998) com a exigência de farmacêutico, notificação de receita e
retenção do documento, registrando o número da notificação, e SHALL manter a escrituração própria. Os prazos de validade da receita controlada e as
obrigações de escrituração em unidade pública (SNGPC e o controle nacional de receituários) SHALL ser parâmetros a confirmar na norma vigente e com a
vigilância sanitária local.

#### Scenario: Controlado sem notificação de receita
- **WHEN** o atendente tenta dispensar controlado sem registrar a notificação de receita
- **THEN** a dispensação é recusada

### Requirement: Quantidade, continuidade e duplicidade
O sistema SHALL aplicar limites de quantidade por item e período, SHALL registrar a dispensação parcial com a pendência do restante, SHALL apoiar a
retirada periódica de uso contínuo e SHALL alertar dispensação recente do mesmo item ao mesmo usuário (inclusive em outra unidade), exigindo
confirmação do farmacêutico para prosseguir.

#### Scenario: Retirada repetida
- **WHEN** o usuário já retirou o mesmo item dentro do intervalo configurado
- **THEN** o terminal alerta, mostra a data e a unidade, e exige o farmacêutico para prosseguir

### Requirement: Separação por lote lido
O sistema SHALL exigir a leitura do código do produto na separação, sugerir o lote por FEFO, recusar lote vencido, em quarentena, bloqueado ou recolhido
(`saude/sus-controle-de-lotes`) e baixar o estoque da unidade no momento da confirmação. A dispensação SHALL guardar o lote e a validade de cada item.

#### Scenario: Lote recolhido
- **WHEN** o atendente lê um produto de lote recolhido
- **THEN** o terminal bloqueia a leitura e indica o recolhimento

### Requirement: Conferência e orientação pelo farmacêutico
O sistema SHALL registrar a conferência da dispensação pelo farmacêutico responsável quando exigida (controlados, exceções, dose ou forma de risco) e SHALL
registrar a orientação prestada ao usuário. O sistema SHALL NOT apoiar decisão clínica além das regras de padronização, quantidade e duplicidade.

#### Scenario: Orientação registrada
- **WHEN** o farmacêutico conclui a dispensação de item que exige orientação
- **THEN** a orientação e o responsável ficam registrados

### Requirement: Comprovante de dispensação não fiscal
O sistema SHALL emitir comprovante de dispensação em impressora térmica e em tela, sem valor fiscal, com unidade, data e hora, usuário (nome e parte do
documento), itens, quantidade, lote, validade, posologia e responsável, e código de autenticação com QR. O comprovante SHALL conter o mínimo de dado pessoal.

#### Scenario: Comprovante
- **WHEN** a dispensação é concluída
- **THEN** o comprovante sai sem valor fiscal, com lote, validade e código de autenticação

### Requirement: Toda dispensação é entrada do prontuário
O sistema SHALL registrar cada dispensação como entrada só de acréscimo no prontuário do paciente, com hash, responsável e local, conforme
`saude/sus-prontuario-do-paciente`.

#### Scenario: Dispensação registrada
- **WHEN** a dispensação é concluída
- **THEN** aparece como entrada do prontuário do usuário

### Requirement: Cancelamento e devolução controlados
O sistema SHALL permitir cancelar a dispensação apenas antes da entrega ao usuário. Depois da entrega, o retorno do produto SHALL ocorrer como devolução
com motivo e farmacêutico, e o lote devolvido SHALL ir à quarentena e NÃO voltar ao estoque disponível sem decisão do farmacêutico. Dispensação NÃO SHALL
ser excluída.

#### Scenario: Devolução de produto
- **WHEN** o usuário devolve um medicamento já dispensado
- **THEN** o lote devolvido vai à quarentena e a devolução fica registrada com o motivo

### Requirement: Fechamento do dia e conciliação
O sistema SHALL fechar o dia de cada ponto de dispensação conciliando o dispensado com a baixa de estoque, listando divergência, e SHALL assinar o fechamento
pelo responsável.

#### Scenario: Divergência no fechamento
- **WHEN** o dispensado do dia difere da baixa de estoque
- **THEN** a divergência é listada e exige tratamento antes do fechamento

### Requirement: Operação sem conectividade
O sistema SHALL permitir dispensar em terminal offline, com a última REMUME, os lotes e as dispensações recentes sincronizados, SHALL impedir estoque
negativo e SHALL sincronizar de forma idempotente quando houver conexão, tratando conflito de lote como ocorrência.

#### Scenario: Retorno da conexão
- **WHEN** o terminal volta a ter conexão
- **THEN** as dispensações sincronizam uma só vez, e o conflito de lote vira ocorrência

### Requirement: Perfis do balcão
O sistema SHALL separar os perfis de atendente, farmacêutico e gestor por unidade, com acesso mínimo, e SHALL exigir o farmacêutico para controlados,
exceções, devoluções e fechamento.

#### Scenario: Atendente tenta devolução
- **WHEN** um atendente tenta registrar devolução
- **THEN** o terminal exige o farmacêutico
