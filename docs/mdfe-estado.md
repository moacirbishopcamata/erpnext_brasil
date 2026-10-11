# Levantamento de estado: MDF-e (Manifesto Eletrônico de Documentos Fiscais, modelo 58)

Mesma disciplina de `docs/cte-estado.md` — levantar antes de implementar. Pré-requisito
cumprido: **CT-e agora existe** neste projeto (ver `docs/cte-*.md`), o que desbloqueia o MDF-e —
ele referencia CT-e/NF-e por chave de acesso, nunca os substitui.

## Método: download local + grep, desde o início

Nenhum obstáculo de extração desta vez — aplicado desde o primeiro passo o método que só foi
adotado no CT-e depois de 3 tentativas falhas (baixar o XSD com `curl` para o worktree e usar
`Grep`/`Read` locais, nunca resumo de página em arquivo grande). Fonte:
`github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b` (versão mais recente das duas
disponíveis no repositório, `300a`/`300b`). Consultado em 2026-08-31.

## Estrutura confirmada de `TMDFe`

`complexType name="TMDFe"` — arquivo mais compacto que o do CT-e (`mdfeTiposBasico_v3.00.xsd`
tem 2526 linhas contra as quase 8000 do CT-e). Filhos diretos de `infMDFe`, em ordem:

| Grupo | Papel |
|---|---|
| `ide` | Identificação — bem mais enxuto que o do CT-e, ver seção própria |
| `emit` | Emitente |
| `infModal` | Dados do modal (rodoviário/aéreo/aquaviário/ferroviário — **sem dutoviário nem multimodal**, diferente do CT-e) |
| `infDoc` | Documentos fiscais vinculados — a ponte com CT-e/NF-e, ver seção própria |
| `seg` | Seguro da carga |
| `prodPred` | Produto predominante |
| `tot` | Totalizadores (peso, valor da carga) |
| `lacres` | Lacres do veículo/unidade de carga |
| `autXML` | Autorizados a baixar o XML |
| `infAdic` | Informações adicionais |
| `infRespTec` | Responsável técnico |
| `infSolicNFF` | Solicitação de NF-e Futura |
| `infPAA` | Programa de Alimentação do Aviador |
| `qrCodMDFe` | QR Code |

## `ide` — 21 campos, bem mais simples que o do CT-e (30 campos)

Confirmado por leitura direta (`mdfeTiposBasico_v3.00.xsd`, linhas 17–232): `cUF`, `tpAmb`,
`tpEmit`, `tpTransp` (opcional), `mod` (**"58"**, não "57"), `serie`, `nMDF`, `cMDF` (8 dígitos,
mesmo padrão de `cCT`/`cNF`), `cDV`, `modal`, `dhEmi`, `tpEmis`, `procEmi`, `verProc`, `UFIni`,
`UFFim`, `infMunCarrega` (até 50, município + nome), `infPercurso` (opcional, até 25, só sigla de
UF), `dhIniViagem` (opcional), `indCanalVerde` (opcional), `indCarregaPosterior` (opcional).

**Sem `CFOP` nem `natOp`** — diferente de CT-e e NF-e. Faz sentido: o MDF-e não é uma operação
ou prestação tributável em si, é um manifesto que agrupa documentos já tributados.

### Achado real: `modal` do MDF-e diverge do `modal` do CT-e — não é o mesmo código

Confirmado, não suposto: `ide/modal` do CT-e usa `"01"`–`"06"` (zero à esquerda, inclui
Dutoviário e Multimodal — ver `docs/cte-orquestracao.md`). `ide/modal` do MDF-e usa `"1"`–`"4"`
(**sem** zero à esquerda, **sem** Dutoviário nem Multimodal — só Rodoviário/Aéreo/Aquaviário/
Ferroviário). Reaproveitar as constantes `MODAL_*` de `fiscal/cte.py` para o MDF-e produziria
XML rejeitado (`"01"` não é um valor válido no MDF-e, e o próprio conjunto de opções é menor) —
exatamente o tipo de suposição por analogia que este projeto errou uma vez com a assinatura do
eSocial (SHA-256 × SHA-1) e por isso agora verifica em vez de presumir.

