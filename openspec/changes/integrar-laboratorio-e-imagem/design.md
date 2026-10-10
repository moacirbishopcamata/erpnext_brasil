## Context

Ver `proposal.md` (Why). O estado verificado em 2026-10-10, no código e nas fontes oficiais:

- **Healthcare (Marley Health 16.6.1, GPL-3.0)** instala e migra sobre Frappe 16.51, ERPNext 16.50 e PostgreSQL 18 (site de teste
  `hc16pg.localhost`). Tem 127 DocTypes, entre eles `Lab Test`, `Lab Test Template`, `Sample Collection`, `Specimen`,
  `Observation` e `Diagnostic Report`. **Não tem** DocType de dispositivo, interface HL7/ASTM nem DICOM; as menções a HL7 no
  código são terminologias (`Code System`: SNOMED CT, RxNorm, LOINC, UCUM, ICD). Há funções de API que lançam resultado
  (`record_observation_result`, `add_observation`), sem identificação de equipamento nem controle de repetição.
- **RDC 786/2023 (ANVISA)**, lida no texto oficial (versão consolidada com a RDC 824/2023), define o que o sistema precisa provar:
  política de acesso e histórico de alteração com data, horário, usuário e local (art. 71); verificação do sistema antes de
  usar, documentada (art. 72); gestão de riscos (art. 73); rastreabilidade da coleta ao descarte (art. 94, 97); cadastro do
  paciente e do exame (art. 100, 102); identificação do material com nome, nascimento ou idade, tipo de material e data e
  hora da coleta (art. 104); liberação e assinatura (art. 136, 137), conteúdo do laudo (art. 138), retificação em novo laudo
  (art. 140); controle interno da qualidade por analito (art. 142 a 147); guarda de 5 anos (art. 81). O prazo de adequação foi
  de 180 dias da publicação (art. 154). **A norma não menciona relógio nem interface com equipamento.**
- **O app fiscal já resolve três problemas que aparecem aqui**: relógio sincronizado (NTP.br, com política de desvio e
  guarda), idempotência de transmissão e recusa preventiva antes de gastar um recurso irrecuperável (o número da série; aqui,
  o identificador do tubo).
- Padrões de integração, lidos em fontes secundárias (a norma é paga ou o suplemento é antigo): CLSI **LIS01** (protocolo de
  baixo nível, ex-ASTM E1381, já com TCP/IP na edição A2) e **LIS02** (conteúdo, ex-ASTM E1394); **HL7 v2** no perfil **IHE LAW**
  (transações LAB-27 consulta, LAB-28 ordem `OML^O33`, LAB-29 resultado `OUL^R22`; HL7 2.5.1, o recipiente na `SAC-3`);
  **HL7 v2 ORU^R01** para resultado; **CLSI POCT01-A2** para equipamento de ponto de atendimento; **CLSI AUTO12** para o
  rótulo (2 x 1 polegada, nome do paciente no canto superior esquerdo); **DICOM** com lista de trabalho da modalidade (C-FIND) e
  DICOMweb, com o **Orthanc** como PACS aberto (plugin de worklists, REST).
- **RNDS**: o modelo nacional de resultado laboratorial é um perfil FHIR; os guias estaduais que o reutilizam (SES-GO) apontam
  LOINC, Tabela SUS (subgrupo 0202), tipos de exame do GAL, TUSS 4.03 e CBHPM 4.03 para o tipo de exame. A página nacional não
  foi lida.
- **TISS** (para o faturamento, fora deste change): a versão 04.03.00 existe e consta no histórico oficial da ANS desde
  nov/2025; o prazo de implantação é 30/06/2026 para as competências de nov/2025 a mai/2026 e 31/12/2026 para set/2026. A
  página "Monitora TISS" da ANS ainda cita a 04.02.00 como vigente: **as duas páginas oficiais divergem**.

## Goals / Non-Goals

**Goals:**
- Tornar **impossível, por construção**, anexar resultado a uma amostra por inferência, e **visível e recuperável** tudo o que
  não casa.
