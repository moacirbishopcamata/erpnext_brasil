# SPED Fiscal (EFD-ICMS/IPI): registros E110, E111, E520 e E530

Quarto incremento do bloco contábil, sobre
[apuracao-periodica.md](apuracao-periodica.md) — primeiro passo em "obrigações
acessórias" do roteiro.

## Por que EFD, não o "Registro de Entradas e Saídas" em papel

O roteiro deste bloco pedia "apuração e livros (Registro de Entradas e Saídas, Apuração
de ICMS e de IPI)". Investigando antes de implementar: o **Ajuste SINIEF 02/2009**
dispensou, para quem é obrigado ao EFD-ICMS/IPI, a emissão e autenticação dos livros em
papel — Registro de Entradas, Registro de Saídas, Registro de Inventário, Registro de
Apuração do IPI e Registro de Apuração do ICMS. Hoje esse é o caso da esmagadora maioria
das empresas brasileiras.

Consequência prática para este projeto: implementar o livro de papel seria construir um
artefato que a lei já tornou dispensável para quem mais importa. O alvo real —
"apuração e livros" no sentido em que ainda importa hoje — é o **registro digital do
EFD** que substitui esses livros, não a forma antiga. Por isso este incremento pula
direto para o SPED Fiscal, em vez de modelar o livro de papel primeiro.

## E110 (ICMS) e E520 (IPI) são conversores, não uma nova apuração

O registro E110 ("Apuração do ICMS — Operações Próprias") traz exatamente o que
`contabil/apuracao_periodo.ApuracaoPeriodo` (para ICMS) já calcula: débito bruto,
crédito bruto, saldo credor anterior, saldo apurado, valor a recolher, saldo credor a
transportar. `contabil/efd_icms_ipi.montar_e110` só organiza esses seis valores no
formato de campo que o Fisco espera — a conta já foi feita em `apuracao_periodo.py`.

O registro **E520** ("Apuração do IPI") faz o mesmo para IPI — layout mais enxuto (8
campos, não 15: sem equivalente a `VL_TOT_DED`), mesma mecânica de saldo mutuamente
exclusivo. **E110 não é o registro de IPI** — cheguei a cogitar "E200" antes de conferir
a fonte, o que estava errado: E200/E210 são de ICMS-Substituição Tributária, E300/E310
são de ICMS-DIFAL (EC 87/2015, o "Diferencial de Alíquota" interestadual — ver
`docs/README.md` para outros gaps deliberados envolvendo DIFAL). A apuração do IPI vive
no bloco E500-E530, numeração completamente separada da do ICMS.

## Layout confirmado (ordem oficial do Guia Prático EFD-ICMS/IPI)

### E110 — Apuração do ICMS

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"E110"` |
| 2 | `VL_TOT_DEBITOS` | Total de débitos do ICMS (saídas) |
| 3 | `VL_AJ_DEBITOS` | Ajustes a débito do documento fiscal |
| 4 | `VL_TOT_AJ_DEBITOS` | Total de ajustes a débito |
| 5 | `VL_ESTORNOS_CRED` | Estornos de crédito |
| 6 | `VL_TOT_CREDITOS` | Total de créditos do ICMS (entradas) |
| 7 | `VL_AJ_CREDITOS` | Ajustes a crédito do documento fiscal |
| 8 | `VL_TOT_AJ_CREDITOS` | Total de ajustes a crédito |
| 9 | `VL_ESTORNOS_DEB` | Estornos de débito |
| 10 | `VL_SLD_CREDOR_ANT` | Saldo credor do período anterior |
| 11 | `VL_SLD_APURADO` | Débitos + ajustes + estornos, menos créditos |
| 12 | `VL_TOT_DED` | Deduções previstas na legislação estadual |
| 13 | `VL_ICMS_RECOLHER` | `VL_SLD_APURADO` menos `VL_TOT_DED` |
| 14 | `VL_SLD_CREDOR_TRANSPORTAR` | Excedente de crédito para o próximo período |
| 15 | `DEB_ESP` | Débitos especiais (extemporâneos) |

### E520 — Apuração do IPI

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"E520"` |
| 2 | `VL_SD_ANT_IPI` | Saldo credor do período anterior |
| 3 | `VL_DEB_IPI` | Total de débitos do IPI (saídas) |
| 4 | `VL_CRED_IPI` | Total de créditos do IPI (entradas) |
| 5 | `VL_OD_IPI` | Outros débitos (inclui estornos de crédito) |
| 6 | `VL_OC_IPI` | Outros créditos (inclui estornos de débito) |
| 7 | `VL_SC_IPI` | Saldo credor a transportar para o próximo período |
| 8 | `VL_SD_IPI` | Saldo devedor (valor a recolher) |

`sped.rfb.gov.br` (fonte oficial, o Guia Prático em si) ficou inacessível às ferramentas
de busca no momento da implementação — mesma limitação já registrada para outras fontes
governamentais neste projeto. As duas tabelas acima foram confirmadas num guia técnico
especializado (vriconsulting.com.br) com descrição campo a campo, corroborado por um
segundo agregador (busca cruzada) que reproduziu a mesma lista de nomes de campo na
mesma ordem. Para o E520, a mesma fonte confirma explicitamente que `VL_SC_IPI` e
`VL_SD_IPI` são mutuamente exclusivos — a mesma regra que `ApuracaoPeriodo` já
implementava antes de eu ler essa confirmação, não o contrário.

## E111: ajuste de apuração do ICMS, agora coberto

