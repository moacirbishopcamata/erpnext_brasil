## Context

Ver `proposal.md` (Why). Estado verificado em 2026-10-12:

- **Existe um change irmão**, `integrar-laboratorio-e-imagem`, que desenha rastreabilidade, etiquetagem e integração com analisadores
  para um laboratório com Healthcare. **Este módulo é independente**: não depende dele, do Healthcare, do ERPNext nem do app fiscal. Onde
  os dois resolvem o mesmo problema (identificador de tubo, custódia, quarentena, retificação em novo laudo), este change **reimplementa a
  regra na própria camada pura**: duplicar uma regra pequena custa menos que acoplar dois módulos. Podem convergir depois.
- **O que o Marley Health (Healthcare) oferece**, lido na documentação (marleyhealth.io/docs): `Sample Collection` com a etiqueta
  "Sample ID Print" e o campo "No. of prints", **sem menção a código de barras**; `Observation` e `Diagnostic Report` com resultado
  preenchido manualmente, aprovação por observação e **sem menção a assinatura digital nem a integração de resultado**. É a lacuna que o
  módulo preenche. O Healthcare não tem CPF/CNS nem dispositivo de laboratório (leitura do código, change irmão).
- **GAL** (manuais de LACENs estaduais): sistema do DATASUS com a SVS/CGLAB; o município cadastra a requisição antes de enviar a amostra,
  o analista libera o resultado online e o município imprime o laudo; módulos Biologia Médica Humana, Animal e Ambiental. **Não foi
  encontrada interface oficial de troca com sistema externo.**
- **REL/RNDS** (texto da Portaria GM/MS 8.276/2025 lido em bvsms): 21 itens de conteúdo mínimo, art. 3º obriga o envio "regularmente",
  **sem prazo numérico** e **sem nomear quem envia**; as especificações técnicas ficam no Portal de Serviços do DATASUS (**não lidas**).
- **LGPD** (texto compilado lido a partir de arquivo enviado pelo usuário): art. 11, II, *f* e *b* sustentam o tratamento sem consentimento;
  §4º do art. 11 resguarda "serviços auxiliares de diagnose e terapia"; art. 20 hoje **não exige** revisão por pessoa natural (a MP
  869/2018 e a Lei 13.853/2019 a retiraram); art. 19 fixa acesso simplificado imediato e declaração completa em 15 dias; art. 52 admite
  suspensões e bloqueio também para ente público. Análise completa em `docs/laboratorio-sus-lgpd.md`.
- **Prontuário**: Lei 13.787/2018 fixa 20 anos mínimos do último registro (fonte secundária); RDC 786 fixa guarda do laboratório (art. 81,
  lido no change irmão, 5 anos) e uma fonte não normativa indicou 3 anos. **Divergência registrada** na tarefa 1.12.
- **Autoverificação** (resumos de estudos e do CLSI AUTO10/AUTO15): categorias de critério e a ideia de que cada laboratório constrói,
  valida e aprova as próprias regras. Estudos relatam cerca de 80% dos resultados autoverificados e discordância de especialistas perto de
  0,8%; **não há padronização de algoritmos**. Repetição e teste reflexo **não têm fonte consultada**.
- **Etiqueta** (resumos): CLSI AUTO12 define conteúdo e leiaute (2 x 1 pol preferido, nome no canto superior esquerdo) e AUTO02 define o
  código de barras do tubo (Code 128). Data Matrix e GS1 DataMatrix para espaços pequenos. **Textos pagos e especificações GS1 não lidos.**
- **Assinatura**: não foi encontrada resolução do CFBM sobre laudo ou assinatura. Por analogia, a Resolução CFM 2.299/2021 exige ICP-Brasil
  nível NGS2 para documentos médicos eletrônicos; vale para médicos. A prática de mercado já usa certificado ICP-Brasil do responsável técnico.
- **eSocial S-2220** (fontes secundárias de 2021 a 2022): envio até o dia 15 do mês seguinte ao ASO; exame pela Tabela 27; `dtExm` não
  anterior à admissão salvo admissional. O repositório já tem `erpnext_brasil/folha/` com assinatura, lote e SOAP de eSocial, mas **sem S-2220**.
- **Padrão do projeto**: regra pura em módulos sem `frappe`, camada fina de integração, adaptadores por `Protocol`, teste arquitetural com
  `ast`. A camada pura inicial (tarefas 2.1 a 2.8) já existe em `laboratorio_sus/puro/`.

## Goals / Non-Goals