`procEmi` também diverge: CT-e usa `"0"`/`"3"` (aplicativo do contribuinte / SEBRAE); MDF-e usa
`"0"`/`"4"` (aplicativo do contribuinte / Provedor de Assinatura e Autorização - PAA). Mais um
par de campos com o mesmo nome e propósito semelhante, mas tabela de valores diferente.

`tpEmit` é novo, sem equivalente no CT-e: `1`-Prestador de serviço de transporte,
`2`-Transportador de Carga Própria (emitentes de NF-e usam este), `3`-Prestador que emitirá
CT-e Globalizado depois. `tpTransp` (opcional): `1`-ETC, `2`-TAC, `3`-CTC — classificação do
transportador perante a ANTT, diferente de `RNTRC` (que é o número de registro em si).

## `infDoc` — a ponte com CT-e/NF-e, confirmada

Estrutura: `infMunDescarga` (até 1000, por município de descarregamento) → dentro de cada um,
até 20000 ocorrências de `infCTe` (`chCTe`, tipo `TChCTe`) **ou** `infNFe` (`chNFe`, tipo
`TChNFe`) **ou** `infMDFeTransp` (chave de outro MDF-e — sub-manifesto, ex. transferência
multimodal). Cada referência carrega só a chave (mesmo padrão de `infDoc/infNFe` do CT-e, já
implementado em `fiscal/cte.py::montar_infnfe`) — mais campos opcionais raros (`SegCodBarra`,
`indReentrega`, `infUnidTransp`, `peri` para produtos perigosos, não investigados a fundo).

**Achado direto**: o MDF-e organiza os documentos referenciados **por município de
descarregamento**, não numa lista plana — diferente da hipótese implícita antes de investigar
(esperava-se algo mais parecido com a lista simples do `infDoc/infNFe` do CT-e). Implementar
`montar_infdoc` do MDF-e vai exigir agrupar por `cMunDescarga`, não só validar chaves.

## Modal rodoviário — aqui sim tem veículo e motorista

Confirmado o oposto do que se viu no CT-e (`docs/cte-modal-rodoviario.md`): o modal rodoviário
do **MDF-e** é que carrega veículo e motorista — faz sentido, é o MDF-e que identifica a viagem
física, não o CT-e (que é só o contrato de uma prestação).

- `infANTT` (opcional): `RNTRC` (mesmo tipo `TRNTRC`, `[0-9]{8}|ISENTO` já usado em
  `fiscal/cte_rodoviario.py` — **candidato real a reuso direto**), `infCIOT` (Código
  Identificador da Operação de Transporte / "conta frete", com CPF/CNPJ de quem gerou),
  `valePed` (vale-pedágio obrigatório, com fornecedor/responsável/valor).
- `veicTracao` (o veículo principal): `cInt` (código interno, opcional), `placa`, `RENAVAM`
  (opcional), `tara`, `capKG`/`capM3` (opcionais), `prop` (proprietário, só quando não é o
  próprio emitente — CPF/CNPJ, RNTRC, nome, IE/UF, `tpProp`: 0-TAC Agregado/1-TAC
  Independente/2-Outros), `condutor` (até 10 — nome + CPF, simples), `tpRod` (`01`–`06`:
  Truck/Toco/Cavalo Mecânico/VAN/Utilitário/Outros), `tpCar` (`00`–`05`: não aplicável/Aberta/
  Fechada-Baú/Granelera/Porta Container/Sider), `UF` de licenciamento (opcional).
- `veicReboque` (até 3 — reboques/carretas adicionais): estrutura semelhante a `veicTracao`
  (sem `condutor`, cada reboque não tem motorista próprio).

## O que ainda falta investigar antes de implementar

