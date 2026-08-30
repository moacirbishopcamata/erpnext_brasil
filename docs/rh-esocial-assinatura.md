# eSocial: assinatura digital — SHA-256, não SHA-1

Continuação da camada de transporte, depois de `docs/rh-esocial-retorno.md`.
Resolve a pergunta que `docs/rh-esocial-s1200.md` tinha deixado em aberto: **não**,
`fiscal/documento/assinador_local.py` (o assinador da NF-e) não é diretamente
reaproveitável para o eSocial — o hash muda.

## O que é igual, o que é diferente

Comparado ao perfil XMLDSig da NF-e (`fiscal/documento/assinatura.py`), confirmado
contra uma fonte especializada em assinatura de eSocial
(`suporte.quarta.com.br/eSocial/AssinaturaXml.htm`):

| Aspecto | NF-e | eSocial |
|---|---|---|
| Canonicalização | C14N 1.0, não exclusive | **Igual** — C14N 1.0, não exclusive |
| Digest | SHA-1 (`.../xmldsig#sha1`) | **SHA-256** (`.../xmlenc#sha256`) |
| Assinatura | RSA-SHA1 (`.../xmldsig#rsa-sha1`) | **RSA-SHA256** (`.../xmldsig-more#rsa-sha256`) |
| Transformação enveloped | `.../xmldsig#enveloped-signature` | **Igual** |
| Namespace dos algoritmos | `xmldsig#` para tudo | `xmldsig-more#`/`xmlenc#` — não é só trocar o sufixo |

A canonicalização — a parte historicamente mais cara de implementar (a doc do módulo
da NF-e lembra que foi aí que a localização anterior do ERPNext morreu, em 2005, por
falta de uma biblioteca que fizesse C14N) — é **idêntica** entre os dois perfis.
Isso significa que a maior parte do trabalho pesado de `assinador_local.py`
(`lxml.etree.tostring(..., method="c14n", exclusive=False)`) se aplica sem qualquer
ajuste; só o hash muda.

## Por que uma classe nova, não um parâmetro na classe da NF-e

`AssinadorLocal` (NF-e) tem `hashes.SHA1()` cravado, documentado como perfil fechado
e usado em produção fiscal — generalizá-la para aceitar outro hash arriscaria
regressão silenciosa numa classe já testada. `AssinadorLocalEsocial` é uma classe
irmã com a mesma estrutura, mesmo raciocínio já aplicado a
`esocial_lote.IdeEmpregadorLote` não reaproveitar `esocial_s1200.IdeEmpregador`
quando o XSD é realmente outro (virtude 1 de Yegor Bugayenko: o nome/tipo precisa
continuar descrevendo o que o objeto realmente é).

## O que é reaproveitado, e o que não é

| Peça | Fonte | Reaproveitada? |
|---|---|---|
| `carregar_certificado` (abrir PKCS#12, checar validade) | `assinador_local.py` | **Sim** — não depende de qual hash assina depois |
| `para_xml` (serialização dict→XML) | `fiscal/documento/serializacao.py` | **Sim** — genérica, não específica da NF-e apesar de onde mora |
| `MaterialAssinatura`/`montar_signed_info`/`AssinaturaInvalida` | `fiscal/documento/assinatura.py` | **Não** — `MaterialAssinatura` da NF-e documenta "SHA-1" no docstring de cada campo; reaproveitá-la deixaria a documentação mentindo sobre o próprio dado que carrega |

`folha/esocial_assinatura.py` define seu próprio `MaterialAssinatura`,
`montar_signed_info`, `montar_signature`, `Assinador` (Protocol) — mesma forma,
constantes de algoritmo diferentes, documentação honesta sobre qual hash cada campo
carrega.

## Prova real, não só estrutura: a assinatura verifica com SHA-256, falha com SHA-1

`tests/test_assinador_esocial.py` (mesmo padrão de `test_assinador_local.py`: gera um
certificado autoassinado em memória, sem depender de A1 real) prova o ponto central
da divergência de um jeito que a estrutura sozinha não provaria: a assinatura
produzida **verifica** com a chave pública usando SHA-256, e **falha**
(`InvalidSignature`) quando verificada com SHA-1 — o mesmo hash que a NF-e usa. Não é
só "o código diz SHA-256 em algum lugar"; é "a assinatura matematicamente exige
SHA-256, tentar validar com SHA-1 é rejeitado".

## Pegadinha registrada para quando a serialização completa existir

A mesma fonte adverte que o XML do eSocial deve conter **apenas** o namespace do
próprio evento no atributo `xmlns` — atributos `xsi`/`xsd` soltos no elemento raiz
produzem rejeição ("Assinatura do evento inválida"), mesmo com assinatura
tecnicamente correta. Não é responsabilidade destes módulos (que só assinam um
elemento já serializado), mas fica registrado para quem for montar a serialização
completa de um evento S-1200.

## O que ainda falta

- **Serialização XML completa de um evento S-1200** a partir dos dataclasses de
  `esocial_s1200.py` — hoje a assinatura recebe XML já pronto como `bytes`, não o
  produz a partir da árvore de negócio.
- **Envio HTTP de verdade** — o `POST` SOAP com certificado, equivalente ao `_enviar`
  de `integracao/autorizacao_sefaz.py` da NF-e.
- **Certificado A1 real** — os testes provam o mecanismo com certificado
  autoassinado; a aceitação por um certificado emitido por autoridade certificadora
  real não foi (nem poderia ser, sem bench e sem certificado de teste do eSocial)
  verificada nesta sessão.

## Arquivos

- `folha/esocial_assinatura.py` — estrutura pura do envelope `Signature` (SHA-256).
- `integracao/assinador_esocial.py` — `AssinadorLocalEsocial`, a criptografia de
  verdade (reaproveitando `carregar_certificado` da NF-e).

## Fontes

- `fiscal/documento/assinatura.py`/`assinador_local.py` — o perfil da NF-e, usado
  como base de comparação (já verificado em sessões anteriores).
- `suporte.quarta.com.br/eSocial/AssinaturaXml.htm` — fonte especializada em
  assinatura de eSocial, usada para os URIs exatos de `SignatureMethod`/
  `DigestMethod` e a confirmação de que a canonicalização é C14N padrão, não
  exclusive. Não é o Manual de Orientação do Desenvolvedor oficial. Consultada em
  2026-08-30.
- Busca agregada anterior (`docs/rh-estado-esocial.md`) — já tinha indicado "o padrão
  de assinatura do eSocial é SHA256", agora confirmado com URIs exatos e prova
  criptográfica.
