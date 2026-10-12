## 1. Fontes primárias e decisões que dependem do serviço

- [ ] 1.1 Ler o texto oficial da Portaria GM/MS 8.276/2025 e o guia de integração da RNDS; registrar em `docs/` o que o REL exige e quem envia, e verificar que o documento cita a fonte e o nível de confiança
- [x] 1.2 Obter o manual vigente do SIASUS/BPA e a tabela SIGTAP da competência; registrar quais procedimentos do subgrupo 02.02 exigem BPA individualizado e verificar que a regra está citada
- [x] 1.3 Ler o Anexo 1 do Anexo V da Portaria de Consolidação GM/MS 4/2017 com as alterações vigentes; extrair a lista de agravos com prazo e verificar que cada item cita a portaria de origem
- [ ] 1.4 Investigar se o GAL tem interface de troca de dados com sistema externo (consultar um LACEN); registrar a conclusão e verificar que o adaptador do GAL fica marcado como opcional ou viável
- [ ] 1.5 Levantar a norma vigente de transporte de material biológico (RDC 504/2021) e os prazos de estabilidade de três exames de rotina; registrar a fonte e verificar que o manifesto usa esses limites como parâmetro
- [ ] 1.6 Resolver com o serviço as perguntas em aberto do `design.md` (licença, contingência P20, assinatura) e verificar que cada resposta foi anotada no design
- [x] 1.7 Ler os textos oficiais da Resolução CD/ANPD 15/2024 (incidente) e dos arts. 33, 37, 38 e 42 da LGPD no arquivo compilado já obtido; atualizar `docs/laboratorio-sus-lgpd.md` e verificar que não restam "a confirmar" evitáveis
- [ ] 1.8 Obter e ler CLSI AUTO12 e AUTO02 (rótulo e código de barras de tubo) e as especificações GS1 DataMatrix e GS1-128; registrar dimensões, zonas de silêncio e módulo mínimo e verificar que os parâmetros do leiaute citam a fonte
- [ ] 1.9 Obter CLSI LIS01, LIS02 e o suplemento IHE LAW; registrar os campos e os códigos usados e verificar que os arquivos de exemplo dos leitores vêm das especificações de interface dos fabricantes do serviço
- [ ] 1.10 Consultar o CFBM/CRBM e a ANVISA sobre assinatura digital de laudo por biomédico; registrar a resposta e verificar que a política de assinatura (nível do certificado, PAdES, carimbo) cita a fonte
- [ ] 1.11 Ler o leiaute vigente e o MOS do eSocial para o S-2220 e a Tabela 27; registrar chaves, regras de data e observação e verificar que a tabela de correspondência cita a versão do leiaute
- [ ] 1.12 Ler a Lei 13.787/2018 e a RDC 786 (art. 81) no texto oficial; fixar o piso de guarda do prontuário e verificar que a divergência entre 3, 5 e 20 anos está resolvida e registrada
- [ ] 1.13 Levantar as tabelas brasileiras da tropicalização (IBGE municípios e raça/cor, CBO, CID, CNES, CEP, feriados nacionais, fuso e histórico de horário de verão) com a fonte e a data de cada uma, e verificar que cada tabela tem origem, versão e plano de atualização registrados
- [ ] 1.14 Obter os textos oficiais da RDC 430/2020, RDC 591/2021 e 884/2024, RDC 625/2022, SNCM (RDC 157/2017 e 319/2019), RDC 80/2006 e Decreto 5.775/2006, RDC 222/2018, Portaria SVS/MS 344/1998 e RDC 873/2024, Portarias GM/MS 5.713, 6.093 e 6.100/2024, WHO TRS 1025 Anexo 7 e 2013/C 343/01, Lei 4.320/1964, Lei 14.133/2021, NBC TSP 04 e MCASP; registrar o que cada uma exige para lote, armazenagem, dispensação e contabilidade e verificar que nenhuma regra do módulo cita só fonte secundária

