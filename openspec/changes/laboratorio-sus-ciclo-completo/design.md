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
- **Farmácia e catálogo (lidos)**: a tabela CATMAT do e-SUS APS LEDI (v4.2.0, alterada em 26/04/2021) tem cinco colunas e **3.334 linhas**, com **2.765 códigos canônicos
  distintos**: 804 linhas têm sufixo `-N` (apresentações do mesmo item, como frascos de 80, 100 e 120 ml); há 6 códigos inválidos, 5 sem zeros ou com dígito a mais e 3 repetidos. Numa amostra de 80
  códigos, **todos existem no catálogo oficial (Compras.gov.br)**, **73 ativos e 7 inativos (cerca de 9%)**, e 3 não são medicamento (reagente, químico, cosmético). `BR0268315` é o item 268315
  (classe 6505, PDM 1601). A REMUME de Porto Velho (6ª edição, Portaria 05/2025-DAF/GAB/SEMUSA) tem 340 itens, 4 competências de financiamento, cerca de 20 subgrupos e 13 siglas de unidade;
  286 itens foram lidos com segurança e 54 foram para curadoria; 99 casam exatamente com o CATMAT e 42 só pelo princípio ativo.
- **Dispensação e redes nacionais (fontes secundárias)**: Hórus migra para o e-SUS Assistência Farmacêutica; a BNAFAR recebe posição de estoque e saídas por movimentação ou perda
  (Portaria GM/MS 5.713/2024) e a RNDS recebe a prescrição (REPM) e a dispensação (REDFM, Portaria 6.100/2024), com OBM e CATMAT (Portaria 6.093/2024); a entrega ao paciente é dispensação, não saída.
- **Lote e rastreabilidade (repositório e fontes)**: o repositório já lê GS1 (`fiscal/gs1.py`, a partir do GS1 Barcode Syntax Dictionary: AI 00, 01, 10, 11, 13, 15, 17, 21; o dia `00` vale o último dia
  do mês) e monta o `rastro` da NF-e (`nLote`, `qLote`, `dFab`, `dVal`), mas `ler_nfe` **não lê** `rastro` nem o grupo de medicamento. UDI (RDC 591/2021, alterada pela RDC 884/2024): UDI-DI e UDI-PI; rotulagem
  escalonada por classe (IV em 10/07/2025, III em 10/01/2026, II em 10/01/2027, I em 10/01/2028, pelo Ofício Circular 2/2025); base de dados UDI da ANVISA aguardando instrução normativa.
- **Armazenagem e despacho (secundárias)**: a RDC 430/2020 substituiu a RDC 304/2019 e define quarentena e qualificação térmica; a distribuição exclui o fornecimento direto ao público; recolhimento passou à RDC 625/2022;
  fracionamento é regido pela RDC 80/2006 e pelo Decreto 5.775/2006 (farmácias e drogarias, farmacêutico, embalagem fracionável). Práticas de recebimento em saúde pública: recebimento provisório
  (nota, empenho, transporte e volumes), conferência quantitativa e qualitativa, definitivo com ateste pelo fiscal do contrato ou da ata.
- **Contabilidade pública (secundárias)**: estoque pelo menor entre custo e valor realizável líquido, por custo médio ponderado ou PEPS, com critério uniforme por classe (NBC TSP 04); a variação patrimonial diminutiva ocorre
  no consumo; liquidação com contrato, empenho e comprovante de entrega (Lei 4.320/1964, arts. 62 e 63); ateste por servidor designado; SIAFIC obrigatório desde 01/01/2023 (Decreto 10.540/2020), um por município.
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

### 20. WMS próprio para insumos, amostras e coletas