- Chave de acesso e assinatura do MDF-e — hipótese de trabalho, não verificada ainda: mesmo
  padrão da família (SHA-1, 44 posições, `Id="MDFe" + chave`), pelo mesmo tipo de raciocínio já
  aplicado ao CT-e (`docs/cte-assinatura.md`) — **precisa da mesma corroboração antes de
  reaproveitar `assinatura.py`**, não presumir só porque "é da mesma família de documentos".
- Autorizador/webservice por UF.
- Eventos do MDF-e (encerramento, cancelamento, inclusão de condutor, inclusão de DF-e
  posterior — mencionados nos arquivos `ev*MDFe_v3.00.xsd` do repositório, não abertos ainda).
- `emit`, `seg`, `tot`, `lacres` — grupos vistos na listagem de `infMDFe` mas não lidos a fundo.

## Implementado até agora

`fiscal/mdfe.py::montar_infdoc` (ver `docs/mdfe-infdoc.md`), `fiscal/mdfe_rodoviario.py`
(veículo/motorista, ver `docs/mdfe-modal-rodoviario.md`, reusando `validar_rntrc`/`RntrcInvalido`
do CT-e), `fiscal/mdfe.py::assinar_mdfe` (assinatura digital, ver `docs/mdfe-assinatura.md`,
reuso total de `assinatura.py`, confirmado por código de produção — não presumido só por CT-e já
ter sido confirmado) e `fiscal/mdfe.py::montar_ide`/`montar_mdfe` (orquestração dos 21 campos de
`ide`, ver `docs/mdfe-orquestracao.md` — lição do `cDV` do CT-e aplicada desde o início desta
vez), `montar_tot`/`montar_lacres` (ver `docs/mdfe-tot-lacres.md`) e `montar_emit`/`montar_seg`/
`montar_prod_pred` (ver `docs/mdfe-emit-seg-prodpred.md`) e `montar_infmodal`/`montar_infmdfe`
(orquestrador de nível mais alto, ver `docs/mdfe-infmdfe.md`). Todos os grupos de conteúdo de
`infMDFe` mapeados neste levantamento estão implementados e compostos num `infMDFe` completo,
com prova de ponta a ponta (`montar_infmdfe` → `montar_mdfe` → `assinar_mdfe`). Ainda falta:
`infLotacao` (dentro de `prodPred`), modais aéreo/aquaviário/ferroviário (só o rodoviário
está implementado). ~~Autorizador por UF~~ — **fechado**, ver
`docs/cte-mdfe-autorizadores.md`: achado real, o MDF-e tem um único autorizador nacional
(diferente do CT-e, que tem 4 grupos, e da NF-e, que tem 12) — todas as 27 UFs mapeiam
para a mesma infraestrutura, hospedada em `svrs.rs.gov.br`.

## Eventos do MDF-e — frente aberta em seguida à conclusão dos onze eventos do CT-e

Sete eventos confirmados em `schemes/PL_MDFe_300b` do `nfephp-org/sped-mdfe`: `evCancMDFe`
(cancelamento), `evEncMDFe` (encerramento), `evIncCondutorMDFe` (inclusão de condutor),
`evInclusaoDFeMDFe` (inclusão de DF-e), `evConfirmaServMDFe` (confirmação do serviço),
`evPagtoOperMDFe` (pagamento da operação), `evAlteracaoPagtoServMDFe` (alteração de
pagamento do serviço).

**Cancelamento implementado** (`fiscal/documento/evento_mdfe.py`, ver
`docs/mdfe-evento-cancelamento.md`): `tpEvento` `"110111"` — o mesmo número usado pelo
cancelamento da NF-e e do CT-e. `TEvento` do MDF-e converge com a forma do CT-e
(`@versaoEvento` como atributo de `detEvento`, sem elemento `verEvento`), diferente da
NF-e. Achado real: o `@Id` do MDF-e tolera **duas** larguras de `nSeqEvento` (2 ou 3
dígitos) — diferente do CT-e, que só aceita 3 — decorrência de `TChMDFe` já incorporar o
suporte ao CNPJ alfanumérico dentro do próprio layout da chave. `TJust` do MDF-e é
numericamente igual ao do CT-e (15-255), mas verificado à parte, não presumido igual.

