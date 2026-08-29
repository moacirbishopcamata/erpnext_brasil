# Transporte nativo — direto à SEFAZ

Referência da decisão de **não depender de ACBr, nem local nem SaaS**, e falar direto
com os webservices da SEFAZ. Decidido pelo usuário em 2026-08-24: *"precisamos mesmo do
ACBr? Podemos implementar nativo, do zero?"*

## Por que dá para ser 100% nativo

A parte difícil do transporte não é o protocolo — é a **canonicalização C14N e a
assinatura**, e essa parte já é nativa (`fiscal/documento/assinatura.py`). O que falta é:

- **SOAP** — um envelope fino em torno do XML já assinado. `serializacao.py` já produz
  o XML; o envelope SOAP é poucas linhas a mais, não uma tecnologia nova.
- **TLS mútuo** com o certificado A1 — o `requests` aceita certificado de cliente
  nativamente (`cert=(arquivo_cert, arquivo_chave)`).

Dado que a parte difícil já está resolvida, o incremento para completar o transporte é
pequeno perto do que já foi construído — não o salto que "falar direto com o governo"
sugere à primeira vista.

## A troca honesta

Com ACBr (local ou API), alguém absorve a operação de 27 endpoints estaduais
heterogêneos e a contingência (EPEC, SVC-AN, SVC-RS). Fazendo nativo, isso é
responsabilidade deste app. O trade-off é real; a decisão foi que vale pagá-lo, dado que
o resto do transporte já segue essa disciplina.

## A tabela de autorizadores

Implementada em `fiscal/documento/autorizadores_sefaz.py`, lida do Portal Nacional da
NF-e (`webServices.aspx`) em 2026-08-24 — nunca escrita de memória.

A maioria das UFs **não roda webservice próprio**:

| Grupo | UFs | Quantidade |
|---|---|---|
| Webservice próprio | AM, BA, GO, MG, MS, MT, PE, PR, RS, SP | 10 |
| **SVAN** (Ambiente Nacional) | MA | 1 |
| **SVRS** (Rio Grande do Sul) | AC, AL, AP, CE, DF, ES, PA, PB, PI, RJ, RN, **RO**, RR, SC, SE, TO | 16 |

**Rondônia (RO) usa o SVRS** — confirmado explicitamente na fonte. É a UF de prioridade
de verificação deste projeto (o negócio do usuário fica no Norte, em RO), mas a tabela
cobre as 27 UFs: o app continua genérico, RO só decide o que se testa primeiro contra a
fonte oficial.

### Homologação — confirmada nos 12 grupos

A página oficial lista só produção; a homologação foi levantada à parte, grupo a grupo
(nunca por inferência de padrão de host — cada grupo troca o nome de um jeito diferente:
SVRS insere um hífen, GO troca a palavra inteira, AM abrevia sem hífen), via a mesma
segunda fonte independente já usada para o resto da tabela (`nfephp-org/sped-nfe`), com
PR e SP checados numa terceira, direto na página oficial de cada estado. Os 12 grupos que
existem (10 próprios + SVAN + SVRS) têm homologação confirmada — não sobrou nenhum grupo
real para `endpoint(..., ambiente="homologacao")` recusar; a exceção
`NotImplementedError` continua existindo como guarda de código, não como lacuna atual.

### O que ainda não está confirmado, e por isso o código recusa

**`NfeConsultaCadastro` para 11 das 16 UFs do SVRS.** A fonte diz explicitamente que só
**AC, ES, RN, PB e SC** usam o CadConsultaCadastro do SVRS. Para as outras 11 —
**RO entre elas** — esse serviço específico não está confirmado por esta página, e
`endpoint()` devolve `None` em vez de assumir que seria o mesmo do SVRS. Não afeta a
emissão em si: `NfeConsultaCadastro` é consulta cadastral, não faz parte do fluxo de
autorização.

## O envelope SOAP — sem `nfeCabecMsg`

Implementado em `fiscal/documento/soap.py`. O achado que decidiu a forma final: duas
fontes técnicas divergiam sobre a necessidade de um `soap12:Header` com `nfeCabecMsg`
(`cUF` + `versaoDados`). A divergência só se resolveu no comentário datado do
código-fonte da própria biblioteca que documentava o header:

> *"will no longer exist in version 4.0 of the SEFAZ layout (...) valid only until
> 11/2017 after that date becomes OBSOLETE and if it is used it will cause
> communication failure."* — `nfephp-org/sped-nfe`, `Factories/Header.php`

O layout 4.00 — o que este app usa — **não leva header**. Só `soap12:Body >
nfeDadosMsg`, com o namespace `http://www.portalfiscal.inf.br/nfe/wsdl/<operação>`. A
operação de cada serviço (`OPERACAO_SOAP`) foi confirmada na mesma biblioteca, e não é
sempre igual ao nome do serviço na tabela de endpoints: `NfeConsultaProtocolo` (f
minúsculo, nome da tabela) usa a operação `NFeConsultaProtocolo4` (maiúscula, com
sufixo).

