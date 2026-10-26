# NFS-e: levantamento de estado

O maior gap identificado em [tropicalizacao-por-area.md](tropicalizacao-por-area.md).
Dimensionamento antes de implementar, com as fontes verificadas e a decisão de escopo.

Levantado em 2026-09-06.

## ⚠️ O achado que muda o desenho

**Não existe "emitir NFS-e" no singular.** Existem dois caminhos incompatíveis, e qual deles
vale depende do **município do prestador**:

| Caminho | Quem usa | Protocolo | Documento |
|---|---|---|---|
| **Sefin Nacional** | MEI, e municípios que aderiram ao emissor nacional | REST/JSON + XML assinado | DPS → NFS-e |
| **Emissor municipal** | a maioria dos municípios, incluindo **Porto Velho** | SOAP, padrão ABRASF | RPS → NFS-e |

Escolher um e chamá-lo de "a NFS-e" seria o erro estrutural deste bloco.

### Porto Velho mantém emissor próprio — verificado

A prefeitura anunciou a integração ao Sistema Nacional, e a leitura apressada dessa notícia
levaria a implementar o caminho errado. O texto oficial da Semec diz o contrário:

> "empresas e prestadores de serviços, **exceto o Microempreendedor Individual (MEI)**,
> estabelecidos em Porto Velho **continuarão a emitir a NFS-e pelo Emissor Próprio do
> Município**"

O MEI usa o Emissor Nacional; todo o resto continua em `nfse.portovelho.ro.gov.br`, por
webservice próprio. O que muda a partir de **1º/01/2026** são **campos novos obrigatórios**
de IBS e CBS no leiaute municipal — a reforma tributária chegando à nota de serviço.

Para a jurisdição deste projeto (Rondônia, Porto Velho), portanto, o caminho que
importa primeiro é o **municipal**, não o nacional. E o municipal é o que tem **menos**
documentação pública padronizada.

## O que está verificado, e como

### Padrão nacional — XSD oficiais, lidos localmente

Baixados de `gov.br/nfse` (`NFSe-ESQUEMAS_XSD-v1.01-20260209.zip`) e lidos no disco, não em
resumo de busca:

- `DPS_v1.01.xsd`, `NFSe_v1.01.xsd`, `evento_v1.01.xsd`, `pedRegEvento_v1.01.xsd`
- `tiposComplexos_v1.01.xsd` (2708 linhas), `tiposSimples_v1.01.xsd` (1843 linhas)
- Namespace: `http://www.sped.fazenda.gov.br/nfse`

Da API (manual oficial `v1.2`, out/2025, também lido localmente):

- `POST /nfse` — recepção **síncrona** da DPS; devolve a NFS-e ou a rejeição
- `GET /nfse/{chaveAcesso}` — consulta por chave
- `GET|HEAD /dps/{id}` — recupera a chave a partir do identificador da DPS
- `POST /nfse/{chaveAcesso}/eventos` — API **genérica** de eventos
- `GET /parametros_municipais/{codigoMunicipio}/...` — alíquotas, regimes, retenções,
  benefícios

Duas diferenças de arquitetura em relação à NF-e, que valem registro:

1. **A emissão é síncrona.** Não há lote nem recibo a consultar depois — o `POST` devolve a
   nota. Toda a máquina de recibo assíncrono da NF-e não se aplica.
2. **A API de eventos é única e genérica.** Um `POST` para qualquer tipo de evento, com
   parte comum e parte específica em XML — diferente da NF-e, onde cada evento tem o seu
   serviço.

### O que já foi implementado

`fiscal/documento/identificador_nfse.py` — os identificadores da DPS (45 posições) e da
NFS-e (53), montagem e leitura, conferidos contra `TSIdDPS` e `TSIdNFSe`.

Foi a fatia escolhida para começar porque é **verificável em fonte primária, pura e base de
todo o resto**: sem identificador não há consulta, não há evento, não há referência.

## Achados do XSD que valem registro

### O identificador **não** é a chave da NF-e

| | NF-e | NFS-e |
|---|---|---|
| prefixo | `NFe` | `NFS` |
| dígitos | 44 | **50** |
| DV | módulo 11, documentado | **algoritmo não declarado no XSD** |

Reaproveitar o cálculo de DV da NF-e seria a analogia entre documentos irmãos que este
projeto já pagou caro para não repetir. Enquanto não houver fonte primária do algoritmo, o
módulo **exige** o DV de quem chama — e isso não atrapalha, porque **quem gera NFS-e é a
Sefin, não o contribuinte**: o identificador se remonta para conferir, não para inventar.

### Um `pattern` do XSD que nenhum validador estrito aceitaria