**Encerramento implementado em seguida** (ver `docs/mdfe-evento-encerramento.md`):
`tpEvento` `"110112"` — fecha a viagem. Achado real: `cUF` usa `TCodUfIBGE_EX`, que
aceita `"99"` para Exterior (27 UFs brasileiras + Exterior), não a tabela comum de 27
UFs — faz sentido para uma viagem que termina fora do Brasil (ex. Mercosul).
`indEncPorTerceiro` só é gravado quando quem encerra é transportador terceiro, diferente
do emitente do MDF-e.

**Inclusão de condutor implementada em seguida** (ver
`docs/mdfe-evento-inclusao-condutor.md`): `tpEvento` `"110114"`. Achado real de reuso: o
grupo `condutor` (`xNome`/`CPF`, um único, não lista) é exatamente a mesma forma já
modelada em `fiscal.mdfe_rodoviario.Condutor`/`montar_condutor` (usada dentro de
`veicTracao`) — reaproveitados diretamente. Achado real 2: `descEvento` tem uma única
grafia possível, sem acento ("Inclusao Condutor") — diferente de outros eventos desta
frente que aceitam variante acentuada.

**Inclusão de DF-e implementada em seguida** (ver `docs/mdfe-evento-inclusao-dfe.md`):
`tpEvento` `"110115"`. Achado real: o arquivo `evInclusaoDFeMDFe_v3.00.xsd` declara o
elemento `evIncDFeMDFe` — nome do arquivo diverge do elemento raiz, mesma classe de
achado já vista no CT-e. Achado real 2: o `infDoc` deste evento só aceita `chNFe`
(nunca CT-e) — diferente do `infDoc` da orquestração principal do MDF-e, que agrupa
`infCTe`/`infNFe`.

**Confirmação do serviço implementada em seguida** (ver
`docs/mdfe-evento-confirmacao-servico.md`): `tpEvento` `"110117"`, o mais simples desta
frente — só `nProt`. Achado real: a numeração dos eventos não é contígua nem segue a
ordem alfabética dos arquivos (`"110117"` vem depois de `"110116"`, que pertence ao
pagamento da operação, alfabeticamente posterior).

**Pagamento da operação implementado em seguida** (ver
`docs/mdfe-evento-pagamento-operacao.md`): `tpEvento` `"110116"`, o evento mais complexo
do MDF-e — `infViagens` + `infPag` (lista, com componentes do frete, três formas de
identificar o responsável — CPF/CNPJ/estrangeiro —, pagamento à vista/a prazo com
parcelas, e três formas de receber o pagamento — banco+agência/CNPJIPEF/PIX). Achado
real: `idEstrangeiro` tem uma inconsistência no próprio XSD entre `minLength`/`maxLength`
declarados e o `xs:pattern` (que na prática só aceita vazio ou 5-20 caracteres, nunca
2-4) — validado pelos limites declarados, não pelo padrão degenerado.

**Alteração do pagamento implementada em seguida — sétimo e último evento do MDF-e** (ver
`docs/mdfe-evento-alteracao-pagamento.md`): `tpEvento` `"110118"`. Achado real de reuso
confirmado (não especulativo): o `infPag` é estruturalmente idêntico ao do pagamento da
operação — `ComponentePagamento`/`InfoBancaria`/`InfoPagamento` e as funções de montagem
são compartilhadas entre os dois eventos, só faltando `infViagens` neste.

## Marco atingido: todos os sete eventos do MDF-e v3.00 implementados