A extração da resposta (`extrair_resultado`) usa `lxml` de verdade, não regex sobre
XML — regex quebra silenciosamente diante de elemento aninhado com o mesmo nome do
wrapper, e a mensagem de erro nunca aponta a causa real.

Instalar `lxml`/`cryptography` de verdade neste ambiente (em vez de só testar com
duplo) já rendeu dois achados que um teste com duplo não pegaria: o bug do `lxml`
propagando `xmlns:soap` de ancestral para o elemento extraído (corrigido com
`etree.cleanup_namespaces`), e uma suíte nova para `AssinadorLocal`
(`test_assinador_local.py`, certificado autoassinado gerado em memória) que verifica a
assinatura com a **chave pública** — não só que a função devolveu algo.

## A armadilha dos dois `cStat`

Implementada em `fiscal/documento/resposta_sefaz.py`. A resposta de autorização carrega
**dois `cStat` em níveis diferentes**, e confundi-los é o erro mais fácil de cometer:

- `retEnviNFe/cStat` — status do **lote**. `104` é "Lote processado", e isso **não
  significa que a nota foi autorizada** — só que o lote terminou de ser processado.
- `retEnviNFe/protNFe/infProt/cStat` — status **da NF-e em si**. `100` é "Autorizado o
  uso da NF-e"; qualquer outro valor é rejeição.

Um código que só olhasse o `cStat` do lote relataria rejeição como sucesso sempre que o
lote tivesse sido processado — que é o caso comum. Há teste específico
(`test_lote_processado_e_nota_rejeitada`) travando exatamente esse cenário.

