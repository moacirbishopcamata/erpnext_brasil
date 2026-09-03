# ERPNext Brasil

Localização fiscal brasileira para o ERPNext, distribuída como **app Frappe separado** —
o ERPNext nunca é forkado nem editado.

## Por que app separado

O `erpnext/regional/` mantém hoje apenas seis países; a localização indiana, que era a
mais pesada do projeto, saiu do core e virou app próprio. Essa é a direção do projeto.
Além disso, o mecanismo de sobrescrita por região do ERPNext dá **prioridade ao último
app instalado**, de modo que um app instalado depois do erpnext vence por construção,
sem precisar tocar em nenhum arquivo do core.

Os dois projetos brasileiros anteriores que tentaram o caminho do fork morreram em
poucos meses. Isto aqui é uma tentativa de não repetir isso.

## Estado atual

Este README cobre o núcleo original (cadastros, NF-e/NFC-e). O índice completo e sempre
atualizado de tudo que existe está em [`docs/README.md`](docs/README.md) — cada
incremento tem seu próprio documento, com fonte citada e nível de confiança declarado
quando a fonte é secundária.

| Área | Situação |
|---|---|
| Cadastros fiscais (Company, Customer, Supplier, Address, Item) | pronto |
| CPF/CNPJ (inclusive **CNPJ alfanumérico**), Inscrição Estadual (27 UFs) | pronto |
| Aritmética fiscal: ICMS, IPI, PIS/COFINS, **IBS/CBS** (Reforma Tributária), retenções | pronto |
| **NF-e/NFC-e** — montagem, assinatura, transmissão SOAP nativa, eventos, QR Code | maduro — ciclo de vida completo |
| **CT-e** (modelo 57) — rodoviário, **os onze eventos** do leiaute v4.00 | completo |
| **MDF-e** (modelo 58) — rodoviário, **os sete eventos** do leiaute v3.00 | completo |
| Autorizador/webservice por UF — NF-e (12 grupos), CT-e (4 grupos), MDF-e (nacional único) | pronto |
| Certificado A1 e ambiente SEFAZ configuráveis via `Company` | pronto |
| **Contábil**: plano de contas, lançamentos, apuração ICMS/IPI, SPED Fiscal, ECD completa | pronto |
| EFD-Contribuições, EFD-Reinf (R-4020/R-2099), DeSTDA (núcleo mínimo) | pronto |
| **ECF** — Blocos 0/J/K (núcleo); Blocos L/M/N (Lucro Real) e P (Lucro Presumido) | em andamento |
| Boleto bancário (CNAB 240/400, emissão + conciliação de retorno) | pronto |
| Pix (payload BR Code, `Company.chave_pix`) | pronto |
| **RH/folha**: eSocial (S-1010/S-1200/S-1299/S-2200/S-2299), INSS, FGTS, IRRF | pronto |
| Transmissão real ao SEFAZ (certificado A1 de verdade) | bloqueado — sem certificado/homologação disponível para testar |
| NFS-e, modais aéreo/aquaviário/ferroviário de CT-e/MDF-e | não iniciado |

### CNPJ alfanumérico

Desde julho de 2026 (IN RFB 2.229/2024) o CNPJ admite letras nas 12 posições da
raiz/ordem, mantendo os 2 dígitos verificadores numéricos. O cálculo do DV continua
sendo o módulo 11; muda apenas a conversão do caractere em valor (`ord(c) - 48`).
CNPJs numéricos antigos permanecem válidos e passam pelo mesmo caminho de código.

Validadores que só aceitam dígitos já nascem quebrados — por isso este é o ponto de
partida do app, e não um detalhe deixado para depois. Atenção especial ao idioma
`re.sub(r'\D', '', valor)`: aplicado a `12ABC34501DE35` ele não falha, devolve
`123450135` e **corrompe o dado em silêncio**.