## 2. Esqueleto do módulo e camada pura

- [x] 2.1 Criar o app Frappe `sus_brasil` com `hooks.py`, `modules.txt` e pacote `puro/` sem `frappe`; verificar que o teste arquitetural falha ao importar `frappe` em `puro/`
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

- [ ] 8.1 Implementar o leitor puro de HL7 v2 do perfil LAW (QBP^Q11/RSP^K11, OML^O33/ORL^O34, OUL^R22) e verificar com mensagens válidas, malformadas, com campos extras e com OUL incoerente com a OML
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
- [ ] 17.8 Implementar o registro e a classificação de incidente com o relógio de três dias úteis (calendário nacional da tarefa 30.4) e o alerta ao encarregado, e verificar o início do relógio
- [ ] 17.9 Implementar o registro de RIPD e do país de hospedagem e dos operadores, com alerta de mudança relevante e de dado fora do Brasil, verificando a pendência sem RIPD
- [ ] 17.10 Implementar a página pública de publicidade da dispensa de consentimento e do encarregado, e verificar o conteúdo
- [ ] 17.11 Tratar o menor de idade com responsável legal e verificar o consentimento só pelo responsável
- [ ] 17.12 Cifrar a estação offline e os dados temporários com eliminação automática e verificar a estação extraviada

## 18. Integração com o ERPNext (módulo acoplável)

- [ ] 18.1 Criar o módulo "Integração SUS" no `erpnext_brasil` e as extensões `hrms_brasil` e `healthcare_brasil`, ativas só onde a aplicação existe, e estender o teste arquitetural para garantir que somente elas importam ERPNext, Healthcare, HRMS e `erpnext_brasil`, verificando a falha ao importar em outro lugar e a instalação de uma aplicação depois da extensão
- [ ] 18.2 Sincronizar os profissionais do Employee do ERPNext (nome, CPF, conselho, registro, UF, CBO, situação) como projeção mínima e verificar o novo, o sem registro e o desligado
- [ ] 18.3 Sincronizar com o estoque do ERPNext as entradas de compra (para o recebimento em quarentena do WMS) e levar o consumo e os ajustes, verificando o lote vencido, a idempotência e a divergência entre os dois saldos
- [ ] 18.4 Expor ao ERPNext a produção, o consumo e os indicadores sem dado identificável e verificar o relatório de consumo
- [ ] 18.5 Verificar que o ciclo continua com o ERPNext fora do ar e que a sincronização é retomada
- [ ] 18.6 Implementar a extensão `healthcare_brasil` (Patient, Practitioner, Lab Test, Sample Collection, Observation, Diagnostic Report) e verificar a ida e volta sem alterar o Healthcare
- [ ] 18.7 Implementar a extensão `hrms_brasil` (Employee como profissional, EPI por pessoa e a saúde ocupacional do S-2220) e verificar o profissional novo, o desligado e o EPI vencido

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

## 21. WMS: reagentes, insumos, amostras armazenadas e coletas

