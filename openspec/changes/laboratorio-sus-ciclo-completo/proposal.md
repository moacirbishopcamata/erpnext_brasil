## Why

O exame público do SUS tem um ciclo próprio que nenhum módulo do projeto cobre de ponta a ponta: o pedido nasce numa UBS, UPA
ou ambulatório diferente do que analisa; a amostra viaja entre unidades e até um laboratório de referência (LACEN); o paciente é
identificado por CNS/CPF; o exame é um procedimento da tabela SIGTAP, não um item de venda; o resultado volta ao solicitante e à
RNDS; alguns achados obrigam notificação; e a produção é declarada, não faturada. Hoje esse ciclo público depende do **GAL**
(Gerenciador de Ambiente Laboratorial, do DATASUS com a SVS/CGLAB), sistema separado do ERP, de acesso por LACEN e sem controle de
etiqueta, de analisador nem de assinatura do profissional no padrão que o serviço precisa provar. O dano mais grave é **resultado
atribuído à amostra ou ao paciente errado**, e o risco se concentra na etiqueta do ponto de coleta, na passagem entre unidades e na
devolução do resultado ao solicitante certo. Este change propõe um **módulo laboratorial do SUS independente do ERPNext, que faz o
que o GAL faz hoje, conversa com os analisadores e se acopla ao ERPNext por um módulo de integração**, com rastreabilidade total
e automação controlada.

## What Changes

- **Núcleo independente** (`laboratorio_sus`, nome provisório): camada pura, serviços e app Frappe próprios com o ciclo inteiro —
  solicitação, etiqueta, custódia, coleta, remessa, recepção, análise, autoverificação, liberação assinada, entrega, produção e
  notificação. O núcleo **nunca importa** ERPNext, Healthcare nem `erpnext_brasil`.
- **Módulo de integração com o ERPNext** (acoplável, em pasta própria): os **profissionais vêm do cadastro de profissionais do
  ERPNext** (Employee, com registro de conselho e CBO) e são espelhados no núcleo como projeção mínima; ponte também para
  **estoque e lote de reagentes**, compras e, opcionalmente, Healthcare. O ERPNext enxerga o laboratório; o laboratório não
  depende dele.
- **Cadastro de pacientes próprio do módulo** (o ERPNext não tem paciente): CNS, CPF, nome, nome social, nascimento, sexo, nome da
  mãe, endereço, contato, município de residência e raça/cor, com deduplicação e fusão rastreável; vínculo opcional de **trabalhador**.
- **Integração com o eSocial** para paciente que é trabalhador: o exame ocupacional (ASO) entrega ao módulo de integração os dados
  que alimentam o **S-2220 (Monitoramento da Saúde do Trabalhador)**, reutilizando a infraestrutura de eSocial já existente em
  `erpnext_brasil/folha/` (assinatura, lote, SOAP). O núcleo só produz o dado neutro do exame; o evento, a assinatura e o envio ficam
  no módulo de integração, de modo que o núcleo continua independente.
- **Faz o que o GAL faz** (módulo Biologia Médica Humana; animal e ambiental ficam fora do início): cadastro de estabelecimentos e
  usuários, requisição de exame entre unidades, recepção e triagem de amostras, gerência de exames, painéis e kits, lançamento e
  liberação de resultado, laudo consultável e imprimível no município de origem, rastreio do cadastro à liberação, relatórios e
  estatísticas, vigilância por agravo e envio à RNDS (REL). Com **caminho de transição**: importar e exportar no formato do GAL
  enquanto os LACENs ainda o usam (formato a confirmar).
- **Integração com os analisadores**: HL7 v2 (perfil IHE LAW: ordem `OML^O33`, resultado `OUL^R22`, e `ORU^R01`) e CLSI
  LIS01/LIS02 (ex-ASTM E1381/E1394), por serial, TCP ou MLLP, com armazenar-e-reenviar, idempotência, consulta de ordem (*worklist*),
  quarentena e modo sombra. Analisadores de protocolo puros; transporte separado.
- **Etiquetas em padrão internacional** para tubos e outras amostras: CLSI AUTO12 (conteúdo e leiaute, rótulo preferido 2 x 1
  polegada) e AUTO02 (código de barras Code 128 no tubo); Data Matrix e GS1 DataMatrix para microtubos, criotubos e lâminas;
  etiquetas de alíquota, lâmina, swab, coletor de urina e remessa; impressão ZPL e TSPL, automática na coleta. Código de barras só
  com o identificador.
