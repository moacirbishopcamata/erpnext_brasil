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

- [x] 2.1 Criar `integracao/cte_documento.py` (mapeador `Sales Invoice` → `TCTe`, com `emit`/
      `tomador`/`vPrest` da fatura, remetente/destinatário do cadastro) — verificar com
      `test_arquitetura.py` que a peça pura de montagem não importa `frappe`

      **Concluída (2026-10-03).** Teste primeiro: `tests/test_cte_montagem.py` foi escrito contra
      uma API inexistente, falhou, e a implementação veio depois. A regra do leiaute ficou em
      `fiscal/cte_montagem.py` (pura); `integracao/cte_documento.py` só lê o cadastro e traduz.
      Resolvidas as pendências do esqueleto: `cNF` sorteado, `infCarga`/`infModal` montados, ICMS
      00/20/45/90/SN calculado (60 e `ICMSOutraUF` recusados nomeando o CST), tomador derivado
      (`toma3` remetente/destinatário, `toma4` outros), `vRec`, `CRT` do emitente, remetente e
      destinatário distintos. A árvore foi **validada contra o `cte_v4.00.xsd` oficial** (`sped-cte`,
      `PL_CTe_400`) nos cinco grupos de ICMS e com duas quantidades de carga — só sem a assinatura.
      Essa validação achou dois defeitos que os testes estruturais não pegavam: `infCte/@versao`
      ausente em `montar_cte` e `dhEmi` sem fuso. Ficam fora, declarados: `infDoc`, `Comp`,
      `ICMSUFFim`, modais não rodoviários. Camada Frappe ainda **não** exercitada em bench (6.2).
- [x] 2.2 Escrever `tests/test_cte_documento.py` cobrando a montagem válida, a recusa quando
      falta dado obrigatório do leiaute e o número alocado entrando na chave — verificar que uma
      recusa por campo faltante nomeia o dado, e que a montagem nunca consome o número quando
      recusa

      **Concluída (2026-10-03).** 48 testes em `tests/test_cte_montagem.py` (montagem válida,
      recusa nomeando o dado) e a costura em `tests/test_cte_documento.py`. O critério "nunca
      consome o número quando recusa" ficou provado com a alocação injetada: dado faltando e CST
      não suportado recusam com **zero** chamadas ao alocador.
- [x] 2.3 Reusar `numero_do_documento(doc, 57, serie)` na numeração do CT-e e confirmar que a
      série `br_serie_cte` alimenta a chamada — verificar que uma emissão sem número livre falha
      alto antes de transmitir

      **Concluída (2026-10-03).** `numero_do_documento` ganhou o parâmetro `campo` (padrão
      `br_numero_nfe`, então `emissao_nfe` segue intacta); o mapeador passa `br_numero_cte`, o
      modelo `57` e a série de `serie_padrao` (`br_serie_cte`, recusada se vazia). A alocação vem
      **depois** da montagem de prova (`montar_cte_alocando_numero`), e uma falha dela sobe antes de
      qualquer árvore. Lado Frappe (`alocar_numero` real, trava de linha) ainda sem bench: 6.2.
- [x] 2.4 Acrescentar os códigos de recusa de campo obrigatório do CT-e em
      `fiscal/codigos_de_erro.py` — verificar que o domínio conhece a recusa com número estável

      **Concluída (2026-10-03).** Dois códigos na faixa 12xx: `1206` dado obrigatório ausente (manda
      preencher um cadastro) e `1207` dado inválido (manda corrigir o que está preenchido); o
      *qual* dado vai em `CteInvalido.campo` e na mensagem. `CteInvalido` ganhou `codigo` e
      `mensagem_com_codigo` (`[1206] ...`), então o domínio conhece a recusa; os números estão
      fixados em teste. Na fronteira de `integracao/cte_documento.py` o `DadosInsuficientes` dos
      leitores vira `CteInvalido` 1206, para o botão da 3.5 tratar um tipo só. Junto: `__all__`
      de `codigos_de_erro` estava sem 1204 e 1205. Limite conhecido: regime tributário sem CRT
      correspondente sai como 1206 (leitor compartilhado com a NF-e).
