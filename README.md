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

Primeiro incremento entregue: **cadastros e campos fiscais**, com validação.

| Área | Situação |
|---|---|
| Validação de CPF/CNPJ (inclusive **CNPJ alfanumérico**) | pronto |
| Campos fiscais em Company, Customer, Supplier, Address, Item | pronto |
| Validação de NCM e código IBGE de município | pronto |
| Inscrição Estadual — as 27 UFs | pronto, com a ressalva abaixo |
| Tabelas de código normativas (CST, CSOSN, origem) | pronto, embarcadas |
| Tabelas voláteis (NCM, CFOP, LC 116) | importador versionado |
| Aritmética de ICMS (por dentro, redução, ST/MVA, DIFAL) | pronto |
| IPI, e a regra do IPI na base do ICMS | pronto |
| PIS/COFINS, com exclusão do ICMS da base | pronto |
| **IBS e CBS** (reforma tributária) | pronto — ver abaixo |
| Grupos de IBS/CBS do layout da NF-e (grupo UB e W03) | pronto — validado no XSD |
| CST do IBS/CBS e cClassTrib (leitor XLSX + importador) | pronto |
| Validação de compatibilidade CST × cClassTrib | pronto |
| Apuração do item (ordem de composição das bases) | pronto |
| Ligação da apuração às linhas de imposto do ERPNext | pronto |
| Retenções (IRRF, CSRF, INSS, ISS) | pronto |
| Chave de acesso (44 posições, DV, CNPJ alfanumérico) | pronto |
| Montagem da NF-e (`ide`, `emit`, `dest`, `infNFe`) | pronto |
| Serialização dict → XML (forma canônica) | pronto |
| Assinatura XMLDSig — estrutura e assinador local | pronto |
| Grupos `prod` e `ICMSTot` (totais do documento) | pronto |
| Grupo `imposto` do item (ICMS00/20/40/41/60, SN, IPI, PIS, COFINS, ISSQN + IBS/CBS) | pronto — escopo declarado |
| Grupos `transp` e `pag` | pronto — escopo declarado |
| Grupo `infAdic` | pronto |
| `montar_nfe`/`assinar_nfe` — raiz, namespace e assinatura ligadas | pronto |
| **Montagem da NF-e — completa do lado da estrutura do documento** | |
| Tabela de autorizadores por UF (webservices da SEFAZ) | pronto — produção e homologação nos 12 grupos |
| Envelope SOAP 1.2 (sem `nfeCabecMsg`, obsoleto desde 2017) | pronto |
| Interpretação da resposta — os dois `cStat` (lote × nota) | pronto |
| Adaptador de transporte — `transmitir` (com *polling*) e `consultar` | pronto |
| Cancelamento (`cancelar`, evento 110111) | pronto — XSD do evento confirmado à parte do leiaute principal |
| Carta de correção (`corrigir`, evento 110110) | pronto — mesma via, `infEvento` idêntico, `detEvento` próprio |
| Rastreabilidade de lote (grupo `rastro`) | pronto |
| Ciclo de vida do documento fiscal e porta de transmissão | pronto |
| Inutilização de faixa de numeração (`inutilizar`) | pronto — CNPJ alfanumérico recusado deliberadamente, ver `docs/inutilizacao-nfe.md` |
| Carta de correção (CC-e), inutilização e cancelamento assinados digitalmente | pronto — bug de assinatura ausente corrigido |
| **NFC-e (modelo 65)** — QR Code (`infNFeSupl`, emissão on-line) | pronto — contingência offline e tabela de URL por UF ainda não, ver `docs/nfce-qrcode.md` |
| Outros documentos fiscais (CT-e, MDF-e, NFS-e) | não iniciado |
| Obrigações acessórias (SPED, EFD-Reinf) | não iniciado |

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

## Documentação

Referências detalhadas por assunto estão em [`docs/`](docs/README.md):

| Documento | Assunto |
|---|---|
| [arquitetura.md](docs/arquitetura.md) | Camadas, resiliência, DbC, como testar sem bench |
| [chave-de-acesso.md](docs/chave-de-acesso.md) | Layout das 44 posições e o impacto do CNPJ alfanumérico |
| [montagem-da-nfe.md](docs/montagem-da-nfe.md) | Grupos `ide`, `emit`, `dest` e por que a chave é derivada |
| [reforma-tributaria.md](docs/reforma-tributaria.md) | IBS, CBS e IS: cronograma e obrigatoriedade vigente |
| [transmissao-documento-fiscal.md](docs/transmissao-documento-fiscal.md) | ACBrLib × ACBr API e a fronteira de licença |
| [transporte-nativo-sefaz.md](docs/transporte-nativo-sefaz.md) | SOAP nativo, autorizadores por UF, cancelamento e CC-e |
| [inutilizacao-nfe.md](docs/inutilizacao-nfe.md) | Inutilização de faixa de numeração — por que é operação à parte |
| [nfce-qrcode.md](docs/nfce-qrcode.md) | QR Code da NFC-e: algoritmo do hash, `infNFeSupl`, o que falta |
| [ambiente-dev-bench.md](docs/ambiente-dev-bench.md) | Bench Frappe local (Windows 11 + WSL2 + Docker) |

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

```sh
bench get-app <url-deste-repositorio>
bench --site <site> install-app erpnext_brasil
```

Os campos fiscais são recriados a cada `bench migrate` (`after_migrate`), de forma
idempotente — campos customizados podem se perder quando o ERPNext altera o DocType base.

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

As funções puras rodam sem infraestrutura nenhuma:

```sh
python -m unittest discover -s erpnext_brasil/tests -t .
```

São 36 testes cobrindo CPF/CNPJ, as 27 regras de Inscrição Estadual e a resolução de UF.

## Licença

MIT.