- Manter a cadeia de custódia completa, imutável e verificável, com retenção e recuperação previstas pela norma.
- Aguentar a queda do ERPNext, do serviço de interface, da impressora e do relógio sem perder nem duplicar mensagem.
- Ser **desligável sem perda**: cada equipamento entra em modo sombra, e o laboratório pode voltar ao processo anterior.

**Non-Goals:**
- **Interpretar resultado ou apoiar decisão clínica** (sugerir diagnóstico, calcular risco). Isso poderia enquadrar o produto
  como software como dispositivo médico (RDC 657/2022) e fica de fora de propósito.
- Faturamento TISS/TUSS, glosa e repasse médico (change próprio).
- Banco de sangue (ISBT 128, hemovigilância) e biobanco.
- Guardar imagens médicas no ERPNext.
- Certificação SBIS e acreditação (PALC, ISO 15189) — o desenho as facilita, mas não as promete.

## Decisions

### 1. Dois artefatos novos, ambos fora do `erpnext_brasil` e do Healthcare

Um **app Frappe** (`saude_brasil`, nome provisório) com os DocTypes de custódia, rótulo, quarentena e correspondência, e um
**serviço de interface** (Python, processo à parte) que fala com os equipamentos. O app fiscal não exige o que não usa, e o
Healthcare (GPL, de terceiro) não é alterado: integra-se por DocTypes, campos e API públicos.
*Alternativas recusadas:* pôr tudo no `erpnext_brasil` (acopla fiscal e saúde, mesma razão de o HRMS entrar por
`regional_overrides`); bifurcar o Healthcare (carrega a manutenção de um app GPL e perde atualizações).

### 2. O ERPNext guarda pedido, estado e laudo; o equipamento fica atrás de um intermediário

Conexão com aparelho é longa, serial ou TCP e sobrevive à queda do ERP; o Frappe é um servidor de requisições. O serviço de
interface mantém as conexões e conversa com o ERPNext por API autenticada. Mesma conclusão da decisão 6 do change
`tropicalizar-demais-modulos`.

### 3. Identidade do tubo: número opaco, único para sempre, com dígito de conferência

O identificador do tubo e o da alíquota são numéricos, **sem significado** (nada de data ou paciente embutido), com dígito de
conferência, gerados por contador transacional e **nunca reaproveitados**; o comprimento é parâmetro do perfil do equipamento.
O código de barras carrega só esse número. *Alternativa recusada:* número de acesso curto que reinicia por dia — colide na
virada, e é exatamente o cenário da amostra trocada. O dígito de conferência pega leitura errada; **é escolha de projeto, não
exigência de norma**.

### 4. Cadeia de custódia: eventos só de acréscimo, com encadeamento por hash

Cada evento guarda o hash do evento anterior do mesmo tubo; um verificador periódico recalcula a cadeia e alerta quebra.
O histórico nativo do Frappe (`Version`) é editável por quem tem acesso ao banco e não serve como prova.
*Custo:* um campo e uma verificação; *ganho:* adulteração detectável, não apenas proibida.

### 5. Etiquetagem: impressão no servidor, em ZPL por padrão, só a partir de coleta iniciada

O servidor envia a etiqueta à impressora de rede (ZPL na porta 9100; perfil TSPL para impressoras TSC), de modo que a
impressão seja auditável e não dependa da estação. Impressora USB local usa um agente (QZ Tray) como segunda opção. O fluxo
exige a identificação positiva do paciente antes de imprimir, o conteúdo do art. 104 mais o código do tubo, e a marca de
segunda via. O leiaute segue a ordem do AUTO12 (nome no canto superior esquerdo, código ao lado), configurável por tipo de
tubo; **o texto do AUTO12 é pago e não foi lido**. Etiquetadora automática de bancada entra pela mesma interface de impressão.
*Alternativa recusada:* `Print Format` do navegador com PDF — o resultado depende do driver e do navegador de cada estação, e
não deixa registro do que foi impresso.

### 6. Protocolos: analisadores de mensagem puros, transporte separado

