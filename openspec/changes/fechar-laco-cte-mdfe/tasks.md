## 1. Fonte primária antes do código

- [x] 1.1 Registrar em `docs/cte-estado.md` e `docs/mdfe-estado.md` os nomes de serviço por
      família — CT-e: recepção **síncrona unitária** `CTeRecepcaoSincV4`, sem lote nem
      recibo; MDF-e: lote + recibo `MDFeRecepcao`/`MDFeRetRecepcao` (com `MDFeRecepcaoSinc`
      síncrona também real), o fluxo escolhido e onde o polling vive — verificar que cada
      fato tem a fonte nomeada (pacote de esquemas do autorizador ou o MOC), como em
      `docs/nfce-contingencia.md`
- [x] 1.2 Registrar em `docs/cte-estado.md` que `infDoc` é opcional no leiaute — verificar que a
      decisão de deixar as referências fora do primeiro incremento consta com a fonte, e que a
      etapa de montagem não depende dela para emitir
- [x] 1.3 Decidir onde mora o campo `br_natureza_transporte` (cabeçalho da `Sales Invoice` ou
      herança do `Item`) e registrar a escolha na docstring — verificar que a detecção de
      "fatura de transporte" usa o campo explícito, nunca inspeção heurística de item
- [x] 1.4 Levantar os campos de `Shipment` e `Shipment Delivery Note` que a montagem vai ler e os
      que o `Shipment` ganha para a viagem (`br_*`: placa/tara, motorista/CPF/CNH, RNTRC/CIOT) —
      verificar que cada um entrou em `setup/leituras_do_erpnext.py` com os campos exatos
- [x] 1.5 Confirmar no bench que o `tipo` do `Transmissao Fiscal` cobra o desfecho dos eventos
      novos (`Cancelamento`/`Carta de Correção`/`Encerramento`; os demais em `Outro`) — se a
      consulta de pendências depender de valor novo, registrar a decisão antes de migrar

## 2. Costura pura do CT-e

- [ ] 2.1 Criar `integracao/cte_documento.py` (mapeador `Sales Invoice` → `TCTe`, com `emit`/
      `tomador`/`vPrest` da fatura, remetente/destinatário do cadastro) — verificar com
      `test_arquitetura.py` que a peça pura de montagem não importa `frappe`
- [ ] 2.2 Escrever `tests/test_cte_documento.py` cobrando a montagem válida, a recusa quando
      falta dado obrigatório do leiaute e o número alocado entrando na chave — verificar que uma
      recusa por campo faltante nomeia o dado, e que a montagem nunca consome o número quando
      recusa
- [ ] 2.3 Reusar `numero_do_documento(doc, 57, serie)` na numeração do CT-e e confirmar que a
      série `br_serie_cte` alimenta a chamada — verificar que uma emissão sem número livre falha
      alto antes de transmitir
- [ ] 2.4 Acrescentar os códigos de recusa de campo obrigatório do CT-e em
      `fiscal/codigos_de_erro.py` — verificar que o domínio conhece a recusa com número estável
- [ ] 2.5 Registrar `Sales Invoice` no laço único de `setup/campos_documento.py` com
      `br_numero_cte` e `br_natureza_transporte` — verificar após `bench migrate` que os campos
      aparecem no formulário e que a geração continua num laço só, sem bloco duplicado

## 3. Transmissão e tela do CT-e

- [ ] 3.1 Criar `integracao/autorizacao_sefaz_cte.py`: autorização **síncrona unitária**
      (`CTeRecepcaoSincV4`, sem lote nem recibo) resolvendo o autorizador e o serviço da UF via
      `TransporteSefaz`, com `dormir` injetado —
      verificar em homologação que o documento é autorizado e que a chave gravada bate com a da
      camada pura; conferia do envelope contra o pacote de esquemas antes de codificar
- [ ] 3.2 Registrar em `Transmissao Fiscal` o desfecho em todos os casos (autorizado, rejeitado,
      denegado) e gravar chave/protocolo no documento de origem — verificar com teste de bench
      que relê do banco por caminho independente
- [ ] 3.3 Confirmar que o bloqueio por consumo indevido recusa o envio do CT-e **antes** de
      chamar a SEFAZ — verificar com teste que conta as chamadas ao transporte (zero)
- [ ] 3.4 Implementar o envio de cancelamento (110111) e CC-e (110110) por família, com desfecho
      registrado e sem reenviar evento já aceito — verificar um teste por evento, incluindo o
      cancelamento de documento já cancelado