`TSSerieDPS` traz `pattern value="^0{0,4}\d{1,5}$"`. Em XML Schema, **`^` e `$` não são
âncoras** — a expressão já é implicitamente ancorada, e os dois viram **caracteres
literais**. Ao pé da letra, o padrão exigiria uma série escrita `^00001$`.

Não é convenção do arquivo: em 1843 linhas, é o **único** pattern com `^` — inclusive o
`TSNumDPS`, logo ao lado, é escrito sem âncora. Quase certamente expressão copiada de uma
linguagem de regex que usa âncoras.

O módulo aplica a intenção e registra a divergência, em vez de silenciá-la.

### O CPF tem regra de preenchimento declarada

A inscrição federal ocupa 14 posições nos dois identificadores, e o XSD diz como preencher
quando é CPF: *"CPF completar com 000 à esquerda"*. Não é zero-fill genérico — é regra
declarada, e por isso a conferência é do **tamanho por tipo** (11 para CPF, 14 para CNPJ), e
não um `rjust(14)` que aceitaria qualquer coisa curta.

### Um bug achado por teste de ciclo, não por leitura

A primeira versão do módulo recusava número começado em zero, fiel ao `[1-9][0-9]{0,14}` de
`TSNumDPS`. Só que `ler_identificador_dps` devolve os campos **como estão no identificador**
— preenchidos até a largura —, e **montar → ler → montar não fechava**: o segundo `montar`
recusava o que o `ler` acabara de produzir.

A leitura certa é que os zeros à esquerda enchem a **posição**, não fazem parte do número.
Nenhum teste de "chama e confere o retorno" acharia isso; o que achou foi o que percorreu o
ciclo inteiro e comparou.

## O que falta, dimensionado

Em ordem de dependência, não de tamanho:

1. **Decidir o caminho por município.** Um `Select` na `Company` — nacional ou municipal —
   ou uma tabela por município. Sem isso, o resto não tem para onde ir.
2. **Leiaute da DPS** (`TCInfDPS`, em `tiposComplexos_v1.01.xsd`): prestador, tomador,
   serviço, valores, tributação municipal e os campos novos de IBS/CBS. É o grosso do
   trabalho no caminho nacional, e o XSD está em mãos.
3. **Assinatura digital** — reaproveitável: `fiscal/documento/assinatura.py` e
   `integracao/assinador_local.py` já assinam NF-e e eSocial.
4. **Transporte REST** — **novo**. Todo o transporte deste app é SOAP com TLS mútuo
   (`TransporteSefaz`); a Sefin Nacional é REST/JSON. O certificado e o TLS mútuo se
   reaproveitam; o envelope, não.
5. **Caminho ABRASF** (o que Porto Velho usa) — SOAP, mas **outro** leiaute, e com variação
   entre municípios mesmo dentro do "padrão". Exige o manual de integração específico da
   prefeitura, que a Semec anunciou e que precisa ser obtido.
6. **Eventos** (`AnexoII`): cancelamento, substituição, manifestação do tomador.
7. **Tabelas oficiais**: `ANEXO_A` (municípios IBGE), `ANEXO_B` (NBS e lista de serviço
   nacional), `ANEXO_C` (INDOP IBS/CBS). São planilhas oficiais, ainda não incorporadas.

## Decisão de escopo

**Não implementar a emissão agora.** Os motivos:

- O caminho que a jurisdição deste projeto usa (Porto Velho, municipal/ABRASF) **depende de
  um manual que ainda não foi obtido** — e o próprio município anunciou que publicaria uma
  Nota Técnica com as orientações do novo leiaute.
- O caminho nacional está documentado e verificável, mas serviria hoje **só ao MEI** em
  Porto Velho — público que não usa ERP.
- Implementar o nacional "porque tem XSD" produziria código completo e sem usuário: o
  formato de gap que este projeto trata como pior que bug.

O que **sim** se faz enquanto isso, e já se fez: as peças **puras e comuns aos dois
caminhos** — identificadores, e depois as tabelas oficiais e os tipos do leiaute. Elas
valem qualquer que seja o caminho escolhido, e são verificáveis contra fonte primária hoje.

## Fontes

- **XSD oficiais**: `NFSe-ESQUEMAS_XSD-v1.01-20260209.zip`, `gov.br/nfse` → Documentação
  Técnica → Documentação Atual. Baixados e lidos localmente.
- **Manual dos Contribuintes — Emissor Público (API)**, v1.2, out/2025, `gov.br/nfse`.
- **Manual dos Municípios — APIs ADN**, v1.2, out/2025.
- **Semec/Prefeitura de Porto Velho** — nota sobre a integração ao Sistema Nacional e a
  manutenção do emissor próprio.
- Anexos oficiais **A** (municípios/países), **B** (NBS/lista de serviço), **C**
  (INDOP IBS/CBS), **I** (leiaute DPS/NFS-e), **II** (eventos) — identificados, ainda não
  incorporados.
