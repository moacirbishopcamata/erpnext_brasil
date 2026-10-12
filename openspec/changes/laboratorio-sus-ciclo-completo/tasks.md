## 1. Fontes primárias e decisões que dependem do serviço

- [ ] 1.1 Ler o texto oficial da Portaria GM/MS 8.276/2025 e o guia de integração da RNDS; registrar em `docs/` o que o REL exige e quem envia, e verificar que o documento cita a fonte e o nível de confiança
- [ ] 1.2 Obter o manual vigente do SIASUS/BPA e a tabela SIGTAP da competência; registrar quais procedimentos do subgrupo 02.02 exigem BPA individualizado e verificar que a regra está citada
- [ ] 1.3 Ler o Anexo 1 do Anexo V da Portaria de Consolidação GM/MS 4/2017 com as alterações vigentes; extrair a lista de agravos com prazo e verificar que cada item cita a portaria de origem
- [ ] 1.4 Investigar se o GAL tem interface de troca de dados com sistema externo (consultar um LACEN); registrar a conclusão e verificar que o adaptador do GAL fica marcado como opcional ou viável
- [ ] 1.5 Levantar a norma vigente de transporte de material biológico (RDC 504/2021) e os prazos de estabilidade de três exames de rotina; registrar a fonte e verificar que o manifesto usa esses limites como parâmetro
- [ ] 1.6 Resolver com o serviço as perguntas em aberto do `design.md` (licença, contingência P20, assinatura) e verificar que cada resposta foi anotada no design
- [ ] 1.7 Ler os textos oficiais da Resolução CD/ANPD 15/2024 (incidente) e dos arts. 33, 37, 38 e 42 da LGPD no arquivo compilado já obtido; atualizar `docs/laboratorio-sus-lgpd.md` e verificar que não restam "a confirmar" evitáveis
- [ ] 1.8 Obter e ler CLSI AUTO12 e AUTO02 (rótulo e código de barras de tubo) e as especificações GS1 DataMatrix e GS1-128; registrar dimensões, zonas de silêncio e módulo mínimo e verificar que os parâmetros do leiaute citam a fonte
- [ ] 1.9 Obter CLSI LIS01, LIS02 e o suplemento IHE LAW; registrar os campos e os códigos usados e verificar que os arquivos de exemplo dos leitores vêm das especificações de interface dos fabricantes do serviço
- [ ] 1.10 Consultar o CFBM/CRBM e a ANVISA sobre assinatura digital de laudo por biomédico; registrar a resposta e verificar que a política de assinatura (nível do certificado, PAdES, carimbo) cita a fonte
- [ ] 1.11 Ler o leiaute vigente e o MOS do eSocial para o S-2220 e a Tabela 27; registrar chaves, regras de data e observação e verificar que a tabela de correspondência cita a versão do leiaute
- [ ] 1.12 Ler a Lei 13.787/2018 e a RDC 786 (art. 81) no texto oficial; fixar o piso de guarda do prontuário e verificar que a divergência entre 3, 5 e 20 anos está resolvida e registrada
- [ ] 1.13 Levantar as tabelas brasileiras da tropicalização (IBGE municípios e raça/cor, CBO, CID, CNES, CEP, feriados nacionais, fuso e histórico de horário de verão) com a fonte e a data de cada uma, e verificar que cada tabela tem origem, versão e plano de atualização registrados

## 2. Esqueleto do módulo e camada pura

- [x] 2.1 Criar o app Frappe `laboratorio_sus` com `hooks.py`, `modules.txt` e pacote `puro/` sem `frappe`; verificar que o teste arquitetural falha ao importar `frappe` em `puro/`
- [x] 2.2 Implementar a validação de CNS e CPF (dígito verificador) e verificar com casos válidos, inválidos e de borda nos testes unitários
- [x] 2.3 Implementar o identificador de tubo com dígito de conferência e verificar unicidade, rejeição de dígito errado e reinício do contador sem reaproveitar
- [x] 2.4 Implementar a máquina de estados do exame com tabela de transições e verificar que salto de estado é recusado em todos os pares inválidos
- [x] 2.5 Implementar o encadeamento de hash da custódia e verificar que alterar qualquer evento quebra a verificação
- [x] 2.6 Implementar a reserva e o consumo de faixa de identificadores por estação e verificar colisão, anulação do não usado e recusa fora da faixa
- [x] 2.7 Implementar as regras de rejeição, estabilidade e tempo por etapa e verificar com testes de limite (exatamente no prazo, um minuto depois)
- [x] 2.8 Definir as portas (`Protocol`) de cadastro, entrada de resultado, impressão, relógio, RNDS e GAL e verificar que a camada pura depende só delas