**Goals:**
- Tornar **impossível por construção** anexar resultado a tubo por inferência e **visível e recuperável** tudo o que não casa.
- Cobrir o ciclo inteiro, da requisição à entrega, ao prontuário e à produção, com custódia verificável também **entre unidades**.
- **Fazer o que o GAL faz** para a biologia médica humana e integrar-se com os analisadores, com total rastreabilidade (lote, equipamento,
  versão de método, regra aplicada) e automação controlada (autoverificação, repetição, roteamento, alertas).
- Ser **independente do ERPNext** e **acoplável a ele** por módulo de integração (profissionais do Employee, estoque de reagentes).
- Estar **conforme a LGPD desde a concepção**, com o prontuário como raiz dos dados, guarda de 20 anos e portal responsivo do paciente.
- Ser **totalmente tropicalizado**.

**Non-Goals:**
- **Interpretar resultado clínico ou apoiar decisão clínica** além da verificação analítica por regra: a autoverificação é controle de
  qualidade analítico, não diagnóstico. Enquadramento como software como dispositivo médico (RDC 657/2022): **a confirmar**.
- Imagem e PACS (ficam no change irmão); banco de sangue (ISBT 128); anatomia patológica; amostra animal e ambiental (módulos do GAL fora do início).
- Faturamento privado (TISS); certificação SBIS e acreditação.

## Decisions

### 1. Núcleo independente, integração à parte

O núcleo (pacote `laboratorio_sus/`) nunca importa ERPNext, Healthcare ou `erpnext_brasil`. O módulo `integracao_erpnext/` é o único que
conhece os dois lados; teste arquitetural com `ast` garante. *Alternativa recusada:* estender o Healthcare, que acopla a um app GPL de terceiro.

### 2. Portas (`Protocol`) para tudo que é de fora

Cadastro, entrada de resultado, impressão, relógio, assinatura, RNDS, GAL e envio de mensagem são interfaces com implementação própria
mínima. Sem adaptador, o módulo opera com cadastro próprio e digitação conferida. Mesma inversão de dependência de `integracao/repositorio_frappe.py`.

### 3. O prontuário é a raiz de todos os dados

Um prontuário por paciente, **linha do tempo só de acréscimo**, com hash por entrada. Solicitação, amostra, resultado, laudo, ocorrência,
consentimento, revisão e acesso são entradas ou referenciam o prontuário. O prontuário concentra **guarda, acesso, auditoria e direitos do
titular**. Segundo a disciplina de agregados do projeto, o exame continua agregado próprio (ciclo de vida independente) e referencia o
prontuário **por Id**, nunca por objeto. *Alternativa recusada:* um agregado "paciente" enorme com todos os exames dentro (contenção e
bloqueio por escrita).

### 4. Guarda do prontuário: 20 anos do último registro, eliminação formal

O piso é o maior prazo aplicável (Lei 13.787: 20 anos), parametrizável para cima; o módulo **não elimina sozinho**. A RDC 786 vira piso
interno do que está no laboratório, não motivo para eliminar antes. A decisão final sobre 3, 5 e 20 anos é a tarefa 1.12.

### 5. Identificador do tubo e número da requisição: dois objetos, duas funções

O **identificador do tubo** é opaco, com dígito de conferência (Verhoeff), contador transacional, nunca reaproveitado, e vai no código de
barras. O **número da requisição** é aleatório, não adivinhável, com dígito de conferência, e é o que o paciente digita no portal; os dois
nunca se confundem. *Alternativa recusada:* um número só em sequência, que serviria para enumerar exames de terceiros.

### 6. Etiquetas por descrição neutra, geradores por linguagem

O rótulo é descrito de forma neutra (campos, posição, simbologia) e gerado em ZPL (padrão) ou TSPL por geradores. A simbologia vem do tipo de
recipiente: Code 128 para tubo, Data Matrix/GS1 DataMatrix para micro e criotubos e lâminas. A impressão é recusada quando o código não cabe
no módulo mínimo. Dimensões, zonas de silêncio e módulo mínimo são **parâmetros que dependem da tarefa 1.8** (textos pagos).

### 7. Coleta em campo: faixa de identificadores reservada por estação

Implementado em `puro/faixa.py`: só o *número* é reservado; o não usado é anulado e registrado; o duplicado vai à quarentena.

### 8. Custódia só de acréscimo encadeada por hash; remessa de primeira classe

Implementado em `puro/custodia.py`. A remessa tem identificador, manifesto e etiqueta sem dado pessoal; divergência vira ocorrência.

### 9. Casamento só por identificador exato; o resto é quarentena