Dois leitores puros (LIS02 sobre LIS01 e HL7 v2 no perfil LAW) que recebem bytes ou texto e devolvem estruturas, sem I/O — no
mesmo padrão do `fiscal/` e testáveis com arquivos de exemplo. O transporte (serial, TCP, MLLP) é outra camada, trocável.
*Alternativas consideradas:* usar um motor de integração pronto ou reaproveitar os leitores do SENAITE (a **licença de ambos
não foi confirmada**; não assumir GPL nem permissiva antes de abrir o `LICENSE`); escrever só o necessário, com fronteira clara
para trocar o transporte depois. Preferida: escrever o necessário e manter a fronteira.

### 7. Idempotência por chave derivada e mensagem bruta preservada

A chave de idempotência combina equipamento, identificador do tubo, código do exame, horário de análise do equipamento, valor e
sinalizadores, mais o identificador de controle da mensagem quando o protocolo o fornece. A **mensagem bruta é guardada
inalterada** (com hash) e o resultado é derivado dela, de modo que qualquer interpretação pode ser refeita e auditada.

### 8. Armazenar e reenviar: fila durável local, entrega pelo menos uma vez, aplicação exatamente uma vez

O serviço grava a mensagem em fila durável (SQLite em modo WAL) e só então confirma ao equipamento; entrega por equipamento, em
ordem, e o ERPNext aplica com a chave de idempotência, o que torna a repetição inofensiva. *Alternativas recusadas:* a fila do
Frappe (Redis/RQ) — vive junto do ERPNext que pode estar fora do ar; um *broker* externo — peso desproporcional para um
laboratório.

### 9. Quarentena como cidadã de primeira classe

Fila de pendências com **motivo enumerado** (identificador desconhecido, ambíguo, digitado à mão, demografia divergente, código
sem correspondência, unidade diferente, controle reprovado, lacuna na cadeia, relógio fora da tolerância). Sair da quarentena exige
usuário autorizado, decisão registrada e, quando o destino é um paciente, a conferência do tubo físico.

### 10. Relógio: mesma política do app fiscal, reimplementada, não importada

O ERPNext já mede o desvio por NTP.br e recusa operações quando o relógio é comprovadamente errado. O serviço de interface e as
estações de coleta aplicam a mesma política com carimbo duplo (recebimento e equipamento). **Duplica-se a política pura** em vez de
fazer o app de saúde depender do app fiscal: duplicar uma regra pequena custa menos que acoplar dois contextos.

### 11. Terminologia: tabela de correspondência no ERP, sem redistribuir tabelas licenciadas

A correspondência (código do equipamento ↔ exame ↔ LOINC ↔ TUSS ↔ UCUM) mora num DocType versionado. Guarda-se **apenas o que o
laboratório mapeou**; não se distribui a tabela completa do LOINC nem da TUSS (a licença do LOINC não foi lida; a TUSS é
publicada pela ANS por competência). Não foi encontrada correspondência oficial TUSS↔LOINC; a curadoria é do laboratório.

### 12. Laudo e liberação como regras sobre o Healthcare, não substituição

Verificações no `validate`/`before_submit` dos DocTypes existentes (`Lab Test`, `Diagnostic Report`) por `doc_events`, sem editá-los:
conteúdo do art. 138, retenção, assinatura, comunicação de crítico, retificação em novo documento. A assinatura legalmente válida
(Lei 14.063/2020) usa o certificado ICP-Brasil do profissional; o provedor de assinatura é pergunta em aberto.

### 13. Imagem: Orthanc como PACS de referência e identificação por número de acesso

O ERPNext publica o pedido na lista de trabalho da modalidade (plugin de worklists, por REST) e recebe a notificação do estudo;
o vínculo é por **número de acesso e identificador do paciente**, e o que não casa vai à mesma quarentena. DICOMweb para consulta e
visualizador externo (OHIF ou outro) para ver a imagem. Ressalva: a arquitetura do Orthanc foi lida em resumos; a lista de
trabalho por DICOM (C-FIND) é um serviço de rede à parte do DICOMweb.

### 14. Estratégia de teste: simulador, arquivos de exemplo, caos e troca