**Verificado contra a fonte oficial.** A Receita publica implementações de referência
do cálculo do DV (Java, Python e TypeScript) em *documentos-técnicos/CNPJ*. A suíte
inclui um teste diferencial que transcreve a versão Python e compara as duas
implementações sobre 3.000 bases alfanuméricas geradas — mais os CNPJs numéricos
legados e o exemplo documentado `12.ABC.345/01DE` → DV `35`. Aqui não se trata de
consistência interna: é concordância com a Receita.

Há **uma divergência intencional**, testada e documentada: a referência é um calculador
de DV puro e aceita `00000000000000` (a soma zera e os dois dígitos saem 0). Este app
recusa base numérica com todos os dígitos iguais, porque é valor-lixo consagrado e
sujaria o cadastro fiscal — mas **não** estende a recusa a base alfanumérica, que não
tem essa convenção contra si e cuja rejeição poderia travar uma inscrição legítima.

### Inscrição Estadual: o que está provado e o que não está

As 27 UFs têm regra implementada, incluindo as irregulares — SP (dígito fora da
posição final e formato próprio de produtor rural), MG (módulo 10 com zero interposto,
somando algarismos do produto), BA (alterna entre módulo 10 e 11 conforme o primeiro
dígito), PE, AP, GO, RO, RR (único caso de módulo 9) e TO.

Os testes constroem uma IE por força bruta sobre as posições de dígito verificador e
exigem que a regra a aceite e que mutações a rejeitem. **Isso prova consistência
aritmética, não aderência à especificação**: um peso trocado em relação ao SINTEGRA
continuaria passando, porque o teste valida a implementação contra ela mesma. Fechar
essa lacuna exige um lote de IEs reais por UF — é o próximo passo dessa frente.

Por isso o viés é deliberadamente a favor do falso positivo: UF que não se consegue
determinar, ou fora das 27, **deixa passar**. Uma IE inválida aceita é pega depois pela
SEFAZ; uma IE válida rejeitada trava o cadastro de um cliente real e não tem contorno
dentro do sistema. O valor `ISENTO` é aceito em qualquer UF, como manda a legislação
para não contribuinte.

A UF vem do endereço padrão da parte, e `state` no ERPNext é texto livre — a resolução
aceita sigla e nome por extenso, com ou sem acento, e devolve "sem regra" quando não dá
para afirmar.

### Cálculo fiscal usa Decimal, não float

Todo valor monetário na aritmética de impostos é `Decimal`, e o arredondamento é
explícito e `ROUND_HALF_UP`. Dois motivos concretos:

- ponto flutuante acumula erro que não aparece no teste unitário e aparece na
  conferência do contador — uma nota tem dezenas de itens somados e rateados;
- o padrão do Python é `ROUND_HALF_EVEN` (arredondamento do banqueiro), que leva `0.125`
  para `0.12`. Documento fiscal espera `0.13`.

Alíquotas entram como **fração** (`0.18`, nunca `18`), e passar percentual levanta erro.
É uma classe inteira de bug — imposto dezoito vezes maior — eliminada na entrada.

O que o ERPNext já resolve não foi reimplementado: `included_in_print_rate` para imposto
por dentro, `On Previous Row Amount` para encadear base, `category: Valuation` para
decidir se o tributo compõe custo de estoque. O que falta ao núcleo, e está aqui, é a
**aritmética**: gross-up do ICMS, MVA ajustada e base dupla do DIFAL.

### Reforma tributária: já é obrigação vigente, não frente futura

**Desde 3 de agosto de 2026**, encerrado o período de tolerância do Ato Conjunto
RFB/CGIBS nº 1/2025, documento fiscal eletrônico **sem os campos de IBS e CBS é
rejeitado pelo autorizador** para empresas do regime regular. A Nota Técnica 2025.002
rege NF-e e NFC-e.

