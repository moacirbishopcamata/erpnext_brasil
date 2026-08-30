# Montagem do documento NF-e

Referência dos grupos `ide`, `emit`, `dest` e `infNFe`. Implementado em
`erpnext_brasil/fiscal/documento/nfe.py`.

## Dicionário, não XML

A montagem devolve uma árvore de dicionários com os nomes oficiais das tags. Atributos
XML usam prefixo `@` (`@versao`, `@Id`, `@nItem`).

O motivo é a porta de transmissão: o ACBrLib consome INI, a ACBr API consome JSON, e um
provedor comercial pode querer outra coisa. Emitir XML aqui obrigaria todo adaptador a
desmontá-lo de volta — e dicionário ainda se testa por igualdade, o que uma string não
permite sem parser.

## A chave é derivada, nunca informada

A chave de acesso **repete oito dados** que também vivem no grupo `ide`: UF, ano/mês,
CNPJ do emitente, modelo, série, número, tipo de emissão e código numérico.

Duas fontes para o mesmo dado é exatamente onde divergência silenciosa nasce. Um sistema
que gere a chave de um lado e preencha o `ide` de outro acaba emitindo documento cuja
chave não corresponde ao próprio conteúdo — e o erro só aparece na validação da SEFAZ.

Aqui:

- `montar_infnfe` **calcula** a chave a partir da identificação e do CNPJ do emitente;
- o `cDV` do `ide` sai da mesma chave, não de um cálculo paralelo;
- o atributo `@Id` é `"NFe" + chave`, como o layout exige (47 caracteres).

Há teste provando que alterar o número da nota move a chave junto.

## Regras de validação implementadas

### Rejeição 897 (regra B03-10) — código numérico

O `cNF` não pode:

- ser igual ao `nNF`;
- ter todos os dígitos iguais (`00000000`, `11111111`, …).

A regra existe para dificultar código de segurança fraco e vigora em produção desde
02/09/2019. Antes disso o `cNF` era ignorado pelas validações e muita gente o usava como
espelho do número da nota — o que a regra passou a recusar.

### Exclusividade de identificação do destinatário

`CNPJ`, `CPF` e `idEstrangeiro` são mutuamente exclusivos no XSD. Informar mais de um é
rejeição, e não informar nenhum também. A escolha é feita pelo que veio preenchido;
informar dois é erro explícito, não escolha silenciosa.

### Inscrição Estadual condicionada ao indicador

A `IE` do destinatário só é informada quando `indIEDest` é `1` (contribuinte). Informá-la
para isento (`2`) ou não contribuinte (`9`) é rejeição.

### Opcional ausente não vira tag vazia

`xFant`, `IM`, `CNAE`, `ISUF` e `enderDest` só entram na árvore quando preenchidos. Tag
vazia é rejeição, não omissão — a diferença é a que separa documento autorizado de
documento recusado.

## Padrões deliberados

**Ambiente padrão é homologação** (`tpAmb` = `2`). Emitir em produção precisa ser escolha
consciente, não o que acontece quando o campo é esquecido.

**Série e número perdem zeros à esquerda no `ide`** (o layout usa o valor natural), mas a
chave os restaura para o tamanho fixo. São representações diferentes do mesmo dado, e a
montagem cuida das duas.

## Campos do grupo `ide`

| Campo | Obrigatório | Conteúdo |
|---|---|---|
| `cUF` | sim | Código da UF (IBGE) |
| `cNF` | sim | Código numérico, 8 dígitos |
| `natOp` | sim | Natureza da operação |
| `mod` | sim | `55` (NF-e) ou `65` (NFC-e) |
| `serie` | sim | Série |
| `nNF` | sim | Número da nota |
| `dhEmi` | sim | Data e hora com fuso — sem fuso a SEFAZ rejeita |
| `tpNF` | sim | `0` entrada, `1` saída |
| `idDest` | sim | `1` interna, `2` interestadual, `3` exterior |
| `cMunFG` | sim | Município do fato gerador |
| `cMunFGIBS` | não | Município do fato gerador do IBS (reforma) |
| `tpImp` | sim | Formato de impressão do DANFE |
| `tpEmis` | sim | Forma de emissão |
| `cDV` | sim | Dígito verificador da chave |
| `tpAmb` | sim | `1` produção, `2` homologação |
| `finNFe` | sim | Finalidade |
| `indFinal` | sim | Operação com consumidor final |
| `indPres` | sim | Presença do comprador |
| `procEmi` | sim | Processo de emissão |
| `verProc` | sim | Versão do processo de emissão |