Simulador de analisador que fala LIS01/02 e HL7/MLLP; arquivos de exemplo (*golden files*) tirados das **especificações de interface
dos fabricantes do laboratório**; testes de propriedade para idempotência e ordem; testes de caos (derrubar ERP e serviço no meio do
fluxo; relógio adiantado e atrasado); teste de troca (dois identificadores quase iguais, leitura com um dígito errado). A
**validação clínica é do laboratório** (RDC 786, art. 72), em modo sombra.

## Análise de perigos (segurança do paciente)

Ordem de gravidade: o dano é diagnóstico ou conduta errados por resultado do paciente trocado.

| # | Perigo | Causa provável | Controle de projeto | Como se verifica |
|---|---|---|---|---|
| P1 | Tubo coletado de um paciente e etiquetado para outro | Rótulo impresso antes, em lote, ou sem confirmar a pessoa | Identificação positiva (2 identificadores ou pulseira); rótulo só de coleta iniciada; lote desligado por padrão | Teste de recusa sem confirmação; teste de impressão sem coleta |
| P2 | Rótulo duplicado ou trocado entre tubos | Reimpressão sem rastro; tubos na mesma mão | Reimpressão exige motivo e imprime "2ª via"; cada impressão registrada | Teste de reimpressão; revisão do registro |
| P3 | Tubo sem rótulo ou ilegível chega à bancada | Falha de impressora; rótulo mal colado | Falha de impressão não confirma a coleta; recebimento bloqueia código desconhecido | Teste de impressora desligada; teste de código ilegível |
| P4 | Alíquota com rótulo de outro paciente | Rótulo preparado à parte | Rótulo de alíquota só depois de ler o tubo de origem; identificador novo ligado ao pai | Teste de recusa sem leitura do pai |
| P5 | Equipamento lê o código errado | Código sujo ou torto | Dígito de conferência no identificador; casamento exato, sem aproximação | Teste com um dígito alterado |
| P6 | Identificador digitado à mão no equipamento | Etiqueta ilegível, pressa | Marcação do protocolo → resultado retido para conferência | Teste com a marcação ligada |
| P7 | Dois tubos com o mesmo identificador | Sequência curta que reinicia | Identificador único para sempre, nunca reaproveitado | Teste de unicidade; teste de reinício do contador |
| P8 | Resultado de controle gravado em paciente | Material de controle lido como amostra | Identificadores de controle cadastrados; controle nunca anexa a paciente | Teste com controle e com paciente de mesmo código |
| P9 | Mesmo resultado aplicado duas vezes | Reenvio do equipamento ou da fila | Chave de idempotência; repetição registrada | Teste de reenvio; teste de queda no meio da entrega |
| P10 | Resultado perdido | ERPNext fora do ar | Fila durável; confirmação só depois de gravar | Teste de caos com 50 mensagens |
| P11 | Resultado antigo sobrescreve o novo | Reentrega fora de ordem; repetição de exame | Versões; nenhuma sobrescrita; profissional escolhe a válida | Teste com mensagens embaralhadas |
| P12 | Resultado com hora errada | Relógio do equipamento ou do servidor | Carimbo duplo; tolerância; retenção; relógio não confiável bloqueia liberação | Teste de desvio adiantado e atrasado |
| P13 | Unidade ou escala errada | mg/dL x mmol/L | UCUM; sem conversão implícita; conversão só com regra aprovada | Teste de unidade diferente |
| P14 | Exame mapeado para o código errado | Correspondência obsoleta | Tabela versionada; código sem correspondência vai à quarentena | Teste de código desconhecido; revisão de versão da TUSS |
| P15 | Liberação automática de resultado duvidoso | Regra permissiva | Liberação manual por padrão; retido nunca libera | Teste de retenção |
| P16 | Laudo corrigido em silêncio | Edição do original | Retificação só em novo laudo; contato registrado | Teste de edição do laudo emitido |
| P17 | Alteração não autorizada de dado | Permissão ampla; acesso ao banco | Papéis; histórico com data, hora, usuário e local; hash encadeado | Teste de permissão; verificador de cadeia |
| P18 | Perda do registro dentro do prazo | Falha de armazenamento | Retenção de 5 anos; backup com teste de restauração | Teste de restauração |
| P19 | Exame errado enviado ao equipamento | Correspondência errada | "Sem trabalho" quando não há pedido; exame sem correspondência sinalizado, nunca presumido | Teste de consulta |
| P20 | Etiquetadora parada na coleta | Falha de hardware | Procedimento de contingência (rótulo manual com reconciliação) | **Pergunta em aberto** |
| P21 | Estudo de imagem ligado ao pedido errado | Número de acesso reaproveitado | Casamento por número de acesso e paciente; quarentena | Teste de número desconhecido |