Para quem integra, isso não é um imposto a mais para calcular: é a diferença entre
emitir e não emitir. Uma localização escrita hoje que ignore IBS/CBS produz notas que
não existem.

Em 2026 a alíquota é de **teste**, 1% no total (0,9% CBS + 0,1% IBS), e a apuração é
*meramente informativa* — não há recolhimento, desde que cumpridas as obrigações
acessórias. Os campos, porém, são obrigatórios.

**Diferença estrutural que o código guarda:** o ICMS é calculado *por dentro* (integra a
própria base, daí o gross-up por `1 - alíquota`); IBS e CBS são *por fora* — não integram
a própria base nem a base um do outro. Há teste travando isso, porque "unificar" os dois
cálculos numa refatoração futura erraria os dois.

As alíquotas de 2027 em diante **não estão embutidas**, e pedi-las é erro explícito em
vez de chute: elas dependem de lei ainda por fixar. Só 2026 tem valor em norma.

Cronograma: 2027 a CBS fica plena e PIS/COFINS são extintos (IPI vai a zero, salvo Zona
Franca de Manaus, e entra o Imposto Seletivo); de 2029 a 2032 o IBS sobe enquanto ICMS e
ISS descem; em 2033 ICMS e ISS se extinguem. Por isso a aritmética de ICMS, IPI e
PIS/COFINS **continua necessária** — ela cobre o regime que ainda vigora e vai conviver
com o novo por seis anos.

### Os grupos do layout: dicionário, não string de XML

`fiscal/documento/ibs_cbs_xml.py` devolve **dicionários com os nomes oficiais das tags**,
não XML pronto. O motivo é a porta de transmissão: o ACBrLib consome INI, a ACBr API
consome JSON, e um provedor comercial pode querer outra coisa. Emitir XML aqui obrigaria
todo adaptador a desmontá-lo de volta — e a árvore de dicionários ainda se testa por
igualdade, o que uma string não permite sem parser.

Dois detalhes que derrubam nota inteira se errados:

- **O IBS é dual.** O XML exige `vIBSUF` e `vIBSMun` separados; tratá-lo como alíquota
  única é o erro que a rejeição 1026 acusa. Em 2026 a regra **UB18-10** exige `pIBSUF`
  igual a `0.1000` — toda a alíquota-teste está na parcela estadual.
- **No XML a alíquota é percentual, não fração.** Dentro do app ela é sempre fração
  (`0.001`); no documento vai `0.1000`, com quatro casas. A conversão acontece num lugar
  só, que é a única fronteira onde a regra "alíquota é fração" pode ser desfeita.

Os totais somam os **valores já arredondados de cada item**, nunca recalculam sobre a
base total: o validador confere o total contra a soma dos itens, e recalcular é como se
produz a rejeição de "total diverge da soma".

**Validado contra o XSD oficial.** Os nomes de tag foram conferidos no *Pacote de
Liberação 010e_v1.02 (NT 2025.002)*, baixado do Portal Nacional da NF-e —
`leiauteNFe_v4.00.xsd` e `DFeTiposBasicos_v1.00.xsd`. A estrutura do item bateu
exatamente. **Os totais não**, e a validação achou dois defeitos reais:

1. Fontes secundárias descreviam os subgrupos dos totais como `gIBSUFTot`/`gIBSMunTot`.
   Esses nomes **não existem** no layout: dentro de `gIBS` os subgrupos repetem `gIBSUF`
   e `gIBSMun`.
2. Em `gIBS` e `gCBS` todos os filhos são obrigatórios quando o grupo é informado, e
   faltavam `vDif`, `vDevTrib`, `vCredPres` e `vCredPresCondSus`. Eles saem zerados —
   diferimento, devolução de tributo e crédito presumido ainda não são calculados aqui,
   mas o layout exige o campo presente.

Documento emitido com a versão anterior seria rejeitado.

