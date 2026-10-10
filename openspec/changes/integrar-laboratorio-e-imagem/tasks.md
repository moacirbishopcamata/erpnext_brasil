## 1. Fontes primárias e decisões que dependem do laboratório

- [ ] 1.1 Obter e ler as normas pagas ou restritas — CLSI LIS01-A2, LIS02-A2, AUTO12-A, GP41 e ISO 15189:2022 — ou registrar em
      `docs/saude-fontes.md` que não foram lidas — verificar que cada padrão citado no `design.md` tem a marca "lido" ou "não lido"
- [ ] 1.2 Reconferir a RDC 786/2023 consolidada no texto oficial (alterada pela RDC 824/2023; confirmar a suposta RDC 978/2025,
      que só apareceu em fonte secundária) — verificar que os artigos citados nas specs batem com a versão vigente
- [ ] 1.3 Ler o suplemento atual do IHE LAW (campos de `SAC`, `SPM`, `OBX`, `ORC` nas transações LAB-27/28/29) — verificar que as
      escolhas de campo do analisador de mensagem citam a versão do suplemento
- [ ] 1.4 Obter com o laboratório marca e modelo dos analisadores, as especificações de interface de cada fabricante, as
      impressoras e etiquetadoras (linguagem, tamanho do rótulo) e o procedimento de contingência — verificar que cada pergunta em
      aberto do `design.md` correspondente tem resposta registrada, com a fonte (documento do fabricante ou decisão do laboratório)
- [ ] 1.5 Consultar especialista sobre o enquadramento na RDC 657/2022 e sobre a convivência de licenças (Healthcare GPL-3.0 com o
      app novo) — verificar que a conclusão, com quem a deu e quando, consta no `design.md`
- [ ] 1.6 Ler a página nacional do perfil de resultado laboratorial da RNDS e a portaria de obrigatoriedade para prestadores
      privados — verificar que o que a terminologia (LOINC, TUSS, SIGTAP) exige no perfil nacional está citado com a fonte

## 2. App `saude_brasil` e modelo de dados

- [ ] 2.1 Criar o app com as camadas `fiscal/`-style (regra pura sem `frappe`) e `integracao/`, e o teste de arquitetura que faz
      valer a separação e o limite de tamanho — verificar que o teste falha quando um módulo puro importa `frappe`
- [ ] 2.2 Implementar o contador de identificador de tubo e de alíquota com dígito de conferência, sem reaproveitamento —
      verificar com teste de unicidade sob concorrência e com teste de reinício do contador sem repetir número
- [ ] 2.3 Criar o DocType de evento de custódia, só de acréscimo, com hash encadeado por tubo, e o verificador de cadeia —
      verificar em bench que editar ou apagar evento é recusado (inclusive por administrador) e que adulterar o banco é detectado
- [ ] 2.4 Declarar em `setup/` os campos que ligam resultado a equipamento, método, lote de reagente e controle, nos DocTypes do
      Healthcare — verificar com teste de costura que todo campo lido pelo código está declarado, e com `bench migrate` nos dois bancos
- [ ] 2.5 Criar a fila de quarentena com motivos enumerados e resolução auditada — verificar que cada motivo da spec tem um caso
      de teste que leva o item à fila
- [ ] 2.6 Definir retenção de 5 anos e backup — verificar com um teste de restauração que recupera o laudo e a cadeia de um
      tubo de teste

## 3. Identificação positiva e etiquetagem

- [ ] 3.1 Implementar a coleta com confirmação de dois identificadores ou leitura de pulseira antes de imprimir — verificar que
      identificador divergente impede a impressão e que impressão sem coleta aberta é recusada
- [ ] 3.2 Escrever o gerador de rótulo (ZPL e TSPL), com o conteúdo do art. 104, truncamento marcado do nome longo e código só
      com o identificador — verificar com arquivos de exemplo impressos e lidos por leitor de código, e com teste de nome truncado
- [ ] 3.3 Implementar a impressão por rede com registro de usuário, horário, impressora e tubo, a marca de segunda via e a
      recusa de confirmar a coleta quando a impressão falha — verificar com impressora falsa que responde, que cai e que reinicia
- [ ] 3.4 Gerar rótulo de alíquota só depois da leitura do tubo de origem — verificar que pedir sem ler é recusado
- [ ] 3.5 Implementar a conferência de recebimento por leitura do código — verificar que código desconhecido, sem coleta ou com
      material inesperado bloqueia o tubo
- [ ] 3.6 Imprimir e ler etiquetas reais na impressora do laboratório e no analisador — verificar que o analisador lê 100% de uma
      amostra de rótulos por tipo de tubo, e registrar a taxa

## 4. Analisadores de protocolo (puros)

- [ ] 4.1 Escrever o leitor de LIS02 (registros de cabeçalho, paciente, pedido, resultado, comentário, término) — verificar com
      arquivos de exemplo dos fabricantes do laboratório e com mensagens malformadas
- [ ] 4.2 Escrever o enquadramento LIS01 (início e fim de quadro, soma de verificação, confirmação, repetição, tempo esgotado) —
      verificar com quadro de soma errada, quadro repetido e tempo esgotado
