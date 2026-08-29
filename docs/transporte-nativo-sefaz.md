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

### O que não está confirmado, e por isso o código recusa

**Homologação.** A página lista só produção. Não há padrão confiável de host para
derivar homologação — alguns ambientes trocam `nfe.` por `homologacao.nfe.`, outros não
seguem esse padrão. `endpoint(..., ambiente="homologacao")` levanta
`NotImplementedError` em vez de arriscar uma URL errada; endpoints de homologação
precisam ser levantados UF a UF antes de uso.

**`NfeConsultaCadastro` para 11 das 16 UFs do SVRS.** A fonte diz explicitamente que só
**AC, ES, RN, PB e SC** usam o CadConsultaCadastro do SVRS. Para as outras 11 —
**RO entre elas** — esse serviço específico não está confirmado por esta página, e
`endpoint()` devolve `None` em vez de assumir que seria o mesmo do SVRS. Não afeta a
emissão em si: `NfeConsultaCadastro` é consulta cadastral, não faz parte do fluxo de
autorização.

## Ainda por implementar

- Envelope SOAP 1.2 (`nfeDadosMsg`) em torno do XML assinado — estrutura conhecida,
  ainda não escrita.
- Adaptador `TransporteFiscal` com TLS mútuo via certificado A1, usando `requests`.
- Tratamento de lote assíncrono (`NFeAutorizacao4` sincrono vs. `NFeRetAutorizacao4`
  para consulta de recibo, quando o lote excede o processamento síncrono).
- Endpoints de homologação, UF a UF, quando a fonte estiver confirmada.

## Fonte

Portal Nacional da NF-e, `webServices.aspx`, consultado em 2026-08-24.
