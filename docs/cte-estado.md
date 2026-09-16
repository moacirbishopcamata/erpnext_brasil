# Levantamento de estado: CT-e (Conhecimento de Transporte Eletrônico, modelo 57)

Mesma disciplina de `docs/rh-estado-esocial.md`/`docs/pcp-estado.md` — levantar antes de
implementar. Pré-requisito do MDF-e (ver "Analise para implementação, manifesto de carga"),
que referencia CT-e/NF-e transportados, nunca os substitui.

## Obstáculo de investigação (registrado e agora superado)

As três primeiras tentativas de ler `cteTiposBasico_v4.00.xsd` via busca de página (resumo por
modelo pequeno) devolveram estruturas erradas em sequência (`TCTeSimp`, depois `TGTVe` — um
documento totalmente diferente, Guia de Transporte de Valores modelo 64) e, numa tentativa
seguinte, a mesma ferramenta chegou a afirmar que `cte_v4.00.xsd` tinha **10 linhas** contendo
só um `include` — falso: o arquivo baixado diretamente tem **7966 linhas** e contém a definição
completa de `TCTe`. Causa raiz: resumo de página truncava/alucinava em arquivo grande. Correção
aplicada: baixar o XSD com `curl` para dentro do worktree e usar `Grep`/`Read` locais — o que
produziu todos os números de linha citados abaixo, verificáveis por qualquer um a qualquer
momento (não é mais uma leitura de terceiro, é o arquivo-fonte).

- Fonte: `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/cte_v4.00.xsd` (contém, apesar do
  nome do arquivo, tanto `TGTVe`, `TCTeSimp`, `TCTe` quanto `TCTeOS` — o nome do arquivo não
  reflete seu conteúdo real; `cteTiposBasico_v4.00.xsd`, que o `cte_v4.00.xsd` principal só
  inclui, tem apenas 10 linhas de verdade — o "arquivo de 10 linhas" que a ferramenta relatou
  antes existe, só que é o outro arquivo). Consultado em 2026-08-31.

## Estrutura confirmada de `TCTe` (CT-e normal e substituto, não o simplificado nem o OS)

`complexType name="TCTe"` começa na linha 2689. Filhos diretos de `infCte` (mesmo nível de
`ide`), em ordem, com linha confirmada por grep:

| Grupo | Linha | Papel |
|---|---|---|
| `ide` | 2700 | Identificação — `cUF`, `cCT`, **`CFOP`** (`type="TCfop"`, mesma tabela de 4 dígitos já implementada em `fiscal/cfop.py`), `natOp`, `mod` (57), `serie`, `nCT`, `dhEmi`, `tpImp` |
| `compl` | 3145 | Complemento (opcional) |
| `emit` | 3542 | Emitente (a transportadora) |
| `rem` | 3621 | Remetente da carga |
| `exped` | 3695 | Expedidor (opcional — quando diferente do remetente) |
| `receb` | 3754 | Recebedor (opcional — quando diferente do destinatário) |
| `dest` | 3813 | Destinatário da carga |
| `vPrest` | 3885 | Valores da prestação do serviço de transporte |
| `imp` | 3931 | Impostos — ver seção própria abaixo |
| `infCTeNorm` \| `infCteComp` | 4012 (`xs:choice`) | Ver seção própria — **não** existe uma terceira opção `infCTeAnu` neste schema v4.00 (correção de uma suposição anterior, baseada em memória de NF-e, não verificada até agora) |
| `autXML` | 4816 | Autorizados a baixar o XML (até 10) |
| `infRespTec` | 4840 | Responsável técnico pelo sistema emissor |
| `infSolicNFF` | 4845 | Solicitação de NF-e Futura (opcional) |
| `infPAA` | 4866 | Programa de Alimentação do Aviador (setor específico, não investigado) |
| `qrCodCTe` | 4929 | QR Code (CT-e tem QR Code, análogo ao da NFC-e — não investigado a fundo ainda) |

