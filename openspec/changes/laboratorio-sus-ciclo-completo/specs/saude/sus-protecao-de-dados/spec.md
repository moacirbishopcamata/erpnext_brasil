## Purpose

Fazer do módulo um tratamento de dado de saúde em conformidade com a LGPD desde a concepção: base legal por atividade, direitos do
titular atendidos por funcionalidade, incidente com relógio de prazo, registro das operações, RIPD e controle de compartilhamento.
A análise e os pontos a confirmar estão em `docs/laboratorio-sus-lgpd.md`.

## ADDED Requirements

### Requirement: Inventário das atividades de tratamento com base legal
O sistema SHALL manter o registro das operações de tratamento: para cada atividade, a finalidade, a categoria de dado, a base legal
(art. 7º ou art. 11 da LGPD), os destinatários, o prazo de guarda e o controlador responsável. Uma atividade nova ou um destinatário
novo SHALL NOT ser ativado sem registro e aprovação do encarregado.

#### Scenario: Novo destinatário de dados
- **WHEN** alguém configura o envio de dado a um destinatário não inventariado
- **THEN** o envio é bloqueado até haver registro com base legal aprovado pelo encarregado

### Requirement: Dado sensível tratado em hipótese do art. 11
O sistema SHALL tratar todo dado de saúde como sensível e SHALL registrar, por atividade, a hipótese do art. 11 que a sustenta.
Consentimento SHALL ser usado apenas para o que depende dele (como o aviso por mensagem), e SHALL ser registrado com data, finalidade e
forma de revogação.

#### Scenario: Aviso por mensagem
- **WHEN** o paciente aceita receber aviso por mensagem
- **THEN** o consentimento fica registrado e pode ser revogado a qualquer momento, sem afetar o tratamento do exame

### Requirement: Nenhum compartilhamento por vantagem econômica
O sistema SHALL NOT enviar dado de saúde a terceiro com objetivo de vantagem econômica (art. 11, §4º), e toda integração nova SHALL
declarar a finalidade e o benefício ao titular antes de ser habilitada.

#### Scenario: Integração sem finalidade declarada
- **WHEN** uma integração é habilitada sem finalidade declarada
- **THEN** ela permanece desligada

### Requirement: Atendimento aos direitos do titular
O sistema SHALL oferecer fluxo registrado para os direitos do art. 18: confirmação e acesso, correção, informação sobre
compartilhamento, portabilidade em formato estruturado, e explicação quando bloqueio ou eliminação forem limitados por guarda legal.
Cada pedido SHALL ter protocolo, responsável, prazo e resposta registrados.

#### Scenario: Pedido de eliminação durante o prazo de guarda
- **WHEN** o titular pede a eliminação de dado do prontuário dentro do prazo legal de guarda
- **THEN** o pedido é registrado e respondido com a explicação da obrigação legal, sem eliminar

### Requirement: Revisão humana de resultado autoverificado
O sistema SHALL permitir ao titular ou ao solicitante pedir a revisão humana de um resultado autoverificado, SHALL informar qual regra
foi aplicada e SHALL registrar o pedido e a decisão do revisor. A revisão SHALL estar disponível independentemente de o texto vigente do
art. 20 da LGPD exigi-la.

#### Scenario: Pedido de revisão
- **WHEN** o paciente pede a revisão de um resultado autoverificado
- **THEN** um biomédico revisa, e a decisão e o motivo ficam registrados no prontuário

### Requirement: Encarregado visível
O sistema SHALL exibir o nome e o canal de contato do encarregado no portal do paciente e no comprovante de coleta.

#### Scenario: Portal do paciente
- **WHEN** o paciente abre o portal
- **THEN** vê o encarregado e o aviso de privacidade

### Requirement: Fluxo de incidente de segurança com prazo
O sistema SHALL oferecer registro e classificação de incidente de segurança com dado pessoal e SHALL contar o prazo de comunicação à ANPD
e aos titulares de **três dias úteis** (arts. 6º e 9º da Resolução CD/ANPD 15/2024), contados do **conhecimento de que o incidente afetou
dados pessoais**, e não da classificação do risco. Dado de saúde é dado sensível e preenche o primeiro critério de risco relevante (art. 5º,
I), então a classificação SHALL ser feita dentro do prazo, e o relógio SHALL NOT esperar por ela. O sistema SHALL alertar o encarregado ao
abrir o registro, SHALL oferecer os campos da comunicação (art. 6º, §2º) e SHALL permitir complementar a comunicação em até vinte dias
úteis (art. 6º, §3º).