## 3. Modelo de dados, prontuário e cadastros próprios

- [ ] 3.1 Criar os DocTypes de paciente, unidade (CNES) e profissional (projeção mínima) próprios e verificar no bench que o núcleo instala sem ERPNext, Healthcare nem app fiscal
- [ ] 3.2 Criar o prontuário do paciente como linha do tempo só de acréscimo, com hash por entrada, e verificar que toda entidade do ciclo exige prontuário e que a adulteração é detectada
- [ ] 3.3 Implementar o cadastro de paciente com CNS/CPF únicos, nome social, nome da mãe, vínculo opcional de trabalhador, deduplicação por similaridade e fusão reversível, verificando CPF repetido, duplicado provável e fusão desfeita
- [ ] 3.4 Criar as tabelas de referência versionadas com vigência (SIGTAP, agravos, motivos de rejeição, Tabela 27) e verificar que a consulta por competência devolve a versão certa
- [ ] 3.5 Declarar em `setup/` todo Custom Field ou campo que o código lê e verificar com o teste de cobertura de bench

## 4. Solicitação de exame

- [ ] 4.1 Criar a solicitação com validações (CNS/CPF, CNES, profissional, SIGTAP da competência, prioridade, preparo, origem) e verificar a recusa de cada caso incompleto
- [ ] 4.2 Implementar a via "paciente sem documento" com pendência de regularização e verificar que o resultado não segue à RNDS enquanto pendente
- [ ] 4.3 Implementar o número da requisição não adivinhável (aleatório com dígito de conferência) e verificar unicidade, ausência de sequência previsível e recusa de dígito errado
- [ ] 4.4 Implementar o cancelamento antes da coleta e o encerramento por descarte depois, e verificar que cancelado não entra na produção
- [ ] 4.5 Implementar a requisição entre unidades (cadastrada antes de enviar a amostra) e verificar que amostra sem requisição fica retida

## 5. Etiquetagem em padrão internacional e custódia

- [ ] 5.1 Implementar a identificação positiva (dois identificadores) e verificar que sem confirmação não há impressão
- [ ] 5.2 Implementar a descrição neutra do rótulo e os geradores ZPL (padrão) e TSPL, e verificar que o mesmo rótulo sai nos dois perfis com o mesmo conteúdo
- [ ] 5.3 Implementar o leiaute AUTO12 (2 x 1 pol, nome no canto superior esquerdo, truncamento com indicação) parametrizado conforme a tarefa 1.8 e verificar com nomes longos e curtos
- [ ] 5.4 Implementar Code 128 para tubo e Data Matrix/GS1 DataMatrix para microtubo, criotubo e lâmina, com recusa quando o código não cabe no módulo mínimo, verificando por leitura de teste
- [ ] 5.5 Implementar os rótulos de alíquota, lâmina, swab, coletor de urina e remessa, cada um ligado à amostra de origem, e verificar o conteúdo mínimo de cada tipo
- [ ] 5.6 Implementar a impressão automática na coleta confirmada, com registro de impressão e reimpressão com motivo e "2ª via", e verificar contra impressora ou simulador
- [ ] 5.7 Impedir a impressão em lote antecipado e verificar a recusa com vários pacientes sem coleta iniciada
- [ ] 5.8 Implementar o evento de custódia de acréscimo com hash encadeado, o verificador periódico e o alerta de quebra, verificando com adulteração direta no banco
- [ ] 5.9 Implementar o bloqueio de liberação por lacuna ou quebra e verificar com um tubo sem evento de recebimento
- [ ] 5.10 Implementar a contingência de rótulo manual com reconciliação e verificar que o tubo reconciliado fica ligado a um identificador válido
- [ ] 5.11 Implementar o rastreio de lote, calibrador, controle, equipamento, versão do método e operador por resultado, e verificar a consulta do lote para os resultados e dos resultados para o lote
- [ ] 5.12 Implementar o mapa para FHIR (ServiceRequest, Specimen, Observation, DiagnosticReport) e verificar a ida e volta de uma amostra exportada