**Investigado em seguida** — `toma3`/`toma4` estão dentro de `ide`, logo depois de `indIEToma`
(linha 2985): é um `xs:choice` entre `toma3` (linha 3003 — o tomador é uma das partes já
citadas no próprio CT-e, indicada por um código 0-remetente/1-expedidor/2-recebedor/
3-destinatário, sem repetir dado) e `toma4` (linha 3032 — papel fixo "4-Outros", exige dados
cadastrais completos do tomador: CNPJ/CPF, IE, `xNome`, `enderToma`). Achado real: o CT-e evita
duplicar dado do tomador sempre que ele coincide com uma parte já identificada na prestação —
mesmo espírito de "preencha o que o sistema já sabe" citado nas preferências de engenharia deste
projeto, só que aplicado pelo próprio layout do XSD, não por uma decisão de UI deste app.

## `imp` (impostos) — `TImp`, `complexType` na linha 6672

Não é um grupo de campos fixo como o `ICMS` da NF-e: é um **`xs:choice`** entre sete situações
tributárias mutuamente exclusivas, cada uma com seu próprio conjunto de campos (linhas
confirmadas por grep):

- `ICMS00` (6677) — tributação normal.
- `ICMS20` (6713) — base reduzida.
- `ICMS45` (6777) — isento/não-tributado/diferimento.
- `ICMS60` (6826) — cobrado por substituição tributária (**ausente** em `TImpOS`, linha 7061 em
  diante — CT-e OS não tem esse caso, coerente com ser para transporte de pessoas/valores, não
  mercadoria revendida).
- `ICMS90` (6894) — outras.
- `ICMSOutraUF` (6963) — prestação cujo ICMS pertence a outra UF.
- `ICMSSN` (7027) — Simples Nacional.

Dentro do grupo `imp` (não do `TImp`), linha 3960: **`ICMSUFFim`**, opcional — "grupo a ser
informado nas prestações interestaduais para consumidor final, não contribuinte do ICMS". É o
**equivalente do `ICMSUFDest` da NF-e** para transporte: `vBCUFFim`, `pFCPUFFim`, `pICMSUFFim`,
`pICMSInter` — mesma partilha entre UF de origem/destino que `fiscal/impostos/icms.calcular_difal`
já calcula, só que com nomes de campo diferentes (`UFFim` = UF de término da prestação, não
`UFDest`). **Achado real, não suposto**: a lógica de cálculo de `calcular_difal` é candidata a
reuso direto aqui (mesma regra, Art. 155 §2º VII/VIII CF), só a montagem do XML muda de nome de
campo — mesmo padrão do reuso de `DetalhamentoContribuicao` entre PIS/Cofins.

## `infCTeNorm` (linha 4013) — o corpo específico do CT-e normal

Filhos diretos confirmados: `infCarga` (4019), `infDoc` (4119, opcional), `infModal` (4551),
`cobr` (4652, opcional — fatura/duplicatas, mesmo padrão de `cobr` da NF-e), `infCteSub` (4726,
opcional — substituição de CT-e). A alternativa do `xs:choice` é `infCteComp` (4801) — CT-e
complementar, que carrega só `chCTe` do CT-e complementado (até 10) — mais simples do que o
`infCTeNorm` completo, coerente com ser um documento de ajuste, não uma prestação nova.

`infModal` é um `xs:any`/extensão para um dos arquivos de modal específico já catalogados
(`cteModalRodoviario_v4.00.xsd`, `cteModalAereo_v4.00.xsd`, `cteModalAquaviario_v4.00.xsd`,
`cteModalDutoviario_v4.00.xsd`, `cteModalFerroviario_v4.00.xsd`) — **não investigado ainda qual
desses é prioritário**; rodoviário é o candidato natural para o primeiro incremento (mais comum
no Brasil), mas isso é suposição, não verificação.

