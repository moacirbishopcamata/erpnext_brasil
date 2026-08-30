# NFC-e: QR Code (`infNFeSupl`)

## Por que a NFC-e precisa de algo que a NF-e não precisa

NFC-e (modelo 65) é a NF-e voltada a consumidor final — o suporte a `modelo="65"` já
existia em `fiscal/documento/nfe.py` (`MODELO_NFCE`) desde a montagem original do
documento. O que faltava é específico da NFC-e: o **QR Code** impresso no DANFCe, que
o consumidor escaneia para consultar a nota — não existe para NF-e (modelo 55).

`infNFeSupl` é informação suplementar: **não afeta a assinatura digital**. Por isso
entra na árvore depois de assinar `infNFe`, como grupo irmão entre `</infNFe>` e
`<Signature>` — a `Reference` da assinatura aponta só para `infNFe`, nunca para
`infNFeSupl`.

## O algoritmo — on-line e contingência offline

Cobertos os dois casos: **emissão on-line** (`tpEmis` diferente de `9`, majoritário) e
**contingência offline** (`tpEmis = 9`, quando o emitente não consegue contato com a
SEFAZ no momento da venda).

Para o caso on-line:

```
sequência = "{chave}|{versão}|{ambiente}|{cscId}"
hash      = SHA-1(sequência + CSC), hexadecimal MAIÚSCULO
url final = "{base}?p={sequência}|{hash}"
```

**`versão` é o inteiro `"2"`, não `"2.00"`.** Confirmado em duas fontes independentes que
batem exatamente — importante registrar porque várias páginas na internet mostram
`"2.00"` por engano ou por descreverem uma versão diferente do layout:

1. **Código-fonte** de `nfephp-org/sped-nfe` (`src/Factories/QRCode.php`, `get200()`):
   `$ver = $versao / 100`, com `$versao = 200` → PHP faz divisão inteira quando o
   resultado é exato, dando `2`, não `2.0`/`"2.00"`.
2. **Um exemplo real publicado** de produção:
   `.../nfce/qrcode?p=28170800156225000131650110000151341562040824|2|1|1|DC6AE2C2B9A992BE59679AC365E29922DE6B7511`
   — o `2` logo após a chave é a versão; bate exatamente com o código-fonte.

