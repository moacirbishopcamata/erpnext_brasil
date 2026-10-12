## Purpose

Proteger o dado de saúde, que é sensível, em um ciclo que atravessa várias unidades, sem impedir o atendimento: acesso mínimo por
unidade e função, acesso de emergência auditado e etiquetas e manifestos com o mínimo de dado pessoal.

## ADDED Requirements

### Requirement: Perfis por função e por unidade
O sistema SHALL conceder acesso por função (solicitante, coletador, recepcionista, analista, responsável técnico, vigilância,
auditor) e por unidade, de modo que cada usuário veja apenas os exames da sua unidade e da sua função. Acesso a dado de
paciente de outra unidade SHALL exigir a via de emergência.

#### Scenario: Coletador de outra unidade
- **WHEN** um coletador tenta abrir o exame de um paciente atendido em outra unidade
- **THEN** o acesso é negado e a tentativa é registrada

### Requirement: Acesso de emergência com justificativa e revisão
O sistema SHALL permitir acesso de emergência apenas com justificativa obrigatória, SHALL registrar usuário, paciente, motivo,
data e hora e SHALL listá-lo para revisão do responsável dentro de prazo configurado.

#### Scenario: Acesso de emergência sem justificativa
- **WHEN** o usuário solicita o acesso de emergência sem informar motivo
- **THEN** o acesso não é concedido

### Requirement: Dado pessoal mínimo em etiqueta e manifesto
O sistema SHALL limitar o dado pessoal impresso no rótulo do tubo ao exigido pelo art. 104 da RDC 786/2023, SHALL NOT imprimir
dado pessoal em etiqueta de remessa e SHALL NOT codificar dado pessoal em código de barras.

#### Scenario: Etiqueta de remessa
- **WHEN** a etiqueta de uma remessa é impressa
- **THEN** ela não contém nome, documento nem data de nascimento de paciente

### Requirement: Auditoria de alteração com antes e depois
O sistema SHALL registrar toda criação, alteração e exclusão lógica de registro do ciclo (solicitação, amostra, resultado, laudo,
regra, cadastro) com o valor anterior e o novo, usuário, endereço de origem, local e horário de relógio sincronizado, em registro
só de acréscimo que o próprio usuário não consegue alterar.

#### Scenario: Correção de resultado antes da liberação
- **WHEN** um analista corrige um resultado ainda não liberado
- **THEN** o registro mostra o valor anterior, o novo, quem alterou, de onde e quando

### Requirement: Trilha de acesso a dado de paciente
O sistema SHALL registrar toda leitura de laudo e de dado de paciente fora do fluxo de trabalho do exame (consulta avulsa,
exportação, impressão), com usuário, data, hora e local, e SHALL manter o registro por, no mínimo, cinco anos.

#### Scenario: Impressão de laudo
- **WHEN** um laudo é impresso
- **THEN** a impressão é registrada com usuário, data, hora e local

### Requirement: Relatório gerencial sem identificação direta
O sistema SHALL oferecer relatórios gerenciais (tempo de resposta, rejeição, produção) sem identificar o paciente. A exportação
com identificação direta SHALL exigir permissão específica e ser registrada.

#### Scenario: Relatório de rejeição
- **WHEN** o gestor consulta o relatório de rejeições por unidade
- **THEN** o relatório traz contagens e motivos, sem nome nem documento de paciente

### Requirement: Canal autenticado e cifrado, estação offline protegida
O sistema SHALL trafegar dados entre unidades, estação offline e laboratório de referência apenas por canal autenticado e
cifrado. A estação offline SHALL guardar dado de paciente cifrado, apagá-lo após a sincronização confirmada e ter a credencial
revogável.

#### Scenario: Estação extraviada
- **WHEN** uma estação offline é extraviada
- **THEN** os dados locais estão cifrados e a revogação da credencial invalida novas sincronizações