**`infDoc` é opcional — confirmado no XSD, não suposto** (linha 4119: `minOccurs="0"`). A decisão
da frente operacional (`docs/cte-operacional.md`/`openspec/changes/fechar-laco-cte-mdfe`) de
deixar as referências de documento fora do primeiro incremento se apoia nisso: um CT-e sem
`infDoc` é válido para autorização. Consequência direta da fonte: a etapa de montagem do CT-e
**não depende** de `infDoc` — o mapeador para a `Sales Invoice` de frete preenche todos os grupos
obrigatórios (emit, tomador, vPrest) sem precisar da lista de chaves, que hoje tampouco é
rastreável de uma fatura de transporte (o `Shipment` não amarra fatura nenhuma). Quando a tela
de chaves vier, ela adiciona `infNFe`/`infNF` sem mudar o resto da montagem.

**`infDoc` investigado em seguida** (linha 4119): é um `xs:choice` entre `infNF` (linha 4128 —
documento originário é NF modelo 01/04 em papel, carrega o detalhamento fiscal inteiro: `vBC`,
`vICMS`, `vBCST`, `vST`, `vProd`, `vNF`, `nCFOP` — caso legado, cada vez mais raro) e `infNFe`
(linha 4271 — documento originário é NF-e eletrônica, referenciada só pela `chave` de acesso,
tipo `TChDFe`). **Achado direto para o MDF-e**: é essa `chave` de `infNFe` — só ela, sem
detalhamento fiscal repetido — que fecha a ponte de correlação; o MDF-e vai precisar da mesma
lista de chaves (de CT-e e de NF-e) para o seu próprio `infDoc`. **Implementado em seguida** (ver
`docs/cte-infnfe.md`): `fiscal/cte.py::montar_infnfe`, reusando `ler_chave`/`ChaveInvalida` de
`fiscal/documento/chave_acesso.py` — mesmo layout de 44 posições e dígito verificador da NF-e,
confirmado idêntico entre os documentos da família (só o dígito de modelo muda).

**Modal rodoviário investigado e implementado em seguida** (ver `docs/cte-modal-rodoviario.md`):
`cteModalRodoviario_v4.00.xsd` tem só 102 linhas — lido inteiro, sem risco de truncamento.
Achado: **não** carrega veículo nem motorista (isso é do MDF-e); só `RNTRC` (obrigatório,
`[0-9]{8}|ISENTO` — a palavra `ISENTO` é valor legítimo, não erro de formato, para frota
própria) e `occ` (ordens de coleta, opcional).

**Assinatura investigada e implementada em seguida** (ver `docs/cte-assinatura.md`): confirmado
— não suposto — que o CT-e usa o **mesmo perfil** de assinatura da NF-e (SHA-1, RSA-SHA1,
enveloped), via `infCte/@Id` = `CTe[0-9]{44}` no XSD e via código de produção do
`nfephp-org/sped-common`/`sped-cte` (o texto do Ajuste SINIEF continua não localizado — o PDF
"Visão Geral" do CONFAZ não desce a esse nível técnico). `fiscal/documento/assinatura.py` foi
reaproveitado **sem nenhuma alteração** — já era genérico o bastante.

## O que ainda falta investigar antes de implementar

- ~~Autorizador/webservice por UF~~ — **fechado**, ver `docs/cte-mdfe-autorizadores.md`:
  achado real, o mapa do CT-e **diverge** do da NF-e (só 4 grupos, não 12; `AM`/`BA`/`GO`/`PE`
  têm webservice próprio na NF-e mas caem no autorizador compartilhado no CT-e).
- `infNF` (NF em papel) — deliberadamente não implementado; caso legado, prioridade baixa.
- Nenhum — os onze eventos de `schemes/PL_CTe_400` no `nfephp-org/sped-cte` estão todos
  implementados (ver seção "Marco atingido" abaixo).

**Evento de cancelamento implementado** (ver `docs/cte-evento-cancelamento.md`): `tpEvento`
110111 e o corpo de `detEvento` são idênticos à NF-e, mas dois pontos divergem de verdade —
justificativa vai até 255 caracteres (não 256), e o `@Id` tem 53 dígitos (`nSeqEvento` com 3
dígitos no Id, não 2). `assinar_evento`/`EventoInvalido` da NF-e reaproveitados sem alteração.

