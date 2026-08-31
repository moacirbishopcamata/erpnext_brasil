# eSocial: serialização da árvore do S-1200 em XML

Continuação da fatia do S-1200, depois de `docs/rh-esocial-assinatura.md`. Fecha o
ciclo entre a árvore de negócio (`esocial_s1200.py`, dataclasses validados) e o XML
que precisa existir antes de qualquer assinatura ou envio.

## Reaproveita `para_xml`, não escreve outro serializador

`fiscal/documento/serializacao.para_xml` já resolve escaping, CDATA, listas viram
elementos repetidos, ordem de inserção preservada — é serialização dict→XML
genérica, não específica da NF-e, apesar de morar sob `fiscal/documento/`. Mesma
decisão de reaproveitamento já tomada em `integracao/assinador_esocial.py` para o
mesmo módulo. `montar_evt_remun` só produz a árvore de dicionário; quem chama decide
quando serializar de fato.

## Descoberta no processo: `IdeEvento` estava incompleto

Tentar montar a árvore inteira forçou uma pergunta que uma leitura só da lista de
campos não força: "por que `perApur` aceita 4 **ou** 7 caracteres?" A resposta —
`indApuracao` decide qual dos dois formatos vale — revelou que esse campo tinha
ficado de fora de `IdeEvento` desde o primeiro incremento do S-1200. Corrigido antes
deste módulo (`docs/rh-esocial-s1200.md` documenta a correção); registrado aqui como
exemplo de como montar o documento inteiro expõe gaps que testar campo a campo
isoladamente não expõe.

## O que este módulo não faz: assinar

A árvore que `montar_evt_remun` produz **não tem** `Signature`. A ordem correta,
ainda não implementada, é: (1) serializar a árvore sem assinatura, (2) assinar esses
bytes com `AssinadorLocalEsocial.assinar` (`docs/rh-esocial-assinatura.md`), usando
o `id_evento` do atributo `Id` de `evtRemun` como referência, (3) mesclar o
`Signature` resultante de `montar_signature` como **irmão** de `evtRemun` dentro do
mesmo dicionário `eSocial`, (4) serializar a árvore completa de novo, desta vez com
a assinatura dentro. Essa orquestração cabe na camada de integração (mistura
dataclasses puros com uma classe que usa `cryptography`), não neste módulo puro.

## Prova de bem-formação: `lxml` analisa o resultado de verdade

`tests/test_esocial_serializacao.py` não só confere substrings no XML gerado — um
teste alimenta o resultado num parser XML real (`lxml.etree.fromstring`) e confirma
que ele aceita sem lançar exceção, e que o elemento raiz é `eSocial`. Substring por
si só provaria "a tag apareceu"; o parser prova "isto é XML de verdade, não uma
string que parece XML".

## Grupos ainda não cobertos pela árvore de negócio

`montar_evt_remun` monta exatamente os grupos que `esocial_s1200.py` modela —
`ideEvento`, `ideEmpregador`, `ideTrabalhador` (com `infoComplem`), `dmDev` (com
`infoPerApur`/`ideEstabLot`/`remunPerApur`/`itensRemun`). Os grupos deliberadamente
fora de escopo lá (`infoMV`, `procJudTrab`, `infoPerAnt`/`ideADC`,
`infoSaudeColet`/`infoAgNocivo`) também estão fora daqui, pela mesma razão.

## O `Id` de `evtRemun` não é gerado por este módulo

`docs/rh-estado-esocial.md` já tinha citado que o `Id` do evento tem 36 caracteres
com posições fixas (tipo, CNPJ/CPF do empregador, timestamp), análogo em espírito ao
`Id` da NF-e — mas o formato exato não foi verificado o bastante para implementar
`montar_evt_remun` gerando-o sozinho. `id_evento` é recebido pronto, mesmo padrão de
"caller decide" já usado para código de rubrica, `campo_livre` do boleto, etc.

## Arquivos

- `folha/esocial_serializacao.py` — `montar_evt_remun`, `NAMESPACE_EVT_REMUN`;
  camada pura, sem Frappe, sem criptografia, testável sem bench.

## Fontes

- `fiscal/documento/serializacao.py` — reaproveitado diretamente, não uma nova fonte
  externa.
- `NAMESPACE_EVT_REMUN` — citado literalmente por um resultado de busca
  (`"http://www.esocial.gov.br/schema/evt/evtRemun/v_S_01_03_00:TS_qtdRubr"`, o
  namespace de um tipo do XSD do evento) — não uma leitura direta da declaração
  `targetNamespace` do XSD oficial. Consultado em 2026-08-30.
