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

Confirmado que a `ide` do CT-e não carrega `toma3`/`toma4` no nível investigado aqui — o
tomador do serviço (quem paga o frete) precisa de investigação própria antes de implementar
(está dentro de `ide`, em profundidade ainda não lida linha a linha).

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

## O que ainda falta investigar antes de implementar

- Conteúdo de `ide` além do que já foi lido aqui — em especial o tomador (`toma3`/`toma4`).
- `infCarga`/`infDoc` a fundo — são a ponte de correlação com a NF-e transportada, que é
  exatamente o dado que o MDF-e precisa referenciar depois.
- `cteModalRodoviario_v4.00.xsd` — estrutura do modal rodoviário (veículo, motorista, RNTRC).
- Assinatura/chave de acesso do CT-e — hipótese de trabalho: mesmo algoritmo da NF-e (SHA-1,
  44 posições) por ser da mesma família de padrão (Ajuste SINIEF), **não confirmado ainda**.
- Autorizador/webservice por UF — provavelmente segue o mesmo SVRS/SVSP/próprio já mapeado em
  `docs/transporte-nativo-sefaz.md` para NF-e, mas CT-e pode ter ambiente próprio — não verificado.

## Nada implementado ainda

Este documento é só levantamento — nenhum código de CT-e existe em `erpnext_brasil/` além do que
já existia (nada). Não é uma frente iniciada, é uma frente **desbloqueada**: o obstáculo de
extração que impedia o levantamento foi contornado (baixar e usar grep local em vez de resumo de
página), então o próximo incremento de verdade (`fiscal/cte.py` com CFOP + `ICMSUFFim`, o
subconjunto mais próximo do que já existe para NF-e/DIFAL) pode começar sem reabrir essa
investigação.