## Risks / Trade-offs

- **Software como dispositivo médico (RDC 657/2022)** → o escopo exclui interpretação e apoio à decisão, mas o enquadramento de
  roteamento de resultado **não foi confirmado**; consultar a ANVISA ou um especialista antes de operar fora do próprio laboratório.
- **Licença** → o Healthcare é GPL-3.0 e o `erpnext_brasil` é MIT. Rodar no mesmo processo não é o mesmo que derivar; a leitura
  jurídica **não foi feita**. Mitigação: o app novo só usa API pública e DocTypes, sem copiar código do Healthcare.
- **Sem equipamento real** → protocolo e particularidades de cada fabricante só se confirmam com o aparelho. Mitigação: modo
  sombra, simulador, e arquivos de exemplo vindos das especificações de interface dos fabricantes do laboratório.
- **Padrões pagos ou antigos** → CLSI LIS01/LIS02/AUTO12/POCT01 e ISO 15189 não foram lidos; o IHE LAW foi lido por resumos de
  2013 a 2016. Mitigação: tarefa de fonte primária antes de cada implementação.
- **Quarentena vira lixeira** → se ninguém trabalha a fila, o resultado fica parado. Mitigação: painel, prazo de envelhecimento e
  alerta; é custo operacional que o laboratório precisa assumir.
- **Fadiga de alerta e viés de automação** → muitos avisos treinam o operador a ignorar. Mitigação: poucos motivos, todos bloqueantes,
  nenhum aviso decorativo.
- **Privacidade (LGPD, dado de saúde é sensível)** → rótulo e mensagens carregam dado pessoal. Mitigação: código de barras só com o
  identificador; registro técnico mínimo; canal cifrado; credencial de serviço de permissão mínima.

## Migration Plan

1. **Sem equipamento**: custódia, identificadores e etiquetagem no ponto de coleta, com a impressora do laboratório.
2. **Um analisador em modo sombra**: resultados recebidos e comparados com o processo atual, nada publicado; relatório de
   divergência até zerar as causas.
3. **Publicação com liberação manual** para esse analisador; os demais seguem no processo anterior.
4. **Demais analisadores**, um por vez, repetindo 2 e 3.
5. **Imagem**: uma modalidade, com Orthanc, em modo sombra primeiro.

Reversão: colocar o equipamento em modo sombra ou desligá-lo devolve o laboratório ao processo anterior; os dados já gravados são
imutáveis e permanecem. Nenhum passo exige alterar o Healthcare nem o `erpnext_brasil`.

## Open Questions

- Nome do app e do repositório (provisório: `saude_brasil`) e a **licença** do app novo (GPL-3.0, como o Healthcare, ou MIT).
- Quais **analisadores** (marca e modelo) o laboratório tem: sem isso, não há especificação de interface para os arquivos de exemplo.
- Quais **impressoras e etiquetadoras** (marca, linguagem ZPL ou TSPL, tamanho do rótulo e do tubo).
- **Contingência** quando a etiquetadora ou o sistema caem (rótulo manual e reconciliação posterior) — define o P20.
- **Provedor de assinatura** ICP-Brasil e o tipo de certificado dos profissionais (A1, A3 ou nuvem).
- Se a **RNDS** é obrigatória para prestadores privados e por qual portaria (herdada do change `tropicalizar-demais-modulos`).
- Enquadramento regulatório do produto (RDC 657/2022) e se o laboratório pretende SBIS ou PALC.