- [ ] 3.5 Adicionar o botão "Emitir CT-e" na `Sales Invoice` (só para fatura de transporte) e os
      botões de cancelar/corrigir conforme o estado — verificar em `doctype_js` que o CTA
      aparece/desaparece pelo estado do `Transmissao Fiscal`, no formato de `emissao_nfe.js`
- [ ] 3.6 Fatorar em módulos se `integracao/` passar de 320 linhas — verificar com a conferência
      de tamanho existente

## 4. Costura pura do MDF-e

- [ ] 4.1 Chamar `referencias_do_shipment` a partir de `integracao/mdfe_documento.py`, agrupando
      por município de descarga com o `MunicipioDescarga` de `mapeamento_cte.py` — verificar que
      `cte_extracao` deixa de ser órfão (a suíte o exercita a partir do `Shipment`)
- [ ] 4.2 Escrever `tests/test_mdfe_documento.py` cobrindo: agrupamento por município, recusa
      quando um documento referenciado não tem município e recusa quando não há carga nenhuma —
      verificar uma recusa por caso, cada uma nomeando o dado faltante
- [ ] 4.3 Montar os dados da viagem (veículo, motorista, RNTRC/CIOT) a partir dos campos `br_*`
      do `Shipment` e alocar o número por série 58 — verificar que o número entra na chave e que
      a montagem recusa quando falta dado da viagem
- [ ] 4.4 Registar `Shipment` no laço único de `setup/campos_documento.py` (`br_numero_mdfe` +
      campos da viagem) — verificar após `bench migrate` que os campos aparecem no formulário
      do `Shipment`

## 5. Transmissão e tela do MDF-e

- [ ] 5.1 Criar `integracao/autorizacao_sefaz_mdfe.py`: autorização por lote + recibo
      (`MDFeRecepcao`/`MDFeRetRecepcao`) com o serviço nacional único via `TransporteSefaz`,
      com polling e `dormir` injetado — verificar em homologação que o manifesto é autorizado e
      que a chave gravada bate com a da camada pura; conferida do envelope contra o pacote de
      esquemas antes de codificar
- [ ] 5.2 Registrar em `Transmissao Fiscal` o desfecho (autorizado, rejeitado, denegado) e gravar
      chave/protocolo no `Shipment` — verificar com teste de bench que relê do banco por caminho
      independente
- [ ] 5.3 Confirmar o bloqueio por consumo indevido recusando o envio do MDF-e **antes** de
      chamar a SEFAZ — verificar com teste que conta as chamadas ao transporte (zero)
- [ ] 5.4 Implementar encerramento (110112) e cancelamento do MDF-e com desfecho registrado e sem
      reenviar evento já aceito — verificar um teste por evento, incluindo o cancelamento de um
      MDF-e já encerrado
- [ ] 5.5 Adicionar "Emitir MDF-e" e "Encerrar" no `Shipment` conforme o estado — verificar em
      `doctype_js` que o CTA aparece/desaparece pelo estado do `Transmissao Fiscal`
- [ ] 5.6 Confirmar que os eventos sem gatilho no cadastro (entrega, GTV, condutor, pagamento)
      **não** ganham botão nesta mudança — verificar que a suíte de arquitetura segue cobrando o
      limite de superfície de tela e que a lista de eventos cobertos consta em `docs/mdfe-estado.md`

## 6. Bench, leituras e fechamento

- [ ] 6.1 Incluir `Shipment`, `Shipment Delivery Note` e `Sales Invoice` na conferência de
      `MODULOS_COBERTOS` e rodar `scripts/cobertura_de_bench.py` — verificar que a cobertura
      sobe e bate com os módulos que a montagem lê
- [ ] 6.2 Teste de bench que salva um `Sales Invoice` de transporte e um `Shipment` reais, relê do
      banco e confere que os campos fiscais e a chave persistiram — verificar relendo por caminho
      de consulta independente e comparando com o que a camada pura montou
- [ ] 6.3 Documentar as duas frentes em `docs/cte-operacional.md` e `docs/mdfe-operacional.md`,
      marcar como pagos os gaps de `cte_extracao` órfão e dos módulos sem bench em `docs/gaps.md`
      — verificar que os gaps deixam de constar como abertos
- [ ] 6.4 Rodar a suíte pura, a de bench e o `ruff`, e conferir o bump de versão em
      `erpnext_brasil/__init__.py` no mesmo commit — verificar que tudo está verde antes do
      commit local