- [ ] 21.1 Implementar o livro de movimentos só de acréscimo e o cálculo puro de saldo por endereço e lote, e verificar que o saldo é sempre a soma dos movimentos e que ajuste é movimento
- [ ] 21.2 Implementar o catálogo de insumos e a hierarquia de endereços com compatibilidade de armazenamento e verificar a recusa de reagente refrigerado em equipamento ambiente
- [ ] 21.3 Implementar o recebimento com conferência, temperatura de chegada, certificado e quarentena de recebimento, e verificar a segregação de reagente que chegou quente
- [ ] 21.4 Implementar FEFO, bloqueio de vencido e de frasco aberto além da estabilidade, sem revalidação, e verificar com lotes de validades diferentes e com limite de validade
- [ ] 21.5 Implementar o consumo por exame e lote ligado ao resultado, e a liberação de novo lote só com controle aprovado, verificando a troca de lote
- [ ] 21.6 Implementar o registro de temperatura dos equipamentos de armazenamento e a quarentena automática por excursão (insumos e amostras), e verificar com excursão de geladeira e de freezer
- [ ] 21.7 Implementar o ressuprimento por mínimo, ponto de pedido e demanda prevista, com alerta de ruptura, e verificar com demanda que supera o saldo utilizável
- [ ] 21.8 Implementar a contagem cíclica, a divergência com motivo e aprovação, e a transferência entre endereços e unidades por separação e conferência, verificando o ajuste e o trânsito
- [ ] 21.9 Implementar o mapa de armazenamento de amostras com uma posição por amostra, entrada por leitura de tubo e posição, e verificar a recusa de posição ocupada
- [ ] 21.10 Implementar a retenção por política, a lista de descarte com aprovação e o bloqueio de descarte de amostra em investigação, e verificar o descarte impedido com ocorrência aberta
- [ ] 21.11 Implementar a localização e a separação de amostra para reanálise, acréscimo de exame e envio, com checagem de estabilidade, e verificar o acréscimo recusado fora da estabilidade
- [ ] 21.12 Implementar o inventário de amostras e o tratamento de amostra não encontrada como ocorrência de custódia, e verificar a lacuna na cadeia
- [ ] 21.13 Implementar as etiquetas de endereço (equipamento, rack, caixa e posição) sem dado de paciente e verificar o conteúdo decodificado
- [ ] 21.14 Implementar a fila de coleta por unidade e prioridade, a agenda e as rotas (inclusive fluvial) com alerta de estabilidade, e verificar a rota longa com exame de estabilidade curta
- [ ] 21.15 Implementar o kit de coleta por rota, a baixa do consumo e a reconciliação solicitado, coletado, remetido e recebido, e verificar o kit com tubo vencido e o tubo coletado e não remetido
- [ ] 21.16 Implementar a interface de movimentação em que o destino define a ação (transferir, descartar com confirmação, bloquear) e verificar o descarte pedindo motivo e confirmação

## 22. Catálogo CATMAT e REMUME

- [ ] 22.1 Implementar o código CATMAT canônico (BR + 7 dígitos), a normalização de variantes e o sufixo de apresentação, e verificar com os casos reais do e-SUS (sem zeros, espaço, barra e repetido)
- [ ] 22.2 Carregar a tabela de medicamentos do e-SUS (3.334 linhas, cinco campos) com carga repetível e linhas problemáticas em curadoria, verificando 2.765 códigos canônicos e 14 linhas ou códigos em pendência
- [ ] 22.3 Validar os códigos contra o catálogo oficial do Compras.gov.br (existência, situação, classe, PDM, NCM) e verificar a recusa de inexistente, o bloqueio de inativo e a amostra de 80 itens (73 ativos e 7 inativos)
- [ ] 22.4 Conciliar a tabela do e-SUS com o catálogo oficial e listar a divergência de situação e de classe, verificando que o oficial prevalece
- [ ] 22.5 Estender o catálogo aos reagentes (classe 6550) e demais insumos com a mesma chave (código, apresentação) e verificar a identificação de um reagente
- [ ] 22.6 Carregar a REMUME de Porto Velho 2025 (340 itens) com edição, ato e vigência, e verificar 286 itens lidos e 54 em curadoria, sem inferência
- [ ] 22.7 Modelar competência e financiamento, subgrupos, unidades padronizadas ligadas a CNES e restrição de uso, e verificar a inclusão de uma nova sigla sem alterar código
- [ ] 22.8 Ligar a REMUME ao CATMAT e à OBM com curadoria e verificar as correspondências exatas, só pelo princípio ativo e sem ligação
- [ ] 22.9 Registrar inclusões e exclusões entre edições com justificativa e deliberação, e verificar a vigência por data de dispensação

## 23. Controle rígido de lotes

