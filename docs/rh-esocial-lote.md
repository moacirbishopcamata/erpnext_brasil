# eSocial: envelope de lote de eventos e endpoints

Primeiro pedaço da "camada de transporte" do eSocial (`docs/rh-estado-esocial.md`
tinha deixado como fatia separada, depois de `docs/rh-esocial-s1200.md` cobrir a
árvore de negócio do evento). Modela só a estrutura do envelope
(`envioLoteEventos`) e a tabela de endpoints — **não** a assinatura XML nem o envio
HTTP de verdade.

## `ideEmpregador`/`ideTransmissor` do envelope não são o mesmo tipo do evento

Pegadinha confirmada ao ler o XSD do envelope (`EnvioLoteEventos-v1_1_1.xsd`): aqui
`tpInsc` é **enumerado** — só `1` (CNPJ) ou `2` (CPF) — diferente do `TEmpregador`
usado dentro do próprio S-1200 (`esocial_s1200.IdeEmpregador`), cujo XSD só exige um
dígito único sem enumerar valores válidos. Mesmo nome de campo, XSD diferente — por
isso `esocial_lote.py` define `IdeEmpregadorLote`/`IdeTransmissorLote` próprias, em
vez de reaproveitar as classes de `esocial_s1200.py`.

`ideTransmissor` pode ser uma pessoa/empresa diferente do empregador — ex. um
contador que centraliza o envio de eventos de vários clientes com o próprio
certificado.

## Endpoints: quatro combinações, uma assimetria real

| Serviço | Ambiente | Subdomínio |
|---|---|---|
| Enviar lote | Produção | `webservices.envio.esocial.gov.br` |
| Enviar lote | Produção Restrita | `webservices.producaorestrita.esocial.gov.br` |
| Consultar lote | Produção | `webservices.consulta.esocial.gov.br` |
| Consultar lote | Produção Restrita | `webservices.producaorestrita.esocial.gov.br` |

Em produção, cada serviço tem seu próprio subdomínio (`envio`/`consulta`); em produção
restrita, os dois serviços compartilham o mesmo host, só o caminho muda — assimetria
real da fonte (confirmada por busca agregada), não erro de transcrição.

## Limite de 50 eventos por lote: regra de negócio, não do XSD

O XSD do envelope declara `eventos`/`evento` com `maxOccurs="unbounded"` — sem limite
estrutural nenhum. O limite de 50 eventos por lote, citado amplamente por fontes de
mercado, **não foi confirmado por leitura direta do Manual de Orientação do
Desenvolvedor oficial** nesta rodada — `LoteEventos` o aplica como pós-condição
própria do módulo, documentado explicitamente como regra de negócio separada do
schema, não como algo que o XSD imporia sozinho.

## O que não está aqui

- **Assinatura XML** de cada evento antes de entrar no lote (`EventoLote.xml_assinado`
  é recebido já pronto — este módulo não assina nada). Não confirmado se
  `fiscal/documento/assinador_local.py` (já usado para NF-e) é diretamente
  reaproveitável para o eSocial — o formato de canonicalização pode divergir o
  bastante para exigir ajuste; decisão adiada para quando a assinatura for
  implementada de fato.
- **Envio HTTP de verdade** (POST SOAP, certificado, timeout) — mesmo padrão de
  `integracao/autorizacao_sefaz.py` para a NF-e, ainda não replicado aqui.
- **`RetornoEnvioLoteEventos`/`RetornoProcessamentoLote`** — a leitura da resposta do
  eSocial (protocolo, situação de cada evento do lote) não foi modelada.
- **O significado dos valores de `grupo`** — atributo obrigatório do envelope, só o
  formato (inteiro não negativo) é validado; a tabela de categorias de grupo de
  eventos não foi pesquisada.

## Arquivos

- `folha/esocial_lote.py` — `IdeEmpregadorLote`, `IdeTransmissorLote`, `EventoLote`,
  `LoteEventos`, `endpoint`; camada pura, sem Frappe, sem rede, testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-esocial`,
  `schemes/comunicacao/v1_5_0/EnvioLoteEventos-v1_1_1.xsd` — XSD literal do envelope
  de lote. Mesma família do `nfephp-org/sped-nfe` já usado para a NF-e neste projeto,
  não a fonte primária oficial. Consultado em 2026-08-30.
- Busca agregada — usada para os quatro endpoints (produção/produção restrita ×
  enviar/consultar) e para o limite de 50 eventos por lote (este último não
  confirmado por fonte oficial primária, registrado como tal).
