# Depreciação fiscal brasileira

As regras do RIR/2018 que um método linear genérico erra — e por que o ERPNext, sozinho,
não calcula a quota dedutível no Brasil.

## O gap

O ERPNext traz `Asset Register` e três métodos de depreciação: linear, saldo decrescente e
duplo decrescente. O Brasil usa **um**: quota sobre o **custo de aquisição**, com taxas por
espécie de bem.

Não é questão de escolher o método certo entre os três — é que a quota fiscal brasileira
tem cinco regras que nenhum dos três implementa.

## As cinco regras, com o artigo

Todas lidas no **RIR/2018 (Decreto nº 9.580/2018)**, baixado do Planalto e lido localmente.

### 1. A base é sempre o custo de aquisição, nunca o saldo residual

> Art. 319. A quota de depreciação dedutível na apuração do imposto sobre a renda será
> determinada por meio da aplicação da taxa anual de depreciação sobre **o custo de
> aquisição** do ativo.

A quota do último ano é **igual** à do primeiro. Não existe saldo decrescente na quota
fiscal brasileira, e é justamente o que o *Written Down Value* do ERPNext faz.

⚠️ O erro **não aparece no primeiro ano** — aparece do segundo em diante, quando o saldo já
caiu. É a asserção-âncora da suíte.

### 2. O mês conta inteiro; não há rateio por dias

> Art. 319, § 2º. A depreciação poderá ser apropriada em quotas mensais, **dispensado o
> ajuste da taxa para os bens postos em funcionamento ou baixados no curso do mês**.

Um bem que entrou em serviço no dia 28 deprecia o mês todo. Quem faz *pro rata die* deduz a
menos, e a diferença atravessa a vida inteira do bem.

O módulo nem oferece o parâmetro `dias` — e um teste confere isso, porque a assinatura é o
lugar onde a regra fica visível.

### 3. Bens usados usam o MAIOR dos dois prazos

> Art. 322. A taxa anual de depreciação de bens adquiridos usados será fixada tendo em
> vista **o maior** dos seguintes prazos: I - a metade da vida útil admissível para o bem
> adquirido novo; ou II - o restante da vida útil.

Parece que seria o menor, e não é. Escolher o menor deduz depressa demais — o lado que o
Fisco glosa.

A metade de vida útil ímpar é arredondada **para cima** (meia vida de 5 anos são 3, não 2).
A norma não trata do ímpar; arredondar para baixo deduziria mais rápido, na mesma direção
da glosa.

### 4. O acumulado nunca passa do custo

> Art. 317, § 3º. **Em qualquer hipótese**, o montante acumulado das quotas de depreciação
> não poderá ultrapassar o custo de aquisição do bem.

"Em qualquer hipótese" inclui a depreciação acelerada. É teto, não meta — e o excedente
**não é diferido**: simplesmente não existe.

É esse corte que faz a aceleração por turnos **encurtar a vida** do bem em vez de aumentar
a dedução total. Três turnos deduzem o mesmo valor em metade do tempo.

### 5. A depreciação começa quando o bem entra em serviço

> Art. 317, § 2º. A quota de depreciação é dedutível **a partir da época em que o bem é
> instalado, posto em serviço ou em condições de produzir**.

Não da compra, nem do pagamento. Para edificação, a partir da **conclusão e do início da
utilização** (art. 318, I) — e o valor da edificação tem de estar destacado do custo do
terreno, que não deprecia.

## Depreciação acelerada por turnos

> Art. 323. Em relação aos **bens móveis**, poderão ser adotados, em função do número de
> horas diárias de operação, os seguintes coeficientes: I - um turno de oito horas - um
> inteiro; II - dois turnos de oito horas - um inteiro e cinco décimos; e III - três turnos
> de oito horas - dois inteiros.

| Turnos de 8h | Coeficiente |
|---|---|
| 1 | 1,0 |
| 2 | 1,5 |
| 3 | 2,0 |

⚠️ **Só bens móveis** — o artigo diz isso com todas as letras. Acelerar uma edificação seria
acelerar o que a lei não acelera.

⚠️ **A lei enumera três casos**, e o módulo recusa qualquer outro número. Interpolar meio
turno ou um quarto turno seria inventar direito que ela não dá.

⚠️ E o coeficiente exige **prova do regime de turnos**. É direito de quem opera naquele
regime, não escolha livre — sem registro de produção e escala, a Receita glosa.

## Bens que não depreciam

Art. 318, parágrafo único — as quatro vedações:

1. **Terrenos**, exceto melhoramentos e construções;
2. prédios ou construções **não alugados nem usados** na produção, ou destinados à revenda;
3. bens que **normalmente aumentam de valor** com o tempo — obras de arte, antiguidades;
4. bens para os quais seja registrada **quota de exaustão**.

O módulo documenta a lista, mas **não classifica**: dizer que um imóvel é terreno é do
usuário.

## As taxas

`TAXAS_ANUAIS` traz um **núcleo** do Anexo III da IN RFB nº 1.700/2017:

