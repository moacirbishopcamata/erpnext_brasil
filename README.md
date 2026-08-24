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
| Grupos de IBS/CBS do layout da NF-e (grupo UB e W03) | pronto — validar contra o XSD |
| Ligação do cálculo às linhas de imposto do ERPNext | não iniciado |
| Retenções (IRRF, CSLL, INSS, ISS) | não iniciado |
| Documento fiscal / NF-e | não iniciado |
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

Ressalva: os nomes de tag foram conferidos em duas fontes independentes que descrevem a
NT 2025.002, **não no XSD oficial**. Nome errado não gera imposto errado — gera documento
rejeitado. Validar contra o XSD antes de emitir em produção.

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

## Decisões de projeto

**Não duplicar o que o ERPNext já tem.** Company, Customer e Supplier já possuem
`tax_id`; é ali que o CPF/CNPJ mora. Criar um campo `cnpj` paralelo produziria dois
lugares para o mesmo dado, divergindo em silêncio. Só se acrescenta o que o núcleo não
modela (Inscrição Estadual, indicador de IE, SUFRAMA, NCM, CEST, origem da mercadoria,
código IBGE do município).

**Regra fiscal separada do framework.** `fiscal/validators.py` não importa `frappe`:
são funções puras, testáveis sem bench, sem site e sem banco. `fiscal/party.py` é a
camada fina que traduz o resultado em `frappe.throw`.

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

## Testes

As funções puras rodam sem infraestrutura nenhuma:

```sh
python -m unittest discover -s erpnext_brasil/tests -t .
```

São 36 testes cobrindo CPF/CNPJ, as 27 regras de Inscrição Estadual e a resolução de UF.

## Licença

MIT.