- [x] 2.5 Registrar `Sales Invoice` no laço único de `setup/campos_documento.py` com
      `br_numero_cte` e `br_natureza_transporte` — verificar após `bench migrate` que os campos
      aparecem no formulário e que a geração continua num laço só, sem bloco duplicado

      **Escopo ampliado (2026-10-03, decisão do usuário — "opção 1")**: o mapeador precisa de
      dados que a fatura não guardava. Além dos dois campos acima, declarar no mesmo laço:
      `br_tomador_cte` (Select: Remetente / Destinatário / Outros — "Outros" usa o cliente da
      fatura como `toma4`), `br_remetente_cte` e `br_destinatario_cte` (Link `Customer`), a carga
      (`br_valor_carga`, `br_produto_predominante`, `br_unidade_carga`, `br_tipo_medida_carga`,
      `br_quantidade_carga`) e o ICMS (`br_cst_icms_cte`, `br_aliquota_icms_cte`,
      `br_reducao_base_icms_cte`). O RNTRC já existe na `Company` (`br_rntrc`). Origem de cada
      grupo conferida no `cteTiposBasico_v4.00.xsd` (sped-cte, `PL_CTe_400`), não de memória.

      **Concluída (2026-10-03).** Declarados e testados sem bench: os campos do CT-e (11 novos, além de
      `br_numero_cte` e `br_natureza_transporte`) entram só na `Sales Invoice` (extraídos do laço de
      `CABECALHOS`), sem duplicata, e as tabelas rótulo→código (modal, tipo de serviço, tomador, unidade,
      CST) batem com os Selects. **Critério de bench atendido:** `bench migrate` em `v16.localhost`
      (MariaDB) e `v16pg.localhost` (PostgreSQL), pilha em Frappe 16.36.1, ERPNext 16.37.0, HRMS 16.20.1;
      12 Custom Fields `br_*cte*` criados nos dois, e `tests_bench/test_cte_documento.py` confere no
      `frappe.get_meta` que existem na `Sales Invoice` e não vazam para `Delivery Note`,
      `Purchase Invoice`, `Purchase Receipt` nem `POS Invoice`.

## 3. Transmissão e tela do CT-e

- [ ] 3.1 Criar `integracao/autorizacao_sefaz_cte.py`: autorização **síncrona unitária**
      (`CTeRecepcaoSincV4`, sem lote nem recibo) resolvendo o autorizador e o serviço da UF via
      `TransporteSefaz`, com `dormir` injetado —
      verificar em homologação que o documento é autorizado e que a chave gravada bate com a da
      camada pura; conferia do envelope contra o pacote de esquemas antes de codificar

      **Parcial (2026-10-03) — código e testes prontos; falta a prova em homologação.** Envelope e
      resposta conferidos em fonte **secundária** (`sped-cte`/`sped-common`, XSD `PL_CTe_400`), não no
      MOC: o CT-e **manda** `cteCabecMsg` (`cUF`+`versaoDados`), leva o `CTe` direto (sem
      `enviCTe`) em **GZip+Base64** dentro de `cteDadosMsg`, e a ação SOAP vai no `Content-Type`;
      `retCTe` com um `cStat` só (autorizado 100/150, denegado 110/205/301). Novos:
      `fiscal/documento/soap_cte.py`, `fiscal/documento/resposta_cte.py`,
      `integracao/autorizacao_sefaz_cte.py` e `TransporteSefaz.transmitir_cte` (49+6 testes). `dormir`
      ficou de fora de propósito: serviço síncrono, sem o que esperar. **Falta** autorizar um CT-e em
      homologação com certificado A1 real e conferir a chave devolvida contra a da camada pura.
- [x] 3.2 Registrar em `Transmissao Fiscal` o desfecho em todos os casos (autorizado, rejeitado,
      denegado) e gravar chave/protocolo no documento de origem — verificar com teste de bench
      que relê do banco por caminho independente

      **Concluída (2026-10-09).** `integracao/emissao_cte.py` (`emitir_cte`): monta, assina, transmite
      e grava o `Transmissao Fiscal` em autorizado, rejeitado e denegado; chave e protocolo vão para
      `br_chave_acesso`/`br_protocolo_autorizacao` só quando autorizado; não reenvia CT-e já
      autorizado; recusa de cadastro (1206/1207) sai sem registro e sem chamar a SEFAZ.
      `tests_bench/test_emissao_cte.py` (5 testes, transporte falso) passou em `v16.localhost`, e o
      teste-âncora falha sem o `commit` (conferido). **Achado:** `frappe.throw` desfaz a transação e
      levava o registro da rejeição junto; `emissao_nfe.emitir_nfe` tinha o mesmo defeito e ganhou o
      `commit` antes do `throw` (travado em `tests/test_emissao_commit_antes_do_throw.py`).

- [ ] 3.3 Confirmar que o bloqueio por consumo indevido recusa o envio do CT-e **antes** de
      chamar a SEFAZ — verificar com teste que conta as chamadas ao transporte (zero)

      **Parcial (2026-10-03).** `test_transporte_cte.py` prova que a guarda recusa o CT-e com **zero**
      chamadas à sessão HTTP, e que o registrador recebe o `656`. **Falta** o encadeamento na tela/ação
      que cria o transporte com `guarda`/`registrador` reais (3.5).