O laboratório tem três "armazéns" com a mesma disciplina de movimento: **insumos** (reagentes, calibradores, controles, material de coleta),
**amostras armazenadas** e **kits de coleta**. Em todos: endereço físico hierárquico (equipamento, prateleira ou rack, caixa, posição);
**livro de movimentos só de acréscimo** com saldo derivado (como a custódia); leitura de código no movimento (lote ou tubo mais posição);
estado "em trânsito" na transferência; inventário cíclico com divergência tratada como ocorrência; e **bloqueio por regra** (vencido,
quarentena, excursão de temperatura, em investigação). Para insumos, FEFO e estabilidade após abertura; para amostras, retenção por
política com descarte **só com aprovação**; para coletas, rotas, kits e reconciliação solicitado, coletado, remetido e recebido. A interface usa
o princípio de que **o destino define a ação** (soltar em outro endereço transfere, na área de descarte descarta com confirmação, na
quarentena bloqueia). *Alternativa recusada:* usar o estoque do ERPNext como fonte única; ele não conhece posição de amostra, estabilidade
após abertura nem excursão de temperatura, e tornaria o módulo dependente dele (contra a decisão 1). O ERPNext fica como espelho
sincronizado pelo módulo de integração.

### 21. Catálogo CATMAT canônico, igual ao do e-SUS

O catálogo usa os cinco campos do e-SUS (código CATMAT, princípio ativo, concentração, forma farmacêutica, unidade de fornecimento) e o código canônico `BR` + 7 dígitos (= `codigoItem` oficial). O sufixo
`-N` do e-SUS é guardado como **apresentação**; a chave de estoque é (código, apresentação). O catálogo oficial do Compras.gov.br é a fonte e a tabela do e-SUS é semente; item inativo bloqueia novas entradas. A mesma
chave identifica reagentes (classe 6550) e insumos. *Alternativa recusada:* usar só a descrição textual, que não distingue apresentação nem situação do item.

### 22. REMUME como lista versionada com subgrupos

A REMUME é modelada em três níveis (competência e financiamento, subgrupo, item), com edição, ato e vigência; as siglas de unidade (FBM, FRM, UPA, SAMU e outras) são tipos de ponto de dispensação cadastráveis e ligados a CNES.
A carga lê o documento e separa para curadoria o que não foi lido com segurança (54 de 340 itens na edição de 2025), nunca inferindo.

### 23. Dispensação por terminal de balcão (POS) próprio, não fiscal

O balcão é um terminal responsivo, guiado e por leitura (CNS, receita, produto e lote), sem preço, pagamento nem documento fiscal, porque a dispensação é gratuita. Cada dispensação é entrada do prontuário, baixa
o estoque por lote lido (FEFO) e vai à RNDS (REDFM). As regras de padronização, restrição de programa, quantidade e duplicidade são do módulo; o controle de receita especial segue parâmetros a confirmar. *Alternativa recusada:* reaproveitar um
PDV de varejo, que traz preço, caixa e fiscal e não conhece REMUME, lote nem prontuário.

### 24. Lote como registro de primeira classe, com parser GS1 puro

O lote carrega item, número, validade, fabricante, registro na ANVISA, série e UDI, tem estados com tabela de transições, é imutável após o primeiro movimento e forma cadeia de hash. A leitura GS1 é um módulo puro do núcleo
(reimplementa a regra do dicionário GS1, em vez de importar `erpnext_brasil`, conforme a decisão 1). O recolhimento muda o estado do lote em todas as unidades de uma vez. *Alternativa recusada:* digitar o lote,
onde a rastreabilidade se perde.

### 25. Compras e recebimento em etapas, com a NF-e como prova a conferir

O pedido é a origem do recebimento; o recebimento tem etapas provisória, conferência e definitiva (ateste); a NF-e é conferida (emitente, destinatário, itens, valores, `rastro`, registro na ANVISA) e nunca corrigida pelo módulo. O
módulo de integração liga ao ERPNext (Purchase Order, Receipt e Invoice) e **estende `ler_nfe`** para o `rastro` e o grupo de medicamento. Fracionamento gera lote derivado; devolução do usuário nunca volta ao estoque;
devolução ao fornecedor baixa o saldo só com a nota de devolução.

### 26. Contabilidade pública como evidência e parâmetro, sem tomar o lugar do SIAFIC

