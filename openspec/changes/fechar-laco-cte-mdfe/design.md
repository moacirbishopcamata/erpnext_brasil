## Context

Ver `proposal.md` — Why. O desenho precisa levar em conta o estado atual:

- `fiscal/cte.py` e `fiscal/mdfe.py` montam as árvores `TCTe`/`TMDFe` completas (inclusive
  `montar_infdoc` do MDF-e, `montar_ide`, modal rodoviário, `ICMSUFFim`), com `assinar_cte`/
  `assinar_mdfe` reusando `fiscal/documento/assinatura.py`. `fiscal/documento/evento_cte.py` e
  `evento_mdfe.py` têm os 18 eventos. Nada disso importa `frappe`.
- `fiscal/documento/autorizadores_cte.py` e `autorizadores_mdfe.py` já mapeiam os autorizadores
  (CT-e: 4 grupos; MDF-e: nacional único).
- `TransporteSefaz` é o único ponto que constrói `ContextoSefaz`, com `guarda`/`registrador`
  injetados (cStat 656) — mas `transmitir`/`_enviar_evento` falam **só** os serviços da NF-e
  (`NFeAutorizacao4`/`NFeRecepcaoEvento4`). O padrão se reaproveita; o envelope, não.
- `integracao/mapeamento_cte.py` agrupa referências por município (`MunicipioDescarga`, puro) e
  `integracao/cte_extracao.py` extrai as chaves de `Shipment` → `Delivery Note` — hoje órfão,
  sem chamador.
- `Numeracao Fiscal` e `numero_do_documento(doc, modelo, serie)` são genéricos por modelo; o
  modelo 57/58 tem série declarada (`br_serie_cte`/`br_serie_mdfe`). `Transmissao Fiscal` é
  genérico por `documento_tipo`.
- Achado real registrado em `docs/integracao-cte-frete.md`: `Shipment` não tem vínculo nenhum
  com `Purchase Invoice` de frete — a ligação de quem emite a mercadoria não existe no ERPNext.

## Goals / Non-Goals

**Goals:**

- CT-e e MDF-e saem de um documento real do ERPNext pelo mesmo molde da NF-e: mapeador →
  assinatura → `TransporteSefaz` (com guarda) → `Transmissao Fiscal` em todos os desfechos.
- `cte_extracao` deixa de ser órfão: o MDF-e nasce de `Shipment` e consome as referências dele.
- A numeração por série, o bloqueio por consumo indevido e a não-retransmissão de documento já
  autorizado valem para os dois modelos desde a primeira entrega.
- Conferência de leitura e teste de bench para `Shipment`/`Shipment Delivery Note`.

**Non-Goals:**

- **Não** implementar os modais aéreo/aquaviário/ferroviário — continua só o rodoviário.
- **Não** transmitir lotes com muitos documentos por chamada — emissão unitária, como a NF-e;
  o "lote" aqui é o envelope do serviço (1 documento), não um modo de envio em massa.
- **Não** abrir as telas para os eventos que dependem de dado operacional externo (comprovante
  de entrega, GTV, inclusão de condutor, pagamento do MDF-e) nesta mudança — só os com gatilho
  claro no cadastro: cancelamento e CC-e do CT-e, encerramento e cancelamento do MDF-e.
- **Não** computar a contingência de CT-e/MDF-e — a contingência offline é exclusividade da
  NFC-e (mesmo escopo já traçado no change `emitir-nfce-do-pos`).

## Decisions

### 1. Origem do CT-e: `Sales Invoice` de serviço de transporte; `infDoc` fora do primeiro incremento

O CT-e nasce da venda da prestação na `Sales Invoice` da transportadora — a mesma origem
econômica da NF-e e o mesmo mecanismo de numeração. `tomador` vem do `Customer`, `vPrest` dos
valores da fatura, `emit` da `Company`.

