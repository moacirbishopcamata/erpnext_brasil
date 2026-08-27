# Transmissão de documento fiscal: opções e fronteiras

Nota de arquitetura para a frente ainda não implementada (NF-e, NFC-e, NFS-e, CT-e,
MDF-e). Registra o que foi apurado para que a decisão não seja retomada do zero.

## O erro a não repetir

Os dois projetos brasileiros de localização do ERPNext que chegaram a existir morreram,
e um deles morreu de forma instrutiva: o histórico de commits mostra trinta commits em
quatro dias, terminando em `feat: adiciona API debug_xml para investigar canonicalização`
— ou seja, congelou **dentro** da depuração da canonicalização C14N da assinatura, que é
a parte mais difícil e a que decide se a SEFAZ aceita a nota.

A conclusão não é "assinar localmente é impossível". É que **o transporte não pode ser o
acoplamento do sistema**. Quem amarra o documento fiscal a um transporte específico
aposta o projeto inteiro naquele transporte funcionar.

## A porta

O DocType de Documento Fiscal conversa com uma **interface**, nunca com um fornecedor.
Operações mínimas: transmitir, consultar situação, cancelar, emitir carta de correção,
inutilizar faixa, e obter a representação impressa.

O agregado é dono do **estado** (rascunho → autorizado → cancelado → denegado) e do
mapeamento ERPNext → leiaute. O adaptador é dono apenas do protocolo. A costura crítica
— e é onde bug silencioso mora — é o retorno do protocolo de autorização: se ele não
persistir, existe nota autorizada no fisco e rascunho no sistema.

## Opção A — ACBrLib (local)

Biblioteca nativa (`.dll` / `.so`), LGPL. Faz tudo na sua infraestrutura: assinatura com
certificado A1, webservices da SEFAZ, DANFE.

Contrato apurado em `Projeto-ACBr-Oficial/ACBrLib-Nodejs` (que é FFI via koffi, sem
lógica fiscal própria — a mesma ABI C vale para qualquer linguagem):

- ciclo de vida `inicializar(configPath, chaveCrypt)` / `finalizar()`;
- configuração por sessão/chave: `configLer`, `configGravar`, `configLerValor(sessao, chave)`;
- retorno por **buffer dimensionado pelo chamador** (daí `ACBrBuffer` e `TAMANHO_PADRAO`):
  função devolve status inteiro e escreve em `char*` com tamanho de entrada/saída;
- classes concretas com sufixo **MT** (multi-thread) — são os binários exigidos;
- pacotes por documento: NFe, NFSe, CTe, MDFe, REINF, CEP, PIX.

Em Python o equivalente ao koffi é `ctypes`, da biblioteca padrão — nenhuma dependência
nova.

### Fronteira de licença (importa, e é precisa)

- **Pode**: carregar dinamicamente a `.so`/`.dll` a partir deste app MIT. É exatamente o
  uso que a LGPL permite, e não contamina nada.
- **Pode**: ler o wrapper Node para saber *quais* operações existem e como o ciclo de
  vida e o protocolo de buffer funcionam. Isso é informação de interoperabilidade —
  fato, não expressão.
- **Não pode**: transliterar o TypeScript dele para Python e distribuir como MIT. Aí é
  obra derivada, e o resultado herda LGPL-2.1.

Base legítima para escrever o binding: os **demos oficiais em Python** do próprio ACBr
(SVN do projeto, `Projetos/ACBrLib/Demos/`) e o manual em `acbr.sourceforge.io/ACBrLib`.
Existe ainda `base4sistemas/acbrlib-python` (Apache-2.0, portanto reutilizável sem
contaminação), útil como referência de desenho — mas **parado desde novembro de 2021**,
então não serve como dependência.

## Opção B — ACBr API (HTTP)

Serviço em nuvem. Dissolve de uma vez a questão de licença, o certificado no servidor e
a compilação nativa.