- [ ] 23.1 Implementar o parser puro de GS1 (AI 00, 01, 10, 11, 13, 15, 17, 21, 30 e 37, FNC1, dia 00 como último dia do mês, dígito do GTIN) e verificar com os casos do dicionário GS1, inclusive o lote que contém GTIN colado
- [ ] 23.2 Implementar o lote como registro de primeira classe com estados e tabela de transições, e verificar todos os pares inválidos e que só lote liberado e válido é usado
- [ ] 23.3 Implementar o recebimento com conferência contra a nota e a etiqueta, validade mínima e quarentena, e verificar com divergência, embalagem violada e validade curta
- [ ] 23.4 Implementar a rastreabilidade do lote para unidades, pacientes e resultados e do paciente para os lotes, e verificar com um lote apontado como defeituoso
- [ ] 23.5 Implementar o recolhimento que bloqueia o lote em todas as unidades no mesmo instante, lista saldos e destinatários e acompanha a retirada, e verificar a leitura bloqueada no balcão
- [ ] 23.6 Implementar FEFO com validade mínima de uso e justificativa de exceção, e verificar tratamento longo com validade curta
- [ ] 23.7 Implementar a serialização (série repetida ou já dispensada) e o UDI-DI e UDI-PI como parâmetros ativáveis, e verificar série já dispensada e produto sem UDI após o prazo
- [ ] 23.8 Implementar a ocorrência de queixa técnica ou evento adverso ligada ao lote com bloqueio preventivo, e verificar que o módulo não notifica sozinho
- [ ] 23.9 Tornar a identificação do lote imutável após o primeiro movimento, corrigida por registro de referência, com cadeia de hash, e verificar a correção de validade
- [ ] 23.10 Implementar o inventário por lote e a divergência de lote como ocorrência, e verificar o lote trocado na prateleira

## 24. Compras e recebimento com notas fiscais

- [ ] 24.1 Implementar o pedido com saldo por item e a entrada excepcional autorizada, e verificar o recebimento sem pedido
- [ ] 24.2 Implementar o recebimento em três etapas (provisório, conferência, definitivo) com recusa e dois conferentes, e verificar a recusa por embalagem violada
- [ ] 24.3 Estender `ler_nfe` do `erpnext_brasil` para ler o `rastro` e o grupo de medicamento, com testes, e verificar com XML de exemplo com vários lotes por item
- [ ] 24.4 Implementar a conferência da NF-e contra o pedido e contra a etiqueta do lote, e verificar XML sem protocolo, emitente diferente e lote da etiqueta diferente da nota
- [ ] 24.5 Implementar o ateste condicionado, a entrega parcial e a recusa de excesso, e verificar o ateste com divergência aberta e a entrega acima do saldo
- [ ] 24.6 Implementar a requisição interna entre almoxarifado e unidades com separação FEFO e transferência conferida, e verificar a chegada com divergência
- [ ] 24.7 Implementar a solicitação de compra gerada pelo ressuprimento, para aprovação, e verificar o risco de ruptura
- [ ] 24.8 Integrar Purchase Order, Purchase Receipt e Purchase Invoice do ERPNext ao pedido, ao recebimento e à nota, e verificar o núcleo operando sem o ERPNext

## 25. Fracionamento, quarentena, devolução e perdas

