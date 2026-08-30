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

## O algoritmo — só emissão on-line, por ora

Implementado apenas o caso majoritário: **emissão on-line** (`tpEmis` diferente de `9`).
A emissão em contingência offline usa uma sequência diferente (dia da emissão, valor
total, hash do digest em vez do digest inteiro) — declarado como trabalho futuro, não
escondido (ver "Ainda por implementar" abaixo).

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

- **Emissão em contingência (`tpEmis = 9`)**: sequência diferente
  (`chave|versão|ambiente|dia|valor|digestHex|cscId`), não implementada.
- **Tabela de URL de consulta por UF** (`webConsultaNFCe`): cada UF tem seu próprio
  domínio de consulta pública da NFC-e, distinto dos webservices de autorização já
  mapeados em `autorizadores_sefaz.py`. Este módulo recebe a URL base já pronta de quem
  chama — levantar a tabela UF a UF é trabalho futuro, mesma disciplina de nunca inferir
  por padrão de nome usada para os autorizadores.
- **QR Code "versão 3" (NT 2025.001)**: atualização recente troca o esquema de
  contingência específico para assinatura criptográfica em vez de hash com CSC — fora do
  escopo desta primeira implementação, que cobre só a versão 2 vigente e majoritária.
- Diferenças de transporte específicas de NFC-e (alguns grupos usam autorizador de
  contingência — SVC-AN/SVC-RS — distinto do autorizador normal de NF-e) ainda não
  levantadas.

## Fonte

`nfephp-org/sped-nfe`, `src/Factories/QRCode.php` (método `get200`), e um exemplo real de
QR Code de produção publicado em fórum técnico — consultados em 2026-08-29. Portal
Nacional da NF-e inacessível às ferramentas de busca no momento da implementação.
