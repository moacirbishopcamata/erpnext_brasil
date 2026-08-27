# Montagem do documento NF-e

Referência dos grupos `ide`, `emit`, `dest` e `infNFe`. Implementado em
`erpnext_brasil/fiscal/documento/nfe.py`.

## Dicionário, não XML

A montagem devolve uma árvore de dicionários com os nomes oficiais das tags. Atributos
XML usam prefixo `@` (`@versao`, `@Id`, `@nItem`).

O motivo é a porta de transmissão: o ACBrLib consome INI, a ACBr API consome JSON, e um
provedor comercial pode querer outra coisa. Emitir XML aqui obrigaria todo adaptador a
desmontá-lo de volta — e dicionário ainda se testa por igualdade, o que uma string não
permite sem parser.

## A chave é derivada, nunca informada

A chave de acesso **repete oito dados** que também vivem no grupo `ide`: UF, ano/mês,
CNPJ do emitente, modelo, série, número, tipo de emissão e código numérico.

Duas fontes para o mesmo dado é exatamente onde divergência silenciosa nasce. Um sistema
que gere a chave de um lado e preencha o `ide` de outro acaba emitindo documento cuja
chave não corresponde ao próprio conteúdo — e o erro só aparece na validação da SEFAZ.

Aqui:

- `montar_infnfe` **calcula** a chave a partir da identificação e do CNPJ do emitente;
- o `cDV` do `ide` sai da mesma chave, não de um cálculo paralelo;
- o atributo `@Id` é `"NFe" + chave`, como o layout exige (47 caracteres).

Há teste provando que alterar o número da nota move a chave junto.

## Regras de validação implementadas

### Rejeição 897 (regra B03-10) — código numérico

O `cNF` não pode:

- ser igual ao `nNF`;
- ter todos os dígitos iguais (`00000000`, `11111111`, …).

A regra existe para dificultar código de segurança fraco e vigora em produção desde
02/09/2019. Antes disso o `cNF` era ignorado pelas validações e muita gente o usava como
espelho do número da nota — o que a regra passou a recusar.

### Exclusividade de identificação do destinatário

`CNPJ`, `CPF` e `idEstrangeiro` são mutuamente exclusivos no XSD. Informar mais de um é
rejeição, e não informar nenhum também. A escolha é feita pelo que veio preenchido;
informar dois é erro explícito, não escolha silenciosa.

### Inscrição Estadual condicionada ao indicador

A `IE` do destinatário só é informada quando `indIEDest` é `1` (contribuinte). Informá-la
para isento (`2`) ou não contribuinte (`9`) é rejeição.

### Opcional ausente não vira tag vazia

`xFant`, `IM`, `CNAE`, `ISUF` e `enderDest` só entram na árvore quando preenchidos. Tag
vazia é rejeição, não omissão — a diferença é a que separa documento autorizado de
documento recusado.

## Padrões deliberados

**Ambiente padrão é homologação** (`tpAmb` = `2`). Emitir em produção precisa ser escolha
consciente, não o que acontece quando o campo é esquecido.

**Série e número perdem zeros à esquerda no `ide`** (o layout usa o valor natural), mas a
chave os restaura para o tamanho fixo. São representações diferentes do mesmo dado, e a
montagem cuida das duas.

## Campos do grupo `ide`

| Campo | Obrigatório | Conteúdo |
|---|---|---|
| `cUF` | sim | Código da UF (IBGE) |
| `cNF` | sim | Código numérico, 8 dígitos |
| `natOp` | sim | Natureza da operação |
| `mod` | sim | `55` (NF-e) ou `65` (NFC-e) |
| `serie` | sim | Série |
| `nNF` | sim | Número da nota |
| `dhEmi` | sim | Data e hora com fuso — sem fuso a SEFAZ rejeita |
| `tpNF` | sim | `0` entrada, `1` saída |
| `idDest` | sim | `1` interna, `2` interestadual, `3` exterior |
| `cMunFG` | sim | Município do fato gerador |
| `cMunFGIBS` | não | Município do fato gerador do IBS (reforma) |
| `tpImp` | sim | Formato de impressão do DANFE |
| `tpEmis` | sim | Forma de emissão |
| `cDV` | sim | Dígito verificador da chave |
| `tpAmb` | sim | `1` produção, `2` homologação |
| `finNFe` | sim | Finalidade |
| `indFinal` | sim | Operação com consumidor final |
| `indPres` | sim | Presença do comprador |
| `procEmi` | sim | Processo de emissão |
| `verProc` | sim | Versão do processo de emissão |

## Ainda não montados

- `enderEmit` e `enderDest` são repassados como vieram, sem validação de conteúdo;
- grupo `det` recebe os itens prontos — o produto (`prod`) e os impostos (`imposto`) são
  montados fora;
- `total`, `transp`, `pag`, `infAdic` e a assinatura não são construídos aqui;
- `NFref` (documento referenciado), necessário em nota de devolução e complementar.

## Fontes

- `leiauteNFe_v4.00.xsd` — Pacote de Liberação 010e_v1.02, Portal Nacional da NF-e.
- NT 2019.001 — regra de validação B03-10 (rejeição 897).