O módulo não executa orçamento: entrega ao SIAFIC as evidências (recebimento atestado como liquidação, entradas, consumo, perdas, doações, fechamento) e leva a fonte de recurso e o componente em cada lote. Avaliação por custo médio ponderado ou PEPS (nunca UEPS), um critério
por classe; natureza da despesa por item como parâmetro a confirmar com a contabilidade; fechamento mensal imutável com conciliação; inventário por comissão. *Alternativa recusada:* embutir um plano de contas fixo, que varia por município.

### 27. Armazém de verdade: zonas, endereços, etiquetas, guia e painel

Zonas segregadas (incluindo quarentena e reprovados), endereçamento hierárquico com GLN opcional, etiquetas GS1 (SSCC para unidade logística), armazenagem e **separação guiadas** (caminho mínimo, FEFO, erro imediato, falta tratada), ondas por rota e prioridade,
conferência e embalagem pela condição de transporte, despacho por rota (inclusive fluvial) com comprovação de entrega e **painel de situação** em tempo real. O mapeamento térmico é requisito do endereçamento termossensível. As normas de referência
(OMS, UE, norma brasileira) são declaradas e ligadas aos controles para auditoria.

### 28. Um só WMS para todos os materiais, com perfil de controle por classe

O armazém não é "da farmácia": é o armazém da rede. Cada classe de material (medicamento, produto para saúde, reagente, material de coleta, consumo geral, EPI, combustível, permanente) tem um **perfil de controle** que liga ou desliga
lote e validade, série, registro sanitário, condição de armazenagem, fracionamento, controle especial, tombamento e quarentena. A disciplina de movimento (livro só de acréscimo, recebimento com ateste, inventário, perda com motivo, fechamento, avaliação
do setor público) é a mesma para todas; o perfil só decide quais controles bloqueiam. Há vários armazéns lógicos sobre a mesma base de itens, endereços e movimentos, com permissão por armazém. O catálogo federal (CATMAT) identifica todos os
materiais pelo `codigoItem` numérico; a forma `BR` + 7 dígitos é a apresentação do e-SUS para os itens de saúde. Bem permanente é tombado e fica fora do estoque de consumo; a depreciação fica no sistema contábil.
*Alternativa recusada:* dois sistemas (farmácia e almoxarifado), que duplicariam endereçamento, recebimento, contabilidade e despacho.