- **Assinatura do biomédico para atestar autenticidade**: laudo em PDF com assinatura digital ICP-Brasil (PAdES, PDF/A para guarda)
  e carimbo de tempo, com nome e registro no CRBM; verificação pública por QR; assinatura por imagem recusada; assinatura do lote
  para resultado autoverificado.
- **Prontuário do paciente como raiz de todos os dados**: toda solicitação, amostra, resultado, laudo, ocorrência, consentimento
  e acesso é entrada de um prontuário único por paciente, linha do tempo só de acréscimo, com guarda mínima de 20 anos do último
  registro (Lei 13.787/2018), eliminação formal e cópia ao paciente.
- **LGPD desde a concepção**: base legal por atividade (art. 11), direitos do titular por funcionalidade, revisão humana da
  autoverificação, fluxo de incidente com prazo, RIPD antes da operação, publicidade da dispensa de consentimento do poder público,
  controle de compartilhamento e de transferência internacional. Análise em `docs/laboratorio-sus-lgpd.md`.
- **Tudo tropicalizado**: português do Brasil, formatos brasileiros, fuso de Brasília com horário de verão histórico, dias úteis com
  feriados nacionais, tabelas oficiais (IBGE, CBO, CID, CNES, SIGTAP, TUSS, Tabela 27), ICP-Brasil, NTP.br, RNDS e eSocial.
- **Portal do paciente, responsivo**: o paciente recupera o próprio exame pelo **número da requisição** (com segundo fator), em
  celular, tablet ou computador; toda tela do módulo é responsiva, como o ERPNext e seus módulos.
- **Autenticação do resultado pelo paciente**: cada laudo emitido leva um código de autenticação e um QR; uma página pública de
  validação confirma ao paciente se o laudo é autêntico, íntegro, vigente ou substituído por retificação, sem expor dado de saúde sem
  segundo fator.
- **Rastreabilidade total**: custódia por hash, mais lote de reagente, calibrador, controle, equipamento, versão do método, operador,
  versão do resultado e do laudo, regra de autoverificação aplicada; mapa para FHIR (ServiceRequest, Specimen, Observation,
  DiagnosticReport); trilha de auditoria com antes/depois, usuário, IP e horário.
- **Automação controlada**: autoverificação conforme CLSI AUTO10/AUTO15 (controle de qualidade, alarmes do instrumento, *delta
  check*, faixas, valor crítico, índices de soro), regras cadastradas e aprovadas pelo responsável técnico; repetição e teste reflexo
  por regra; roteamento de listas de trabalho; alertas automáticos; envio automático à RNDS. **Liberação automática é permitida,
  desligada até a validação**; o que foge das regras vai à revisão humana.
- **Produção e notificação**: produção por procedimento SIGTAP e unidade (BPA); alerta de agravo da lista nacional.
- **Segurança e privacidade**: perfis por função e unidade, acesso de emergência auditado, dado pessoal mínimo em etiqueta e manifesto,
  estação offline cifrada e retenção de cinco anos.

## Capabilities

### New Capabilities
- `saude/sus-solicitacao-de-exame`: pedido do SUS com CNS/CPF, CNES, CBO, procedimento SIGTAP, prioridade e preparo.
- `saude/sus-rastreabilidade-e-etiquetagem`: identificador do tubo, identificação positiva, etiquetas em padrão internacional,
  reimpressão, custódia imutável e rastreio de lote, equipamento e versão.
- `saude/sus-coleta-e-recepcao`: ciclo de estados, rejeição, recoleta, coleta em campo e recepção.
- `saude/sus-remessa-de-amostras`: lote, manifesto, conferência por tubo, transporte e divergência.
- `saude/sus-integracao-com-analisadores`: ordem e resultado por HL7 v2 e LIS01/LIS02, armazenar-e-reenviar, idempotência e
  quarentena.
- `saude/sus-analise-e-liberacao`: casamento por identificador exato, controle de qualidade, liberação, retificação e valor crítico.
- `saude/sus-autoverificacao-e-automacao`: regras de autoverificação, repetição, teste reflexo, roteamento e alertas automáticos.
- `saude/sus-assinatura-e-autenticidade`: assinatura ICP-Brasil do biomédico, carimbo de tempo, verificação pública e assinatura de lote.
- `saude/sus-portal-do-paciente`: recuperação do exame pelo número da requisição, segundo fator, interface responsiva e acessível.
- `saude/sus-autenticacao-de-resultado`: código e QR no laudo, página pública de validação pelo paciente, estado do laudo
  (autêntico, vigente, retificado, revogado) e proteção contra enumeração e vazamento.