**Carta de correção implementada em seguida** (ver `docs/cte-evento-correcao.md`): achado real
e grande — a CC-e do CT-e **não é texto livre** como a da NF-e, é `infCorrecao`, uma lista
estruturada de correções campo a campo (`grupoAlterado`/`campoAlterado`/`valorAlterado`/
`nroItemAlterado`). `xCondUso` cita uma base legal diferente (Art. 58-B do Convênio SINIEF
06/89, não o Art. 7º do Convênio S/N usado pela NF-e). `tpEvento` (`"110110"`) é o mesmo
número da NF-e, mesmo o corpo divergindo por completo.

**Comprovante de entrega implementado em seguida** (ver
`docs/cte-evento-comprovante-entrega.md`): `tpEvento` `"110180"`, código próprio sem
equivalente na NF-e. `hashEntrega` é um cálculo real (SHA-1 de chave+imagem, recodificado em
Base64), não um campo de texto livre — confirmado pelo tipo `base64Binary` de 20 bytes no
XSD, o tamanho exato de um digest SHA-1.

**EPEC implementado em seguida** (ver `docs/cte-evento-epec.md`): `tpEvento` `"110113"`, a
prévia enviada em contingência. Achado real: o `toma4` do EPEC não é o `toma4` real do `ide` —
aceita qualquer um dos 5 papéis (não só "Outros"), e é minimalista (sem `xNome`/`enderToma`/
`email`) — por isso ganhou um tipo à parte (`TomadorEpec`). `tpCTe` é fixo em `"0"` (só CT-e
Normal), diferente do `ide/tpCTe` que aceita `0`/`1`/`3` — não é parâmetro da função.

**Cancelamento do comprovante de entrega implementado em seguida** (ver
`docs/cte-evento-cancelamento-comprovante-entrega.md`): `tpEvento` `"110181"`. Achado real,
contra o nome do arquivo (`evCancCECTe`): "CE" é Comprovante de Entrega, não Carta de Correção
— confirmado pelo texto do próprio XSD, não suposto por analogia com `evCCeCTe`. Corpo simples:
`nProt` (protocolo do CT-e) e `nProtCE` (protocolo do evento de entrega cancelado).

**Insucesso na entrega implementado em seguida** (ver `docs/cte-evento-insucesso-entrega.md`):
`tpEvento` `"110190"`, quase gêmeo do comprovante de entrega. Dois achados reais: `xJustMotivo`
usa `TString` (15-256), não `TJust` (15-255) como o cancelamento/EPEC do mesmo documento — 256
é válido aqui, diferente do resto do CT-e; e o hash (`hashTentativaEntrega`) é **opcional**
(diferente de `hashEntrega`, obrigatório no comprovante de entrega) — calculado só quando há
imagem. `_montar_inf_entrega_nfe` extraído e reaproveitado entre os dois eventos (mesma regra
de `infEntrega`, antes duplicada inline).

**Cancelamento do insucesso na entrega implementado em seguida** (ver
`docs/cte-evento-cancelamento-insucesso-entrega.md`): `tpEvento` `"110191"`. Confirmado
estruturalmente idêntico ao cancelamento do comprovante de entrega — só o nome do campo do
segundo protocolo (`nProtIE`, não `nProtCE`) e o texto de `descEvento` mudam. Reuso real (não
especulativo, é a segunda instância confirmada da mesma forma):
`_montar_evento_cancelamento_protocolo`, função privada comum às duas.

**Informações da GTV implementadas em seguida** (ver `docs/cte-evento-gtv.md`): `tpEvento`
`"110170"`, registra as Guias de Transporte de Valores transportadas — sem equivalente na
NF-e. Achado real: `descEvento` aceita duas grafias válidas no próprio XSD (`"Informações"`/
`"Informacoes"`) — este projeto sempre grava a acentuada. Reuso: `validar_rntrc` de
`cte_rodoviario` (mesmo RNTRC), `ParteGtv`/`montar_parte_gtv` únicos para `rem`/`dest` (mesma
forma exata). Fora de escopo documentado: remetente/destinatário estrangeiro (`TCnpjOpc` com
CNPJ de zeros), que `validar_cnpj` deste projeto rejeita por desenho.

