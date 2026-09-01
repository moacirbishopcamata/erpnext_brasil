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

`fiscal/mdfe.py::montar_infdoc` (ver `docs/mdfe-infdoc.md`) e `fiscal/mdfe_rodoviario.py`
(veículo/motorista, ver `docs/mdfe-modal-rodoviario.md`, reusando `validar_rntrc`/`RntrcInvalido`
do CT-e). Ainda falta: chave de acesso/assinatura (hipótese, não corroborada), autorizador por
UF, eventos, `emit`/`seg`/`tot`/`lacres`, e um orquestrador `montar_ide`/`montar_mdfe` que amarre
tudo — mesmo papel que `fiscal/cte.py::montar_ide`/`montar_cte` cumprem para o CT-e.

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd` (`ide`,
  linhas 17–232; `infDoc`, a partir da linha 331) e `mdfeModalRodoviario_v3.00.xsd` (`veicTracao`
  a partir da linha 496, `condutor` a partir da linha 638) — arquivos baixados e lidos localmente
  em 2026-08-31.
