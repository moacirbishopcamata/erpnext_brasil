# eSocial: leitura da resposta de envio e de processamento de lote

Continuação da camada de transporte, depois de `docs/rh-esocial-lote.md` (o envelope
de envio). Aqui é a direção contrária: interpretar o que o eSocial devolve.

## Duas respostas, dois momentos

1. **`RetornoEnvioLoteEventos`** — resposta imediata ao enviar (`"recebi o lote, aqui
   está o protocolo"`). Confirma só que o lote chegou, não que cada evento foi aceito.
2. **`RetornoProcessamentoLote`** — consultado depois, com o `protocolo_envio` da
   primeira resposta, no endpoint `consultarLoteEventos`
   (`esocial_lote.endpoint`) — o resultado evento a evento.

Mesma separação de `fiscal/documento/resposta_sefaz.py` interpretar a resposta da
SEFAZ como dado puro: este módulo só lê a estrutura, não decide o que fazer com um
erro (reenviar, alertar, logar) — isso é responsabilidade de quem chama.

## O limite de 50 eventos, confirmado de dois jeitos agora

`docs/rh-esocial-lote.md` registrou que o envelope de **envio**
(`EnvioLoteEventos-v1_1_1.xsd`) declara `eventos`/`evento` como `unbounded` — o limite
de 50 ali é regra de negócio, não do schema. O XSD de **retorno**
(`RetornoProcessamentoLote-v1_3_0.xsd`), lido para este módulo, é diferente: declara
`retornoEventos/evento` com `maxOccurs="50"` — um limite estrutural de verdade, do
lado da resposta. As duas fontes concordam no número, uma sem confirmação estrutural
e outra com — reforça a regra de 50, mas não a torna confirmada pelo lado do envio.

## Códigos de `cdResposta`: cinco confirmados, não uma tabela completa

| Código | Significado | Categoria |
|---|---|---|
| 201 | Lote recebido com sucesso | `sucesso` |
| 202 | Lote recebido com advertências | `sucesso` (com ressalva) |
| 203 | Lote já recebido, ainda em fila de processamento | `pendente` |
| 301 | Erro no servidor do eSocial | nenhuma das duas |
| 401 | Lote incorreto — erro de preenchimento | nenhuma das duas |

O XSD não enumera valores de `cdResposta` (é `xs:int` livre) — os cinco acima vêm de
busca agregada, não do Manual de Orientação do Desenvolvedor lido diretamente nesta
rodada. `StatusRetorno.sucesso`/`.pendente` só reconhecem os códigos confirmados;
qualquer código fora da tabela não vira "sucesso" nem "pendente" por omissão — mesma
disciplina de `cnab400_retorno.foi_pago` nunca assumir um código não tabelado.

## `tem_erro` olha as ocorrências, não o código

Um lote pode ter `cdResposta=202` (sucesso com advertências) e ainda ter uma
`Ocorrencia` do tipo aviso — `StatusRetorno.tem_erro` só é `True` quando existe ao
menos uma ocorrência do **tipo 1 (erro)**, distinto de tipo 2 (aviso). Um status pode
ser "sucesso" e ainda ter avisos; os dois são informações independentes.

## Correção registrada: `RetornoEvento` não tem um `status` — e `eventos_com_erro` foi removida

Uma leitura mais específica do XSD (o complexType anônimo de `retornoEventos/evento`
em `RetornoProcessamentoLote-v1_3_0.xsd`) mostrou que o modelo original deste
incremento estava errado: `evento` só tem os atributos `Id`/`evtDupl` confirmados e
um filho `retornoEvento` (`TArquivoEsocial`, um `xs:any`) — o status/ocorrências de
processamento de cada evento fica **dentro** desse conteúdo opaco, num schema
próprio que não foi localizado nesta rodada (não é `sped-esocial/schemes/comunicacao/`,
nem apareceu em nenhuma pasta de primeiro nível óbvia do mesmo repositório).

`RetornoEvento` foi corrigido: em vez de um campo `status: StatusRetorno` inventado
por semelhança com o status do lote, guarda `xml_retorno: str` — o conteúdo cru, sem
interpretação, mesmo padrão de "quem chama entrega/recebe XML pronto" já usado em
`esocial_lote.EventoLote`. A função `eventos_com_erro` dependia diretamente do campo
removido e foi **removida**, não adaptada — mantê-la funcionando exigiria inventar
uma estrutura para `xml_retorno` sem fonte, pior que não ter a função.

## O que não está aqui

- **Reenvio automático** de eventos com erro, ou qualquer lógica de retry — decisão
  de quem chama, este módulo só classifica.
- **Parsing de XML real** para essas estruturas — os dataclasses recebem os campos já
  extraídos; a extração de um XML/SOAP real para estes campos ainda não foi escrita
  (mesma situação da assinatura/envio em si, ver `docs/rh-esocial-lote.md`).
- **Interpretação de `RetornoEvento.xml_retorno`** — o schema de onde mora o
  status/ocorrências de cada evento individual não foi localizado (ver correção
  acima); até achá-lo, esse conteúdo fica opaco.
- ~~Formato exato de `protocolo_envio` não confirmado~~ — resolvido em
  `docs/rh-esocial-consulta.md`: `A.B.` + 19 dígitos, confirmado no XSD de
  `ConsultaLoteEventos-v1_0_0.xsd`. `DadosRecepcaoLote` já valida o formato completo.

## Arquivos

- `folha/esocial_retorno.py` — `Ocorrencia`, `StatusRetorno`, `DadosRecepcaoLote`,
  `RetornoEnvioLote`, `RetornoEvento`, `RetornoProcessamentoLote`; camada pura, sem
  Frappe, sem rede, testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-esocial`,
  `schemes/comunicacao/v1_5_0/RetornoEnvioLoteEventos-v1_1_0.xsd` e
  `RetornoProcessamentoLote-v1_3_0.xsd` — XSDs literais usados para a estrutura.
  Mesma família do `nfephp-org/sped-nfe` já usada para a NF-e, não a fonte primária
  oficial. Consultado em 2026-08-30.
- Busca agregada — usada para os cinco códigos de `cdResposta` (201/202/203/301/401),
  não confirmados por leitura direta do Manual de Orientação do Desenvolvedor oficial
  nesta rodada.