**Prestação em desacordo e seu cancelamento implementados em seguida** (ver
`docs/cte-evento-prestacao-desacordo.md`): `tpEvento` `"610110"`/`"610111"`. Achado real:
primeiro par de eventos desta frente **fora** do padrão `110xxx` (todos os oito anteriores
seguiam essa família) — não dá para supor a faixa de código de um evento pelo padrão dos
demais. Achado real 2: o cancelamento (`evCancPrestDesacordo`) diverge da forma dos
cancelamentos anteriores — carrega só `nProtEvPrestDes`, sem `nProt` do CT-e — por isso não
reaproveita `_montar_evento_cancelamento_protocolo`.

**Registro multimodal implementado em seguida — o último dos onze eventos do CT-e v4.00**
(ver `docs/cte-evento-registro-multimodal.md`): `tpEvento` `"110160"`, de volta ao padrão
`110xxx` (não segue a exceção `610xxx` do evento anterior). Achado real: `nDoc` (1-44
dígitos) tem o mesmo comprimento de uma chave de acesso, mas o XSD tipa como `[0-9]{1,44}`
solto, não `TChDFe` — este módulo não valida `nDoc` como chave (sem dígito verificador),
fiel ao que o schema realmente pede. `xRegistro` vai até 1000 caracteres, o maior limite de
texto livre entre os eventos do CT-e desta frente.

**Marco atingido: todos os onze eventos do CT-e v4.00 implementados.** Os onze eventos
listados em `schemes/PL_CTe_400` do `nfephp-org/sped-cte` estão modelados, testados e
serializáveis: cancelamento, carta de correção, comprovante de entrega, EPEC, cancelamento
do comprovante de entrega, insucesso na entrega, cancelamento do insucesso na entrega,
informações da GTV, prestação em desacordo, cancelamento da prestação em desacordo e
registro multimodal. Cada um foi verificado individualmente contra o XSD correspondente
(nunca suposto por analogia entre eventos irmãos) — a frente descobriu divergências reais
em quase todos: limites de texto livre diferentes (255/256/1000), campos que existem num
evento e não no "gêmeo" aparente, `tpEvento` fora do padrão esperado (`610xxx`), e grafias
múltiplas aceitas pelo próprio XSD (`descEvento`). Pendente fora do conteúdo de eventos
(à época): autorizador/webservice por UF do CT-e, transmissão de verdade, e eventos do
MDF-e — os dois primeiros fechados em seguida (ver `docs/cte-mdfe-autorizadores.md` e
`docs/mdfe-estado.md`), só falta mesmo a transmissão real (bloqueada por falta de
certificado A1/homologação testável nesta investigação).

**`toma3`/`toma4` implementados em seguida** (ver `docs/cte-toma.md`): `montar_toma3` (o
tomador é uma das partes já citadas no CT-e, só valida o código) e `montar_toma4` (tomador
"Outros", cadastro completo — CNPJ/CPF exclusivo como no destinatário da NF-e, `enderToma`
obrigatório, ordem de campos estrita do `xs:sequence`).

**Orquestração fechada em seguida** (ver `docs/cte-orquestracao.md`): `montar_ide`/`montar_cte`
amarram tudo — os 30 campos de `ide` verificados e ordenados contra o XSD, composição com
`toma3`/`toma4` já prontos, `Id`/chave derivados como na NF-e. Prova de ponta a ponta
(`montar_ide` → `montar_cte` → `para_xml` → `assinar_cte`) confirma que as peças implementadas
em incrementos separados realmente se encaixam.

## Implementado até agora