`evCancMDFe`, `evEncMDFe`, `evIncCondutorMDFe`, `evIncDFeMDFe`, `evPagtoOperMDFe`,
`evConfirmaServMDFe`, `evAlteracaoPagtoServMDFe` — todos modelados, testados e
serializáveis em `fiscal/documento/evento_mdfe.py`. Combinado com os onze eventos do
CT-e já concluídos (`docs/cte-estado.md`), a frente de eventos dos dois documentos de
transporte está fechada. Pendente fora do conteúdo de eventos (à época): autorizador/
webservice por UF (MDF-e e CT-e) e a camada `integracao/` que liga tudo a doctypes reais
do ERPNext — os dois fechados em seguida (ver `docs/cte-mdfe-autorizadores.md` e
`docs/integracao-cte-frete.md`). Só falta mesmo a transmissão de verdade, bloqueada por
falta de certificado A1/ambiente de homologação testável nesta investigação.

## Serviços de autorização do MDF-e — nomes reais, lote + recibo

Fonte: `autorizadores_mdfe.py` (lido de `nfephp-org/sped-mdfe`, `storage/wsmdfe_3.00.xml` e
`storage/autorizadores.json`, chave `"58"` — consultados em 2026-09-03). Autorizador **único
nacional** (todas as 27 UFs, ver `docs/cte-mdfe-autorizadores.md`).

**Achado real que corrige o planejamento**: os nomes `MDFeAutorizacao`/`MDFeRetAutorizacao`,
usados no `openspec/changes/fechar-laco-cte-mdfe`, **não existem na fonte** — são invenção por
analogia com a NF-e. Os serviços reais são `MDFeRecepcao` (lote, devolve `nRec`) e
`MDFeRetRecepcao` (consulta do recibo) — o fluxo de **lote + recibo** que a entrega escolheu,
reusando a máquina de polling da NF-e; e a **síncrona** `MDFeRecepcaoSinc` também existe como
alternativa. Serviços confirmados na fonte:

| Serviço | Papel |
|---|---|
| `MDFeRecepcao` | Autorização por **lote** — devolve `nRec` |
| `MDFeRetRecepcao` | Consulta do **recibo** (polling até o protocolo) |
| `MDFeRecepcaoSinc` | Autorização **síncrona** (alternativa, não usada nesta entrega) |
| `MDFeRecepcaoEvento` | Recepção de eventos (110112/110111…) |
| `MDFeConsulta` | Consulta da situação do manifesto |
| `MDFeStatusServico` | Status do serviço |
| `MDFeConsNaoEnc` | Consulta de MDF-e não encerrados |
| `MDFeDistribuicaoDFe` | Distribuição |

## Transmissão e eventos (tarefa 5 de `fechar-laco-cte-mdfe`)

A autorização por lote e recibo, o encerramento e o cancelamento estão implementados e documentados em
[mdfe-operacional.md](mdfe-operacional.md). Dois achados deste passo: o montador de evento do MDF-e devolvia a raiz `evento`
(a da NF-e) em vez de `eventoMDFe`, com os campos soltos em `detEvento` — corrigido para cancelamento e encerramento, pendente
nos outros cinco (`docs/gaps.md`); e `MDFeRecepcaoSinc` existe, mas o app usa o lote.

## Campos de `Shipment` e `Shipment Delivery Note` que a montagem lê — e os `br_*` que o Shipment ganha (tarefa 1.4)

Fonte: leitura direta do core de `G:\PROJECTS\erpnext\erpnext\stock\doctype\shipment\shipment.json` e
`...\shipment_delivery_note\shipment_delivery_note.json` (consultados em 2026-09-15). Decisão da
tarefa 1.4 — o levantamento contra a fonte corrige duas afirmações do `design.md`:

### O que a montagem lê do `Shipment` (campos do core, nenhum nosso)

| Campo | Papel na montagem |
|---|---|
| `shipment_delivery_note` | Tabela filha (`Shipment Delivery Note`) — as `Delivery Note` da viagem; já é a base de `cte_extracao.referencias_do_shipment` |
| `delivery_address_name` | Link → `Address` de entrega — município de descarga e `UFFim`; já lido como `br_codigo_municipio_ibge`/`city` |
| `pickup_address_name` | Link → `Address` de coleta — município de carga (`infMunCarrega`) e `UFIni` |
| `total_weight` | `Float`, read_only — peso da carga (`tot.qCarga`) |
| `value_of_goods` | `Currency`, reqd — valor da carga (`tot.vCarga`) |
| `pickup_company` / `delivery_company` | Link → `Company` de origem/destino — decidir a `Company` emitente (tpEmit 2) na montagem, tarefa 4.x |