Para que isso não volte, `elementos_nfe.json` guarda os 598 nomes de elemento extraídos
dos dois XSD, e um teste confere que **toda tag emitida existe no layout**. Ele não
substitui validar o XML final contra o XSD antes de produção — mas pega barato a falha
que de fato acontece: nome digitado errado, que nenhum teste de aritmética encontraria.

### Rejeição barrada no salvamento, não na SEFAZ

CST e cClassTrib não são campos independentes: cada cClassTrib **pertence** a um CST, e
cada CST determina estritamente quais grupos do XML podem aparecer. A legenda da tabela
oficial é binária — 0 é **vedado**, 1 é **exigido** —, então informar um grupo a mais é
tão inválido quanto omitir um obrigatório. E dos 164 cClassTrib publicados, só **96**
valem para NF-e: usar um de NFS-e é rejeição garantida.

Nada disso é derivável do cálculo, e o custo de errar não é imposto errado — é documento
que não existe. A validação roda em `validate`, antes da apuração, e reporta **todos** os
problemas de uma vez, com mensagem que diz o que fazer.

Duas decisões que evitam falso positivo: tabela ainda não importada **não** acusa erro
(sem ela não há como afirmar invalidez, e travar impediria salvar em instalação nova), e
item sem classificação também não — a obrigatoriedade pertence à montagem do documento
fiscal, quando já se sabe que ele será transmitido.

Há teste rodando contra a **tabela oficial real**: todos os 96 pares válidos para NF-e
passam sem falso positivo.

### O documento fiscal: estado privado, transições guardadas

Um documento fiscal tem ciclo de vida real — rascunho → aguardando → autorizado →
cancelado, com desvios para rejeitado e denegado. Tratar isso como um campo `status` que
qualquer parte do código atribui produz nota "cancelada" que nunca foi autorizada, ou
"autorizada" sem protocolo. Aqui o estado é privado e só muda por método com guarda: de
fora se pede a ação, não se atribui o resultado.

**A costura crítica é o protocolo.** Se a SEFAZ autoriza e o protocolo não persiste,
existe nota válida no fisco e rascunho no sistema — divergência que só aparece na
fiscalização. Por isso `autorizar` **exige** protocolo, e `reconstituir` recusa carregar
um documento autorizado sem ele: falhar alto na leitura é melhor que propagar a mentira.

Regras confirmadas na fonte, não de memória:

- prazo de cancelamento de **24 horas** (evento 110111); fora dele a orientação é NF-e
  de estorno, e a mensagem de erro diz isso;
- recepção extemporânea até **480 horas** é faculdade de cada UF, em geral com
  penalidade — por isso exige pedido explícito em vez de acontecer sozinho;
- justificativa de **15 a 256 caracteres**, limites lidos do tipo `xJust` no XSD oficial;
- **denegado é final** — a SEFAZ registrou e negou por irregularidade do destinatário,
  a numeração fica queimada. Confundi-lo com rejeição permitiria reenvio indevido, então
  a denegação tem precedência na leitura da resposta.

O transporte fica atrás de uma **porta** (`TransporteFiscal`), com adaptadores trocáveis.
O agregado não sabe transmitir, e o adaptador não decide estado: devolve o que a SEFAZ
respondeu e quem transiciona é o agregado. Foi o acoplamento inverso que matou a
localização brasileira anterior, que congelou depurando a assinatura local.

### A apuração: a ordem é a regra

Cada módulo sabe calcular *o seu* imposto a partir de uma base. Nenhum sabe **qual**
base — e é aí que mora o erro, porque as bases dependem umas das outras. `apuracao.py`
escreve essa ordem num lugar só:

1. **IPI** sobre o valor da operação, e a decisão constitucional de entrar ou não na
   base do ICMS;
2. **ICMS** sobre essa base composta;
3. **PIS/COFINS** sobre a receita, com o ICMS destacado **fora** da base;
4. **IBS e CBS** por fora, com o Imposto Seletivo integrando a base deles.