### 29. Estratégia de teste

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
| P31 | Reagente vencido, bloqueado ou fora da estabilidade após abertura usado | Bloqueio por lote e por frasco aberto; sem revalidação; FEFO com justificativa | Teste de uso de lote vencido e de frasco aberto vencido |
| P32 | Reagente ou amostra fora da cadeia de frio sem ninguém saber | Registro de temperatura; excursão põe lotes e amostras em quarentena e alerta | Teste de excursão em geladeira e em freezer |
| P33 | Troca de lote de reagente sem verificação de desempenho | Liberação do novo lote só com controle aprovado | Teste de lote novo sem controle |
| P34 | Amostra extraviada no armazenamento | Uma posição por amostra; movimento só com leitura; amostra não encontrada vira ocorrência | Teste de posição ocupada e de tubo ausente |
| P35 | Amostra descartada enquanto ainda é necessária | Descarte só com aprovação; bloqueio por ocorrência, revisão ou notificação pendente | Teste de descarte de amostra em investigação |
| P36 | Kit de coleta incompleto ou com insumo vencido leva a recoleta | Kit montado por exames previstos; vencido impedido; conferência na saída e no retorno | Teste de kit com tubo vencido |
| P37 | Coleta pedida e perdida entre unidade e laboratório | Reconciliação solicitado x coletado x remetido x recebido com pendências | Teste de tubo coletado e não remetido |
| P38 | Lote recolhido continua sendo dispensado em alguma unidade | Recolhimento muda o estado do lote em todas as unidades no mesmo instante; leitura bloqueada no balcão | Teste de recolhimento e de leitura de lote recolhido |
| P39 | Lote digitado errado no recebimento ou na dispensação | Lote lido do código GS1; digitação recusada com código legível; GTIN com dígito de conferência | Teste de GTIN inválido e de lote divergente da nota |
| P40 | Medicamento dispensado fora da REMUME, da unidade ou do programa | Padronização aplicada no balcão; exceção só do farmacêutico com justificativa | Teste de item não padronizado e de paciente não inscrito |
| P41 | Medicamento controlado dispensado sem notificação | Exigência de notificação e farmacêutico; escrituração própria | Teste de controlado sem notificação |
| P42 | Nota fiscal atestada sem ter sido conferida | Ateste só depois da conferência, por fiscal designado; segregação de funções | Teste de ateste com divergência aberta e de usuário não designado |
| P43 | Devolução do usuário reintegra produto de origem duvidosa | Devolução vai à quarentena e ao descarte, nunca ao estoque disponível | Teste de devolução de usuário |
| P44 | Perda encoberta por ajuste de saldo | Diferença negativa exige motivo ou ocorrência; alerta de perda recorrente | Teste de ajuste sem motivo |
| P45 | Lote vencido ou fora da cadeia de frio despachado a uma unidade | Separação por FEFO com bloqueio; embalagem validada pelo tempo de rota; alerta de rota longa | Teste de rota fluvial com item refrigerado |
| P46 | Estoquista guarda ou separa item no endereço errado | Guia com confirmação por leitura de endereço e produto; erro imediato | Teste de produto lido errado e de endereço incompatível |
| P47 | Entrega às micro unidades sem comprovação ou com volume faltante | Conferência por volume na entrega; custódia em trânsito até a conferência | Teste de volume faltante |
| P48 | Estoque do módulo diverge da contabilidade | Fechamento mensal com conciliação; período fechado imutável | Teste de movimento retroativo |
| P49 | Classificação de despesa errada por suposição | Natureza da despesa parametrizada e confirmada pela contabilidade | Teste de item sem natureza |
| P50 | Item inativo ou inexistente no catálogo usado em estoque ou dispensação | Validação contra o catálogo oficial; inativo bloqueia nova entrada | Teste com a amostra de itens inativos |
| P51 | Controle de lote ou validade exigido de material que não o tem (ou o inverso) bloqueia a operação ou deixa passar item perecível | Perfil de controle por classe, ajustável por item, com teste de cada combinação | Teste de item de expediente sem lote e de item perecível sem validade |
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
- **Farmácia, lotes e armazém**: status vigente do SNCM (serialização) e qual RDC o regula (157/2017 ou 319/2019); texto da RDC 430/2020 e se alcança a distribuição interna da rede pública; regras de receita controlada em unidade pública
  (validade, SNGPC, RDC 873/2024); obrigação de fracionamento na rede pública; natureza de despesa dos medicamentos de distribuição gratuita; necessidade de documento fiscal na movimentação entre unidades da mesma entidade; layout de
  lançamentos do SIAFIC do município e formato de prestação de contas ao tribunal de contas (RO); prazo do e-SUS AF e se Porto Velho migra do Hórus; quais itens do Componente Estratégico chegam por nota e em que formato.
- **WMS**: política de retenção de amostras por exame e material (a ANVISA informa não haver norma federal de prazo de guarda do material
  biológico); tipo de sensor de temperatura e integração com *dataloggers* existentes; quais itens do estoque o ERPNext continua dono
  (compra e financeiro) e quais o laboratório (endereço, estabilidade, consumo).
- **Política de assinatura**: nível do certificado, A1, A3 ou nuvem, e posição do CFBM/CRBM e da ANVISA.
- **Piso de guarda** do prontuário (3, 5 ou 20 anos) e a posição da Resolução CFM 1.821/2007 (guarda permanente).
- **Controlador e operadores** de cada ente (município, Estado, LACEN) e os instrumentos que os ligam; nome do encarregado.
- Quem **transmite o S-2220** em cada instalação e a versão vigente do leiaute.
- Escopo futuro de **anatomia patológica, microbiologia e amostra animal ou ambiental**.
- Se o módulo terá **adaptador do Healthcare** já na primeira versão (hoje: opcional).