### O que a montagem lê de `Shipment Delivery Note` (tabela filha, `istable`)

| Campo | Papel |
|---|---|
| `delivery_note` | Link → `Delivery Note`, reqd — de onde vem `br_chave_acesso` |
| `grand_total` | `Currency`, read_only — não lido pela primeira montagem (o `tot` usa `value_of_goods` do `Shipment`, não a soma das linhas) |

Só `delivery_note` é lido — por isso a entrada em `LEITURAS` declara só ele.

### `br_*` que o `Shipment` **ganha** (tarefa 4.4) — e os que **não** ganha (correção do design)

Ganha (mapeados às dataclasses de `fiscal/mdfe_rodoviario.py`):

- veículo de tração (`Veiculo`): `br_placa`, `br_tara` (ambos obrigatórios em `_montar_campos_comuns`),
  e os opcionais `br_codigo_interno`, `br_renavam`, `br_capacidade_kg`, `br_capacidade_m3`,
  `br_tipo_carroceria`, `br_uf_licenciamento`, `br_tipo_rodado` (`tpRod`, obrigatório para
  `montar_veiculo_tracao`)
- condutor (`Condutor`): `br_condutor_nome` + `br_condutor_cpf` (até 10; a primeira montagem
  declara um no formulário)
- retorno da numeração: `br_numero_mdfe` (série 58, mesma forma do `br_numero_nfe`)

**Não ganha — correção do `design.md` decisão 2, feita a partir da fonte:**

- **RNTRC**: já existe como `Company.br_rntrc`, lido por `integracao/configuracao_fiscal.py::rntrc_da_empresa`
  (usado pelo CT-e). Duplicá-la como `br_*` no `Shipment` criaria a segunda fonte de verdade para
  o mesmo atributo; a montagem usa `rntrc_da_empresa`, como o CT-e já faz.
- **CIOT** (`infANTT/infCIOT`) e **vale-pedágio** (`infANTT/valePed`): já declarados **fora do
  escopo** do modal rodoviário em `fiscal/mdfe_rodoviario.py` (docstring do módulo). Ganhar campo
  de formulário para dado que a montagem ainda não consome é campo morto.

### Entrada do `Shipment` no contrato de leituras — e por que `Shipment` fica fora de `LEITURAS`

`Shipment Delivery Note` entra em `setup/leituras_do_erpnext.py` com `("delivery_note",)`: é pura
leitura de estrutura alheia (a `istable` não ganha campo nosso). Mas `Shipment` **não** pode entrar
em `LEITURAS`: a tarefa 4.4 o registra em `setup/campos_documento.py` com `br_numero_mdfe` + campos
da viagem, e `tests/test_leituras_do_erpnext.py::test_nenhum_lido_tem_campo_ou_hook_nosso` exige que
um DocType com campo nosso **nunca** esteja em `LEITURAS` (é a mesma regra que tirou o `POS Invoice`
de `NOMES_USADOS_COMO_CHAVE` quando o cupom ganhou campos fiscais). O `Shipment` passa a ser cobrado
pela conferência **de campo** (tarefa 4.4) e pela prova de bench da tarefa 6.2 (salvar/reler),
não pela conferência de leitura.

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd` (`ide`,
  linhas 17–232; `infDoc`, a partir da linha 331) e `mdfeModalRodoviario_v3.00.xsd` (`veicTracao`
  a partir da linha 496, `condutor` a partir da linha 638) — arquivos baixados e lidos localmente
  em 2026-08-31.
- `G:\PROJECTS\erpnext\erpnext\stock\doctype\shipment\shipment.json` e
  `G:\PROJECTS\erpnext\erpnext\stock\doctype\shipment_delivery_note\shipment_delivery_note.json`
  (campos lidos acima) — consultados em 2026-09-15.