Apurado da especificação (`acbrapi-sdk-net/api/openapi.yaml`, 4 MB, OpenAPI 3.0.1):

- **ACBr API v3.1.8**;
- autenticação **OAuth 2.0 `client_credentials`** via Keycloak, em
  `https://auth.acbr.api.br/realms/ACBrAPI/protocol/openid-connect/token`, com escopos
  por módulo (`empresa`, `nfe`, `nfse`, …);
- dois ambientes: `https://prod.acbr.api.br` e **`https://hom.acbr.api.br`** — a
  homologação existe, o que é condição para testar sem emitir documento real;
- **179 endpoints, 221 operações**, em 8 módulos: Cep, Cnpj, Conta, Email, Geral,
  Documentos Fiscais, Distribuição DF-e e Auxiliares;
- cobre **emissão e entrada no mesmo provedor**: além de `/nfe`, há `/distribuicao/nfe`
  com documentos, XML, PDF, manifestações e notas sem manifestação. É exatamente o que
  o app da Intelligence8 teve de construir sob medida.

### Não portar SDK gerado

Os SDKs publicados (`-net`, `-python`, `-node`, `-php`, `-delphi`) **são gerados** da
mesma especificação pelo OpenAPI Generator 6.5.0 — o repositório Python tem o diretório
`.openapi-generator` que comprova. Traduzir o C# para Python à mão seria manter
manualmente uma tradução de código de máquina, que é regerado a cada versão da API.
Se precisar de cliente gerado, gera-se da `openapi.yaml`; não se traduz de outro SDK.

**Para este app, porém, provavelmente nenhum dos dois.** 179 endpoints são superfície
demais: o ERPNext precisa de algo entre oito e doze operações (emitir, consultar,
cancelar, carta de correção, inutilizar, baixar XML e PDF, e do lado de entrada a
distribuição DF-e e a manifestação). Um adaptador fino sobre `requests` — que o Frappe
já traz — resolve, sem dependência nova, sem acoplar a uma versão de gerador, e
testável com respostas gravadas.

Ressalva que permanece: o SDK Python oficial foi criado em julho de 2026 e **não declara
LICENSE**. Como a recomendação é não depender dele, a ressalva deixa de ser bloqueante —
mas vale abrir issue pedindo a licença de qualquer forma.

## Opção C — Python nativo

Terceiro caminho, e o que dispensa binário nativo e serviço externo: implementar em
Python puro, usando bibliotecas maduras que já existem.

### Portar o ACBr não é o caminho

A pergunta "não dá para portar o ACBr para Python?" tem três respostas, porque são três
códigos diferentes:

**Os wrappers (C#, Node, Delphi) — portar é inútil.** São cascas finas de FFI sobre a ABI
C: o `acbrlib-base-node` inteiro depende de `koffi` e não contém lógica fiscal nenhuma.
O contrato é a ABI, não o wrapper. Um binding Python se escreve com `ctypes` a partir da
mesma ABI, sem olhar para o código C#.

**O núcleo (Object Pascal) — portar é grande, derivado e redundante.** É onde mora a
lógica de verdade: escrita e leitura de XML de todas as versões de layout, clientes SOAP
dos webservices de cada UF, contingência, DANFE, tratamento de certificado. Traduzir isso
cria obra derivada (o ACBr é LGPL) e levaria o resultado a herdar LGPL.

**O conhecimento fiscal — esse sim se aproveita, e não é código.** Qual endpoint de qual
UF, qual validação a SEFAZ aplica, qual peculiaridade de layout: são fatos, não expressão,
e consultar o ACBr como referência para isso é legítimo e recomendável.

### O que matou o projeto anterior é fácil em Python

A localização brasileira do ERPNext que morreu congelou depurando a **canonicalização C14N
da assinatura**. Em Pascal, em 2005, isso era trabalho pesado. Em Python é biblioteca:

| Necessidade | Biblioteca |
|---|---|
| Canonicalização C14N | `lxml` (nativo) |
| Assinatura XMLDSig | `signxml` |
| Certificado A1 (.pfx / PKCS#12) | `cryptography` |
| SOAP / HTTP | `zeep` ou `requests` |

A parte que inviabilizou a tentativa anterior é, hoje, a parte resolvida.

### E já existe implementação nativa

| Projeto | Estrelas | Última atualização | Licença |
|---|---|---|---|
| [PyNFe](https://github.com/TadaSoftware/PyNFe) | 589 | fevereiro de 2026 | LGPL |
| [PyTrustNFe](https://github.com/danimaribeiro/PyTrustNFe) | 181 | junho de 2024 | **AGPL-3.0** |

**PyNFe** é a opção séria: mantida, com adoção real (227 forks) e LGPL — importá-la de um
app MIT é o uso que a licença permite, do mesmo modo que carregar a `.so` do ACBrLib.

**PyTrustNFe é AGPL-3.0**, licença fortemente viral que alcança até uso em rede. Para um
app que se quer reutilizável, é problema de adoção sério — vale conhecer o código, não
depender dele.

## Decisão: Python nativo

**Escolhida a opção C.** A emissão é implementada em Python nativo, com `lxml` e
`cryptography` — as duas já são dependências do frappe, então não há nada novo a instalar
num bench.

`signxml` foi dispensado pelo mesmo critério que dispensou `openpyxl` na leitura das
tabelas oficiais: o perfil da NF-e é estreito o bastante para não justificar mais uma
dependência num bench compartilhado por vários apps.

Isso **não fecha** as outras portas. `TransporteFiscal` continua sendo a interface, e um
adaptador de ACBrLib ou de ACBr API pode conviver com o nativo — a escolha segue
reversível, que é a razão de a porta existir.

### Como ficou dividido

| Camada | Onde | Depende de |
|---|---|---|
| Estrutura do envelope XMLDSig | `fiscal/documento/assinatura.py` | nada |
| Serialização dict → XML | `fiscal/documento/serializacao.py` | nada |
| Criptografia (C14N, digest, RSA) | `integracao/assinador_local.py` | `lxml`, `cryptography` |

A porta `Assinador` tem **uma operação**. Quem assina não precisa saber montar XML, e
quem monta XML não precisa saber de chave privada. Os imports das bibliotecas ficam
**dentro das funções**, para que a suíte verifique a estrutura da assinatura sem exigir
`lxml` instalado.

### Detalhes que decidem aceitação

- **SHA-1, não SHA-256.** Obsoleto em geral, mas é o que o layout manda; trocar gera
  rejeição.
- **C14N 1.0 sem comentários**, não exclusive.
- O que se assina é o **`SignedInfo` canonicalizado**, não o documento.
- O serializador emite atributos já na **forma canônica** — aspas duplas com `&quot;`, e
  não a troca de delimitador que `quoteattr` faria. É XML válido nos dois casos, mas sair
  canônico evita depender de a normalização acontecer depois.
- Certificado é validado na **abertura**: vencido produz assinatura tecnicamente correta e
  documento rejeitado, e descobrir na SEFAZ é pior que descobrir no upload.

## Como escolher

Não é "melhor" e "pior", é onde se quer o custo:

| | ACBrLib local | ACBr API |
|---|---|---|
| Custo por documento | nenhum | por uso |
| Certificado A1 | no seu servidor | delegado |
| Binário nativo por plataforma | sim (e Alpine é problemático) | não |
| Contingência e indisponibilidade da SEFAZ | sua | do provedor |
| Ambiente de homologação | configurável na lib | `hom.acbr.api.br` |
| Entrada (DF-e, manifestação) | módulo à parte | mesmo provedor |
| Licença | LGPL, com a fronteira acima | SDK sem LICENSE (evitável) |
| Como integrar | binding `ctypes` próprio | adaptador sobre `requests` |

A porta existe justamente para que essa escolha seja adiável e reversível — e para que
uma empresa possa usar uma e outra empresa a outra, na mesma instalação.