## 6. Coleta, recepção e estação offline

- [ ] 6.1 Implementar a coleta com preparo conferido e observação registrada e verificar que a observação aparece no laudo
- [ ] 6.2 Implementar a rejeição com lista enumerada e a recoleta com novo tubo ligado ao rejeitado, e verificar que o identificador antigo nunca é reaproveitado
- [ ] 6.3 Implementar a recepção com leitura do tubo e conferência com a requisição, verificando que tubo sem solicitação fica retido
- [ ] 6.4 Implementar a estação offline com dado cifrado, sincronização por faixa de identificadores e revogação de credencial, e verificar a colisão de identificador e a perda da estação

## 7. Remessa de amostras

- [ ] 7.1 Implementar a remessa com manifesto e etiqueta sem dado pessoal, e verificar que a etiqueta decodificada não revela paciente
- [ ] 7.2 Implementar a conferência por tubo na saída e na chegada com ocorrência de transporte, verificando tubo faltante, a mais e danificado
- [ ] 7.3 Implementar o registro de temperatura e tempo comparados à estabilidade do exame (norma da tarefa 1.5) e verificar o encaminhamento à rejeição
- [ ] 7.4 Implementar o estado "em trânsito" com alerta por tempo e verificar que a remessa sem chegada abre o alerta
- [ ] 7.5 Implementar o vínculo com o identificador do laboratório de referência e verificar que resultado sem vínculo vai à quarentena

## 8. Integração com os analisadores

- [ ] 8.1 Implementar o leitor puro de HL7 v2 (OML^O33, OUL^R22, ORU^R01) e verificar com mensagens de exemplo válidas, malformadas e com campos extras
- [ ] 8.2 Implementar o leitor puro de CLSI LIS01/LIS02 e verificar com sessões completas, com NAK e com retransmissão
- [ ] 8.3 Implementar o transporte serial, TCP e MLLP em camada trocável e verificar a troca de transporte sem mudar o protocolo
- [ ] 8.4 Implementar o serviço de interface com fila durável (armazenar e reenviar), confirmação só depois de gravar e aplicação por chave de idempotência, verificando queda no meio da entrega
- [ ] 8.5 Guardar a mensagem bruta com hash e rederivar o resultado dela, verificando a reinterpretação após correção da regra
- [ ] 8.6 Implementar a consulta de ordem e o envio de trabalho ao equipamento, com "sem trabalho" e sinalização de exame sem correspondência, e verificar com tubo sem pedido
- [ ] 8.7 Implementar versões por horário de análise (repetição e correção) e verificar mensagens fora de ordem
- [ ] 8.8 Implementar isolamento por equipamento e o modo sombra com relatório de divergência, verificando que a queda de um não afeta os outros e que sombra nada publica
- [ ] 8.9 Autenticar o serviço de interface com credencial mínima em canal cifrado e verificar a recusa de credencial inválida

## 9. Análise, controle de qualidade e liberação

- [ ] 9.1 Implementar a entrada de resultado digitado com dupla conferência e verificar que sem conferência não libera
- [ ] 9.2 Implementar o casamento por identificador exato e a quarentena com motivo enumerado, verificando identificador inexistente, ambíguo e com um dígito errado
- [ ] 9.3 Implementar unidade e faixa de referência sem conversão implícita e verificar a retenção por unidade diferente
- [ ] 9.4 Implementar o controle de qualidade por exame e lote com retenção dos resultados do período e verificar com controle reprovado
- [ ] 9.5 Implementar a liberação por profissional habilitado, o conteúdo mínimo do laudo e a recusa de resultado retido
- [ ] 9.6 Implementar a retificação em novo laudo e a comunicação de valor crítico, verificando que o original nunca é editado
- [ ] 9.7 Implementar a importação por arquivo passando pelo mesmo casamento e quarentena, verificando que não há caminho que os contorne

## 10. Autoverificação e automação