**`infDoc` (chaves dos documentos transportados) fica de fora da primeira entrega** — é
opcional no XSD e a origem das chaves não é rastreável de uma `Sales Invoice` de frete: o
mesmo achado que motivou `referencia_cte_do_documento_frete` (o `Shipment` não amarra fatura
nenhuma) vale aqui por construção. Um CT-e sem `infDoc` é válido; a tela que preenche as chaves
pode vir depois sem mudar nada do resto.

*Alternativa considerada:* `Shipment` como origem do CT-e. Recusada — `Shipment` pertence a
quem expede a mercadoria (o remetente), não à transportadora que emite o CT-e, e não carrega a
relação comercial (tomador, valor).

### 2. Origem do MDF-e: `Shipment`, consumindo `cte_extracao`; dados da viagem em campos no próprio `Shipment`

O manifesto nasce da viagem — o `Shipment` — e as referências vêm de
`referencias_do_shipment` (chaves de `Delivery Note` por município de descarga), que passa a ter
chamador na montagem. Isso cobre `tpEmit = 2` (transportador de carga própria), o caso em que o
emitente do MDF-e é dono das NF-e que carrega.

Veículo, motorista e RNTRC/CIOT moram em **campos `br_*` declarados no próprio `Shipment`** (via
`setup/`), não num DocType novo nem no core `Vehicle`: o ERPNext não modela motorista, e amarrar
o manifesto ao cadastro de frota exigiria leitura de mais uma estrutura alheia sem ganho para a
primeira entrega. O cadastro de frota do core fica como alternativa futura.

*Alternativa considerada:* ler `Vehicle` (placa/tara) e criar DocType `Condutor`. Recusada —
`Vehicle` não tem motorista, e um DocType novo para a primeira entrega amplia a superfície sem
destravar nada: a viagem carrega o dado da própria viagem.

### 3. Transmissão: `TransporteSefaz` ganha métodos por família, delegando a módulos novos

`TransporteSefaz` continua sendo o único dono do ciclo de vida do `ContextoSefaz` e da guarda de
consumo indevido. Os métodos `transmitir`/`_enviar_evento` atuais são NF-e puro e **não são
generalizados**: cada família ganha o seu, delegando a módulos por serviço
(`autorizacao_sefaz_cte.py`, `autorizacao_sefaz_mdfe.py`, e os de evento correspondentes),
respeitando o teto de 320 linhas por módulo.

Isso impede o engano que seria o pior resultado possível: mandar um CT-e para `NFeAutorizacao4`.
Os fluxos de cada família foram verificados contra a tabela de endpoints (fonte:
`autorizadores_cte.py`/`autorizadores_mdfe.py`, lidas de `sped-cte`/`sped-mdfe`):

- **CT-e 4.00: síncrono unitário** — `CTeRecepcaoSincV4`, resposta na própria chamada. **Não
  existe** `CTeAutorizacao4`/`CTeRetAutorizacao4` nem lote + recibo no leiaute do CT-e.
- **MDF-e 3.00: lote + recibo** — `MDFeRecepcao` devolve `nRec` e `MDFeRetRecepcao` consulta
  o recibo, a mesma máquina de polling da NF-e com outros nomes de serviço (`MDFeAutorizacao`/
  `MDFeRetAutorizacao` **não** existem na fonte; `MDFeRecepcaoSinc` existe, mas o fluxo
  escolhido é o de lote + recibo, coerente com a máquina de polling já existente).

A leitura da resposta reusa o contrato `RespostaTransmissao`. Os nomes de serviço e o leiaute
da resposta de cada família são verificados contra o pacote de esquemas antes de escrever (nada
por analogia com a NF-e).

*Alternativa considerada:* generalizar `transmitir` por parâmetro de modelo. Recusada — faria o
módulo conhecer três envelopes e o teste da NF-e passaria a depender de que o CT-e não regrida.

### 4. Eventos acionáveis só quando há gatilho claro

Cancelamento (110111) e CC-e do CT-e (110110, lista estruturada) entram na tela; encerramento
(110112) e cancelamento do MDF-e também. Os demais 14 eventos continuam montáveis e testados na
camada pura, sem botão — exigem dado operacional (imagem de entrega, condutor, pagamento) que
não tem forma de entrada nesta mudança.