O registro E111 discrimina, um a um, cada ajuste que compõe os 7 campos de ajuste do
E110 — `VL_TOT_AJ_DEBITOS`, `VL_ESTORNOS_CRED`, `VL_TOT_AJ_CREDITOS`,
`VL_ESTORNOS_DEB`, `VL_TOT_DED`, `DEB_ESP` (`VL_AJ_DEBITOS`/`VL_AJ_CREDITOS` são
ajuste vinculado a documento fiscal específico, categoria diferente, continuam fora de
escopo). Layout (4 campos, ordem oficial):

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"E111"` |
| 2 | `COD_AJ_APUR` | Código do ajuste (4 caracteres) |
| 3 | `DESCR_COMPL_AJ` | Descrição complementar |
| 4 | `VL_AJ_APUR` | Valor do ajuste |

`COD_AJ_APUR` **não tem tabela nacional única** — cada UF mantém sua própria tabela de
códigos (Ato COTEPE/ICMS 09/2008, item 5.1.1, usado como *fallback* só quando o estado
não tem tabela própria) — mesma variação por UF já vista em `boleto.py`
(`campo_livre`)/`cnab400_retorno.py` (dialeto por banco). Por isso `Ajuste.codigo` vem
pronto de quem chama; este módulo só lê o **4º caractere**, que decide o tipo (e,
portanto, para qual campo do E110 o valor soma):

| 4º caractere | Tipo | Campo do E110 |
|---|---|---|
| `0` | Outros débitos | `VL_TOT_AJ_DEBITOS` |
| `1` | Estornos de crédito | `VL_ESTORNOS_CRED` |
| `2` | Outros créditos | `VL_TOT_AJ_CREDITOS` |
| `3` | Estornos de débito | `VL_ESTORNOS_DEB` |
| `4` | Deduções | `VL_TOT_DED` |
| `5` | Débitos especiais (extemporâneos) | `DEB_ESP` |

`montar_e110(apuracao, ajustes)` recalcula `VL_SLD_APURADO`/`VL_ICMS_RECOLHER`/
`VL_SLD_CREDOR_TRANSPORTAR` somando os ajustes à fórmula — não reaproveita
`ApuracaoPeriodo.a_recolher`/`saldo_credor_a_transportar` direto, porque esses dois não
sabem de ajuste algum (escopo de débito/crédito bruto só). `DEB_ESP` fica de fora da
fórmula — confirmado na fonte como valor informativo (débito extemporâneo), não algo
que altera o saldo apurado. Dedução maior que o saldo devedor apurado levanta erro
explícito (`EfdInvalido`) — caso não coberto, sem fonte confirmada para o tratamento
correto.

## E530: ajuste de apuração do IPI — tabela nacional, não por UF

Diferente do ICMS, `COD_AJ` do E530 **tem tabela nacional única**, publicada pela RFB
(IN RFB 932/2009, atualizada pela IN RFB 1009/2010) — não varia por estado. A tabela usa
faixa numérica com a natureza embutida no próprio código: `001`-`099` são crédito,
`101`-`199` são débito (`100` é reservado/inexistente). Por isso `AjusteIpi.ind_aj` é
**derivado** do código, não pedido como parâmetro separado — evita o chamador informar
os dois e arriscar divergência (mesmo motivo de `montar_infnfe` derivar a chave do
`ide`, nunca aceitá-la em paralelo).

Layout (7 campos, ordem diferente do E111 — aqui o indicador vem antes do valor, e o
valor antes do código):

| # | Campo | Descrição |
|---|---|---|
| 1 | `REG` | Fixo, `"E530"` |
| 2 | `IND_AJ` | `"0"` débito / `"1"` crédito |
| 3 | `VL_AJ` | Valor do ajuste |
| 4 | `COD_AJ` | Código da tabela nacional da RFB |
| 5 | `IND_DOC` | Origem do documento que respalda o ajuste (`0` judicial, `1` administrativo, `2` PER/DComp, `3` documento fiscal, `9` outros) |
| 6 | `NUM_DOC` | Número do processo/documento |
| 7 | `DESCR_AJ` | Descrição do ajuste |

`montar_e520(apuracao, ajustes)` soma ajustes de débito em `VL_OD_IPI` e de crédito em
`VL_OC_IPI`, recalculando `VL_SC_IPI`/`VL_SD_IPI` — mesma disciplina de
`montar_e110`/`Ajuste`. Diferente do E110, o E520 não tem campo de dedução
(`VL_TOT_DED`): a fórmula aqui é só débito mais outros débitos, menos crédito menos
outros créditos menos saldo credor anterior.

## Formato de saída: dict, não a linha de texto do EFD

O layout de texto do SPED (campos separados por `|`, decimal com vírgula, escapes
próprios, um registro por linha dentro de um bloco) é uma preocupação de serialização
separada de "quais valores vão em quais campos". `montar_e110`/`montar_e520` devolvem
um `dict` (campo → `Decimal`), não a linha pronta — resolver as duas coisas juntas
arriscaria acertar o valor e errar o formato, ou vice-versa, sem teste dedicado para
cada responsabilidade (mesma separação de `fiscal/documento/serializacao.py`: a árvore
de dados primeiro, o formato de texto depois, como camada própria).

## Correção: `COD_AJ_APUR` tem 8 caracteres, não 4 (2026-09-03)

Bug real, encontrado ao levantar o layout do E220 (ICMS-ST): `Ajuste.__post_init__`
exigia `len(codigo) == 4` e a docstring do módulo afirmava "COD_AJ_APUR tem 4
caracteres". O layout oficial declara **`008`**, e todo código real da tabela 5.1.1 tem
oito caracteres — `GO040024`, `GO090004`, `PE000001` são exemplos literais do próprio
Guia Prático. Ou seja: a validação **rejeitaria qualquer código real** que um usuário
informasse; nenhum teste pegou isso porque todos usavam códigos inventados de 4
caracteres (`MG00`, `MG04`), que a validação aceitava e o Fisco recusaria.

A estrutura por posição, agora modelada:

| Posição | Conteúdo |
|---|---|
| 1-2 | Sigla da UF cuja tabela define o código |
| 3 | Tributo: `0` = ICMS operações próprias, `1` = ICMS-ST |
| 4 | Tipo do lançamento (a tabela de seis tipos, já documentada acima) |
| 5-8 | Sequencial dentro da tabela da UF |

O índice do 4º caractere (que decide o campo de destino) já estava certo — só o tamanho
e a ausência da checagem do 3º caractere estavam errados. `Ajuste` passou a exigir `0`
na 3ª posição, recusando um código de ST usado por engano num E111.

**Fonte que revelou o erro**: Guia Prático oficial da EFD-ICMS/IPI publicado pela
SEFAZ-GO (`goias.gov.br/economia/.../Guia_pratico_5.8.pdf`) — PDF baixado e lido
localmente com `pdftotext`, não resumido por ferramenta. O site oficial da RFB
(`sped.rfb.gov.br`) recusou conexão nesta rodada, mesmo obstáculo já registrado em
`docs/nfce-qrcode.md`.

## E200/E210/E220 (ICMS-ST): implementados em módulo próprio

Ver `contabil/efd_icms_st.py`. São apurações genuinamente distintas do E110 — não o
mesmo registro com outros nomes de campo:

- **Escopo por UF**: o E200 se repete por Unidade da Federação onde o contribuinte é
  substituto tributário (ocorrência `1:N`); o E110 é um só por período.
- **Composição diferente**: o E210 tem `VL_DEVOL_ST`/`VL_RESSARC_ST`/`VL_RETENCAO_ST`,
  que não existem no E110.
- **`IND_MOV_ST`**: indicador de "sem operações"/"com operações" que o E110 não tem —
  derivado dos próprios valores aqui, nunca recebido em paralelo (evita o chamador
  declarar "sem operações" com valores preenchidos).

**Achado real**: a apuração da ST **não tem campo de estorno**. Dos seis tipos de
`COD_AJ_APUR`, só quatro têm destino no E210 (`0` outros débitos, `2` outros créditos,
`4` deduções, `5` débitos especiais); os tipos `1`/`3` (estorno de crédito/débito) não
têm campo correspondente, e a descrição oficial do E220 confirma isso ao enumerar
exatamente esses quatro campos como os que ele discrimina. `AjusteSt` recusa `1`/`3` em
vez de somá-los em algum campo "parecido" — silenciar produziria um E210 que fecha
aritmeticamente e mente sobre a natureza do lançamento.

`ApuracaoSt` **não** reaproveita `ApuracaoPeriodo` de propósito: aquela classe modela
débito/crédito bruto de tributo com não cumulatividade constitucional
(`TRIBUTOS_APURAVEIS = {ICMS, IPI}`), e a ST não é isso — o débito é imposto **retido**
de terceiro (o que `fiscal.impostos.icms.calcular_icms_st` já produz por item) e os
créditos são devolução/ressarcimento, conceitos ausentes daquela classe.

**Nível de confiança**: o layout campo a campo de E200/E210/E220 vem de fonte
secundária (`vriconsulting.com.br`, guias 142/143/144, que reproduzem o Guia Prático da
RFB), cruzada com descrições de TOTVS/Senior que concordam quanto ao propósito de cada
registro e à relação E220 → E210. Só o tamanho/estrutura do `COD_AJ_APUR` tem
confirmação oficial (ver seção acima).

## E300/E310/E311 (DIFAL e FCP): a terceira e última apuração do bloco E

Ver `contabil/efd_icms_difal.py`. Fecha o bloco E de apuração: operações próprias
(E110), ICMS-ST (E210) e agora DIFAL/FCP da EC 87/2015 (E310).

**A versão do E310 importa.** Existe uma anterior, válida até 31/12/2016, **sem** a
metade do FCP. Este módulo implementa a vigente (a partir de 01/01/2017), com 22 campos:
dois blocos de 10 estruturalmente idênticos (DIFAL nos campos 3-12, FCP nos 13-22) mais
`REG` e `IND_MOV_FCP_DIFAL`. Os dois blocos usam a mesma função interna, chamada duas
vezes — não duas cópias que divergiriam na primeira manutenção.

### Achado real: três registros de apuração, três tratamentos de estorno

O tipo de divergência que só aparece lendo o layout de cada registro, nunca supondo por
analogia entre irmãos:

| Registro | Estorno de crédito | Estorno de débito |
|---|---|---|
| E110 (próprias) | campo dedicado `VL_ESTORNOS_CRED` | campo dedicado `VL_ESTORNOS_DEB` |
| E210 (ST) | **não existe campo** (tipo recusado) | **não existe campo** (tipo recusado) |
| E310 (DIFAL/FCP) | somado em `VL_OUT_DEB_DIFAL` | somado em `VL_OUT_CRED_DIFAL` |

No E310 isso é o rótulo oficial do campo, não interpretação: `VL_OUT_DEB_DIFAL` é
"Outros débitos **e estornos de créditos**".

### Achado real: o E311 fecha a tabela do 3º caractere do `COD_AJ_APUR`

`efd_icms_ipi.py` modelou o 3º caractere como tributo (`0` = ICMS próprio),
`efd_icms_st.py` acrescentou `1` = ICMS-ST, e o E311 confirma `2` = DIFAL/FCP — a fonte
lista os códigos `20`-`25` (o par 3º+4º caractere) como outros débitos / estorno de
créditos / outros créditos / estorno de débitos / deduções / débito especial. A mesma
tabela de seis tipos no 4º caractere vale para as três apurações; é o 3º que diz de qual
apuração o código é. Cada um dos três módulos recusa código que não seja o seu.

### Divergência declarada: no E310 a dedução excedente não levanta erro

`montar_e110`/`montar_e210` levantam `EfdInvalido` quando a dedução supera o saldo
devedor, porque para aqueles dois não havia fonte confirmando o tratamento. Para o E310
há: a fórmula oficial do campo 10 é "se (08 - 09) ≥ 0, então 10 = (08-09); senão 10 =
0". Implementado como a fonte manda; a divergência entre os três registros fica
registrada em vez de uniformizada por gosto.

### Fora de escopo declarado: roteamento de ajuste para a metade FCP

A fonte confirma que o E311 discrimina quatro campos da metade **DIFAL**
(`VL_OUT_CRED_DIFAL`, `VL_OUT_DEB_DIFAL`, `VL_DEDUCOES_DIFAL`, `DEB_ESP_DIFAL`), mas
**não** confirma se (e como) um código do E311 se dirige à metade **FCP**. Por isso os
quatro campos equivalentes do FCP são parâmetros explícitos de `ApuracaoDifal`, não
derivados de ajuste — inventar uma regra de roteamento sem fonte seria o erro que este
projeto evita.

**Nível de confiança**: layout e fórmulas vêm de fonte secundária
(`vriconsulting.com.br`, guias 235/258/237, que reproduzem o Guia Prático da RFB). O
site oficial da RFB recusou conexão nesta rodada.

## Bloco 0 (abertura, identificação e cadastros)

Ver `contabil/efd_bloco_0.py`. Sem este bloco não existe arquivo EFD: os registros de
apuração são o conteúdo, e o Bloco 0 identifica a entidade, o período, o perfil e os
cadastros que os demais blocos referenciam por código. Cobertos: `0000`
(abertura/identificação, 15 campos), `0001` (abertura do bloco), `0150` (participantes,
13 campos), `0190` (unidades de medida, 3 campos), `0200` (itens, 13 campos) e `0990`
(encerramento).

### Achado real: `IND_MOV` do `0001` é o inverso do `IND_MOV_ST` do `E210`

Mesmo prefixo de nome, semântica oposta — o tipo de detalhe que produz um arquivo aceito
pelo validador e errado no conteúdo:

| Campo | `0` significa | `1` significa |
|---|---|---|
| `0001.IND_MOV` (abertura de bloco) | bloco **com** dados | bloco **sem** dados |
| `E210.IND_MOV_ST` (apuração da ST) | **sem** operações | **com** operações |

Por isso `montar_0001` recebe `tem_dados: bool` e converte, em vez de aceitar a string
crua — mesma proteção que `ecf_bloco_0.montar_0001` já aplicava ao `IND_DAD` da ECF (que
segue a convenção do `0001`, não a do `E210`).

### Achado real: fonte oficial antiga não basta — o `0200` ganhou o CEST

O layout foi lido do Guia Prático oficial **versão 2.0.13** (cópia publicada pela
SEFAZ-SP, PDF baixado e lido localmente com `pdftotext`, não resumido por ferramenta —
o site da RFB continua recusando conexão). Conferindo contra fonte secundária atual
antes de implementar, apareceu uma diferença real: o `0200` ganhou um **13º campo,
`CEST`**, introduzido na versão 2.0.20 do guia e válido a partir de 01/01/2017 —
posterior ao PDF lido. Implementado com os 13 campos. O `0000` foi conferido do mesmo
jeito e continua com 15 campos, sem mudança.

Reforça a disciplina do projeto: fonte oficial não basta se for de versão antiga;
cruzar com uma fonte atual é o que pega o campo novo.

### Regras cruzadas que o módulo checa

- `0000`: CNPJ **ou** CPF, exatamente um (a entidade é PJ ou PF); e se o CPF for
  informado, `IND_ATIV` tem de ser `1` (Outros) — pessoa física não é estabelecimento
  industrial para efeito da EFD. Regra do próprio layout, checada aqui em vez de deixar
  o validador do Fisco recusar depois.
- `0150`: CNPJ e CPF são os dois "obrigatórios quando houver", e o layout **não** exige
  um dos dois (participante estrangeiro se identifica só por `COD_PAIS`) — por isso
  `Participante` não replica a exclusividade do `0000`. Exigir inventaria uma regra que
  o layout não tem.

### Fora de escopo declarado

`0005` (dados complementares), `0100` (contabilista), `0175`, `0205`, `0206` (ANP),
`0210`, `0220`, `0300`/`0305` (CIAP), `0400` (natureza da operação), `0450`, `0460`,
`0500` (plano de contas) e `0600` (centros de custo) — cada um é um cadastro próprio;
entrar neles sem um consumidor real seria montar estrutura sem uso, mesmo critério
aplicado aos blocos da ECF.

## Bloco C (documentos fiscais de mercadoria)

Ver `contabil/efd_bloco_c.py`. O maior bloco do arquivo — é onde cada nota fiscal entra.
Cobertos `C001` (abertura), `C100` (o documento, 29 campos), `C190` (registro analítico,
12 campos) e `C990` (encerramento).

**O recorte C100 + C190 é regra do guia, não "o que deu tempo"**: para NF-e de emissão
própria (Exceção 2) e para NFC-e (Exceção 9), o Guia Prático diz que "regra geral, devem
ser apresentados **somente os registros C100 e C190**". O `C170` (itens, ~38 campos) só é
admitido em hipóteses específicas — ressarcimento de ICMS-ST com `C176`, ou documentos de
terceiros — e fica para um incremento próprio, com sua própria verificação.

### Achado real: `IND_FRT` mudou de significado duas vezes, com os mesmos números

O campo mais perigoso do registro. Três domínios ao longo do tempo, e **os mesmos códigos
significando coisas diferentes**:

| Código | Até 31/12/2011 | 2012-2017 | Vigente (desde 01/01/2018) |
|---|---|---|---|
| `0` | por conta de terceiros | por conta do emitente | frete por conta do remetente (CIF) |
| `1` | por conta do emitente | por conta do destinatário/remetente | frete por conta do destinatário (FOB) |
| `2` | por conta do destinatário | por conta de terceiros | frete por conta de terceiros |
| `3` | — | — | transporte próprio por conta do remetente |
| `4` | — | — | transporte próprio por conta do destinatário |
| `9` | sem cobrança de frete | sem cobrança de frete | sem ocorrência de transporte |

`0` e `1` **trocaram de sentido** entre a primeira e a segunda versão: um arquivo montado
com a tabela antiga atribui o frete à parte errada **e passa no validador** — erro
silencioso, do tipo que só aparece numa fiscalização. Implementada a tabela vigente; a
histórica fica documentada para que ninguém "corrija" o código de volta ao que uma fonte
antiga diz.

Foi o segundo caso, na mesma frente, em que o guia oficial de 2013 estava desatualizado
(o primeiro foi o `CEST` do `0200`) — a cada registro, cruzar com fonte atual antes de
implementar deixou de ser zelo e virou necessidade demonstrada.

### Regras cruzadas do guia, checadas no módulo

- **`CHV_NFE` obrigatória** desde abril/2012 em todas as situações, exceto com numeração
  inutilizada (`COD_SIT = "05"`) — e validada de verdade (44 posições e dígito
  verificador) reaproveitando `fiscal.documento.chave_acesso.validar_chave`, a mesma
  validação da família NF-e/CT-e/MDF-e, não uma segunda implementação.
- **NFC-e (modelo 65)** não informa `COD_PART` nem os campos de ICMS-ST/IPI/PIS/COFINS
  (Exceção 9). Preencher esses campos numa NFC-e é erro de montagem; falhar aqui é
  melhor que ser rejeitado depois sem contexto.

### Conflito de fonte declarado: `IND_PGTO`

O Guia 2.0.13 anota que a partir de 01/07/2012 o domínio passaria a ser `0`/`1`/`2`, sem
o `9`. A fonte secundária atual lista `0`/`1`/`2`/`9`. Como se contradizem e nenhuma é a
versão mais recente do guia oficial, o módulo aceita o **superconjunto**: recusar um
valor possivelmente válido quebraria um usuário legítimo, enquanto aceitar um
possivelmente inválido é pego pelo validador do Fisco. Dúvida declarada, não resolvida
por chute.

## Bloco 9 (controle e encerramento) — e o arquivo completo de ponta a ponta

Ver `contabil/efd_bloco_9.py`. `9001` (abertura), `9900` (uma linha por tipo de registro,
com a contagem de cada um), `9990` (encerramento do bloco) e `9999` (encerramento do
arquivo, com o total de linhas).

### A sutileza real do `9900`: a contagem é auto-referente

O guia diz que "todos os registros referenciados neste arquivo, **inclusive os
posteriores a este registro**, devem ter uma linha totalizadora". Ou seja, o `9900`
precisa totalizar o `9001`, o `9990`, o `9999` — e o **próprio `9900`**. E a quantidade
de linhas `9900` é o número de tipos distintos no arquivo, que inclui o `9900`. A
contagem depende de si mesma.

Resolvido em `montar_bloco_9` de forma fechada, sem iterar até convergir: com `N` tipos
distintos fora do Bloco 9, o total é `N + 4` (os quatro registros do Bloco 9, que não
aparecem em nenhum outro lugar), e daí saem as três contagens:

- linhas `9900` = `N + 4`
- `QTD_LIN_9` = 1 (`9001`) + (`N + 4`) + 1 (`9990`) = `N + 6`
- `QTD_LIN` = linhas dos demais blocos + (`N + 6`) + 1 (o próprio `9999`)

Errar essa conta não produz um arquivo "quase certo": o PVA valida cada `QTD_` contra a
contagem real e rejeita o arquivo inteiro.

### Marco: arquivo EFD completo, montado e serializado

`tests/test_efd_arquivo_completo.py` monta um arquivo mínimo mas real — identificação,
participante, unidade, item, uma nota fiscal com seu analítico e a apuração do ICMS —
do `0000` ao `9999`, e serializa em texto SPED via `contabil/sped_texto.py`.

É um teste de **costura**, não de unidade: confere cada linha `9900` contra a contagem
real do arquivo (o que o PVA faz), confere `QTD_LIN` contra o número de linhas
efetivamente produzidas, e confere os encerramentos de bloco (`0990`/`C990`) contra as
linhas de cada bloco. Nenhum teste anterior cruzava os quatro módulos do EFD com o
serializador — cada um estava testado sozinho, e é exatamente aí que a contagem de um
arquivo inteiro pode sair errada com todas as peças individualmente corretas.

## Bloco H (inventário) e o par `E001`/`E990`

Fonte: **Guia Prático EFD-ICMS/IPI versão 3.2.1 (28/10/2025)**, páginas 250-251 e
260-264. Desta vez o `sped.rfb.gov.br` respondeu — as versões anteriores deste projeto
tiveram de recorrer a cópias publicadas por SEFAZ estaduais porque o site oficial
recusava conexão. O PDF (360 páginas) foi baixado e lido localmente, não resumido por
ferramenta.

### O achado: o mesmo item tem dois valores certos e diferentes

O `H010` tem `VL_ITEM` (campo 06) **e** `VL_ITEM_IR` (campo 11). O guia explica a
diferença no próprio campo 11:

> "o valor do ICMS recuperável mediante crédito na escrita fiscal do adquirente ... não
> integra o custo de aquisição para efeito do Imposto de Renda ... Tratamento idêntico
> deve ser aplicado ao PIS-Pasep e à Cofins não cumulativos ... Observe-se, porém, que
> **as legislações do IPI e do ICMS não contemplam essas exclusões**."

Ou seja, o **mesmo item, no mesmo arquivo, no mesmo dia**, tem dois valores legítimos:
`VL_ITEM` inclui o tributo recuperável (ótica ICMS/IPI) e `VL_ITEM_IR` o exclui (ótica do
IR). Informar o mesmo número nos dois é o erro natural de quem não sabe que a diferença
existe — e é caro, porque distorce o custo dos estoques na apuração do lucro real.

É exatamente a regra do RIR/2018 art. 301, §3º que `contabil/custo_aquisicao.py` já
implementava, agora confirmada por uma segunda fonte oficial e independente. `custo` é o
valor para o IR, `custo + creditos` é o valor pela ótica do ICMS/IPI, e há teste de
costura provando que os dois módulos concordam — a mesma nota vista pelas duas
legislações. O módulo **não deduz** um do outro: a exclusão depende de recuperabilidade,
que depende de regime e destinação.

### O segundo achado: `E001` não é `H001`

Registro de abertura de bloco parece intercambiável e não é:

| Registro | `IND_MOV` — valores válidos |
|---|---|
| `0001`, `C001`, `H001` | `[0, 1]` — o bloco pode ser declarado vazio |
| **`E001`** | **`[0]`** — só isso |

O bloco de apuração do ICMS **nunca pode ser vazio**, porque `E100`/`E110` são sempre
obrigatórios (e `E500` também, para industrial ou equiparado). Copiar a validação de um
para o outro produz um arquivo que o montador aceita e o PVA rejeita.

A resposta não foi validar o `bool` e recusá-lo: `montar_e001()` **não recebe parâmetro
nenhum**, o que torna o erro impossível de escrever em vez de detectá-lo depois. Pelo
mesmo motivo `montar_e990` exige no mínimo **quatro** linhas (`E001`, `E100`, `E110` e ele
próprio), enquanto os demais encerramentos aceitam duas.

Mais um caso da regra que este projeto já aprendeu várias vezes: **nunca assumir por
analogia entre registros irmãos**.

### O terceiro achado, que veio de graça: faltava o `E100`

`montar_e990` exige no mínimo **quatro** linhas, porque `E001`, `E100`, `E110` e ele
próprio são todos obrigatórios. Ao ligar essa validação ao teste de arquivo completo, ela
falhou — e a falha estava certa: **o projeto montava um Bloco E sem o `E100`**, o registro
que informa o período da apuração.

Ninguém tinha percebido porque cada `montar_*` estava correto isoladamente; só a contagem
do bloco inteiro revelou o registro ausente. Um arquivo assim é aceito por qualquer
montador e rejeitado pelo PVA. A resposta não foi baixar o mínimo para três — seria
afrouxar uma validação correta para acomodar uma lacuna real: foi escrever `montar_e100`.

O `E100` trouxe seu próprio detalhe: comparar datas em `ddmmaaaa` **como texto** daria
`"31012026" > "01022026"` — o dia pesando mais que o mês, erro que passa em quase todo
teste e falha exatamente na virada. `_ordenavel` reordena para `aaaammdd` antes de
comparar, e há teste com um período que atravessa a virada do mês.

O teste de arquivo completo agora monta o Bloco E inteiro (`E001`/`E100`/`E110`/`E990`) e
o Bloco H, e confere os quatro encerramentos de bloco contra as linhas reais.

### As validações cruzadas, que falham alto

O guia impõe regras **entre** registros, não dentro de um — e é por isso que existe
`montar_bloco_h`, que monta o bloco inteiro em vez de deixar o encadeamento por conta de
quem chama:

- **`VL_INV` = soma dos `VL_ITEM`.** O total é **calculado**, não recebido: pedi-lo de
  quem chama abriria a porta para um total que não bate com os itens.
- **`VL_INV = 0` proíbe `H010`** — "atribuir valor Zero ao inventário significa escriturar
  sem estoque".
- **`IND_PROP` 1 ou 2 exige `COD_PART`** — item em posse de terceiro sem dizer de quem é
  informação pela metade.
- **`VL_FCP` não pode superar `VL_ICMS_ST`** no `H030`: o campo 04 já contém a parcela do
  FCP e o 05 a destaca de dentro dele. Somar os dois contaria o FCP duas vezes.
- **`MOT_INV = 06` é recusado** por `montar_bloco_h`, porque exige um `H030` por item que
  essa função não monta. Recusar é melhor que devolver um bloco incompleto com cara de
  pronto.

### Fora de escopo, declarado

- **Quais itens entram no inventário** — depende do saldo em estoque na data; é a camada
  de integração que lê o ERPNext.
- **A obrigação de fevereiro** (repetir na EFD de fevereiro o inventário de 31/12 já
  apresentado em dezembro ou janeiro) e o **inventário mensal do CNAE 4681-8/01 e
  4681-8/02** (combustíveis) — são regras de *quando* entregar, não de *como* montar, e
  pertencem a `contabil/prontidao_fiscal.py`.

## Bloco K (controle da produção e do estoque)

Núcleo implementado: `K001`, `K010`, `K100`, `K200`, `K220`, `K230`, `K235`, `K990`.
Mesma fonte primária do Bloco H — Guia Prático 3.2.1, páginas 264-273.

### Achado 1: "quantidade" tem precisão diferente dentro do mesmo bloco

| Registro | Campo | Decimais |
|---|---|---|
| `K200` (saldo) | `QTD` | **3** |
| `K220` (movimentação) | `QTD_ORI`, `QTD_DEST` | **6** |
| `K230` (produção) | `QTD_ENC` | **6** |
| `K235` (consumo) | `QTD` | **6** |

O mesmo conceito — quantidade da mercadoria, na mesma unidade de controle de estoque do
`0200` — declarado com **o dobro de casas** na movimentação e metade no saldo. Não são
blocos diferentes nem versões diferentes do leiaute: são registros irmãos, no mesmo bloco,
no mesmo arquivo.

Isso importa porque o guia manda o `K200` ser **derivado** dos apontamentos:

```text
Estoque final = estoque inicial + entradas/produção/movimentação interna
                                − saídas/consumo/movimentação interna