- [ ] 10.1 Implementar o motor puro de regras (controle de qualidade, flags, delta check, faixas, crítico, índices de soro, média móvel) e verificar cada critério isolado e combinado, inclusive nos limites
- [ ] 10.2 Implementar regras versionadas com aprovação nominal do responsável técnico e verificar que regra não aprovada nunca libera
- [ ] 10.3 Implementar a liberação automática desligada por padrão e a exclusão de crítico, controle reprovado, lacuna e quarentena, verificando cada exclusão
- [ ] 10.4 Implementar a fila de revisão humana com o motivo de cada critério e verificar a decisão registrada
- [ ] 10.5 Implementar repetição automática e teste reflexo por regra com limite de repetições, e verificar que só ocorrem com regra aprovada
- [ ] 10.6 Implementar o roteamento de listas de trabalho e verificar a prioridade de urgência
- [ ] 10.7 Implementar os alertas automáticos com escalonamento (prazo, crítico, notificação, remessa, controle, quarentena envelhecida, certificado, RNDS) e verificar o escalonamento
- [ ] 10.8 Registrar cada decisão automática com regra, versão e valores avaliados, e verificar a reconstituição de uma liberação sem humano
- [ ] 10.9 Implementar o monitoramento da taxa de autoverificação e da discordância por regra com alerta e desligamento, verificando com discordância acima do limite

## 11. Assinatura e autenticação do resultado

- [ ] 11.1 Implementar o provedor de assinatura por porta com certificado A1 em arquivo e verificar que a chave nunca vai a log nem a claro
- [ ] 11.2 Implementar a assinatura PAdES do laudo com carimbo de tempo e PDF/A, e verificar a validação em validador externo
- [ ] 11.3 Recusar assinatura com certificado de outro titular, expirado, revogado ou de profissional inativo, e verificar cada recusa
- [ ] 11.4 Implementar a assinatura de lote de resultados autoverificados com a referência no laudo e verificar a declaração "autoverificado pela regra vN"
- [ ] 11.5 Implementar o código de autenticação não adivinhável, o QR e a página pública de validação com segundo fator, verificando só código, segundo fator errado e correto
- [ ] 11.6 Implementar a conferência de integridade por hash do PDF enviado (em memória, sem reter) e a situação do laudo (vigente, retificado, revogado), verificando um PDF alterado e um laudo retificado
- [ ] 11.7 Implementar limite de tentativas e respostas idênticas contra enumeração, e verificar uma varredura de códigos

## 12. Portal do paciente (responsivo e acessível)

- [ ] 12.1 Implementar a recuperação pelo número da requisição com segundo fator e verificar que só o número nunca revela dado
- [ ] 12.2 Implementar o estado do exame em linguagem simples, "em andamento" para retido e o pedido de recoleta, verificando resultado em revisão
- [ ] 12.3 Implementar o download do laudo assinado com cabeçalhos contra indexação e cache e verificar o registro do download
- [ ] 12.4 Tornar o portal e as telas do módulo responsivos e acessíveis e verificar em 360 px sem rolagem horizontal, com foco visível e leitor de tela
- [ ] 12.5 Implementar o comprovante de coleta com número da requisição, QR, aviso de privacidade e encarregado, verificando o conteúdo impresso

## 13. Entrega e RNDS

- [ ] 13.1 Implementar a entrega ao solicitante com ciência e a lista de pendências, verificando o prazo vencido
- [ ] 13.2 Implementar o tempo de resposta por etapa e o relógio sincronizado com bloqueio por desvio, verificando urgência atrasada e relógio adiantado e atrasado
- [ ] 13.3 Implementar a montagem e o envio idempotente do REL à RNDS em homologação, com pendências por dado faltante, verificando reenvio e retificação

## 14. Equivalência ao GAL

- [ ] 14.1 Implementar o cadastro de estabelecimentos e usuários com termo de confidencialidade e verificar que o usuário só acessa após aceitar
- [ ] 14.2 Implementar o catálogo de exames, painéis e kits e verificar que a requisição de um painel gera os exames componentes
- [ ] 14.3 Implementar a consulta de rastreio por paciente, requisição, tubo ou código de autenticação e verificar o histórico e os tempos
- [ ] 14.4 Implementar relatórios e estatísticas sem identificação, com supressão de contagens pequenas, e verificar um agravo raro em município pequeno
- [ ] 14.5 Implementar a visão de vigilância por agravo e território com perfil próprio, verificando o acesso por perfil
- [ ] 14.6 Implementar a importação e exportação de transição com o GAL conforme a tarefa 1.4, recusando amostra animal e ambiental, e verificar a quarentena de divergência