Quando o lote ainda não foi julgado (`cStat` diferente de `104`, ex. `103` "Lote
recebido com sucesso"), `protNFe` não vem na resposta — modelado como `protocolo=None`,
nunca como erro: é estado válido do fluxo (exige nova consulta via
`NFeConsultaProtocolo4`/`NFeRetAutorizacao4`), não falha de parsing.

## O adaptador `TransporteSefaz` — `transmitir`, `consultar`, `cancelar` e `corrigir` prontos

Implementado em `integracao/transporte_sefaz.py`. É *context manager*: o certificado A1
é carregado uma vez em memória (`cryptography`), mas o `requests` só aceita certificado
de cliente como **arquivo** — não há suporte a certificado em memória na biblioteca
padrão de SSL do Python. Os PEM são escritos num diretório temporário na entrada do
`with` e apagados na saída, nunca reescritos a cada requisição.

`transmitir` resolve o *polling* do lote assíncrono de verdade: quando a primeira
resposta vem `pendente` (`cStat` diferente de `104`), consulta de novo via
`NFeRetAutorizacao4`/`consReciNFe` com o `numero_recibo`, um número limitado de vezes
(`tentativas_consulta_recibo`, padrão 5) com intervalo entre tentativas — e **desiste
com erro explícito** (`TransporteIndisponivel`) em vez de entrar em loop infinito ou
declarar sucesso/rejeição sem a SEFAZ ter decidido.

### `cancelar` — o evento de cancelamento (110111)

A estrutura completa de `infEvento` não veio no pacote de leiaute principal — o esquema
de eventos é distribuído à parte. O bloqueio anterior (`NotImplementedError`) durou até
o pacote correto ser baixado do Portal Nacional da NF-e ("Esquemas XML NF-e/NFC-e -
Evento Cancelamento", 21/12/2018) e a ordem de `infEvento` ser lida direto de
`leiauteEventoCancNFe_v1.00.xsd`: `cOrgao, tpAmb, (CNPJ|CPF), chNFe, dhEvento, tpEvento,
nSeqEvento, verEvento, detEvento`. A montagem em si vive em `fiscal/documento/evento.py`
(camada pura, sem Frappe) — este adaptador só serializa, envelopa e envia.

Duas decisões de projeto valem registrar:

- **A porta `TransporteFiscal.cancelar` ganhou um parâmetro `protocolo`** que a primeira
  versão não previa. Só apareceu ao implementar o adaptador de verdade: o schema do
  evento de cancelamento exige `nProt` — a SEFAZ precisa saber *qual* autorização está
  sendo cancelada, não só qual chave. É uma mudança que quebra compatibilidade
  (propagada a todo implementador e duplo de teste), mas widenar a porta é melhor do que
  inventar um protocolo vazio ou reconsultar a SEFAZ dentro do adaptador para descobri-lo.
- **`cnpj_emitente` entrou no construtor de `TransporteSefaz`, não na porta.** O schema
  exige o CNPJ do "autor do evento" (`CNPJ` dentro de `infEvento`), mas esse dado é
  configuração estável do adaptador — quem está autenticado por aquele certificado A1 —
  e não muda a cada chamada como `protocolo`/`justificativa` mudam. Colocar na porta
  obrigaria todo `transmitir`/`consultar` a carregar um parâmetro que não usam.

A pegadinha do `@Id` (`"ID" + tpEvento + chave + nSeqEvento`, em que o `nSeqEvento`
*dentro do `Id`* leva zero à esquerda até 2 dígitos e o *elemento* `nSeqEvento` não leva)
está documentada com mais detalhe em `fiscal/documento/evento.py`, junto da leitura do
retorno (`interpretar_retorno_evento`): o `cStat` do lote (recepção do pedido) e o
`cStat` de `retEvento/infEvento` (se a SEFAZ de fato homologou) são dois números
distintos — mesma armadilha dos dois `cStat` da autorização, um nível abaixo.

**Correção: o evento precisa vir assinado.** A primeira versão de `cancelar` montava e
enviava o `evento` sem `Signature` — todo cancelamento real teria sido rejeitado pela
SEFAZ (`TEvento` exige `Signature` com cardinalidade 1-1, confirmado no XSD), e nenhum
teste pegava isso porque todos simulam a resposta SOAP, nenhum inspecionava o XML de
saída. Corrigido com `evento.assinar_evento` (mesmo padrão de `nfe.assinar_nfe`: assina
a árvore já com `@xmlns` aplicado, `Signature` como irmão de `infEvento`) e uma checagem
nova (`test_transporte_sefaz.TestCancelar.test_xml_enviado_esta_assinado`) que inspeciona
o corpo da requisição de verdade, não só a resposta simulada — a categoria de teste que
faltava.

**`eventos_sefaz.py`**: `cancelar`/`corrigir`/o envio de evento em si foram extraídos de
`transporte_sefaz.py` para este módulo novo só por tamanho de arquivo —
`test_arquitetura.py` limita módulo de integração a 320 linhas, e o adaptador já estava
no limite antes mesmo da assinatura entrar. Não é separação de responsabilidade nova, é
o mesmo transporte em dois arquivos; `TransporteSefaz` continua sendo o único ponto que
implementa `TransporteFiscal`.

### `corrigir` — a carta de correção (110110)

Mesma via de transporte do cancelamento (`NFeRecepcaoEvento4`) e o mesmo `infEvento` —
só `detEvento` muda: `xCorrecao` (texto livre, 15 a 1000 caracteres — teto diferente da
justificativa de cancelamento, que vai até 256) e `xCondUso`, um aviso legal fixo que o
XSD (`leiauteCCe_v1.00.xsd`) restringe a uma enumeração de duas variantes — não é campo
livre. O texto exato (`evento.XCONDUSO_CCE`) foi conferido caractere a caractere direto
no XSD, não copiado de blog ou biblioteca de terceiros.

`corrigir` não tem parâmetro `protocolo` — o schema da CC-e não pede o `nProt` da
autorização original, só a chave e o texto. E o retorno não deve alimentar
`aplicar_resposta`: uma CC-e homologada não muda o estado do `DocumentoFiscal` (ele
continua autorizado), só emenda o texto de um documento que já está autorizado.

**Por que não existe um único conjunto de `cStat` de sucesso para todo evento.** `135`
("Evento registrado e vinculado a NF-e") é o código genérico de qualquer evento
homologado via `NFeRecepcaoEvento4` — confirmado num exemplo real de CC-e homologada.
Cancelamento tem dois códigos adicionais só dele (`101`, `155`) que não existem para
carta de correção. `interpretar_retorno_evento` agora lê o `tpEvento` que a própria
resposta ecoa (confirmado no schema de resposta, `retEnvEvento`/`retEvento/infEvento`) e
escolhe o conjunto certo — usar um conjunto fixo teria dois jeitos de errar: aceitar
`101` como sucesso de uma CC-e (nunca vai aparecer, mas seria logicamente incorreto) ou
rejeitar um cancelamento genuinamente homologado com `101`/`155` por só reconhecer `135`.

## Ainda por implementar

- `NfeConsultaCadastro` para AM e SVAN em homologação (ausente na fonte, não confirmado
  em nenhuma outra) — inutilização já implementada, ver `docs/inutilizacao-nfe.md`.

## Fonte

Portal Nacional da NF-e, `webServices.aspx`, consultado em 2026-08-24. Esquema da carta
de correção (`leiauteCCe_v1.00.xsd`) confirmado via o pacote oficial em 2026-08-28,
corroborado por exemplo real de CC-e homologada e pelo código-fonte de referência do
`nfephp-org/sped-nfe`. Homologação dos 12 grupos (própria UF × 10 + SVAN + SVRS)
confirmada em 2026-08-29 pela mesma fonte, com PR e SP checados de novo contra a página
oficial de cada estado.