Motivos enumerados em `puro/rejeicao.py`; saída por decisão humana registrada com conferência do tubo físico. Vale para digitação, arquivo,
analisador e GAL.

### 10. Analisadores: leitores puros e transporte separado

Leitores de HL7 v2 (LAW) e LIS01/LIS02 sem E/S; serviço de interface em processo à parte com fila durável (SQLite em modo WAL),
confirmação ao equipamento só depois de gravar, entrega em ordem por equipamento e aplicação por chave de idempotência. A mensagem bruta é
guardada com hash. *Alternativas recusadas:* fila do Frappe (vive junto do ERP que pode cair) e *broker* externo (peso desproporcional).

### 11. Autoverificação: motor puro, regras aprovadas, liberação automática desligada por padrão

O motor avalia critérios (controle de qualidade, flags, *delta check*, faixas, crítico, índices de soro, média móvel); só libera quando
**todos** passam, a regra está **aprovada nominalmente** e a liberação automática do exame foi **ativada**. Crítico, controle reprovado,
lacuna e quarentena nunca são autoverificados. Cada decisão registra regra, versão e valores. A discordância é monitorada por regra.
**Revisa** a decisão do change anterior de "liberação manual por padrão": a automação é permitida, mas sob aprovação e monitoramento.

### 12. Assinatura: ICP-Brasil pessoal, PAdES, carimbo de tempo, assinatura de lote

O laudo é assinado com o certificado do biomédico liberador; o titular do certificado deve corresponder ao profissional logado e estar
habilitado. O resultado autoverificado referencia a **assinatura de lote** do responsável técnico e a versão da regra. Provedor por porta
(A1 em arquivo, A3 e nuvem por adaptador). *Alternativa recusada:* assinatura por imagem, sem valor probatório.

### 13. Autenticação do resultado: código aleatório, segundo fator, hash do PDF

Código não adivinhável impresso com QR; a validação pública sem segundo fator só mostra autenticidade e situação; com segundo fator mostra o
conteúdo. O paciente pode enviar o PDF para conferir o hash (processado em memória). A assinatura ICP-Brasil é verificável fora do sistema.

### 14. Portal do paciente pelo número da requisição, responsivo

Recuperação por número da requisição e segundo fator, com limite de tentativas e resposta idêntica contra enumeração. Interface responsiva e
acessível em celular, tablet e computador, como o ERPNext e seus módulos.

### 15. Equivalência ao GAL e transição

O módulo é o sistema principal. A transição é por importação e exportação, no formato que o GAL aceitar (tarefa 1.4); sem interface oficial,
por arquivo ou digitação conferida. Divergência entre os dois vai à quarentena. O escopo inicial é humano.

### 16. Integração com o ERPNext

Profissionais vêm do **Employee** (nome, CPF, conselho, registro, UF, CBO, situação) como projeção mínima; o cadastro do ERPNext é a fonte.
Reagentes, calibradores, controles e lotes vêm do estoque; o consumo volta. O ERPNext vê produção e consumo sem dado identificável.
Sincronização idempotente; o ciclo não para se o ERPNext cair. Healthcare é adaptador opcional.

### 17. eSocial: dado neutro no núcleo, evento no módulo de integração

O núcleo expõe o registro neutro do exame ocupacional; o módulo de integração monta o S-2220, o assina e o transmite com a infraestrutura de
`erpnext_brasil/folha/`. Quem transmite é configuração explícita: o empregador, ou exportação do dado.

### 18. LGPD como requisito de projeto, não como revisão final

Inventário das atividades com base legal, direitos do titular por funcionalidade, revisão humana da autoverificação (oferecida mesmo sem a
lei exigir), incidente com relógio de dias úteis, RIPD antes da operação, publicidade da dispensa de consentimento (art. 11 §2 e art. 23),
anonimização com supressão de células pequenas, atenção à transferência internacional.

### 19. Tropicalização como camada de dados versionados

Tabelas oficiais (IBGE, CBO, CID, CNES, SIGTAP, Tabela 27, TUSS, LOINC) são dados versionados com origem e vigência, não código. Fuso e
horário de verão históricos e dias úteis com feriados nacionais ficam em módulos puros testados.

### 20. Estratégia de teste

Testes puros para estados, identificadores, hash, faixa, rejeição, tempos, regras de autoverificação, leitores de protocolo, formatos e
calendário; teste de bench para DocTypes, permissões por unidade e fluxo completo; simulador de analisador HL7/LIS02; teste de troca (dois
tubos lidos em sequência); testes de caos (queda no meio da sincronização, relógio fora da tolerância, mensagem fora de ordem, reenvio à RNDS).
A validação clínica e do sistema (RDC 786, art. 72) é do serviço, em modo sombra.