O envio de evento por família segue o mesmo molde do `_enviar_evento` atual, com os serviços
de recepção próprios e o registro de desfecho em `Transmissao Fiscal` (o `tipo` já cobre
`Cancelamento`/`Carta de Correção`/`Encerramento`; os demais caem em `Outro`).

### 5. Numeração: reuso de `numero_do_documento`, com campos por modelo

`numero_do_documento(doc, modelo, serie)` já é genérico; os modelos 57/58 entram por `serie`
(`br_serie_cte`/`br_serie_mdfe`). Faltam os campos de retorno `br_numero_cte`/`br_numero_mdfe`
(mesma forma do `br_numero_nfe`), declarados no laço único de `setup/campos_documento.py`.

### 6. Tela: botões por cada família, no formato já consagrado de `emissao_nfe.js`

`Sales Invoice` ganha o botão **Emitir CT-e** (com a detecção de "fatura de transporte" decidida
por campo explícito na fatura — não por inspeção heurística de item, para não recusar nem
enganar). `Shipment` ganha **Emitir MDF-e** e **Encerrar**. CTA pertence ao objeto: os botões de
evento aparecem conforme o estado do documento (`Transmissao Fiscal`).

### 7. Capacidade de leitura e prova de bench de `Shipment`

`Shipment` e `Shipment Delivery Note` entram em `setup/leituras_do_erpnext.py` (a conferência
pura + a de bench reprovam leitura declarada e não conferida). `tests_bench/` ganha um teste de
gravação/releitura que monta o CT-e e o MDF-e a partir de documentos reais salvos.

## Risks / Trade-offs

- **Serviço SOAP equivocado para o modelo** → a decisão 3 separa os métodos por família; o teste
  de envio não existiria sem a conferência do pacote de esquemas de cada autorizador.
- **MDF-e do prestador (tpEmit 1) agregando chaves de CT-e que não vêm de lugar nenhum** →
  primeira entrega cobre só carga própria (NF-e via `Shipment Delivery Note`); a agregação de
  CT-e fica declarada como iteração futura, não silenciada.
- **Relação comercial (tomador/valor) mal derivada da `Sales Invoice`** → o mapeador exige o
  campo explícito de natureza de transporte; sem ele, recusa em vez de chutar documento.
- **CT-e sem `infDoc`** → válido no XSD, mas a operação real agrega documentos; registrar na
  entrega que a tela de chaves fica para a iteração seguinte.
- **Envelope de resposta diferente do esperado por família** → leitura da resposta conferida
  contra o XSD do retorno de cada serviço antes de codificar.

## Migration Plan

1. **Costura pura primeiro** (a parte que erra caro e é testável sem bench): `integracao/
   cte_documento.py` e `integracao/mdfe_documento.py`, com campos declarados e a numeração por
   série — inertes até o botão existir.
2. **Transmissão por família**: serviços de autorização e evento + `Transmissao Fiscal` em todos
   os desfechos; botões no `Sales Invoice` (CT-e) e no `Shipment` (MDF-e).
3. **Bench**: conferência das leituras de `Shipment` e teste de gravação/releitura; contrato de
   leituras completo.

Reversão: remover os botões e os `hooks.py` devolve o comportamento anterior — os campos ficam
declarados e vazios, sem efeito. Documento já autorizado não é retransmitido (a guarda de
duplicidade nasce com a transmissão, decisão 3).

## Open Questions

- O `tipo` do `Transmissao Fiscal` ganha valores específicos dos eventos de CT-e/MDF-e
  (`Comprovante de Entrega`, `Inclusão de Condutor`, …) nesta mudança ou ficam em `Outro` até
  cada tela existir? Não muda spec nem tarefa — só o Select.
- A detecção de "fatura de transporte" na `Sales Invoice` será um campo explícito
  (`br_natureza_transporte`, Select) — falta só confirmar se herda de `Item` ou fica no
  cabeçalho; decisão de tarefa, não de desenho.