Calcular os quatro isoladamente e somar produz números plausíveis e errados. O teste que
prova isso é o par revenda/consumidor final: mesma mercadoria, mesmos valores, e o
**total pago é idêntico** — porque o ICMS é por dentro — mas o ICMS sobe R$ 18,00 e o
PIS/COFINS cai em cascata, porque o ICMS maior reduz a base das contribuições.

O total do item soma apenas o que é **por fora**: IPI, IBS, CBS e Imposto Seletivo. Somar
o ICMS ali dobraria o imposto — é exatamente o que a distinção por dentro/por fora existe
para evitar.

### Retenção é outra categoria, e o que dá trabalho é a dispensa

ICMS, IPI e PIS/COFINS incidem *sobre a operação*. Retenção é o tomador descontando do
que vai pagar e recolhendo no lugar do prestador — o valor da nota não muda, muda quem
entrega o dinheiro. Reter a menos gera responsabilidade solidária do tomador.

O que efetivamente erra não é a multiplicação, é o **limite de dispensa**, porque os dois
principais funcionam de formas diferentes:

- **IRRF** dispensa pelo **imposto calculado** (não se retém se o apurado não supera
  R$ 10,00). Uma base grande com alíquota baixa pode ficar dispensada.
- **CSRF** (CSLL + PIS + COFINS, 4,65% somados) dispensa pela **base** do pagamento
  (R$ 215,05). Os dois pisos se correspondem: 215,05 × 4,65% = 10,00.

**INSS** não tem dispensa por valor, e a alíquota do **ISS** é obrigatória e sem padrão —
varia de 2% a 5% por município e item da lista de serviços, e assumir um valor seria
inventar tributo.

A CSRF é retida junta mas recolhida em códigos distintos; a decomposição faz o componente
maior absorver o centavo de arredondamento, com invariante testado de que a soma das
partes sempre bate com o total.

Os limites são **parâmetro com padrão explícito**, não constante: mudam por lei ordinária
e o ISS é municipal. Confirme os vigentes com a contabilidade antes de produção.

### Duas regras jurídicas que o código torna explícitas

Não são detalhes de cálculo; mudam o imposto devido e, quando erradas, produzem nota
aceita pela SEFAZ e autuação depois. Por isso cada uma é uma função com nome próprio,
não um `if` perdido no meio da conta.

**IPI na base do ICMS** (CF art. 155, §2º, XI). O IPI só fica **fora** da base do ICMS
na conjunção de duas condições: destinatário contribuinte **e** produto destinado a
industrialização ou comércio. Basta uma falhar — consumidor final, ou não contribuinte —
e ele entra. Numa nota de R$ 1.000 com IPI de 10% e ICMS de 18%, tratar os dois casos
igual erra o ICMS em R$ 18,00.

**Exclusão do ICMS da base de PIS/COFINS** (RE 574.706, a "tese do século"). O ICMS
destacado não compõe a base das contribuições. Sobre R$ 1.000 com ICMS de 18%, a base cai
de 1.000 para 820, e manter o ICMS ali recolhe R$ 6,57 a maior no regime cumulativo —
dinheiro que a empresa não deve. A exclusão é o padrão, mas continua sendo parâmetro,
porque a decisão tem modulação.

## Padrões de engenharia deste projeto

O que diferencia este app de uma localização fiscal típica não é o volume de código —
é a disciplina por trás de cada linha. Cinco regras não-negociáveis, aplicadas desde o
primeiro incremento:

1. **Nenhuma regra fiscal nasce de memória.** Alíquota, prazo, base de cálculo, layout
   de campo — tudo é conferido contra a norma (lei, IN RFB, Ajuste SINIEF, Convênio
   ICMS, Nota Técnica, XSD oficial) antes de virar código. Quando só existe fonte
   secundária, o nível de confiança é **declarado no próprio módulo**, nunca
   apresentado como se fosse primário — ver por exemplo `contabil/destda.py` ou
   `contabil/ecf_bloco_k.py`.
