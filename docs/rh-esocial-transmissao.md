# eSocial: transmissão HTTP de verdade (`enviarLoteEventos`/`consultarLoteEventos`)

Fecha o item registrado em `docs/rh-estado-esocial.md` desde a implementação do S-1200:
"o envio HTTP de verdade (`requests.post` com o certificado como client cert TLS, cabeçalhos
`Content-Type`/`SOAPAction`, equivalente ao `_enviar` de `integracao/autorizacao_sefaz.py` da
NF-e)". Espelha exatamente esse módulo, com as duas diferenças reais do eSocial (não
cosméticas): SOAP 1.1 em vez de 1.2 (cabeçalhos diferentes), e polling por `cdResposta=203`
em vez do `cStat` de lote da NF-e.

## Peças novas, em ordem de dependência

1. **`folha/esocial_lote.montar_xml_lote`** — faltava serializar `LoteEventos` em XML de
   verdade. Estrutura confirmada em `EnvioLoteEventos-v1_1_1.xsd`: `eSocial >
   envioLoteEventos[@grupo] > ideEmpregador, ideTransmissor, eventos > evento[@Id]{xs:any}`.
   Por concatenação de string (cada `EventoLote.xml_assinado` já é XML pronto — `para_xml` não
   tem como embutir um fragmento já serializado dentro de uma árvore de dicionário), mesma
   técnica de `esocial_soap.montar_envelope`.

2. **`folha/esocial_retorno_leitura.py`** (novo módulo) — `esocial_retorno.py` só modelava os
   dados já prontos (`RetornoEnvioLote`/`RetornoProcessamentoLote`); nada os produzia a partir
   do XML de verdade. `ler_retorno_envio_lote`/`ler_retorno_processamento_lote` fecham essa
   lacuna, mesmo papel de `resposta_sefaz.interpretar_autorizacao` para a NF-e. Estrutura
   confirmada campo a campo em `RetornoEnvioLoteEventos-v1_1_0.xsd` e
   `RetornoProcessamentoLote-v1_3_0.xsd` — os nomes já batiam com o que `esocial_retorno.py`
   tinha declarado, a leitura aqui é confirmação, não descoberta de campo novo.

3. **`integracao/contexto_esocial.ContextoEsocial`** — mesmo objeto de valor de
   `ContextoSefaz`, sem `uf` (o eSocial não tem UF, `esocial_lote.endpoint` já confirmou um
   único endpoint nacional por ambiente).

4. **`integracao/transmissao_esocial.py`** (novo módulo) — `_enviar`/`_resolver_pendencia`/
   `enviar_lote`/`consultar_lote`, espelhando `autorizacao_sefaz.py` função a função.

## Achado real: a ressalva de `esocial_soap.py` sobre o wrapper `<consulta>` está resolvida

`esocial_soap.py` tinha registrado "a estrutura XML exata do conteúdo [de `<consulta>`]...
não foi verificada nesta rodada — só o nome do elemento wrapper". Lendo
`ConsultaLoteEventos-v1_0_0.xsd` para montar `transmissao_esocial.py`, a resposta apareceu:
o conteúdo é `eSocial > consultaLoteEventos > protocoloEnvio` — a árvore inteira que
`esocial_consulta.montar_consulta_lote_eventos` já produzia, serializada e colocada dentro do
wrapper. A pegadinha adicional: essa consulta tem seu **próprio namespace**
(`.../schema/lote/eventos/envio/consulta/retornoProcessamento/v1_0_0`), diferente do
namespace da operação SOAP em si (`.../servicos/empregador/.../v1_0_0`) — sem declará-lo
explicitamente no `<eSocial>` interno, ele herdaria por engano o namespace da operação SOAP
ao ser aninhado dentro do `<consulta>`. Resolvido com `para_xml(..., namespace=...)`.

## `enviar_lote` nunca devolve `RetornoEnvioLote` como resultado final

Diferente de `autorizacao_sefaz.enviar_autorizacao`: a resposta imediata do eSocial ao
`enviarLoteEventos` não traz o resultado por evento — só confirma a recepção do lote e, em
sucesso, o `protocolo_envio` para consultar depois. Por isso `enviar_lote` sempre faz ao menos
uma segunda chamada (`consultarLoteEventos`) quando o envio foi aceito, e só então resolve o
polling se `cdResposta=203` ("já recebido em fila").

## O que continua fora de escopo

- **Autenticação de fato** ainda depende de um certificado A1 real e ambiente de
  homologação/produção — não testável neste ambiente, mesma limitação já registrada para a
  SEFAZ.
- **`dadosProcessamentoLote/versaoAplicativoProcessamentoLote`** não é capturado por
  `ler_retorno_processamento_lote` — campo de baixo valor (versão do aplicativo que
  processou), não parecia justificar mexer no dataclass já usado.
- **Schema de `retornoEvento` por dentro** continua opaco (`xml_retorno: str`) — mesma
  decisão já registrada em `esocial_retorno.RetornoEvento`, o schema de verdade não foi
  localizado.

## Fontes

`github.com/nfephp-org/sped-esocial`, `schemes/comunicacao/v1_5_0/` (`EnvioLoteEventos-v1_1_1.xsd`,
`RetornoEnvioLoteEventos-v1_1_0.xsd`, `RetornoProcessamentoLote-v1_3_0.xsd`,
`ConsultaLoteEventos-v1_0_0.xsd`) — não a fonte primária oficial, mesma advertência já
registrada para os outros módulos eSocial deste projeto.