- [x] 3.4 Implementar o envio de cancelamento (110111) e CC-e (110110) por família, com desfecho
      registrado e sem reenviar evento já aceito — verificar um teste por evento, incluindo o
      cancelamento de documento já cancelado

      **Concluída (2026-10-09), sem a prova em homologação.** `integracao/eventos_cte.py`
      (`cancelar_cte`, `corrigir_cte`) monta o evento, e `TransporteSefaz.transmitir_evento_cte` o
      assina e envia por `CTeRecepcaoEventoV4` (`eventos_sefaz_cte.py`; sem lote, corpo em texto,
      resposta `retEventoCTe` com 135/136 e 155 só no cancelamento). Cancelamento de CT-e já cancelado
      recusa antes de chamar a SEFAZ; a carta avança `nSeqEvento` (1 a 20) e a rejeitada não o consome;
      toda rejeição fica gravada (`commit` antes do `throw`). `tests_bench/test_eventos_cte.py` (9) passou
      em `v16.localhost`; 16 testes puros novos em `tests/test_eventos_sefaz_cte.py`.
      **Achado:** os montadores de evento do CT-e tinham a forma da NF-e (raiz `evento`, campos soltos em
      `detEvento`) e a SEFAZ os recusaria; cancelamento e CC-e foram corrigidos, os outros 8 estão em
      `docs/gaps.md`. **Falta** enviar um evento em homologação e confirmar o cabeçalho SOAP.

- [x] 3.5 Adicionar o botão "Emitir CT-e" na `Sales Invoice` (só para fatura de transporte) e os
      botões de cancelar/corrigir conforme o estado — verificar em `doctype_js` que o CTA
      aparece/desaparece pelo estado do `Transmissao Fiscal`, no formato de `emissao_nfe.js`

      **Concluída (2026-10-09), sem clique em site real.** `public/js/emissao_cte.js`, ligado ao lado de
      `emissao_nfe.js` em `doctype_js` (lista). "Fatura de transporte" = `br_natureza_transporte`
      preenchida; cada arquivo se cala na fatura do outro. A situação vem de `situacao_fiscal` com
      `familia: "cte"`: **achado** — sem separar pelo modelo da chave (posições 21-22), o CT-e apareceria
      como "NF-e: Autorizado"; `da_familia` (puro) faz a separação e a NF-e segue como padrão. Emissão
      síncrona (sem fila), justificativa de 15 a 255, carta como tabela grupo/campo/novo valor. Travado em
      `test_costura_cliente.TestBotoesFiscaisDoCte` (12) e `test_situacao_fiscal.TestFamiliaDoRegistro` (6);
      bench: `test_a_situacao_do_cte_nao_vaza_para_a_da_nfe`. **Falta** abrir uma fatura de transporte no
      navegador e clicar (lacuna de `docs/gaps.md`, seção 2).

- [x] 3.6 Fatorar em módulos se `integracao/` passar de 320 linhas — verificar com a conferência
      de tamanho existente

      **Concluída (2026-10-09), sem fatoração necessária.** O maior módulo de `integracao/` é
      `transporte_sefaz.py` com 299 linhas (limite 320); os novos do CT-e têm 91 a 228. Para não
      estourar o limite, o evento do CT-e entrou como **um** método no transporte
      (`transmitir_evento_cte`) e a montagem ficou em `eventos_cte.py`, em vez de `cancelar`/`corrigir`
      duplicados lá. `test_arquitetura.TestCamadaDeIntegracao.test_toda_regra_fica_do_lado_puro` segue verde.

## 4. Costura pura do MDF-e

- [x] 4.1 Chamar `referencias_do_shipment` a partir de `integracao/mdfe_documento.py`, agrupando
      por município de descarga com o `MunicipioDescarga` de `mapeamento_cte.py` — verificar que
      `cte_extracao` deixa de ser órfão (a suíte o exercita a partir do `Shipment`)

      **Concluída (2026-10-09).** `integracao/mdfe_documento.py` chama `referencias_do_shipment` e agrupa com
      `agrupar_por_municipio_descarga`; `cte_extracao` e `mapeamento_cte` deixam de ser órfãos (travado em
      `tests/test_mdfe_documento.py::TestCteExtracaoDeixaDeSerOrfao`, e exercitado em bench). A montagem pura
      que faltava para encadear os grupos ficou em `fiscal/mdfe_montagem.py`, irmã de `cte_montagem.py`.