2. **Nunca supor por analogia entre documentos "da mesma família".** NF-e, CT-e e
   MDF-e parecem primos — e divergem sistematicamente em pontos que só a leitura
   direta do XSD de cada um revela (`modal` do CT-e é `01`-`06`, do MDF-e é `1`-`4`;
   o `tpEvento` de cancelamento é o mesmo número nos três documentos, mas o autorizador
   por UF do CT-e não bate com o da NF-e nem para as UFs que têm webservice próprio
   nos dois). Cada divergência real vira um achado documentado, não um bug descoberto
   depois em produção.
3. **Camada fiscal pura, sem uma linha de framework.** `fiscal/`, `contabil/` e
   `folha/` não importam `frappe` — são funções e dataclasses testáveis com
   `python -m unittest`, sem bench, sem site, sem banco. A regra é **executável**, não
   só documentada: `tests/test_arquitetura.py` percorre a árvore de imports e falha se
   algum módulo violar essa fronteira. `integracao/` é a única camada que fala com o
   Frappe, e é deliberadamente fina (limite de linhas também testado).
4. **Todo incremento vira documento, não só commit.** Cada peça de código tem um
   `.md` irmão em [`docs/`](docs/README.md) explicando o que foi verificado, contra
   qual fonte, e o que ficou de fora e por quê — inclusive quando a resposta é "isto
   não é um gap real" (ver `docs/gia-nao-e-gap.md`) ou "isto está fora do que dá para
   verificar com segurança agora" (ver `docs/versoes-frappe-erpnext.md`).
5. **Achado real > suposição conveniente.** Quando um teste ou uma investigação revela
   algo que contradiz a expectativa — um campo com nome diferente do esperado, uma
   tabela que não bate com a de um documento irmão, um bug no próprio teste em vez de
   no código — isso é registrado explicitamente como achado, nunca silenciado para a
   história ficar mais limpa.

### SOLID, Design by Contract e Elegant Objects — como lentes, não como dogma

Três referências de design orientam decisões concretas neste projeto, sempre a favor
do pragmatismo quando conflitam com o estilo idiomático do Frappe:

- **SOLID**: a inversão de dependência é a mais aplicada — `fiscal/` nunca depende de
  `integracao/` (regra 3 acima é uma instância disso), e onde a apuração fiscal precisa
  de uma tabela oficial (classificação, CFOP), ela depende de um `Protocol` (ex.
  `RepositorioClassificacao`), não da fonte concreta do dado. Responsabilidade única
  contra o "AppService" que cresceria para cobrir casos não relacionados — cada módulo
  de `contabil/`/`fiscal/` cobre um registro/documento, não um domínio inteiro.
- **Design by Contract** (pré-condição/pós-condição/invariante, não só "contrato" no
  sentido de interface): a correção real de `montar_ide` do CT-e — que não validava o
  modelo da chave antes de extrair o `cDV` — foi resolvida acrescentando uma
  pré-condição explícita (`CteInvalido` se a chave não for modelo `"57"`), não só
  corrigindo o valor. Pós-condição é o que `test_j050_e_i050_com_reg_trocado`/
  `test_k155_reaproveita_i155_com_indicadores_renomeados` verificam: não só "a função
  devolveu algo", mas que os valores batem exatamente com o que a função reaproveitada
  já calculou.
- **Elegant Objects** (Bugayenko) como lente de revisão, não regra a obedecer: as
  dataclasses `frozen=True` que dominam `fiscal/`/`contabil/` (`CorrecaoCte`,
  `SaldoInicial`, `MapeamentoReferencial`) são o pedaço do estilo que custa zero e só
  traz benefício — imutabilidade real, sem setter. Onde o projeto **diverge**
  conscientemente (métodos estáticos/funções soltas em vez de objeto com estado, ORM do
  Frappe como Active Record deliberado) isso é uma escolha registrada, não um
  descuido — ver a seção "Sete Virtudes de Bugayenko vs. arquitetura em camadas" nas
  diretrizes de engenharia deste time.