| Espécie | Taxa anual | Vida útil |
|---|---|---|
| Edificações | 4% | 25 anos |
| Instalações | 10% | 10 anos |
| Móveis e utensílios | 10% | 10 anos |
| Máquinas e equipamentos | 10% | 10 anos |
| Computadores e periféricos | 20% | 5 anos |
| Veículos de passageiros | 20% | 5 anos |
| Veículos de carga | 25% | 4 anos |
| Tratores, motocicletas | 25% | 4 anos |
| Ferramentas | 20% | 5 anos |

⚠️ **Núcleo, não a tabela.** O Anexo III tem centenas de linhas classificadas por NCM, e o
art. 320, § 1º assegura ao contribuinte computar quota diferente desde que **prove a
adequação**. Uma tabela fechada aqui seria falsa mesmo se completa — quem tem o NCM do bem
deve usar a taxa que o Anexo III lhe atribui.

Um teste confere que taxa e vida útil são coerentes entre si (100 ÷ anos = taxa): uma linha
em que as duas discordem é erro de digitação que passaria despercebido, porque a taxa seria
usada e a vida útil ignorada.

## Uma regra que o módulo deliberadamente não implementa

> Art. 320, § 3º. Quando o registro do imobilizado for feito por **conjunto** de instalação
> ou equipamentos, sem especificação suficiente [...], ficará obrigado a utilizar as taxas
> aplicáveis aos bens de **maior vida útil** que integrem o conjunto.

Está registrada aqui porque é fácil errar na direção contrária (usar a média, ou a do bem
principal), mas depende de saber o que há dentro do conjunto — informação que o módulo não
recebe.

## A costura com o `Asset`, sem inventar campo nenhum

O ERPNext já tem a estrutura certa, e ela é melhor do que qualquer campo customizado que se
criasse:

| Estrutura nativa | O que resolve |
|---|---|
| **`Asset Finance Book`** (tabela filha) | vários livros por ativo — a separação contábil × fiscal que o art. 321 pressupõe |
| **`Asset Shift Factor`** (`shift_name` + `shift_factor`) | os coeficientes do art. 323 |
| **`available_for_use_date`** | literalmente o *"posto em serviço"* do art. 317, § 2º |

Criar um `br_taxa_depreciacao` ao lado do `rate_of_depreciation` nativo produziria **duas
verdades sobre a mesma taxa** — o mesmo erro que já se evitou no `Bank Account` com o
número da conta.

`integracao/depreciacao_ativo.py` faz três coisas:

1. **`instalar_livro_fiscal` / `instalar_turnos`** — criam o `Finance Book` "Fiscal
   (Brasil)" e os três `Asset Shift Factor` do art. 323, no `after_install` e no
   `after_migrate`. Idempotentes, e **não sobrescrevem** o que já existe: um fator ajustado
   por quem administra o site é decisão dele, não ruído a corrigir a cada `migrate`.
2. **`aplicar_taxa_fiscal(asset, especie)`** — preenche a linha do livro fiscal a partir do
   núcleo do Anexo III: método linear, taxa, parcelas mensais, e início em
   `available_for_use_date` — **não** em `purchase_date`, porque comprar não é usar e a
   diferença é dedução tomada antes da hora.
3. **`validar_livro_fiscal`** — ligado no `validate` do `Asset`.

### ⚠️ Os dois padrões do ERPNext que a lei não admite

A validação recusa exatamente dois, e ambos passam despercebidos porque **produzem números
plausíveis**:

- **`depreciation_method` ≠ "Straight Line".** *Written Down Value* e *Double Declining
  Balance* aplicam a taxa sobre o saldo residual. **A primeira quota é igual nos dois** — a
  divergência só aparece do segundo período em diante.
- **`daily_prorata_based` marcado.** Ratear por dias contraria o art. 319, § 2º, e deduz a
  menos pela vida inteira do bem.

Nenhum dos dois levanta erro no ERPNext: são configurações válidas para outros países. Por
isso a guarda **falha alto** em vez de avisar — um aviso amarelo sobre método de
depreciação seria clicado sem ler, e o erro que ele evita não aparece no primeiro período.

A validação só olha a linha do livro fiscal: os demais livros são do contador, e o método
contábil pode legitimamente ser outro.

## O que falta
- **Exercitar num bench real.** A camada Frappe tem teste de costura estática, não de
  execução.
- **O LALUR.** O art. 321 permite **excluir** do lucro líquido a diferença quando a
  depreciação contábil é menor que a fiscal, e manda **adicioná-la** de volta quando o
  acumulado atinge o teto. Isso é controle de Parte B — domínio que o projeto ainda não tem
  (ver [ecf-blocos-l-m-n.md](ecf-blocos-l-m-n.md)).
- **Depreciação acelerada incentivada** (art. 324): benefício por indústria e prazo certo,
  com exclusão direta no Lalur.

## Fontes

- **RIR/2018 — Decreto nº 9.580/2018**, arts. 317 a 324, `planalto.gov.br`, baixado e lido
  localmente.
- **Lei nº 4.506/1964, art. 57** — a base legal que o RIR consolida (citada artigo a artigo
  no próprio RIR).
- **Lei nº 3.470/1958, art. 69** — os coeficientes de turno, citada no art. 323 do RIR.
- **IN RFB nº 1.700/2017, Anexo III** — taxas anuais e prazos de vida útil.