- [ ] 25.1 Implementar o fracionamento como operação que gera lote derivado ligado ao de origem, e verificar a herança de lote e validade e a rastreabilidade nos dois sentidos
- [ ] 25.2 Implementar a fracionabilidade por apresentação, a exigência de farmacêutico e a recusa da embalagem hospitalar, e verificar cada recusa
- [ ] 25.3 Implementar o rótulo do fracionado com nome, princípio ativo, concentração, registro, lote e validade e a validade do derivado menor que a do original, verificando o conteúdo impresso
- [ ] 25.4 Implementar a quarentena com motivos enumerados, a saída por decisão registrada e o alerta de quarentena parada, e verificar a liberação, a devolução e o descarte
- [ ] 25.5 Implementar a devolução ao fornecedor com acompanhamento da nota de devolução pelo ERPNext e baixa do saldo só com a emissão, e verificar o saldo antes e depois da nota
- [ ] 25.6 Implementar a devolução pelo usuário que vai à quarentena e ao descarte sem reintegrar o estoque, e verificar que o saldo disponível não muda
- [ ] 25.7 Implementar o retorno de saldo entre unidades com conferência e preservação do estado do lote, e verificar o retorno de lote íntegro e de lote vencido
- [ ] 25.8 Implementar a perda com motivo, o bloqueio do item furtado e o descarte conforme o plano de resíduos com a saída por perda à BNAFAR, e verificar o descarte de vencidos
- [ ] 25.9 Impedir o ajuste de saldo que encubra perda e alertar perda recorrente, e verificar a diferença negativa sem motivo

## 26. Contabilidade e fiscal públicos do estoque

- [ ] 26.1 Implementar o ateste por servidor designado com registro do ato e a segregação de funções, e verificar o usuário não designado e o mesmo usuário em etapas conflitantes
- [ ] 26.2 Implementar a fonte de recurso e o componente de financiamento por lote e o consumo contra a fonte de origem, e verificar o lote do Componente Estratégico
- [ ] 26.3 Implementar a natureza da despesa por item como parâmetro, com entrada pendente de classificação, e verificar o item sem natureza
- [ ] 26.4 Implementar a avaliação por custo médio ponderado e por PEPS, sem UEPS, com composição do custo e menor entre custo e valor realizável líquido, e verificar com sequências de entradas e saídas e com a troca de critério
- [ ] 26.5 Implementar a classificação de cada movimento para a contabilidade patrimonial (compra, consumo, perda, doação, devolução), com a tabela de contas do município como parâmetro, e verificar cada tipo
- [ ] 26.6 Implementar a entrada de doação e remessa de outro ente sem empenho, com valor de referência, e verificar a remessa do Ministério
- [ ] 26.7 Implementar o fechamento mensal imutável com relatório de movimentação e conciliação com o saldo contábil, e verificar o movimento retroativo e o ajuste no período aberto
- [ ] 26.8 Implementar o inventário por comissão com termos de responsabilidade e apuração de divergência, e verificar a falta apurada
- [ ] 26.9 Implementar a exportação idempotente de lançamentos ao SIAFIC em layout parametrizável, e verificar o reenvio após falha
- [ ] 26.10 Implementar os dados para o tribunal de contas e o portal da transparência sem dado pessoal, e verificar o relatório de consumo por medicamento
- [ ] 26.11 Implementar a conferência da NF-e do ente público (destinatário, emitente e valores contra o empenho), e verificar o destinatário diferente

## 27. Armazenagem e despacho