`fiscal/cte.py`: `montar_icms_uf_fim` (grupo `ICMSUFFim`, ver `docs/cte-icms-uf-fim.md`),
`montar_infnfe` (grupo `infDoc/infNFe`, ver `docs/cte-infnfe.md`), `assinar_cte` (assinatura
digital, ver `docs/cte-assinatura.md`, reuso total de `assinatura.py`), `montar_toma3`/
`montar_toma4` (tomador do serviço, ver `docs/cte-toma.md`) e `montar_ide`/`montar_cte`
(orquestração completa, ver `docs/cte-orquestracao.md`). `fiscal/cfop_transporte.py`: CFOP de
prestação de serviço de transporte (ver `docs/cfop-transporte.md`). `fiscal/cte_rodoviario.py`:
modal rodoviário — `RNTRC`/`occ` (ver `docs/cte-modal-rodoviario.md`).

O CT-e rodoviário básico está funcionalmente completo do lado puro (Python, sem Frappe): dá para
montar, assinar e serializar um CT-e de ponta a ponta. O que falta é o que nenhum módulo puro
resolve sozinho: autorizador/webservice por UF (não investigado — provavelmente segue o mesmo
SVRS/SVSP já mapeado para NF-e, mas não verificado), transmissão de verdade, e a integração com
Frappe (`integracao/`, doctypes) para gerar `IdentificacaoCte`/`TomadorOutros` a partir de um
documento de transporte real do ERPNext.

## O campo `br_natureza_transporte` mora no cabeçalho da `Sales Invoice` — decidido

A detecção de "fatura de transporte" (que habilita o botão Emitir CT-e) usa um campo explícito
no **cabeçalho** da `Sales Invoice`, nunca inspeção heurística de item. A natureza de transporte
é atributo da **prestação inteira** (do documento), não de uma linha: uma fatura pode misturar
itens, e herdar do `Item` reintroduziria a heurística que o design recusou — recusar uma
prestação de transporte legítima sem item classificado, ou habilitar uma fatura que não é de
transporte só porque tem um item com nome de frete. O `natOp` do CT-e já vem de
`br_natureza_operacao` (também campo de cabeçalho, ver `integracao/nfe_documento.py`); o
`br_natureza_transporte` (Select) é a declaração explícita do usuário de que a fatura é a venda
de uma prestação de transporte. Registrado na docstring de `integracao/cte_documento.py` quando
o módulo existir (tarefa 2.1).

## Serviços de autorização do CT-e — nomes reais, fluxo síncrono

Fonte: `autorizadores_cte.py` (lido de `nfephp-org/sped-cte`, `storage/wscte_4.00_mod57.xml`
e `storage/autorizadores.json` — consultados em 2026-09-03). A tabela de endpoints por UF já
está implementada (ver `docs/cte-mdfe-autorizadores.md`); o que falta é a transmissão em si.

**Achado real que corrige o planejamento**: o CT-e 4.00 **não tem lote + recibo**. A
autorização é **síncrona por documento único** (`CTeRecepcaoSincV4`), resposta na própria
chamada — não existe `CTeAutorizacao4`/`CTeRetAutorizacao4` no leiaute deste documento (esses
termos, que apareciam em `openspec/changes/fechar-laco-cte-mdfe`, eram suposição por analogia
com a NF-e, não verificação). Serviços confirmados na fonte:

| Serviço | Chave no mapa | Papel |
|---|---|---|
| `CTeRecepcaoSincV4` | `CteRecepcao` | Autorização — **síncrona, unitária**, sem recibo |
| `CTeRecepcaoSimpV4` | `CteRecepcaoSimp` | Recepção síncrona simplificada (alternativa não usada) |
| `CTeConsultaV4` | `CteConsultaProtocolo` | Consulta de protocolo |
| `CTeStatusServicoV4` | `CteStatusServico` | Status do serviço |
| `CTeRecepcaoEventoV4` | `CteRecepcaoEvento` | Recepção de eventos (110111/110110…) |
| `CTeDistribuicaoDFe` | `CteDistribuicaoDFe` | Distribuição — **só grupo `AN`**, não autoriza |

Consequência para a transmissão (ver `openspec/changes/fechar-laco-cte-mdfe/design.md`, decisão
3): o CT-e **não reusa a máquina de polling de recibo** da NF-e — o desfecho vem da resposta da
própria chamada síncrona. O MDF-e, sim (ver `docs/mdfe-estado.md`).