Estas três referências (SOLID, Design by Contract, Elegant Objects) e o modo como se
aplicam a este projeto são escolha própria do projetista de software **Moacir Bishop
Camata** (<moacirbishopcamata@gmail.com>).

### TDD e cobertura de teste — na costura, não só na unidade isolada

Nenhum incremento entra sem teste — não como formalidade depois do fato, mas como parte
do próprio ciclo de escrever o código: toda função de montagem nasce com o teste que
prova o formato certo antes de ser considerada pronta, e todo achado real (uma
divergência de nome de campo, um reuso que bate exatamente com o que outro módulo já
produz) vira um teste nomeado pelo achado, não um `assert` genérico — os nomes de teste
deste projeto são pesquisáveis por achado (`test_k155_reaproveita_i155_com_indicadores_
renomeados`, `test_cdv_e_o_digito_verificador_da_chave`).

Cobertura alta de linha não é o alvo em si — é consequência de mirar na **costura**, não
no componente isolado: um teste que só confere "a função devolveu sem erro" não pega uma
mutação que devia ter persistido e não persistiu, porque nunca releu por um caminho
independente para comparar. É por isso que `test_j050_e_i050_com_reg_trocado` compara o
resultado de duas funções calculadas por caminhos diferentes campo a campo, em vez de só
checar que cada uma "funciona" sozinha — e por isso a primeira rodada real de
`tests_bench/test_certificado_a1.py` contra bench de verdade achou dois bugs (`decode`
do `File`, estado que não voltava entre testes) que a suíte pura, sem banco real, não
tinha como pegar.

Mais de **1.670 testes** para o volume de código deste app é, também, o resultado
prático dessa disciplina: cada regra fiscal chega com o teste que a defende, e a
arquitetura em si (camada pura sem `frappe`, dependência numa direção só) é imposta por
teste, não só por convenção em prosa (`tests/test_arquitetura.py`).

## Documentação

O índice completo, sempre atualizado, está em [`docs/README.md`](docs/README.md) — mais
de cem documentos, um por incremento, cada um citando a fonte legal/técnica usada e
declarando o nível de confiança quando a fonte é secundária. Alguns pontos de partida:

| Documento | Assunto |
|---|---|
| [arquitetura.md](docs/arquitetura.md) | Camadas, resiliência, DbC, como testar sem bench |
| [montagem-da-nfe.md](docs/montagem-da-nfe.md) | Grupos `ide`, `emit`, `dest` e por que a chave é derivada |
| [cte-estado.md](docs/cte-estado.md) | Estado do CT-e — conteúdo, assinatura, orquestração, os onze eventos |
| [mdfe-estado.md](docs/mdfe-estado.md) | Estado do MDF-e — conteúdo, assinatura, orquestração, os sete eventos |
| [cte-mdfe-autorizadores.md](docs/cte-mdfe-autorizadores.md) | Autorizador por UF de CT-e (4 grupos) e MDF-e (nacional único) |
| [certificado-a1-configuracao.md](docs/certificado-a1-configuracao.md) | Certificado A1 e ambiente SEFAZ via `Company` |
| [ecf-estado.md](docs/ecf-estado.md) | Estado da ECF — Blocos 0/J/K implementados, L/M/N/P pendentes |
| [rh-estado-esocial.md](docs/rh-estado-esocial.md) | Estado do eSocial/folha — INSS, FGTS, IRRF |
| [ambiente-dev-bench.md](docs/ambiente-dev-bench.md) | Bench Frappe local (Windows 11 + WSL2 + Docker; nativo no Windows não funciona) |

## Decisões de projeto