- [ ] 27.1 Implementar as zonas de armazenagem e a compatibilidade entre estado do lote, condição e zona, e verificar o lote recolhido em endereço comum gerando tarefa de movimentação
- [ ] 27.2 Implementar o endereçamento hierárquico com capacidade, condição e GLN opcional, e verificar o endereço de capacidade esgotada
- [ ] 27.3 Implementar as etiquetas do armazém (endereço, SSCC, caixa de separação, volume de expedição, quarentena, recolhido, fracionado e área segregada) e verificar o conteúdo decodificado de cada uma
- [ ] 27.4 Implementar a armazenagem guiada com proposta de endereço, confirmação por leitura e justificativa de divergência, e verificar o endereço diferente do proposto
- [ ] 27.5 Implementar a separação guiada com ordenação por caminho mínimo, lote FEFO, confirmação por leitura, erro imediato e tratamento de falta, e verificar o produto lido errado e a separação curta
- [ ] 27.6 Implementar as ondas por rota, janela e prioridade e a reposição do endereço de separação, e verificar a requisição urgente com a onda em andamento
- [ ] 27.7 Implementar a conferência por volume e a escolha da embalagem pela condição de transporte, e verificar o volume refrigerado
- [ ] 27.8 Implementar o despacho por rota (veículo ou embarcação, motorista, paradas) com guia de remessa e comparação do tempo de rota com a estabilidade, e verificar a rota fluvial longa com item refrigerado
- [ ] 27.9 Implementar a comprovação de entrega por volume, lote e condição, com custódia em trânsito até a conferência, e verificar o volume faltante
- [ ] 27.10 Implementar o painel de situação responsivo e atualizado sem recarregar, com os indicadores e o caminho até a lista de origem, e verificar o alarme de temperatura e o layout em 360 px
- [ ] 27.11 Implementar os alertas operacionais com escalonamento (ruptura, vencimento, quarentena, recolhimento, entrega atrasada, excursão e inventário) e verificar a entrega atrasada
- [ ] 27.12 Implementar o mapeamento térmico e a qualificação das áreas com validade e a recusa de endereçamento termossensível sem qualificação, e verificar a qualificação vencida
- [ ] 27.13 Implementar o inventário cíclico guiado com contagem às cegas, priorização e recontagem, e verificar que o saldo esperado não aparece
- [ ] 27.14 Registrar as normas de referência do armazém com versão e data de leitura e ligar cada exigência aos controles do módulo, e verificar o relatório de evidência para auditoria

## 28. Dispensação ao público e interoperabilidade

- [ ] 28.1 Implementar o terminal de balcão (POS) responsivo e acessível, sem preço nem fiscal, operável por teclado e leitor, e verificar em tablet e em computador
- [ ] 28.2 Implementar a identificação do usuário por CNS ou CPF com confirmação por segundo identificador e a via sem documento com farmacêutico, e verificar o CNS inválido
- [ ] 28.3 Implementar o registro da prescrição (prescritor, datas, itens, posologia, forma) e a validade por tipo de receita, e verificar a receita vencida
- [ ] 28.4 Aplicar a padronização da REMUME por unidade, subgrupo e restrição de programa no balcão, com exceção do farmacêutico, e verificar o item não padronizado e o paciente não inscrito
- [ ] 28.5 Implementar o fluxo de controlados com notificação de receita, farmacêutico e escrituração conforme os parâmetros confirmados, e verificar o controlado sem notificação
- [ ] 28.6 Implementar limites de quantidade, dispensação parcial, uso contínuo e alerta de dispensação recente em qualquer unidade, e verificar a retirada repetida
- [ ] 28.7 Implementar a separação por lote lido com FEFO e a baixa do estoque da unidade, e verificar o lote recolhido
- [ ] 28.8 Implementar a conferência e a orientação pelo farmacêutico quando exigidas, e verificar o registro
- [ ] 28.9 Implementar o comprovante de dispensação não fiscal com lote, validade e código de autenticação, e verificar o conteúdo impresso e a ausência de valor fiscal
- [ ] 28.10 Registrar cada dispensação como entrada do prontuário com hash, e verificar a entrada
- [ ] 28.11 Implementar o cancelamento antes da entrega e a devolução depois, com quarentena do lote e perfil do farmacêutico, e verificar que a dispensação nunca é excluída
- [ ] 28.12 Implementar o fechamento do dia com conciliação entre dispensado e baixa, e verificar a divergência
- [ ] 28.13 Implementar a operação offline com sincronização idempotente e sem estoque negativo, e verificar o conflito de lote
- [ ] 28.14 Implementar o envio idempotente da dispensação à RNDS (REDFM) com recibo e tentativas, e verificar o reenvio
- [ ] 28.15 Implementar o recebimento e o envio da prescrição eletrônica (REPM) e o vínculo à dispensação, e verificar o balcão com prescrição eletrônica
- [ ] 28.16 Implementar o envio de posição de estoque e de saídas por movimentação ou perda à BNAFAR, distinguindo a dispensação, e verificar a perda por validade
- [ ] 28.17 Aplicar CATMAT e OBM nos envios com pendência para item sem código, e verificar o item sem correspondência
- [ ] 28.18 Implementar a lista de pendências de envio com prazo e a importação de cadastros e estoque do Hórus ou do e-SUS AF no formato publicado, e verificar o registro pendente além do prazo