#### Scenario: Incidente que afetou dados pessoais
- **WHEN** o responsável registra o conhecimento de que um incidente afetou dados pessoais
- **THEN** o relógio de três dias úteis inicia nesse instante, o encarregado é alertado e a classificação de risco passa a ser pendência dentro do prazo

### Requirement: Registro do incidente por no mínimo cinco anos
O sistema SHALL manter o registro de todo incidente de segurança, **inclusive o não comunicado** à ANPD e aos titulares, por no mínimo cinco
anos a contar do registro (art. 10 da Resolução CD/ANPD 15/2024), com a data de conhecimento, as circunstâncias, a natureza dos dados, o
número de titulares e as medidas adotadas.

#### Scenario: Incidente avaliado como sem risco relevante
- **WHEN** o encarregado conclui que o incidente não exige comunicação
- **THEN** o registro permanece, com a justificativa, pelo prazo mínimo de cinco anos

### Requirement: Comunicação ao titular direta e individualizada
O sistema SHALL apoiar a comunicação do incidente ao titular por linguagem simples e, quando for possível identificá-lo, de forma direta e
individualizada; quando não for possível, SHALL apoiar a divulgação pelos canais públicos por, no mínimo, três meses (art. 9º, §§1º a 3º).

#### Scenario: Titular identificável
- **WHEN** os titulares afetados podem ser identificados
- **THEN** a comunicação sai pelo contato cadastrado de cada um, e a declaração de comunicação é anexada ao processo

### Requirement: RIPD antes da operação
O art. 38 da LGPD faz o relatório de impacto exigível quando a ANPD o determinar, inclusive para dado sensível; **o módulo adota o
relatório como pré-condição de operação por escolha de projeto**, não por exigência legal prévia. O sistema SHALL ter o relatório,
com o conteúdo mínimo do parágrafo único do art. 38 (tipos de dados, metodologia de coleta e de segurança, análise de medidas e
mitigação), registrado e aprovado antes de habilitar o tratamento em produção, e SHALL alertar quando uma mudança relevante (nova
integração, nova finalidade, novo destinatário) exigir a revisão do relatório.

#### Scenario: Sem RIPD
- **WHEN** o ambiente de produção é habilitado sem RIPD aprovado
- **THEN** o sistema avisa o responsável e registra a pendência

### Requirement: Minimização e anonimização em relatório e exportação
O sistema SHALL gerar relatórios e exportações estatísticas sem identificação direta e com supressão de contagens pequenas, faixa etária
em vez de data de nascimento e granularidade geográfica compatível com a população, de modo que remover o nome não seja tratado como
anonimização. O limiar de supressão SHALL ser parâmetro.

#### Scenario: Agravo raro em município pequeno
- **WHEN** o relatório teria menos casos que o limiar em um município
- **THEN** a contagem é suprimida ou agregada

### Requirement: Hospedagem e transferência internacional
O sistema SHALL registrar o país de hospedagem do dado e dos operadores e SHALL alertar quando dado de paciente for armazenado ou
tratado fora do Brasil, exigindo a base do art. 33 da LGPD registrada.

#### Scenario: Provedor de assinatura em nuvem no exterior
- **WHEN** um provedor fora do Brasil é configurado
- **THEN** o sistema exige o registro da base de transferência antes de habilitá-lo

### Requirement: Dado de criança e adolescente
O sistema SHALL identificar o paciente menor de idade, SHALL exigir o responsável legal nos fluxos que dependam de consentimento e SHALL
aplicar a ele as mesmas proteções do portal, usando o segundo fator do responsável quando o portal for acessado por ele.

#### Scenario: Paciente menor
- **WHEN** o paciente tem menos de 18 anos
- **THEN** o cadastro exige o responsável legal e o aviso por mensagem só é consentido por ele