**Não duplicar o que o ERPNext já tem.** Company, Customer e Supplier já possuem
`tax_id`; é ali que o CPF/CNPJ mora. Criar um campo `cnpj` paralelo produziria dois
lugares para o mesmo dado, divergindo em silêncio. Só se acrescenta o que o núcleo não
modela (Inscrição Estadual, indicador de IE, SUFRAMA, NCM, CEST, origem da mercadoria,
código IBGE do município).

**Regra fiscal separada do framework, e a separação é testada.** Nenhum módulo em
`fiscal/` importa `frappe` — são funções puras, testáveis sem bench, sem site e sem
banco. `integracao/` é a camada fina que persiste e traduz em `frappe.throw`.

A regra não fica só no README: `tests/test_arquitetura.py` percorre a árvore de imports
e falha se um módulo de `fiscal/` importar `frappe`, se a dependência entre as camadas
inverter, ou se um teste passar a exigir bench. Foi escrito depois de a auditoria
encontrar três módulos com `import frappe` dentro de `fiscal/` — regra de arquitetura
só escrita em prosa é aspiracional.

**Dependência invertida onde importa.** A validação de classificação precisa das tabelas
oficiais, mas não precisa saber que vieram de um Code List: depende de
`RepositorioClassificacao`, um `Protocol` de duas operações. É o que permite testar a
orquestração de um documento inteiro com um duplo de poucas linhas.

**Validação só em contexto brasileiro.** As validações consultam o país da Company; uma
instalação multiempresa com filial no exterior não passa a exigir CNPJ de fornecedor
estrangeiro.

## Instalação

Guia técnico completo (bench nativo e Docker) em
[`docs/instalacao.md`](docs/instalacao.md). Resumo:

```sh
bench get-app erpnext_brasil <url-ou-caminho-local-deste-repositorio>
bench --site <site> install-app erpnext_brasil
```

Os campos fiscais são recriados a cada `bench migrate` (`after_migrate`), de forma
idempotente — campos customizados podem se perder quando o ERPNext altera o DocType base.

### Com Docker

```sh
docker compose up -d
```

Ver [`docs/docker-compose.md`](docs/docker-compose.md) — caminho alternativo ao bench
WSL2 nativo (que é o ambiente de desenvolvimento efetivamente confirmado funcionando,
ver [`docs/ambiente-dev-bench.md`](docs/ambiente-dev-bench.md)); o compose ainda não foi
build-testado de ponta a ponta.

## Dependências

Nenhuma nova para o bench: `lxml`, `cryptography` e `requests` já acompanham o frappe.
Para rodar a suíte completa **fora** de um bench (como neste repositório), instale-as
no ambiente de desenvolvimento:

```sh
pip install lxml cryptography requests
```

Sem elas, os testes que exercitam assinatura e extração de resposta SOAP são pulados
(`unittest.skipUnless`) em vez de falhar — a suíte continua passando, só com menos
cobertura.

## Testes

As funções puras (`fiscal/`, `contabil/`, `folha/`) rodam sem infraestrutura nenhuma —
sem bench, sem site, sem banco:

```sh
python -m unittest discover -s erpnext_brasil/tests -t .
```

Mais de 1.670 testes, cobrindo desde CPF/CNPJ e as 27 regras de Inscrição Estadual até a
montagem completa de NF-e/CT-e/MDF-e (com os dezoito eventos dos dois últimos), ECD/ECF,
eSocial e cálculo de folha. `test_arquitetura.py` faz valer, de forma executável, que
nenhum desses módulos importa `frappe` — a regra não fica só em prosa.

`erpnext_brasil/tests_bench/` cobre, à parte, o que só é testável com um bench de
verdade (`integracao/`, que fala com `frappe.get_doc`/banco) — ver
[`ambiente-dev-bench.md`](docs/ambiente-dev-bench.md) para como rodar.

## Licença

MIT — ver [`license.txt`](license.txt).
