## Why

CT-e (modelo 57) e MDF-e (modelo 58) estão completos na camada pura — conteúdo, assinatura,
orquestração, os 18 eventos (11 do CT-e + 7 do MDF-e), autorizador por UF (4 grupos do CT-e,
nacional do MDF-e). E nenhum deles sai de um site: `TransporteSefaz.transmitir` fala só o
serviço de autorização da NF-e, não existe mapeador que monte um CT-e/MDF-e a partir de um
documento do ERPNext, e a única peça de integração dos dois — `integracao/cte_extracao.py` —
está órfã: nada a chama. É o mesmo formato de gap que a NF-e teve até `emissao_nfe.py` e o
eSocial até `transporte_esocial.py`: cadeia pronta e inalcançável de uma tela. Enquanto isso,
a triade do frete (NF-e → CT-e → MDF-e) para antes da rede, e duas leituras de estrutura alheia
(`Shipment`, `Shipment Delivery Note`) seguem sem contrato declarado nem teste de bench.

## What Changes

- **Mapeador do CT-e** (contraparte de `nfe_documento.montar_nfe_do_documento`): monta a árvore
  `TCTe` a partir do documento de transporte do ERPNext — `ide` com numeração por série (o
  modelo 57 já tem série declarada), `emit`, `rem`, `dest`, tomador (`toma3`/`toma4`), `vPrest`,
  `imp` (incluindo `ICMSUFFim`) e `infCarga`/`infDoc`/modal rodoviário.
- **Mapeador do MDF-e**: monta o manifesto a partir do `Shipment` — referências por município de
  descarga (`cte_extracao` deixa de ser órfão), dados da viagem (veículo, motorista, RNTRC/CIOT,
  `tot`, `seg`, `prodPred`) e `infAdic`.
- **Serviços de autorização por família** no `TransporteSefaz`: CT-e síncrono unitário
  (`CTeRecepcaoSincV4`, sem lote nem recibo) e MDF-e lote + recibo
  (`MDFeRecepcao`/`MDFeRetRecepcao`), com `guarda`/`registrador` já injetados — o cStat 656
  vale para os três documentos e a porta é a mesma.
- **Tela**: botões de emissão e de eventos (cancelamento, CC-e do CT-e; encerramento,
  cancelamento, inclusão de condutor/DF-e e pagamento do MDF-e) nos documentos de origem,
  espelhando o já ligado `public/js/emissao_nfe.js`.
- **Registro**: `Transmissao Fiscal` já é genérico por `documento_tipo` e recebe os dois modelos
  em todos os desfechos; `br_chave_acesso`/`br_protocolo_autorizacao` gravados no documento de
  origem, como na NF-e.
- **Exercício em bench**: leitura de `Shipment`/`Delivery Note`/`Purchase Invoice` e a gravação
  da numeração — os dois módulos novos entram na cobertura barrada em `tests_bench/` e em
  `setup/leituras_do_erpnext.py`.

## Capabilities

### New Capabilities
- `fiscal/cte-operacional`: emissão e transmissão do CT-e (modelo 57) a partir de um documento
  do ERPNext, com eventos acionáveis de uma tela.
- `fiscal/mdfe-operacional`: emissão e transmissão do MDF-e (modelo 58) — manifesto montado a
  partir das cargas de um `Shipment`, com eventos operacionais acionáveis.

### Modified Capabilities
<!-- Nenhuma: o projeto ainda não tem specs registradas em openspec/specs/. -->

## Impact

- **Código do app**: módulos novos `integracao/cte_documento.py` e
  `integracao/mdfe_documento.py`; extensão de `integracao/transporte_sefaz.py`/
  `autorizacao_sefaz.py` com os serviços de CT-e/MDF-e; `integracao/cte_extracao.py` passa a ter
  chamador; `hooks.py` + `doctype_js`; `setup/leituras_do_erpnext.py` (Shipment,
  `Shipment Delivery Note`); campos de numeração por modelo e de cadastro de veículo/motorista;
  `registros_fiscais` (`Transmissao Fiscal` — eventos dos dois modelos).
- **ERPNext**: leitura de `Shipment`, `Shipment Delivery Note`, `Vehicle`/motorista (a decidir o
  local do cadastro) — estrutura alheia, sujeita ao contrato de leituras e à conferência de bench.
- **SEFAZ**: nenhum autorizador novo — mapas por UF já implementados para os dois modelos.
- **Gaps pagos**: o órfão `cte_extracao` (§ 1.4 de `docs/gaps.md`) e dois módulos de integração
  sem teste de bench (seção 2 do mesmo documento).
- **Riscos**: serviço de autorização por família não pode ser suposto por analogia com a NF-e —
  o CT-e e o MDF-e transmitem **lote** e resolvem recibo, e a numeração por série é por modelo;
  dados ANTT (RNTRC/CIOT) e veículo/motorista dependem de cadastro que o ERPNext não modela —
  decisão de onde vivem os campos antes de escrever o mapeador.