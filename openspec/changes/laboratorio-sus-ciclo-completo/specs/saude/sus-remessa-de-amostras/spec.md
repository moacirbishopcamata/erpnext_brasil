## Purpose

Manter a custódia e a integridade da amostra enquanto ela viaja entre unidades coletoras, a central de recebimento e o
laboratório de referência, tratando o transporte como etapa auditável e não como lacuna.

## ADDED Requirements

### Requirement: Remessa em lote com manifesto
O sistema SHALL agrupar tubos em remessa com identificador próprio, unidade de origem e de destino, responsável pelo envio, data
e hora e lista de tubos. A remessa SHALL ter etiqueta própria legível por leitor, com identificador da remessa, origem, destino
e quantidade, e sem dado pessoal de paciente.

#### Scenario: Etiqueta de caixa sem dado pessoal
- **WHEN** a etiqueta da remessa é impressa
- **THEN** ela traz identificador, origem, destino e quantidade de tubos, e nenhum nome de paciente

### Requirement: Conferência por tubo na saída
O sistema SHALL exigir a leitura de cada tubo ao compor a remessa. Tubo não lido SHALL NOT entrar na remessa, e o fechamento
SHALL exigir contagem de tubos lidos igual à do manifesto.

#### Scenario: Tubo esquecido
- **WHEN** o responsável tenta fechar a remessa com um tubo previsto que não foi lido
- **THEN** o sistema recusa o fechamento e indica o tubo faltante

### Requirement: Conferência por tubo na chegada e divergência como ocorrência
O sistema SHALL exigir, na chegada, a leitura de cada tubo e a comparação com o manifesto. Tubo faltante, a mais ou danificado
SHALL gerar ocorrência de transporte ligada à remessa, e o tubo a mais SHALL ficar retido até ser identificado.

#### Scenario: Tubo a mais na caixa
- **WHEN** a leitura na chegada encontra um tubo que não consta do manifesto
- **THEN** uma ocorrência é aberta, o tubo fica retido e a unidade de origem é consultada

### Requirement: Condições de transporte registradas e avaliadas
O sistema SHALL registrar, por remessa, a temperatura e o tempo entre coleta e recebimento quando o exame exigir, e SHALL
compará-los com a faixa e o prazo de estabilidade do exame. Fora do limite, a amostra SHALL ser tratada pelos critérios de
rejeição, não aceita por omissão.

#### Scenario: Estabilidade vencida
- **WHEN** o tempo entre coleta e recebimento excede o prazo de estabilidade do exame
- **THEN** o tubo é marcado para rejeição por estabilidade vencida e a recoleta é solicitada

### Requirement: Transferência de custódia explícita
O sistema SHALL registrar na cadeia a entrega ao transportador e a entrega ao destino, com o responsável de cada lado. A remessa
SHALL permanecer em trânsito até a conferência de chegada, e tempo em trânsito acima do limite configurado SHALL gerar alerta.

#### Scenario: Remessa sem chegada
- **WHEN** uma remessa passa do limite de tempo em trânsito sem conferência de chegada
- **THEN** um alerta é aberto para a unidade de origem e para a de destino

### Requirement: Laboratório de referência preserva a identidade de origem
O sistema SHALL preservar o identificador do tubo de origem ao enviar a laboratório de referência, e o vínculo com o
identificador interno do laboratório de referência SHALL ser registrado sem substituí-lo, de modo que o resultado volte ao tubo
certo.

#### Scenario: Resultado do laboratório de referência
- **WHEN** o laboratório de referência devolve resultado com o identificador interno
- **THEN** o sistema o casa ao tubo de origem pelo vínculo registrado, e resultado sem vínculo vai à quarentena