## 29. Todos os materiais: classes, perfis e armazéns lógicos

- [ ] 29.1 Implementar as classes de material e o perfil de controle (lote e validade, série, registro sanitário, condição, fracionamento, controle especial, tombamento, quarentena), ajustável por item, e verificar cada combinação ligada e desligada
- [ ] 29.2 Aplicar o catálogo federal a todos os materiais com o código de item numérico como chave, situação e classe do catálogo oficial, e verificar um item de limpeza, um de expediente e um de saúde
- [ ] 29.3 Aplicar a mesma disciplina de movimento (livro, recebimento com ateste, requisição, inventário, perda, fechamento, avaliação) a todas as classes ligando só os controles do perfil, e verificar o item perecível sem validade recusado e o de expediente aceito sem lote
- [ ] 29.4 Implementar o bem permanente com tombamento, responsável, localização e transferência entre responsáveis e locais, entregando o inventário ao sistema contábil, e verificar a transferência de equipamento
- [ ] 29.5 Implementar o controle de combustível por veículo ou embarcação e rota, conciliado com a rota de despacho e a coleta, e verificar o consumo de uma rota fluvial
- [ ] 29.6 Implementar a entrega de EPI e uniforme por pessoa, com certificado, validade e termo, e alerta de reposição, e verificar o EPI vencido
- [ ] 29.7 Implementar vários armazéns lógicos sobre a mesma base, com permissões por armazém, fonte de recurso e responsável, e verificar o usuário do almoxarifado geral negado na farmácia
- [ ] 29.8 Filtrar o painel de situação e os alertas por classe e armazém, com visão consolidada para o gestor da rede, e verificar o gestor do almoxarifado geral sem dados clínicos

## 30. Tropicalização completa

- [ ] 30.1 Fazer todo texto, rótulo, mensagem, laudo e e-mail em português do Brasil com acentuação correta e verificar com um teste que falha ao encontrar cadeia de interface sem tradução ou sem acento
- [ ] 30.2 Implementar os formatos brasileiros (data dd/mm/aaaa, hora de 24 h, vírgula decimal, CPF, CNS, CNPJ, CEP e telefone) em tela, etiqueta, laudo e exportação, e verificar a ida e volta de cada formato
- [ ] 30.3 Implementar fuso horário de Brasília e as regras históricas de horário de verão em carimbo e prazo, e verificar uma coleta numa data com horário de verão e a conversão para UTC
- [ ] 30.4 Implementar o calendário de dias úteis com os feriados nacionais para contar prazos (incidente, S-2220, ciência) e verificar uma contagem que atravessa feriado e fim de semana
- [ ] 30.5 Carregar as tabelas oficiais (IBGE municípios e raça/cor, CBO, CID, CNES, SIGTAP, Tabela 27, TUSS e LOINC com correspondência brasileira) como dados versionados com origem, e verificar a consulta por vigência e a recusa de código inexistente
- [ ] 30.6 Implementar o endereço brasileiro (CEP, logradouro, município IBGE, UF) com validação de município contra a tabela IBGE e verificar a recusa de município incompatível com a UF
- [ ] 30.7 Aplicar o vocabulário do SUS e da ANVISA nos termos de tela e laudo (requisição, amostra, material biológico, CNES, competência) e verificar uma lista de termos proibidos em inglês
- [ ] 30.8 Aplicar as normas brasileiras às integrações (ICP-Brasil para assinatura, NTP.br para tempo, RNDS, eSocial) e verificar que nenhuma depende de padrão estrangeiro sem equivalente brasileiro registrado