## 15. Produção e notificação

- [ ] 15.1 Implementar a produção por competência, unidade e procedimento SIGTAP contando só exame liberado, e verificar exame rejeitado e recoletado
- [ ] 15.2 Implementar o instrumento de registro conforme a tabela vigente e o fechamento imutável com retificação, verificando a correção depois do fechamento
- [ ] 15.3 Implementar o alerta de notificação compulsória com a lista versionada e verificar que resultado anterior à vigência não gera alerta

## 16. Prontuário: guarda, cópia e eliminação

- [ ] 16.1 Implementar o relógio de guarda de 20 anos do último registro (parametrizável para cima) e verificar a recusa de eliminação antes do prazo
- [ ] 16.2 Implementar a eliminação formal com aprovação, destinação registrada e remoção do conteúdo mantendo o registro, e verificar o resultado
- [ ] 16.3 Implementar a cópia assinada do prontuário a pedido do titular com conferência de identidade e verificar o registro da entrega
- [ ] 16.4 Implementar a verificação periódica de integridade do prontuário e verificar o alerta de uma entrada alterada

## 17. Segurança e LGPD

- [ ] 17.1 Implementar perfis por função e unidade e verificar o acesso negado de coletador de outra unidade
- [ ] 17.2 Implementar o acesso de emergência com justificativa e a lista de revisão, verificando a recusa sem motivo
- [ ] 17.3 Implementar a auditoria só de acréscimo com antes e depois, usuário, origem e horário, e a trilha de leitura e impressão com retenção, verificando a alteração de um resultado antes da liberação
- [ ] 17.4 Implementar o inventário das atividades de tratamento com base legal e o bloqueio de destinatário não inventariado, e verificar o bloqueio
- [ ] 17.5 Implementar o consentimento específico para aviso por mensagem, com revogação, e verificar que revogar não afeta o tratamento do exame
- [ ] 17.6 Implementar o fluxo de direitos do titular com protocolo, prazo e resposta, incluindo a explicação de limite por guarda legal e o aviso aos destinatários (art. 18, §6º), e verificar um pedido de eliminação dentro do prazo de guarda
- [ ] 17.7 Implementar o pedido de revisão humana de resultado autoverificado e a informação dos critérios, e verificar a decisão registrada no prontuário
- [ ] 17.8 Implementar o registro e a classificação de incidente com o relógio de três dias úteis (calendário nacional da tarefa 21.4) e o alerta ao encarregado, e verificar o início do relógio
- [ ] 17.9 Implementar o registro de RIPD e do país de hospedagem e dos operadores, com alerta de mudança relevante e de dado fora do Brasil, verificando a pendência sem RIPD
- [ ] 17.10 Implementar a página pública de publicidade da dispensa de consentimento e do encarregado, e verificar o conteúdo
- [ ] 17.11 Tratar o menor de idade com responsável legal e verificar o consentimento só pelo responsável
- [ ] 17.12 Cifrar a estação offline e os dados temporários com eliminação automática e verificar a estação extraviada

## 18. Integração com o ERPNext (módulo acoplável)

- [ ] 18.1 Criar `integracao_erpnext/` e estender o teste arquitetural para garantir que só ela importa ERPNext, Healthcare e `erpnext_brasil`, verificando a falha ao importar em outro lugar
- [ ] 18.2 Sincronizar os profissionais do Employee do ERPNext (nome, CPF, conselho, registro, UF, CBO, situação) como projeção mínima e verificar o novo, o sem registro e o desligado
- [ ] 18.3 Sincronizar reagentes, calibradores, controles e seus lotes e validades e baixar o consumo, verificando o lote vencido e a idempotência
- [ ] 18.4 Expor ao ERPNext a produção, o consumo e os indicadores sem dado identificável e verificar o relatório de consumo
- [ ] 18.5 Verificar que o ciclo continua com o ERPNext fora do ar e que a sincronização é retomada
- [ ] 18.6 Implementar o adaptador opcional do Healthcare (Patient, Practitioner, Lab Test, Sample Collection, Observation, Diagnostic Report) e verificar a ida e volta sem alterar o Healthcare

