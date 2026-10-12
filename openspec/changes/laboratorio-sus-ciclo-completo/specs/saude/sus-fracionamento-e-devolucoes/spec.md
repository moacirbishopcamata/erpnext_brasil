## Purpose

Tratar as operações que desfazem ou subdividem o fluxo normal do estoque farmacêutico: fracionamento (subdivisão de embalagem), quarentena, devolução ao
fornecedor, devolução pelo usuário, perdas e descarte, sempre com lote e validade preservados e sem que produto de origem duvidosa volte à prateleira.

## ADDED Requirements

### Requirement: Fracionamento gera lotes derivados
O sistema SHALL registrar o fracionamento como operação que consome a quantidade do lote de origem e gera **lote derivado** ligado a ele, herdando lote e
validade do fabricante, e SHALL guardar quem fracionou, quando, a quantidade, a sobra e a perda. O lote derivado SHALL ser rastreável ao lote de origem em
ambos os sentidos.

#### Scenario: Fracionar um blíster
- **WHEN** o farmacêutico fraciona uma caixa em unidades para dispensação
- **THEN** o sistema cria o lote derivado com o lote e a validade do original e baixa a caixa de origem

### Requirement: Fracionamento só de embalagem fracionável e por farmacêutico
O sistema SHALL permitir fracionar apenas item cuja apresentação seja fracionável e SHALL exigir o farmacêutico como executor. Item em embalagem
hospitalar SHALL NOT ser fracionado para dispensação ao público. O catálogo SHALL marcar a fracionabilidade por apresentação, e a regra aplicada (RDC 80/2006
e Decreto 5.775/2006, a conferir se se estendem à rede pública) SHALL ser parâmetro.

#### Scenario: Embalagem hospitalar
- **WHEN** alguém tenta fracionar item de embalagem hospitalar para o balcão
- **THEN** o fracionamento é recusado com o motivo

### Requirement: Rótulo do fracionado com identificação completa
O sistema SHALL imprimir, para a embalagem fracionada, o nome do medicamento, o princípio ativo, a concentração, o número de registro na ANVISA, o lote e a
validade, além da unidade dispensadora, em português e com tinta indelével.

#### Scenario: Rótulo do fracionado
- **WHEN** a embalagem fracionada é etiquetada
- **THEN** o rótulo traz nome, princípio ativo, concentração, registro, lote e validade

### Requirement: Validade do derivado nunca excede a do original
O sistema SHALL limitar a validade do lote derivado à do lote de origem, e SHALL permitir validade menor quando a estabilidade pós-fracionamento a exigir
(parâmetro por item), impedindo o uso depois dela.

#### Scenario: Estabilidade menor após fracionar
- **WHEN** o item perde estabilidade após o fracionamento
- **THEN** o lote derivado recebe a validade menor e vence antes do original

### Requirement: Quarentena com motivo e saída decidida
O sistema SHALL colocar o lote em quarentena por motivo enumerado (recebimento divergente, excursão de temperatura, suspeita de qualidade, queixa técnica,
devolução, recolhimento, validade abaixo do mínimo, avaria) e SHALL exigir decisão registrada de usuário autorizado para sair dela: liberar, devolver ao
fornecedor ou descartar. A quarentena parada além do prazo configurado SHALL gerar alerta.

#### Scenario: Saída da quarentena
- **WHEN** o farmacêutico libera um lote em quarentena
- **THEN** a decisão, o motivo e o responsável ficam registrados

### Requirement: Devolução ao fornecedor com documento fiscal
O sistema SHALL abrir a devolução ao fornecedor a partir de um lote em quarentena ou recusado, SHALL acompanhar a emissão da nota fiscal de devolução (pelo
ERPNext e `erpnext_brasil`, pela integração) e a coleta, e SHALL baixar o saldo somente quando a nota de devolução for emitida. O acompanhamento SHALL cobrir a
reposição ou o crédito.

#### Scenario: Devolução de lote avariado
- **WHEN** um lote recusado é devolvido ao fornecedor
- **THEN** o saldo só baixa quando a nota de devolução é emitida, e a reposição fica acompanhada

### Requirement: Devolução pelo usuário nunca volta ao estoque
O sistema SHALL tratar o medicamento devolvido pelo usuário como devolução registrada, com motivo, e SHALL destiná-lo à quarentena e ao descarte, sem
reintegrá-lo ao estoque disponível, porque a custódia e as condições de guarda fora da farmácia não são verificáveis. A regra de que não há reintegração é
boa prática adotada pelo desenho e SHALL ser confirmada com a vigilância sanitária local.

#### Scenario: Usuário devolve medicamento
- **WHEN** o usuário devolve um medicamento já dispensado
- **THEN** o item vai à quarentena para descarte, e não retorna ao estoque disponível

### Requirement: Retorno de saldo entre unidades
O sistema SHALL tratar o retorno de saldo de uma unidade ao almoxarifado como transferência de retorno com conferência de lote, validade e condição, mantendo o
estado do lote (um lote vencido, avariado ou em recolhimento retorna em quarentena, não como disponível).

#### Scenario: UBS devolve excedente
- **WHEN** uma UBS devolve ao almoxarifado um excedente de lote íntegro e válido
- **THEN** o retorno é conferido e o lote volta disponível ao almoxarifado

### Requirement: Perdas com motivo e descarte conforme o plano de resíduos
O sistema SHALL registrar a perda por motivo (vencimento, avaria, quebra, furto ou roubo, descarte por qualidade) com quantidade, lote e responsável, SHALL
impedir que o item furtado ou roubado volte ao estoque, e SHALL encaminhar o descarte conforme o plano de gerenciamento de resíduos do serviço (RDC 222/2018
e norma local), com o registro do destino. A perda SHALL ir à BNAFAR como saída por perda.

#### Scenario: Descarte de vencidos
- **WHEN** lotes vencidos são descartados
- **THEN** o descarte fica registrado com responsável e destino, e a saída por perda é gerada

### Requirement: Ajuste de estoque nunca esconde perda
O sistema SHALL NOT permitir ajuste de saldo para encobrir perda: toda diferença negativa exige o motivo de perda ou a abertura de ocorrência investigada, e SHALL
alertar padrões de perda repetida por item, lote ou unidade.

#### Scenario: Diferença negativa recorrente
- **WHEN** uma unidade registra perdas repetidas do mesmo item sem causa
- **THEN** o sistema alerta o responsável para investigação