**`cscId` entra sem zero à esquerda**, mesmo que o cadastro na SEFAZ mostre com zeros —
confirmado explicitamente por fonte separada ("identificador CSC... sem os zeros não
significativos") e visível no mesmo exemplo real (`|1|`, não `|000001|`).

**O CSC nunca aparece na URL** — só participa do cálculo do hash. É um segredo
compartilhado entre o contribuinte e a SEFAZ (como uma senha), não um dado público; expor
o valor do CSC na nota anularia a segurança que ele existe para dar.

Essa dupla verificação (código-fonte + exemplo real) foi necessária porque o Portal
Nacional da NF-e — a fonte primária — está inacessível às ferramentas de busca deste
projeto (mesmo obstáculo já registrado em `docs/inutilizacao-nfe.md`). Sem conseguir ler
o XSD/manual oficial diretamente, a segunda fonte independente é o que sustenta a
confiança na implementação — não uma fonte secundária isolada.

Para o caso de **contingência offline** (`tpEmis = 9`), a sequência muda — troca `cscId`
sozinho por dia da emissão, valor total e o digest, mantendo `cscId` no fim:

```
sequência = "{chave}|{versão}|{ambiente}|{dia}|{valor}|{digHex}|{cscId}"
hash      = SHA-1(sequência + CSC), hexadecimal MAIÚSCULO   (mesmo algoritmo)
```

Confirmado na mesma leitura do código-fonte (`get200()`, ramo `$tpEmis == 9`). A
pegadinha real está em `digHex`: **não** é o digest binário decodificado — é a string
**base64** do `DigestValue`, exatamente como aparece no XML assinado, com **cada
caractere ASCII** convertido para 2 dígitos hexadecimais
(`str2Hex`: `sprintf("%02x", ord($c))` por caractere, lido literalmente do PHP).
Decodificar o base64 antes de gerar o hex produz um `digHex` diferente, e o hash não bate
com o que a SEFAZ calcula — o tipo de detalhe que só aparece lendo código-fonte, não
prosa. `dia` tem 2 dígitos (`day:02d`) e `valor` tem sempre 2 casas decimais com ponto
(`Decimal` com `ROUND_HALF_UP`, nunca `float`).

## `infNFeSupl`: `qrCode` (CDATA) antes de `urlChave`

```xml
<infNFeSupl>
  <qrCode><![CDATA[https://.../nfce/qrcode?p=...]]></qrCode>
  <urlChave>https://.../consultaChave</urlChave>
</infNFeSupl>
```

`qrCode` precisa de no mínimo 100 caracteres, `urlChave` no mínimo 21 — abaixo disso não
é uma URL real, é sinal de algo montado errado antes de chegar em `montar_infnfesupl`.

**`qrCode` como CDATA, não texto XML-escapado.** A URL contém `&` (separador de query
string) que, fora de CDATA, precisaria virar `&amp;` — mudando o que está de fato escrito
ali. `serializacao.py` ganhou uma classe `Cdata` só para isso
(`Cdata(texto)` no lugar de um valor normal), com uma checagem que falha na construção se
o texto contiver `]]>` (encerraria a seção CDATA no meio) — falha aqui, não como rejeição
misteriosa da SEFAZ.

## `consulta_nfce.py` — URL de consulta por UF

`montar_qrcode_online` recebe a URL base já pronta (`url_base`) — não a deriva sozinho.
`fiscal/documento/consulta_nfce.py` (`url_qrcode(uf, ambiente)`) fecha essa lacuna para
as **27 UFs**, em produção e homologação: a página pública de consulta do QR Code
(`webConsultaNFCe`) é infraestrutura completamente diferente dos webservices SOAP de
autorização já mapeados em `autorizadores_sefaz.py` — cada UF mantém a própria, mesmo as
que delegam a autorização ao SVRS (RO autoriza via SVRS, mas consulta em
`nfce.sefin.ro.gov.br`, domínio próprio; não há como derivar uma tabela pela outra).

RO (prioridade de verificação) foi conferido em **duas fontes independentes**: a tabela
de configuração de `nfephp-org/sped-nfe` (já usada para os autorizadores de NF-e) e a
Cartilha de Orientações NFC-e da própria SEFIN-RO — bateram exatamente
(`http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp`). As demais 26 UFs vêm só da
primeira fonte, mesmo padrão de confiança já usado nos autorizadores (a tabela reproduziu
exatamente o que já estava confirmado antes, o que sustenta a correção do arquivo como
um todo).

`urlChave` (a consulta por chave — para RO, `http://www.nfce.sefin.ro.gov.br`, domínio e
caminho **diferentes** do QR Code) tem tabela própria em `consulta_nfce.URL_CHAVE_POR_UF`
(fonte: ENCAT), confirmada para 22 das 27 UFs em produção (mais Ceará só em
homologação); Goiás, Minas Gerais, Pernambuco e Santa Catarina não constam na fonte em
nenhum ambiente. `montar_infnfesupl` continua recebendo `url_consulta_chave` como
parâmetro — quem chama pode resolvê-lo via `consulta_nfce.url_chave(uf)` quando a UF
estiver confirmada, ou fornecer por fora quando não estiver.

## Onde `infNFeSupl` entra na árvore assinada

`anexar_infnfesupl` (não `montar_nfe`/`assinar_nfe`, que continuam agnósticos a
NFC-e) insere o grupo entre `infNFe` e `Signature` **depois** de `assinar_nfe` já ter
rodado — nunca antes, porque `infNFeSupl` não deve fazer parte do que foi assinado.

```python
nfe = montar_nfe(infnfe)
nfe_assinada = assinar_nfe(nfe, assinador)          # só para NFC-e:
grupo = montar_infnfesupl(qrcode_url, url_consulta)
nfe_completa = anexar_infnfesupl(nfe_assinada, grupo)
```

## Ainda por implementar

- ~~**`urlChave`** (consulta por chave, distinta do QR Code) só tem valor confirmado
  para RO~~ — **resolvido em 2026-08-30**: 22 das 27 UFs confirmadas em produção via
  ENCAT (mais CE só em homologação), ver `consulta_nfce.URL_CHAVE_POR_UF`/`url_chave`.
  Goiás, Minas Gerais, Pernambuco e Santa Catarina continuam sem confirmação — ausência
  real na fonte primária, não falta de busca.
- **QR Code "versão 3" (NT 2025.001)**: atualização recente troca o esquema de
  contingência específico para assinatura criptográfica em vez de hash com CSC — fora do
  escopo desta primeira implementação, que cobre só a versão 2 vigente e majoritária.
- ~~Diferenças de transporte específicas de NFC-e via autorizador de contingência
  (SVC-AN/SVC-RS)~~ — **investigado e descartado em 2026-08-29**: SVC-AN/SVC-RS são
  exclusivos de NF-e (modelo 55); NFC-e nunca usa SVC, sua contingência é sempre offline
  (`tpEmis=9`, já implementado neste módulo), exceto SP (SAT/EPEC-NFCe, fora de escopo).
  Confirmado em `nfephp-org/sped-nfe`'s `docs/Contingency.md`; ver
  `docs/transporte-nativo-sefaz.md` para a tabela SVC-AN/SVC-RS implementada (só para
  NF-e).

## Fonte

`nfephp-org/sped-nfe`, `src/Factories/QRCode.php` (método `get200`) e
`storage/wsnfe_4.00_mod65.xml` (tabela de URL de consulta por UF), um exemplo real de QR
Code de produção publicado em fórum técnico, e a Cartilha de Orientações NFC-e da
SEFIN-RO (segunda fonte, cross-verificação de RO) — consultados em 2026-08-29. Portal
Nacional da NF-e inacessível às ferramentas de busca no momento da implementação.
Tabela `urlChave` por UF: ENCAT, "URL por UF utilizada para consulta chave"
(`nfce.encat.org/desenvolvedor/url-por-uf-utilizada-para-consulta-chave/`) — consultado
em 2026-08-30.