## Análise de perigos (segurança do paciente)

| # | Perigo | Controle de projeto | Como se verifica |
|---|---|---|---|
| P1 | Tubo coletado de um paciente e etiquetado para outro | Identificação positiva; etiqueta só na coleta; sem lote antecipado | Teste de impressão sem confirmação |
| P2 | Etiqueta duplicada ou trocada | Reimpressão com motivo e "2ª via"; impressão auditada | Teste de reimpressão |
| P3 | Tubo sem rótulo na bancada | Coleta não confirma sem impressão; recepção retém código desconhecido | Teste de falha de impressora |
| P4 | Alíquota com rótulo de outro paciente | Rótulo só após ler o tubo pai | Teste de recusa sem leitura |
| P5 | Leitura de código errada | Dígito de conferência; casamento exato | Teste com um dígito alterado |
| P6 | Mesmo identificador em duas estações offline | Faixa reservada por estação; duplicado em quarentena | Teste de sincronização com colisão |
| P7 | Tubo perdido ou trocado no transporte | Conferência por tubo nas duas pontas; ocorrência; alerta de trânsito | Teste de tubo a mais e faltante |
| P8 | Amostra degradada aceita | Temperatura e tempo comparados à estabilidade; rejeição enumerada | Teste de estabilidade vencida |
| P9 | Resultado atribuído a tubo por aproximação | Identificador exato; senão quarentena | Teste de identificador inexistente |
| P10 | Erro de digitação do resultado | Dupla conferência; unidade e faixa explícitas | Teste de resultado sem conferência |
| P11 | Resultado de controle gravado em paciente | Controle separado; controle reprovado retém | Teste com controle e com paciente |
| P12 | Unidade ou escala errada | Sem conversão implícita; retenção | Teste de unidade diferente |
| P13 | Laudo corrigido em silêncio | Retificação só em novo laudo | Teste de edição de laudo liberado |
| P14 | Valor crítico não comunicado | Pendência de comunicação em destaque; nunca autoverificado | Teste de crítico sem registro |
| P15 | Laudo entregue à unidade errada | Entrega por unidade solicitante; perfil por unidade | Teste de acesso de outra unidade |
| P16 | Vazamento de dado de saúde | Dado mínimo em etiqueta e manifesto; trilha; emergência auditada; estação cifrada | Teste de decodificação do código; revisão de acesso |
| P17 | Hora errada no carimbo | Relógio sincronizado; bloqueio por desvio; fuso e horário de verão tratados | Teste de desvio e de horário de verão |
| P18 | Alteração do registro por acesso ao banco | Hash encadeado no prontuário e na custódia; verificador | Teste de adulteração |
| P19 | Resultado divergente entre este módulo e o GAL | Nenhum sobrescreve; quarentena | Teste de divergência |
| P20 | Etiquetadora parada na coleta | Contingência com rótulo manual e reconciliação | **Pergunta em aberto** (procedimento) |
| P21 | **Regra de autoverificação errada libera resultado indevido** | Aprovação nominal; liberação automática desligada por padrão; exclusões; monitoramento de discordância; desligamento por regra | Teste de cada critério e de regra não aprovada; teste de discordância acima do limite |
| P22 | Laudo assinado com certificado expirado ou revogado, ou de outra pessoa | Conferência antes de assinar; titular igual ao profissional; validade registrada | Teste de cada recusa |
| P23 | Mensagem de analisador fora de ordem ou duplicada | Versões por horário de análise; chave de idempotência | Teste com mensagens embaralhadas e repetidas |
| P24 | Etiqueta ilegível por módulo ou tamanho do código | Recusa quando não cabe no módulo mínimo; leitura de teste | Teste de código que não cabe |
| P25 | Conflito de resultado em transição com o GAL | Quarentena; sem sobrescrever | Teste de divergência entre sistemas |
| P26 | Número da requisição adivinhado no portal | Aleatório; segundo fator; limite de tentativas; resposta idêntica | Teste de varredura |
| P27 | Empregador recebendo mais que o dado do ASO | Dado neutro mínimo; configuração explícita de quem transmite | Teste de conteúdo do registro ocupacional |
| P28 | Eliminação do prontuário antes do prazo | Piso de 20 anos; eliminação formal com aprovação | Teste de eliminação antes do prazo |
| P29 | Lote de reagente defeituoso sem rastro | Lote ligado a cada resultado; consulta nos dois sentidos | Teste de lote recolhido |
| P30 | Profissional desligado continua liberando | Sincronização do Employee desabilita; laudos antigos permanecem válidos | Teste de biomédico desligado |