## 19. Integração com o eSocial

- [ ] 19.1 Implementar a marcação de solicitação ocupacional ligada a paciente com vínculo e verificar a recusa sem vínculo
- [ ] 19.2 Implementar o registro neutro do exame ocupacional e verificar os campos e a referência ao laudo
- [ ] 19.3 Implementar a correspondência versionada com a Tabela 27 (tarefa 1.11) e a chave do grupo, e verificar a recusa sem correspondência
- [ ] 19.4 Implementar as regras de data e de observação do S-2220 e verificar o exame anterior à admissão
- [ ] 19.5 Montar, assinar e transmitir o S-2220 com a infraestrutura de `erpnext_brasil/folha/` e verificar o recibo e o erro de retorno ligados ao exame
- [ ] 19.6 Implementar o alerta de prazo e a configuração de quem transmite (empregador ou exportação), verificando o laboratório que não é o empregador

## 20. Validação, modo sombra e documentação

- [ ] 20.1 Escrever o teste de bench do fluxo completo (solicitação à entrega, com remessa, rejeição, autoverificação e assinatura) e verificar que passa em WSL2/Linux
- [ ] 20.2 Declarar `MODULOS_COBERTOS` nos testes de bench e verificar que `scripts/cobertura_de_bench.py` não aponta o módulo sem teste
- [ ] 20.3 Escrever os testes de caos (queda na sincronização offline, reenvio à RNDS, relógio fora da tolerância, mensagem de analisador fora de ordem) e verificar que nenhum duplica nem perde evento
- [ ] 20.4 Rodar o modo sombra em uma unidade e com um analisador e comparar com o processo atual, verificando um relatório de divergência até zerar as causas
- [ ] 20.5 Elaborar o RIPD com o encarregado antes da operação e verificar a aprovação registrada
- [ ] 20.6 Documentar o módulo em `docs/` com índice em `docs/README.md`, a análise de perigos e as lacunas em `docs/gaps.md`, e verificar que `ruff check`, `ruff format --check` e a suíte pura passam

## 21. Tropicalização completa

- [ ] 21.1 Fazer todo texto, rótulo, mensagem, laudo e e-mail em português do Brasil com acentuação correta e verificar com um teste que falha ao encontrar cadeia de interface sem tradução ou sem acento
- [ ] 21.2 Implementar os formatos brasileiros (data dd/mm/aaaa, hora de 24 h, vírgula decimal, CPF, CNS, CNPJ, CEP e telefone) em tela, etiqueta, laudo e exportação, e verificar a ida e volta de cada formato
- [ ] 21.3 Implementar fuso horário de Brasília e as regras históricas de horário de verão em carimbo e prazo, e verificar uma coleta numa data com horário de verão e a conversão para UTC
- [ ] 21.4 Implementar o calendário de dias úteis com os feriados nacionais para contar prazos (incidente, S-2220, ciência) e verificar uma contagem que atravessa feriado e fim de semana
- [ ] 21.5 Carregar as tabelas oficiais (IBGE municípios e raça/cor, CBO, CID, CNES, SIGTAP, Tabela 27, TUSS e LOINC com correspondência brasileira) como dados versionados com origem, e verificar a consulta por vigência e a recusa de código inexistente
- [ ] 21.6 Implementar o endereço brasileiro (CEP, logradouro, município IBGE, UF) com validação de município contra a tabela IBGE e verificar a recusa de município incompatível com a UF
- [ ] 21.7 Aplicar o vocabulário do SUS e da ANVISA nos termos de tela e laudo (requisição, amostra, material biológico, CNES, competência) e verificar uma lista de termos proibidos em inglês
- [ ] 21.8 Aplicar as normas brasileiras às integrações (ICP-Brasil para assinatura, NTP.br para tempo, RNDS, eSocial) e verificar que nenhuma depende de padrão estrangeiro sem equivalente brasileiro registrado