```

Somar valores de seis casas e gravar em três é **arredondamento, não truncamento**, e
fazê-lo implicitamente a cada chamada é como um saldo passa a não fechar com a
movimentação que o produziu, por diferenças de centésimo de milésimo que ninguém procura.
`arredondar_quantidade(quantidade, casas)` torna a conversão explícita e única.

### Achado 2: cada registro aceita um conjunto próprio de tipos de item

| Registro | Tipos aceitos (`TIPO_ITEM` do `0200`) |
|---|---|
| `K200` | 00, 01, 02, 03, 04, 05, **06**, 10 |
| `K220` | 00, 01, 02, 03, 04, 05, 10 |
| `K230` | **só 03 e 04** |
| `K235` | 00, 01, 02, 03, 04, 05, 10 |

Nenhum aceita "qualquer item do `0200`", e o **produto intermediário (tipo 06)** é a
exceção que explica o resto: ele **tem saldo** no `K200` e seu consumo **não é
escriturado** no `K235`. O guia diz por quê — o Fisco o deduz por diferença:

> "Quantidade consumida = estoque inicial (K200) + entrada (C170) − saída (C100/NF-e −
> Devolução) − estoque final (K200)."

Escriturar o consumo do tipo 06 não é "informação a mais": é informação que o leiaute não
prevê, e o PVA rejeita. `validar_tipo_do_item` recebe o **conjunto**, não o nome do
registro — um `if registro == ...` esconderia justamente a diferença que ela existe para
mostrar.

### Achado 3: um campo que existe no leiaute e não deve ser preenchido

O campo 05 do `K235` (`COD_INS_SUBST`) traz na descrição oficial: "**A partir de
01/01/2022 não preencher**". A posição permanece no leiaute — não pode sumir sem quebrar
todo arquivo já gerado — mas a regra de negócio acabou.

`InsumoConsumido` **não expõe o campo**: sai sempre vazio. Oferecê-lo como parâmetro seria
dar ao usuário uma forma de gerar arquivo recusado, e há teste (`TypeError`) provando que
não há como preenchê-lo por engano.

### O `K010` decide o que é obrigatório abaixo

Desde 2023 o contribuinte escolhe entre leiaute **simplificado** (`0`), **completo** (`1`)
e **restrito aos saldos** (`2`), e a escolha muda quais registros são exigidos.
`REGISTROS_DISPENSADOS_NO_SIMPLIFICADO` registra a consequência; o `K235` é a diferença
mais cara, por ser o registro de maior volume. A escolha é do contribuinte, condicionada
ao Ajuste SINIEF 02/09 — o módulo a registra, não a decide.

### Onde a perda de estoque aparece — e onde não aparece

O Bloco K **não tem registro de perda**. Quebra, vencimento ou furto não viram lançamento
próprio: reduzem o saldo declarado no `K200`, e o estorno de crédito que a perda dispara
(ver `contabil/perdas.py` e `docs/precificacao-custos-rastreabilidade.md`) é um ajuste de
apuração no `E111`, cujo código vem da tabela da UF — que este projeto documenta como não
modelada.

Reclassificação de produto não conforme é caso **diferente** e tem registro: `K220` (troca
de código) ou `K260` (reprocessamento mantendo o código). Confundir perda com
reclassificação é o erro natural aqui — uma some do estoque, a outra muda de código dentro
dele. `montar_k220` recusa origem igual a destino e diz, na mensagem, que o registro certo
nesse caso é o `K260`.

### Convenção de data: `date`, não `ddmmaaaa`

Os módulos mais antigos deste projeto (`efd_bloco_0`, `efd_icms_ipi`) recebem data como
texto já formatado; `efd_bloco_h` e `efd_bloco_k` recebem `date`. A divergência é
deliberada e o `_ordenavel` do `efd_icms_ipi` é a prova do motivo: comparar `ddmmaaaa`
como texto dá `"31012026" > "01022026"`, com o dia pesando mais que o mês. Com `date` o
problema não existe.

## Ainda por implementar
- **E230/E240 (detalhamento dos ajustes de ST) e E250 (guias de recolhimento da ST)** —
  o E250 exige dado de guia/pagamento (número, vencimento, banco) que este projeto não
  modela; o E230 detalha processo judicial/fiscal por trás do ajuste, mesma categoria de
  dado externo já excluída do E112/E113 no lado das operações próprias.
- ~~Registros E200/E210 (ICMS-ST)~~ — **feito em 2026-09-03**, ver seção acima.
- ~~Serialização para o formato de texto do EFD~~ — **feito em 2026-08-30**, ver
  `docs/sped-texto.md` (`contabil/sped_texto.montar_linha`).
- **`C170` (itens do documento, ~38 campos) e demais filhos do `C100`** (`C105`,
  `C110`/`C111`-`C114`, `C120`, `C176`, `C195`/`C197`) — o `C170` é dispensado justamente
  no caso mais comum (NF-e de emissão própria), e os demais dependem de dado externo
  (norma legal, processo, ajuste por UF).
- **Blocos D, K, 1** do EFD (documentos fiscais de serviço/transporte, controle da
  produção, outras informações).
- ~~Bloco H (inventário)~~ — **feito em 2026-09-03**, ver seção acima.
- ~~Abertura/encerramento do Bloco E (`E001`/`E990`)~~ — **feito em 2026-09-03**; o
  `E001` reservava uma armadilha, ver seção acima.
- **`H020`/`H030` montados, mas sem montador de bloco que os posicione.** `montar_bloco_h`
  cobre o caso comum (`MOT_INV = 01`) e **recusa** o `MOT_INV = 06`, que exige um `H030`
  por item; os registros existem e são testados, falta o encadeamento das duas situações
  especiais, que depende de dado por item que a integração ainda não fornece.
- ~~Bloco 9 (controle e encerramento do arquivo)~~ — **feito em 2026-09-03**, ver seção
  acima.
- ~~Bloco C (núcleo: `C001`/`C100`/`C190`/`C990`)~~ — **feito em 2026-09-03**, ver seção
  acima.
- ~~Bloco 0 (identificação e cadastros)~~ — **feito em 2026-09-03**, ver seção acima
  (`0000`/`0001`/`0150`/`0190`/`0200`/`0990`); os demais registros do bloco continuam
  fora de escopo, listados lá.
- **Tabela de códigos de ajuste por UF (ICMS)** — `Ajuste.codigo` vem pronto de quem
  chama; nenhuma das 27 tabelas estaduais (nem a federal de fallback) foi modelada
  aqui. A tabela do IPI (`AjusteIpi`) é nacional e também não foi transcrita — só a
  faixa numérica (001-099/101-199) que decide `IND_AJ`.

## Arquivos

- `contabil/efd_icms_ipi.py` — `Ajuste`, `AjusteIpi`, `montar_e110`, `montar_e111`,
  `montar_e520`, `montar_e530`; camada pura, sem Frappe, testável sem bench.
- `contabil/efd_icms_st.py` — `ApuracaoSt`, `AjusteSt`, `montar_e200`, `montar_e210`,
  `montar_e220` (apuração do ICMS-ST); mesma camada pura.
- `contabil/efd_icms_difal.py` — `ApuracaoDifal`, `AjusteDifal`, `montar_e300`,
  `montar_e310`, `montar_e311` (apuração do DIFAL e do FCP, EC 87/2015); mesma camada
  pura.
- `contabil/efd_bloco_0.py` — `Identificacao`, `Participante`, `Item`, `montar_0000`,
  `montar_0001`, `montar_0150`, `montar_0190`, `montar_0200`, `montar_0990` (abertura,
  identificação e cadastros); mesma camada pura.
- `contabil/efd_bloco_c.py` — `DocumentoFiscal`, `RegistroAnalitico`, `montar_c001`,
  `montar_c100`, `montar_c190`, `montar_c990` (documentos fiscais de mercadoria); mesma
  camada pura.
- `contabil/efd_bloco_9.py` — `montar_9001`, `montar_9900`, `montar_9990`, `montar_9999`
  e `montar_bloco_9` (a contagem auto-referente resolvida em um lugar só); mesma camada
  pura.
- `contabil/efd_bloco_h.py` — `ItemInventario`, `montar_h001`, `montar_h005`,
  `montar_h010`, `montar_h020`, `montar_h030`, `montar_h990` e `montar_bloco_h`
  (inventário, com as validações cruzadas do guia); mesma camada pura. `montar_e001` e
  `montar_e990` ficam em `efd_icms_ipi.py`, junto dos demais registros do Bloco E.
- `contabil/efd_bloco_k.py` — `EstoqueEscriturado`, `MovimentacaoInterna`,
  `ItemProduzido`, `InsumoConsumido`, `arredondar_quantidade`, `validar_tipo_do_item`,
  `montar_k001`, `montar_k010`, `montar_k100`, `montar_k200`, `montar_k220`,
  `montar_k230`, `montar_k235`, `montar_k990` e `montar_bloco_k` (controle da produção e
  do estoque); mesma camada pura. `montar_e100` também ficou em `efd_icms_ipi.py`.

## Fontes

- Ajuste SINIEF 02/2009 (dispensa dos livros em papel) — confirmado em fontes
  secundárias consistentes (`sped.rfb.gov.br`, `sefaz.pe.gov.br`) — consultado em
  2026-08-30.
- IN RFB 932/2009 (atualizada pela IN RFB 1009/2010) — tabela nacional de códigos de
  ajuste do IPI, citada pela mesma fonte técnica do layout do E530 — não lida
  diretamente, só a faixa numérica que ela define foi usada.
- Guia Prático EFD-ICMS/IPI, layout dos registros E110, E111, E520 e E530 — fonte
  oficial (`sped.rfb.gov.br`) inacessível às ferramentas de busca no momento; confirmado
  em guia técnico especializado (`vriconsulting.com.br`) com descrição campo a campo,
  corroborado por busca cruzada — consultado em 2026-08-30.
- **Guia Prático EFD-ICMS/IPI versão 3.2.1 (28/10/2025)** — layout do Bloco H e do par
  `E001`/`E990`. **Fonte primária**, desta vez acessível: PDF de 360 páginas baixado de
  `sped.rfb.gov.br` e lido localmente, campo a campo, sem intermediário. Uma cópia da
  versão 3.1.9 publicada pelo CONFAZ (`confaz.fazenda.gov.br`) foi baixada em paralelo e
  serviu de contraprova — consultado em 2026-09-03.
