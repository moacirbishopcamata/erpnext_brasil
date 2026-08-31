# eSocial: envelope SOAP — SOAP 1.1, não 1.2 como a NF-e

Continuação da camada de transporte, depois de `docs/rh-esocial-montagem.md`. Fecha
a última peça puramente estrutural antes do envio HTTP de verdade: como embrulhar o
XML já montado/assinado no envelope que os webservices do eSocial esperam.

## Mais uma divergência real da NF-e, não suposição

`fiscal/documento/soap.py` (NF-e) monta SOAP **1.2**
(`http://www.w3.org/2003/05/soap-envelope`). Os WSDLs do eSocial
(`nfephp-org/sped-esocial`, `WsEnviarLoteEventos-v1_1_0.wsdl` e
`WsConsultarLoteEventos-v1_1_0.wsdl`) declaram `soap:binding
transport="http://schemas.xmlsoap.org/soap/http"` — **SOAP 1.1**
(`http://schemas.xmlsoap.org/soap/envelope/`), namespace diferente, não uma
variação do mesmo padrão. É a terceira vez neste bloco eSocial que uma peça
"parecida" com a da NF-e se revela genuinamente diferente ao ler a fonte de verdade
(depois do `tpInsc` enumerado do envelope de lote e do hash SHA-256 da assinatura).

## Um wrapper interno por serviço, confirmado no WSDL de cada um

| Serviço | Operação | Wrapper interno | Namespace |
|---|---|---|---|
| Enviar lote | `EnviarLoteEventos` | `<loteEventos>` | `.../lote/eventos/envio/v1_1_0` |
| Consultar lote | `ConsultarLoteEventos` | `<consulta>` | `.../lote/eventos/envio/consulta/retornoProcessamento/v1_1_0` |

Os dois WSDLs declaram o conteúdo do wrapper como `xs:any` — aceitam qualquer XML por
dentro. `montar_envelope` não valida esse conteúdo, só monta o envelope em volta —
mesmo "quem chama entrega XML pronto" já usado em `esocial_montagem.py` para o
`Signature`.

`soap_action(servico)` monta o cabeçalho HTTP `SOAPAction` exigido — confirmado nos
dois WSDLs como `<namespace>/Servico<Operação>/<Operação>`.

## O conteúdo de `<consulta>`: resolvido em seguida

O wrapper de `ConsultarLoteEventos` chama-se `consulta` — o conteúdo XML por dentro
dele (`ConsultaLoteEventos-v1_0_0.xsd`) foi lido no incremento seguinte
(`docs/rh-esocial-consulta.md`): é só `<eSocial><consultaLoteEventos><protocoloEnvio>
...</protocoloEnvio></consultaLoteEventos></eSocial>`, com o formato exato do
protocolo confirmado.

## Autenticação por certificado: TLS mútuo, não deste módulo

Os dois WSDLs declaram `RequireClientCertificate="true"` — o eSocial autentica pelo
TLS da conexão HTTP, apresentando o mesmo certificado A1 usado para assinar o XML
como certificado de cliente. Isso é responsabilidade de quem faz a chamada HTTP de
verdade (ainda não implementada), não deste módulo, que só monta o XML do envelope.

## `extrair_resultado`: mesma estratégia da NF-e, namespace diferente

Em vez de fixar o nome do elemento de resposta (que muda por operação —
`EnviarLoteEventosResult`, `ConsultarLoteEventosResult`), pega o primeiro (e único)
filho de `soap:Body`, e dentro dele o primeiro filho de novo — mesma estratégia de
`fiscal/documento/soap.extrair_resultado`, só trocando o namespace do SOAP 1.1.
Testado com `lxml` de verdade contra uma resposta sintética que reproduz a forma
real (elemento `*Result` embrulhando `<eSocial><retornoEnvioLoteEventos>...`).

## O que ainda falta

- **A chamada HTTP de verdade** (`requests.post` com o certificado como client cert
  TLS, cabeçalhos `Content-Type`/`SOAPAction`) — equivalente ao `_enviar` de
  `integracao/autorizacao_sefaz.py` da NF-e, ainda não escrito.
- **Polling do resultado** — o eSocial pode devolver `cdResposta=203` (em fila,
  `esocial_retorno.CODIGO_LOTE_JA_RECEBIDO_EM_FILA`) e exigir nova consulta depois,
  mesmo padrão de `_resolver_pendencia` já implementado para a NF-e — não replicado
  aqui ainda.

## Arquivos

- `folha/esocial_soap.py` — `montar_envelope`, `soap_action`, `extrair_resultado`;
  camada pura (SOAP 1.1), `lxml` só na extração (import tardio), testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-esocial`,
  `schemes/comunicacao/v1_5_0/WsEnviarLoteEventos-v1_1_0.wsdl` e
  `WsConsultarLoteEventos-v1_1_0.wsdl` — WSDLs literais usados para operação,
  namespace, `soapAction` e nome do wrapper interno de cada serviço. Mesma família
  do `nfephp-org/sped-nfe` já usada para a NF-e, não a fonte primária oficial.
  Consultado em 2026-08-30.