- `saude/sus-resultado-e-entrega`: devolução ao solicitante, prazo por etapa, REL/RNDS e consulta pelo paciente.
- `saude/sus-equivalencia-ao-gal`: cadastros, requisição entre unidades, estatísticas, vigilância e transição com o GAL.
- `saude/sus-producao-e-notificacao`: produção por procedimento SIGTAP e alerta de notificação compulsória.
- `saude/sus-cadastro-de-pacientes`: cadastro próprio de pacientes com deduplicação, fusão rastreável e vínculo de trabalhador.
- `saude/sus-integracao-com-erpnext`: módulo de integração acoplável ao ERPNext (profissionais do Employee, estoque de reagentes),
  sem dependência do núcleo.
- `saude/sus-integracao-com-esocial`: dado de exame ocupacional para o S-2220, montado e enviado pelo módulo de integração.
- `saude/sus-prontuario-do-paciente`: prontuário único como linha do tempo só de acréscimo, guarda de 20 anos, eliminação formal e cópia.
- `saude/sus-protecao-de-dados`: LGPD — base legal, direitos do titular, incidente, RIPD, encarregado, anonimização e transferência.
- `saude/sus-tropicalizacao`: idioma, formatos, fuso e horário de verão, dias úteis, tabelas oficiais (IBGE, CBO, CID, CNES, SIGTAP,
  TUSS), ICP-Brasil e NTP.br.
- `saude/sus-seguranca-e-privacidade`: perfis, acesso de emergência, minimização de dado, trilha de auditoria e canal cifrado.

### Modified Capabilities

<!-- Nenhuma. O módulo é novo e independente: não altera capacidade existente. O change `integrar-laboratorio-e-imagem` cobre o
     laboratório privado/hospitalar sobre o Healthcare; os dois coexistem e podem convergir depois, sem depender um do outro. -->

## Impact

- **Código novo**: pacote `laboratorio_sus/` com `puro/` (regra, sem `frappe`), app Frappe do núcleo, serviço de interface com
  analisadores (processo à parte, fila durável) e `integracao_erpnext/` (módulo acoplável). Testes puros rodam em qualquer máquina.
- **Independência**: o núcleo não importa `erpnext_brasil`, `erpnext`, `healthcare` nem `frappe` na camada pura (teste arquitetural).
  A integração com o ERPNext é a única que conhece os dois lados.
- **Integrações externas**: analisadores (HL7 v2, LIS01/LIS02), RNDS (REL, FHIR), GAL (transição), SIGTAP, CNES, SINAN, provedor de
  assinatura ICP-Brasil e carimbo de tempo.
- **Infraestrutura**: impressoras térmicas (ZPL ou TSPL) nas unidades, leitores de código de barras linear e 2D, conversores
  serial/TCP para analisadores, caixas de transporte com registrador de temperatura quando o analito exigir, estação offline para
  campo, certificados ICP-Brasil dos biomédicos.
- **Healthcare (Marley) opcional**: a documentação (marleyhealth.io/docs) mostra Sample Collection com etiqueta "Sample ID Print" sem
  código de barras, Diagnostic Report sem assinatura digital e Observation sem integração de resultado; é onde o módulo agrega.
- **Regulatório**: LGPD (Lei 13.709/2018, texto compilado lido), Lei 13.787/2018 (prontuário digital), RDC 786/2023 (ANVISA), RDC 504/2021 (transporte de material biológico), LGPD, Portaria GM/MS 8.276/2025 (REL),
  Lista Nacional de Notificação Compulsória, Lei 14.063/2020 e MP 2.200-2 (assinatura). Enquadramento como software como
  dispositivo médico (RDC 657/2022): **a confirmar**, pois a autoverificação aproxima o produto de apoio à decisão.
- **eSocial**: S-2220 (envio até o dia 15 do mês seguinte ao ASO, segundo fontes secundárias de 2021 a 2022; exame pela Tabela 27;
  `dtExm` não anterior à admissão, salvo admissional). Leiaute oficial e MOS vigentes **não foram lidos**. **Premissa registrada**:
  "e-social" foi lido como eSocial/S-2220; quem transmite o S-2220 é o empregador, não o laboratório (a confirmar).
- **Não verificado**: texto pago de CLSI AUTO12, AUTO02, AUTO10, AUTO15, LIS01/LIS02 e ISO 15189:2022; especificações GS1; existência de
  resolução do CFBM sobre assinatura de laudo (**não encontrada**); interface de troca de dados do GAL; quais procedimentos SIGTAP
  exigem BPA individualizado; quem envia o REL e desde quando; regras de repetição e teste reflexo (sem fonte consultada).
