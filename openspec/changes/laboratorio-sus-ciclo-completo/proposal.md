## Why

O exame público do SUS tem um ciclo próprio que nenhum módulo do projeto cobre de ponta a ponta: o pedido nasce numa UBS, UPA ou
ambulatório diferente do que analisa; a amostra viaja entre unidades e até um laboratório de referência (LACEN); o paciente é
identificado por CNS/CPF; o exame é um procedimento da tabela SIGTAP, não um item de venda; o resultado volta ao solicitante e
à RNDS; alguns achados obrigam notificação; e a produção é declarada, não faturada. O dano mais grave nesse ciclo é um
**resultado atribuído à amostra ou ao paciente errado**, e o risco se concentra em três pontos: a etiqueta no ponto de
coleta, a passagem entre unidades e a devolução do resultado ao solicitante certo. Este change propõe o **modo laboratorial
do SUS como módulo avulso**: autocontido, instalável e testável sem depender de outro módulo de saúde.

## What Changes

- **Módulo avulso `laboratorio_sus`** (nome provisório): um app Frappe próprio que traz o **núcleo inteiro** do ciclo —
  solicitação, identificação do tubo, etiqueta, custódia, coleta, remessa, recepção, análise, liberação, entrega, produção e
  notificação. Não importa de, nem exige, o `erpnext_brasil` fiscal, o Healthcare ou o change `integrar-laboratorio-e-imagem`.
- **Integrações são adaptadores opcionais por porta** (interface), nunca dependência: cadastro de paciente e profissional
  (próprio, ou ponte para o Healthcare), entrada de resultado (digitação conferida, arquivo ou, no futuro, analisador),
  impressão de etiqueta, RNDS e GAL. Sem nenhum adaptador, o módulo funciona sozinho com digitação conferida.
- **Solicitação do SUS**: paciente por CNS/CPF validado, unidade (CNES) e profissional (conselho, CBO) solicitantes,
  procedimento SIGTAP da competência, prioridade, preparo, hipótese diagnóstica e origem.
- **Rastreabilidade e etiquetagem**: identificador de tubo opaco, único para sempre, com dígito de conferência; **identificação
  positiva** do paciente antes de imprimir; rótulo no ponto de coleta (nunca em lote antecipado) com o conteúdo do art. 104 da
  RDC 786/2023; reimpressão com rastro; cadeia de custódia só de acréscimo, encadeada por hash.
- **Coleta e recepção** com ciclo de estados explícito, **rejeição por motivo enumerado**, recoleta com novo tubo e coleta em campo
  com faixa de identificadores reservada à estação offline.
- **Remessa entre unidades**: lote, manifesto e etiqueta de remessa sem dado pessoal, conferência por tubo na saída e na chegada,
  condições de transporte e divergência tratada como ocorrência.
- **Análise e liberação**: entrada de resultado casada **só por identificador exato**, com dupla conferência na digitação,
  unidade e faixa de referência, controle de qualidade, quarentena do que não casa, liberação por responsável habilitado,
  **retificação sempre em novo laudo** e comunicação de valor crítico.
- **Entrega e relatórios ao sistema público**: devolução ao solicitante com prazo por etapa, REL/RNDS (Portaria GM/MS
  8.276/2025), intercâmbio com o GAL do laboratório de referência.
- **Produção e notificação compulsória**: produção por procedimento SIGTAP e unidade (BPA); alerta de agravo da lista nacional,
  sem decidir pelo profissional.
- **Segurança e privacidade**: perfis por função e unidade, acesso de emergência auditado, dado pessoal mínimo em etiqueta e
  manifesto, estação offline cifrada, trilha de acesso e retenção de 5 anos.

## Capabilities

### New Capabilities
- `saude/sus-solicitacao-de-exame`: pedido do SUS com CNS/CPF, CNES, CBO, procedimento SIGTAP, prioridade e preparo.
- `saude/sus-rastreabilidade-e-etiquetagem`: identificador de tubo, identificação positiva, rótulo, reimpressão e cadeia de
  custódia imutável.
- `saude/sus-coleta-e-recepcao`: ciclo de estados, rejeição, recoleta, coleta em campo e recepção.
- `saude/sus-remessa-de-amostras`: lote, manifesto, conferência por tubo, transporte e divergência.
- `saude/sus-analise-e-liberacao`: entrada e casamento do resultado, quarentena, controle de qualidade, liberação,
  retificação e valor crítico.
- `saude/sus-resultado-e-entrega`: devolução ao solicitante, prazo por etapa, REL/RNDS, GAL e consulta pelo paciente.
- `saude/sus-producao-e-notificacao`: produção por procedimento SIGTAP e alerta de notificação compulsória.
- `saude/sus-seguranca-e-privacidade`: perfis, acesso de emergência, minimização de dado e trilha de acesso.

### Modified Capabilities

<!-- Nenhuma. O módulo é avulso: não altera capacidade existente. O change `integrar-laboratorio-e-imagem` cobre o laboratório
     privado/hospitalar com Healthcare e analisadores; os dois podem coexistir e convergir depois, mas nenhum depende do outro. -->

## Impact

- **Código novo**: app Frappe `laboratorio_sus` e camada pura (máquina de estados, validação de CNS/CPF, dígito de conferência,
  regras de rejeição, tempo de resposta, divisão de faixa de identificadores, encadeamento de hash) **sem `frappe`**, no padrão
  de `fiscal/`, com os testes puros rodando em qualquer máquina.
- **Sem dependência de**: `erpnext_brasil`, Healthcare (GPL-3.0) e `integrar-laboratorio-e-imagem`. A ponte opcional com o
  Healthcare fica em adaptador separado, de modo que a licença do módulo não é condicionada por ele (escolha de licença: pergunta
  em aberto).
- **Integrações externas (opcionais)**: RNDS (REL, FHIR), GAL, tabelas SIGTAP e CNES, vigilância epidemiológica (SINAN).
- **Infraestrutura**: impressoras térmicas nas unidades coletoras, leitor de código de barras, caixa de transporte com
  registrador de temperatura quando o analito exigir, e estação offline para campo.
- **Regulatório**: RDC 786/2023 (ANVISA), LGPD, Portaria GM/MS 8.276/2025, Lista Nacional de Notificação Compulsória (Anexo 1 do
  Anexo V da Portaria de Consolidação GM/MS 4/2017, com alterações posteriores) e norma de transporte de material biológico
  (**a confirmar**).
- **Não verificado**: quais procedimentos SIGTAP do subgrupo 02.02 exigem BPA individualizado; quem tem a obrigação de enviar o
  REL e desde quando; se o GAL tem interface de troca de dados para sistemas externos; a norma vigente de transporte de amostra.
  Cada um é tarefa de fonte primária antes de codificar.
