# Inutilização de faixa de numeração

## Por que é uma operação separada de cancelamento/CC-e

Cancelamento e carta de correção são **eventos** — dizem respeito a uma NF-e que já
existe, já foi transmitida e tem chave de acesso (`NFeRecepcaoEvento4`, grupo `TEvento`,
ver `fiscal/documento/evento.py` e `docs/transporte-nativo-sefaz.md`). Inutilização é
outra coisa: comunica que uma faixa de numeração **nunca chegou a virar documento** —
não existe chave de acesso porque a NF-e nunca foi emitida (webservice próprio,
`NfeInutilizacao4`, schema `inutNFe`/`TInutNFe`, sem lote, sem `idLote`, sem `infEvento`,
sem processamento assíncrono).

Por isso a porta `TransporteFiscal.inutilizar` tem uma assinatura sem nenhum parecido
estrutural com `cancelar`/`corrigir`: não recebe `chave_acesso`, recebe `ano`, `cnpj`,
`modelo`, `serie` e a faixa (`numero_inicial`/`numero_final`).

## A ordem confirmada de `infInut`

Lida direto de `leiauteInutNFe_v4.00.xsd` (pacote oficial da NF-e):

```
tpAmb, xServ, cUF, ano, CNPJ, mod, serie, nNFIni, nNFFin, xJust
```

`xServ` é fixo em `"INUTILIZAR"` — único valor que o XSD aceita. `xJust` vai de 15 a 255
caracteres (`TJust`) — **diferente** do teto de 256 do cancelamento e de 1000 da CC-e.
Cada operação tem seu próprio limite, sempre confirmado no schema específico, nunca
assumido por analogia com a anterior (a mesma disciplina que evitou reusar por engano o
limite errado quando `imposto_item.py` quase herdou um nome de campo por analogia falsa).

## A pegadinha do `@Id`

Padrão confirmado: `ID[0-9]{41}`. A regra, decompondo um `Id` real de exemplo
(`ID41140616149400017255001000000002000000002`):

```
"ID" + cUF(2) + ano(2) + CNPJ(14) + mod(2) + serie(3) + nNFIni(9) + nNFFin(9)
```

Cada campo numérico entra no `@Id` com zero à esquerda até a largura fixa — mesmo quando
o **elemento** correspondente no corpo do documento não leva zero nenhum (`TSerie` e
`TNF` são definidos sem zero à esquerda: `serie="1"`, não `serie="001"`). É a mesma
categoria de pegadinha do `nSeqEvento` do cancelamento/CC-e (duas representações do
mesmo número), só que aqui são três campos, não um.

## `cUF` (código IBGE) não é a sigla que o resto do app usa

`autorizadores_sefaz.py` e o construtor de `TransporteSefaz` trabalham com a **sigla**
(`"RO"`) para resolver o endpoint da UF. O layout de inutilização exige o **código IBGE**
(`"11"`) dentro do próprio corpo do documento — os dois representam a mesma UF, em
formatos diferentes, e não são intercambiáveis no XML. `inutilizacao.CODIGO_UF_POR_SIGLA`
existe só para essa conversão, com um teste dedicado (`TestCodigoUfPorSigla`) garantindo
que as duas tabelas (sigla→código e o conjunto de códigos válidos) nunca divergem — um
`cUF` errado não geraria erro de schema (ainda seria um código de 2 dígitos válido),
só uma inutilização registrada contra a UF errada.

## CNPJ alfanumérico: gap conhecido, deliberadamente não coberto

A Nota Técnica 2026.004 (v1.01, 08/06/2026) inclui o layout de `NFeInutilizacao` entre os
atualizados para aceitar CNPJ alfanumérico (IN RFB 2.229/2024) — confirmado em fontes
secundárias (blogs técnicos especializados), mas o XSD atualizado (`TCnpj` com o novo
padrão `[A-Z0-9]{12}[0-9]{2}`) **não foi localizado nem lido diretamente**: o pacote de
referência espelhado publicamente (`nfephp-org/sped-nfe`) ainda trazia, nesta data, só a
versão anterior (`TCnpj` = `[0-9]{14}`, puramente numérico). Adivinhar o novo padrão do
`@Id` sem confirmar no XSD real seria exatamente o erro que este app existe para evitar
— por isso `montar_inutilizacao` **recusa explicitamente** um CNPJ alfanumérico com uma
mensagem que aponta a causa, em vez de aceitar silenciosamente e arriscar um `@Id`
malformado que a SEFAZ rejeitaria sem dizer por quê. CNPJ numérico (a esmagadora maioria
dos emitentes até esgotar a faixa atual) continua funcionando sem restrição. Levantar essa
recusa exige primeiro ler o XSD real pós-NT-2026.004 — está listado em "Ainda por
implementar" abaixo, não é para "depois que alguém reclamar".

## Resposta: um único `cStat`, sem par lote/evento

Diferente de `transmitir` (dois níveis: lote e nota) e dos eventos (dois níveis: lote e
evento), a inutilização não é assíncrona nem passa por lote — uma requisição, uma
resposta, um único `cStat`. `102` ("Inutilização de número homologado") é o único código
de sucesso confirmado (`CODIGO_SUCESSO_INUTILIZACAO`); qualquer outro é tratado como não
homologado, sem categoria intermediária.

## Assinatura obrigatória, desde o início

`TInutNFe` exige `Signature` com cardinalidade 1-1, mesma exigência já corrigida para
cancelamento/CC-e (ver `docs/transporte-nativo-sefaz.md`, seção "o evento precisa vir
assinado"). Este módulo nasceu já assinando (`assinar_inutilizacao`, mesmo padrão de
`assinar_nfe`/`assinar_evento`) — o bug de esquecer a assinatura só se repete quando o
padrão não é seguido desde a primeira versão.

## Arquivos

- `fiscal/documento/inutilizacao.py` — montagem, assinatura e leitura de retorno; camada
  pura, sem Frappe, testável sem certificado nem rede.
- `integracao/inutilizacao_sefaz.py` — envio via `NfeInutilizacao4`; extraído do mesmo
  jeito que `eventos_sefaz.py`, só por limite de tamanho de arquivo da camada de
  integração (`test_arquitetura.py`), não por responsabilidade nova.
- `TransporteSefaz.inutilizar` — ponto de entrada público, converte sigla→código IBGE e
  delega ao módulo acima.

## Ainda por implementar

- Confirmar o XSD atualizado pós-NT-2026.004 e levantar a recusa de CNPJ alfanumérico.
- Endpoints de homologação para os 11 grupos que não são SVRS (mesma lacuna documentada
  em `transporte-nativo-sefaz.md`).

## Fonte

`leiauteInutNFe_v4.00.xsd` e `tiposBasico_v4.00.xsd` (pacote oficial da NF-e, espelhado
em `nfephp-org/sped-nfe`), tabela de códigos IBGE por UF, e cobertura da NT 2026.004 em
fontes secundárias — consultados em 2026-08-28.