## Risks / Trade-offs

- **Software como dispositivo médico (RDC 657/2022)** → a autoverificação aproxima o produto de apoio à decisão; manter o escopo analítico e
  consultar a ANVISA ou especialista **antes** de operar fora do próprio serviço.
- **Escopo muito grande** → o plano tem 21 grupos. Mitigação: o núcleo (grupos 1 a 9) entrega valor sozinho; automação, assinatura,
  portal, GAL, integrações e eSocial vêm depois, cada um desligável.
- **Duplicação com o change irmão** → regras reimplementadas. Mitigação: nomes alinhados; convergência quando ambos estiverem estáveis.
- **Fontes pagas ou não lidas** (CLSI AUTO12, AUTO02, LIS01/02, ISO 15189, GS1, leiaute eSocial, guia FHIR do REL) → parâmetros marcados
  como a confirmar e tarefas de fonte primária no grupo 1 **antes** de cada implementação.
- **Interface do GAL desconhecida** → sem interface oficial localizada; transição por arquivo ou digitação; funciona sem ela.
- **Autoverificação e confiança excessiva** → viés de automação. Mitigação: poucas regras, todas aprovadas, taxa de discordância
  monitorada, revisão humana sob pedido.
- **Quarentena vira lixeira** → painel, envelhecimento e alerta.
- **LGPD** → leitura de artigos 33, 37, 38 e 42 ainda por resumo, e o texto sobre encarregado/ANPD foi reestruturado pela Lei 15.352/2026;
  instrumentos entre controladores e operadores dependem do jurídico de cada ente; **RIPD é pré-condição de operação**.
- **Guarda de 20 anos** → custo de armazenamento e superfície de risco por mais tempo. Mitigação: cifragem, backup testado, eliminação formal.
- **Conectividade ruim nas unidades** → a estação offline reduz o risco operacional e aumenta a superfície de segurança (dado local).
  Mitigação: cifragem, apagar após sincronizar, credencial revogável.
- **Normas mudam por portaria** → tabelas versionadas com vigência, não código fixo.
- **Sem equipamento nem unidade real** → nada foi exercitado em campo; modo sombra antes de ampliar.

## Migration Plan

1. **Núcleo em uma unidade coletora e no laboratório**, fluxo completo com digitação conferida e impressora de etiqueta, em paralelo ao
   processo atual (modo sombra: o módulo registra, o papel continua valendo).
2. **Remessa** entre essa unidade e o laboratório, depois a central de recebimento.
3. **Portal do paciente** e **assinatura** do laudo, com validação pública.
4. **Um analisador em modo sombra**; depois publicação com liberação por profissional; só então autoverificação, regra a regra.
5. **RNDS** em homologação, depois produção; **GAL** em transição conforme a interface confirmada.
6. **Integração com o ERPNext** (profissionais e reagentes), depois **eSocial**.
7. **Demais unidades e coleta em campo**.

Reversão: voltar uma unidade ao processo anterior não apaga o que foi gravado (prontuário e custódia imutáveis). Desligar a autoverificação
de uma regra devolve o exame à liberação por profissional. Nenhum passo altera outro módulo do repositório.

## Open Questions

- Nome do app e do repositório (provisório: `laboratorio_sus`) e **licença** (MIT, como o `erpnext_brasil`, ou GPL).
- **O que é o "LAM"** citado pelo usuário e como o CNES o representa (estabelecimento, serviço ou convênio): define a consulta de unidades.
- **Interface de troca de dados do GAL** e quais LACENs e estados serão atendidos.
- Quem envia o **REL** e desde quando; e quais procedimentos SIGTAP exigem BPA individualizado.
- **Norma de transporte** aplicável (RDC 504/2021) e os limites por exame.
- **Contingência** quando etiquetadora ou sistema caem (define o P20).
- **Política de assinatura**: nível do certificado, A1, A3 ou nuvem, e posição do CFBM/CRBM e da ANVISA.
- **Piso de guarda** do prontuário (3, 5 ou 20 anos) e a posição da Resolução CFM 1.821/2007 (guarda permanente).
- **Controlador e operadores** de cada ente (município, Estado, LACEN) e os instrumentos que os ligam; nome do encarregado.
- Quem **transmite o S-2220** em cada instalação e a versão vigente do leiaute.
- Escopo futuro de **anatomia patológica, microbiologia e amostra animal ou ambiental**.
- Se o módulo terá **adaptador do Healthcare** já na primeira versão (hoje: opcional).