- [ ] 4.3 Escrever o leitor de `ORU^R01` e `OUL^R22` e o escritor de `OML^O33` e `RSP^K11` — verificar com arquivos de exemplo e
      com a ordem dos segmentos trocada
- [ ] 4.4 Escrever o simulador de analisador (LIS01/02 e HL7 sobre MLLP) — verificar que ele reproduz as mensagens dos arquivos
      de exemplo e consegue enviar duplicadas, fora de ordem e truncadas
- [ ] 4.5 Escrever os testes de propriedade de idempotência e ordem, e o teste de troca de identificador — verificar que um
      dígito alterado e dois tubos quase iguais nunca casam

## 5. Serviço de interface

- [ ] 5.1 Implementar a fila durável local com confirmação ao equipamento só depois de gravar — verificar com teste que mata o
      processo no meio do fluxo e confere que nada se perde e nada se duplica
- [ ] 5.2 Implementar o transporte TCP, MLLP e serial, com isolamento de falha por equipamento — verificar que a queda de um
      equipamento não interrompe os outros
- [ ] 5.3 Implementar o cliente da API do ERPNext com credencial mínima e repetição segura — verificar que a credencial do serviço
      só consegue lançar resultado e que a repetição não duplica
- [ ] 5.4 Aplicar a política de relógio: carimbo de recebimento e do equipamento, tolerância e retenção por desvio — verificar
      com relógio adiantado e atrasado, e com perda de sincronização
- [ ] 5.5 Montar o painel de estado dos equipamentos e da fila — verificar que um equipamento desconectado e uma fila crescendo
      aparecem como alerta

## 6. Entrada de resultado no ERPNext

- [ ] 6.1 Implementar a ingestão idempotente: casamento exato, quarentena (desconhecido, ambíguo, digitado, demografia), controle
      de qualidade e versões — verificar em bench, relendo do banco por caminho independente, cada cenário da spec
- [ ] 6.2 Implementar a resposta às consultas de ordem, com tradução de códigos e "sem trabalho" — verificar com a consulta de um
      tubo com pedido, sem pedido e com exame sem correspondência
- [ ] 6.3 Implementar o modo sombra e o relatório de divergência — verificar que nada é publicado no modo sombra e que a
      divergência aparece no relatório

## 7. Terminologia laboratorial

- [ ] 7.1 Criar a tabela de correspondência versionada (código do equipamento, exame, LOINC, TUSS, UCUM) — verificar que código
      sem correspondência e unidade diferente vão à quarentena e que a alteração só vale para o futuro
- [ ] 7.2 Importar a competência vigente da TUSS apenas para os códigos mapeados, registrando a versão — verificar com a
      competência real baixada da ANS e com um código descontinuado
- [ ] 7.3 Implementar a conversão de unidade somente por regra aprovada e versionada — verificar que o valor original, o
      convertido e a regra aplicada ficam guardados

## 8. Laudo e liberação

- [ ] 8.1 Validar o conteúdo mínimo do laudo (art. 138) — verificar com um teste por elemento ausente que a emissão é recusada
- [ ] 8.2 Implementar a liberação manual por padrão e a retenção — verificar que resultado retido nunca é liberado
- [ ] 8.3 Implementar a retificação em novo laudo e o registro do contato com o paciente — verificar que o original é preservado
- [ ] 8.4 Implementar a lista de valores críticos e o registro da comunicação — verificar que a liberação exige o registro
- [ ] 8.5 Integrar a assinatura legalmente válida (ICP-Brasil), depois de decidido o provedor (pergunta em aberto) — verificar que
      laudo sem assinatura válida não é emitido

## 9. Imagem

- [ ] 9.1 Publicar o pedido na lista de trabalho de um Orthanc de teste por REST — verificar que uma modalidade simulada encontra
      o pedido com o identificador do paciente e o número de acesso
- [ ] 9.2 Ligar o estudo ao pedido por número de acesso, com quarentena do que não casa — verificar com estudo de número desconhecido
- [ ] 9.3 Aplicar as notificações de estado de forma idempotente — verificar que a notificação repetida não altera o estado

## 10. Validação e documentação

- [ ] 10.1 Escrever o documento de verificação do sistema (RDC 786, art. 72: disponibilidade, confiabilidade, integridade de dados
      e responsabilidades) — verificar que cada controle da análise de perigos aponta para o teste que o prova
- [ ] 10.2 Executar o modo sombra com um analisador no laboratório e produzir o relatório de divergência — verificar que as
      divergências foram explicadas antes de qualquer publicação
- [ ] 10.3 Documentar as frentes em `docs/saude-*.md` e atualizar `docs/gaps.md` (5.3) e a tarefa 5.6 de
      `tropicalizar-demais-modulos` — verificar que os gaps deixam de constar como abertos onde foram pagos
- [ ] 10.4 Rodar a suíte pura, a de bench em MariaDB e PostgreSQL e o `ruff`, e conferir o bump de versão — verificar tudo verde
      antes de mesclar