- [x] 4.2 Escrever `tests/test_mdfe_documento.py` cobrindo: agrupamento por município, recusa
      quando um documento referenciado não tem município e recusa quando não há carga nenhuma —
      verificar uma recusa por caso, cada uma nomeando o dado faltante

      **Concluída (2026-10-09).** `tests/test_mdfe_montagem.py` (23 testes): agrupamento por município preservando
      a ordem, e uma recusa por caso nomeando o dado (sem carga, município sem documento, valor e peso não
      positivos, sem RNTRC, veículo sem condutor/placa, emitente CPF, endereço incompleto, data sem fuso, modal,
      UF, número). Mutação conferida: tirar a validação da carga derruba 5 testes.

- [x] 4.3 Montar os dados da viagem (veículo, motorista, RNTRC/CIOT) a partir dos campos `br_*`
      do `Shipment` e alocar o número por série 58 — verificar que o número entra na chave e que
      a montagem recusa quando falta dado da viagem

      **Concluída (2026-10-09).** Veículo (tração e reboque opcional), motorista e RNTRC (da `Company`) vêm dos
      campos `br_*_mdfe` do `Shipment`; a série 58 vem de `br_serie_mdfe` e o número é alocado só depois de a
      montagem de prova validar, entrando na chave. **Achado:** o `Shipment` do core não tem `company`, então
      `numero_do_documento` ganhou o parâmetro `company` (a empresa é a de `pickup_company`). Valor da carga =
      soma de `grand_total` das notas **com chave** (não o `value_of_goods`, campo livre). **Limites
      declarados:** só `tpEmit` 2 e emitente CNPJ (a chave leva CNPJ); sem `infCIOT` — `montar_rodo` só produz
      `infANTT/RNTRC`.

- [x] 4.4 Registar `Shipment` no laço único de `setup/campos_documento.py` (`br_numero_mdfe` +
      campos da viagem) — verificar após `bench migrate` que os campos aparecem no formulário
      do `Shipment`

      **Concluída (2026-10-09).** 10 Custom Fields no `Shipment` (`br_numero_mdfe` + viagem), declarados em
      `setup/campos_documento.py` e criados em `v16.localhost` por `criar_campos_fiscais`; o bench confere pelo
      `frappe.get_meta` que existem no `Shipment` e não vazam para `Sales Invoice`, `Delivery Note` nem
      `Purchase Invoice`. Não rodei `bench migrate` completo (evita patches de outras mudanças no banco
      compartilhado); a função é a mesma que o `after_migrate` chama. **Falta** o PostgreSQL (`v16pg`).

## 5. Transmissão e tela do MDF-e

- [ ] 5.1 Criar `integracao/autorizacao_sefaz_mdfe.py`: autorização por lote + recibo
      (`MDFeRecepcao`/`MDFeRetRecepcao`) com o serviço nacional único via `TransporteSefaz`,
      com polling e `dormir` injetado — verificar em homologação que o manifesto é autorizado e
      que a chave gravada bate com a da camada pura; conferida do envelope contra o pacote de
      esquemas antes de codificar
- [ ] 5.2 Registrar em `Transmissao Fiscal` o desfecho (autorizado, rejeitado, denegado) e gravar
      chave/protocolo no `Shipment` — verificar com teste de bench que relê do banco por caminho
      independente

      **Acrescentado (2026-10-09):** a emissão do MDF-e também chama `garantir_relogio_confiavel()` (mudança
      `fonte-de-tempo-ntp-br`, tarefa 4.3) como **primeira instrução**, antes de alocar número — incluir a
      função em `tests/test_guarda_de_relogio.py::EMISSOES`.

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
      **Parcial (2026-10-09): CT-e e `Shipment` feitos, falta o PostgreSQL do MDF-e.** `tests_bench/test_mdfe_documento.py`
      (11 testes) salva `Shipment` e `Delivery Note` reais, monta a árvore e relê o `br_numero_mdfe` e o contador por
      `frappe.db.get_value`; passa em MariaDB.
      **(2026-10-03)** Lado do CT-e feito: `tests_bench/test_cte_documento.py` (8 testes) salva
      uma `Sales Invoice` de transporte real, monta a árvore, e relê do banco por `frappe.db.get_value`
      o `br_numero_cte` e o contador de `Numeracao Fiscal` (aloca uma vez, reemissão reaproveita, recusa
      não consome) — passa em MariaDB e em PostgreSQL. **Falta** o `Shipment` (MDF-e, bloco 4).
- [ ] 6.3 Documentar as duas frentes em `docs/cte-operacional.md` e `docs/mdfe-operacional.md`,
      marcar como pagos os gaps de `cte_extracao` órfão e dos módulos sem bench em `docs/gaps.md`
      — verificar que os gaps deixam de constar como abertos
- [ ] 6.4 Rodar a suíte pura, a de bench e o `ruff`, e conferir o bump de versão em
      `erpnext_brasil/__init__.py` no mesmo commit — verificar que tudo está verde antes do
      commit local