## Grupo `prod` e `ICMSTot`

Implementados em `fiscal/documento/produto.py`.

**`prod`** descreve a mercadoria — não contém imposto, que é o grupo `imposto`, irmão
dele dentro de `det`. Duas exigências do layout que parecem redundância e não são:

- **`cEAN` nunca fica vazio.** Produto sem código de barras informa o literal
  `SEM GTIN`; deixar vazio é rejeição, e inventar um EAN seria pior — falsificaria um
  identificador que existe para rastrear o produto de verdade.
- **Unidade e quantidade tributáveis são campos distintos** dos comerciais
  (`uTrib`/`qTrib` vs. `uCom`/`qCom`). Quase sempre coincidem — por isso, quando não
  informados, os tributáveis **repetem** os comerciais — mas quem vende em caixa e
  tributa em unidade precisa preencher os dois, e o layout não admite omitir.

**`ICMSTot`** soma os valores já arredondados de cada item apurado, nunca recalcula sobre
a base agregada. Todo campo é informado, **zerado quando não houver valor** — omitir é
rejeição, não economia. O `vNF` soma apenas o que é por fora do preço (produtos, frete,
seguro, outras despesas, menos desconto, mais IPI); ICMS, PIS e COFINS já estão no preço
e não se somam de novo.

## Grupo `imposto`

Implementado em `fiscal/documento/imposto_item.py`. O XSD define **cerca de 20
variantes de ICMS** por CST/CSOSN, e modelar as 20 não cabia num único incremento —
fazê-lo pela metade seria pior que ser explícito sobre o recorte.

**Cobertas** (as que `fiscal/impostos/icms.py` já calcula): ICMS00 (integral), ICMS20
(redução de base), ICMS40/41/60 (isenta/não tributada/ST anterior), ICMSSN101/102
(Simples Nacional, com e sem crédito). IPI, PIS e COFINS no padrão "Aliq" (alíquota por
percentual). ISSQN para item de serviço.

**Fora do escopo, declarado no código**: ICMS-ST em suas variantes próprias (`ICMSPart`,
`ICMSST`), DIFAL (`ICMSUFDest`), `PISST`/`COFINSST`, imposto de importação (`II`).
Adicionar uma dessas exige primeiro o cálculo correspondente — o módulo só monta o que a
apuração sabe calcular.

**Exclusividade mútua**, com erro explícito quando violada:

- `CST` e `CSOSN` nunca coexistem — regime normal informa um, Simples Nacional o outro;
- `ISSQN` é incompatível com `ICMS`/`IPI` no mesmo item — mercadoria e serviço não se
  misturam no mesmo detalhe;
- o grupo **IBS/CBS entra sempre**, mercadoria ou serviço: a reforma tributária alcança
  os dois, e por isso não está condicionado à branch de ICMS.

Um erro real que o teste de conformidade contra o XSD pegou: o campo do município no
ISSQN é **`cMunFG`**, não `cMunFGISS` — nome que pareceria natural por analogia com
`cMunFGIBS`, mas não existe no leiaute.

## Grupos `transp` e `pag`

Implementados em `fiscal/documento/transporte.py` e `fiscal/documento/pagamento.py`.

**`transp`** — `modFrete` é obrigatório em **toda** NF-e, mesmo sem transporte a
relatar: `9` é "Sem Ocorrência de Transporte", e é o valor que emissão de serviço ou
nota sem frete deve usar. Cobertos: modalidade, transportador (CNPJ ou CPF, exclusivos
como em `dest`) e volumes. Fora do escopo: `retTransp` (retenção de ICMS sobre o frete)
e identificação de veículo (`veicTransp`/`reboque`/`vagao`/`balsa`).

**`pag`** — achado do XSD que vale registrar: `tPag` **não tem enumeração fixa** no
schema, é só `[0-9]{2}`. Os códigos válidos vêm de uma tabela externa publicada à parte
no Portal da NF-e, atualizada independente da versão do leiaute — `FORMAS_PAGAMENTO`
espelha essa tabela, mas por ser externa a uma emissão em produção cabe confirmá-la
antes de assumir completude.

A regra condicional que decide aceitação: o XSD documenta que **`vPag` só é dispensado
quando `tPag=90`** (sem pagamento) — inclusive pagamento "a prazo" ou parcial exige o
valor. Um erro real que a implementação corrigiu antes do commit: `if cartao:` tratava
`{}` (cartão com valores padrão) como ausente, porque dicionário vazio é falso em
Python — trocado por `is not None`.

## `transp` e `pag` são obrigatórios — sem valor padrão inventado

O XSD não marca `transp` nem `pag` com `minOccurs="0"`: os dois grupos são obrigatórios
mesmo quando não há nada de fato a relatar. `montar_infnfe` recusa (`NFeInvalida`)
quando faltam, em vez de preencher por conta própria — inventar `modFrete="9"` ou
`tPag="90"` silenciosamente seria decidir dado de negócio que não é do módulo. A
mensagem de erro orienta o valor mínimo (`montar_transp("9", ...)` /
`montar_pag([{"forma": "90", "valor": None}])`) para quem realmente não tem nada a
declarar.

## `montar_nfe` e `assinar_nfe` — a raiz e a assinatura

`montar_nfe` envolve `infNFe` na raiz `NFe`, aplicando o namespace do leiaute
(`http://www.portalfiscal.inf.br/nfe`). É neste nível, não dentro de `infNFe`, que a
assinatura entra como elemento **irmão** — a NF-e usa assinatura *enveloped*.

`assinar_nfe` é a costura entre três módulos que, isoladamente, não se conheciam:
`serializacao.py` (dict → XML, para o assinador calcular o digest), `assinatura.py`
(estrutura do envelope XMLDSig) e a porta `Assinador` (a criptografia, local ou
remota). Recebe a árvore `NFe` já com namespace — assinar antes disso produziria um
digest que não bate com o XML final, porque o `xmlns` faz parte do que é canonicalizado.

Com isso a montagem da NF-e está completa do lado da estrutura do documento. O que
falta para emitir de fato é o adaptador de transporte.

## `ativar_contingencia_svc` — `dhCont`/`xJust` e a chave que muda

Contingência SVC-AN/SVC-RS é exclusiva de NF-e (modelo 55) — ver
`docs/transporte-nativo-sefaz.md` para o porquê e para a tabela de endpoints. Do lado do
documento, entrar em contingência muda três coisas no grupo `ide` — `tpEmis` (de `"1"`
para `"6"`/`"7"`), e dois campos novos que só aparecem quando `tpEmis != "1"`: `dhCont`
(quando a contingência começou) e `xJust` (motivo, 15 a 256 caracteres — mesmo tipo/
limite do `xJust` de cancelamento em `evento.py`). Confirmado no construtor de
referência que os dois vêm por último no grupo, depois de `verProc`, não logo após
`tpEmis`.

Como `tpEmis` é uma das 44 posições da chave de acesso, mudar de emissão normal para
contingência **muda a chave inteira** — o documento com a chave antiga deixa de valer, e
precisa ser regravado com a nova (mesmo aviso que a fonte de referência faz).
`ativar_contingencia_svc(identificacao, justificativa, desde=None)` devolve uma nova
`Identificacao` (a classe é imutável — a original não muda) já com `tipo_emissao`
resolvido pela UF do emitente via `UF_CONTINGENCIA_SVC` (não é escolha do chamador,
evita divergir do que a SEFAZ realmente aceita para aquele estado); o chamador então
remonta com `montar_infnfe` e assina de novo com `assinar_nfe`.

Não implementado: a orquestração que decide *quando* entrar em contingência (detectar
timeout/indisponibilidade da SEFAZ, ativar, e depois voltar ao normal) — isso é
responsabilidade da camada de negócio, este módulo só garante que o documento fica
estruturalmente correto quando alguém decide entrar em contingência.

## Ainda não montados

- `enderEmit` e `enderDest` são repassados como vieram, sem validação de conteúdo;
- `NFref` (documento referenciado), necessário em nota de devolução e complementar.

## Fontes

- `leiauteNFe_v4.00.xsd` — Pacote de Liberação 010e_v1.02, Portal Nacional da NF-e.
- NT 2019.001 — regra de validação B03-10 (rejeição 897).
- `nfephp-org/sped-nfe`, `docs/Contingency.md` (regras de contingência, `dhCont`/`xJust`
  obrigatórios quando `tpEmis != 1`) e `src/Traits/TraitTagIde.php` (ordem dos elementos
  no grupo `ide`, confirmando `dhCont`/`xJust` como os dois últimos) — consultados em
  2026-08-29.
